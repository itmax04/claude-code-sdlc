#!/usr/bin/env python3
"""PreToolUse(Bash) guard for projects driven by the SDLC plugin.

Active only inside a project that has .sdlc/ (so other projects are untouched).
Denies destructive Git, pushes to protected branches, merges that the project
policy does not allow, owner-only SDLC records, access to protected paths and
project-specific forbidden commands (config.deny_commands).
"""
from __future__ import annotations

import fnmatch
import re
import shlex
import subprocess
import sys

from hooklib import config, deny, read_input, sdlc_root

SEGMENT_SPLIT = re.compile(r"\|\||&&|;|\||\n|\$\(|`")


def segments(command: str) -> list:
    out = []
    for part in SEGMENT_SPLIT.split(command):
        part = part.strip().strip(")")
        if not part:
            continue
        try:
            toks = shlex.split(part, posix=True)
        except ValueError:
            toks = part.split()
        # drop leading env assignments and common wrappers
        while toks and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", toks[0]) or toks[0] in ("sudo", "command", "env", "time", "nohup")):
            toks = toks[1:]
        if toks:
            out.append(toks)
    return out


def current_branch(root) -> str:
    try:
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def git_sub(toks: list):
    """Return (subcommand, args) for a git invocation, skipping -C/-c options."""
    if not toks or os_base(toks[0]) != "git":
        return None, []
    i = 1
    while i < len(toks) and toks[i].startswith("-"):
        i += 2 if toks[i] in ("-C", "-c", "--git-dir", "--work-tree") else 1
    if i >= len(toks):
        return None, []
    return toks[i], toks[i + 1:]


def os_base(tok: str) -> str:
    return tok.rsplit("/", 1)[-1]


def check_git(toks: list, cfg: dict, root) -> None:
    sub, args = git_sub(toks)
    if sub is None:
        return
    protected = cfg.get("protected_branches") or ["main", "master"]
    if sub == "push":
        flags = [a for a in args if a.startswith("-")]
        if any(f in ("-f", "--force", "--force-with-lease", "--force-if-includes") or f.startswith("--force")
               for f in flags):
            deny("SDLC guard: force-push is forbidden (history must never be rewritten).")
        if any(f in ("--mirror", "--all", "--delete", "-d", "--prune") for f in flags):
            deny("SDLC guard: mirror/all/delete/prune pushes are forbidden.")
        refs = [a for a in args if not a.startswith("-")][1:]  # skip remote
        for ref in refs:
            if ref.startswith("+"):
                deny("SDLC guard: forced refspec (+) is forbidden.")
            if ref.startswith(":"):
                deny("SDLC guard: deleting remote branches is forbidden.")
            target = ref.split(":")[-1].replace("refs/heads/", "")
            if target in protected or (target == "HEAD" and current_branch(root) in protected):
                deny(f"SDLC guard: pushing to protected branch '{target}' is forbidden — push a feature branch and open a PR.")
        if not refs and current_branch(root) in protected:
            deny(f"SDLC guard: you are on protected branch '{current_branch(root)}'; switch to a feature branch before pushing.")
    elif sub == "reset" and "--hard" in args:
        deny("SDLC guard: `git reset --hard` can destroy work; use `git revert`, `git stash` or a new branch.")
    elif sub == "clean" and any(re.match(r"^-[a-zA-Z]*f", a) or a == "--force" for a in args):
        deny("SDLC guard: `git clean -f` deletes untracked files; remove specific files instead.")
    elif sub == "branch" and any(a in ("-D", "--delete", "-d") for a in args):
        deny("SDLC guard: deleting branches is forbidden for the agent (the owner cleans up).")
    elif sub in ("filter-branch", "filter-repo", "replace"):
        deny("SDLC guard: history rewriting is forbidden.")
    elif sub == "checkout" and ("--" in args and "." in args or "-f" in args):
        deny("SDLC guard: discarding working-tree changes is forbidden; commit or stash first.")
    elif sub == "restore" and "." in args and "--staged" not in args:
        deny("SDLC guard: `git restore .` discards changes; restore specific files you changed yourself.")
    elif sub == "rebase" and any(b in args for b in protected) and "--onto" in args:
        deny("SDLC guard: rebasing protected branches is forbidden.")


def check_gh(toks: list, cfg: dict) -> None:
    if not toks or os_base(toks[0]) != "gh" or len(toks) < 3:
        return
    area, action = toks[1], toks[2]
    if area == "pr" and action == "merge":
        if "--admin" in toks:
            deny("SDLC guard: `--admin` bypasses branch protection — forbidden.")
        if cfg.get("merge_policy", "owner") != "agent":
            deny("SDLC guard: in this project the owner merges PRs (config.merge_policy = owner). "
                 "Mark the PR ready and report it.")
    if area == "repo" and action in ("delete", "archive", "rename", "edit"):
        deny(f"SDLC guard: `gh repo {action}` changes the repository itself — owner only.")
    if area in ("secret", "auth", "ssh-key", "gpg-key") or (area == "variable" and action in ("set", "delete")):
        deny(f"SDLC guard: `gh {area}` touches credentials/settings — owner only.")
    if area == "api" and any(t.upper() in ("-XDELETE", "DELETE") for t in toks) and "-X" in " ".join(toks):
        deny("SDLC guard: DELETE calls through `gh api` are forbidden.")


def check_rm(toks: list) -> None:
    if not toks or os_base(toks[0]) != "rm":
        return
    flags = "".join(t.lstrip("-") for t in toks[1:] if t.startswith("-"))
    if "r" in flags.lower() and "f" in flags:
        targets = [t for t in toks[1:] if not t.startswith("-")]
        for t in targets:
            if t in ("/", "~", "$HOME", "..", ".", "*", "./*") or t.rstrip("/").endswith(".git") \
                    or t.startswith("~/") and t.count("/") <= 1 or t.startswith("/") and t.count("/") <= 2:
                deny(f"SDLC guard: `rm -rf {t}` is too broad.")


def check_owner_only(command: str) -> None:
    if re.search(r"sdlc\.py[\"']?\s+(--project\s+\S+\s+)?decide-raw\b", command):
        deny("SDLC guard: owner decisions are recorded only by the owner via /sdlc:decide.")
    if re.search(r"\.sdlc/state\.json", command) and "sdlc.py" not in command and \
            re.search(r"(>|\btee\b|\bsed\s+-i|\bperl\s+-\w*i|\btruncate\b|\bmv\s|\bcp\s|\brm\s|open\()", command):
        deny("SDLC guard: change .sdlc/state.json only through sdlc.py (set/advance/gate).")


def check_protected_paths(toks_list: list, cfg: dict) -> None:
    pats = cfg.get("protected_paths") or []
    if not pats:
        return
    for toks in toks_list:
        for t in toks[1:]:
            path = t[2:] if t.startswith("./") else t
            for pat in pats:
                base = pat.rstrip("*").rstrip("/")
                if fnmatch.fnmatch(path, pat) or (base and (path == base or path.startswith(base + "/"))):
                    deny(f"SDLC guard: '{t}' is a protected path ({pat}) — not readable or writable by the agent.")


def in_window(cfg: dict) -> bool:
    """True when the current local time of config.night_window is inside [start, end)."""
    win = cfg.get("night_window") or {}
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo(win.get("tz", "UTC")))
        sh, sm = (int(x) for x in win.get("start", "23:00").split(":"))
        eh, em = (int(x) for x in win.get("end", "08:00").split(":"))
    except Exception:
        return True  # cannot evaluate → do not block on a guard bug
    cur, start, end = now.hour * 60 + now.minute, sh * 60 + sm, eh * 60 + em
    return start <= cur < end if start < end else (cur >= start or cur < end)


def check_night_only(command: str, cfg: dict) -> None:
    for pat in cfg.get("night_only_commands") or []:
        try:
            hit = re.search(pat, command)
        except re.error:
            continue
        if hit and not in_window(cfg):
            win = cfg.get("night_window") or {}
            deny(f"SDLC guard: '{hit.group(0)}' is a bulk/quota-heavy command allowed only between "
                 f"{win.get('start', '23:00')} and {win.get('end', '08:00')} {win.get('tz', 'UTC')}. "
                 "Schedule it for the night window or run a single request instead.")


def main() -> None:
    data = read_input()
    if data.get("tool_name") != "Bash":
        return
    root = sdlc_root(data)
    if root is None:
        return  # not an SDLC project: stay out of the way
    cfg = config(data)
    command = (data.get("tool_input") or {}).get("command", "") or ""
    check_owner_only(command)
    check_night_only(command, cfg)
    for pat in cfg.get("deny_commands") or []:
        try:
            if re.search(pat, command):
                deny(f"SDLC guard: command matches a forbidden pattern of this project ({pat}). "
                     "This is an owner-only action — give the owner exact steps instead.")
        except re.error:
            continue
    segs = segments(command)
    for toks in segs:
        check_git(toks, cfg, root)
        check_gh(toks, cfg)
        check_rm(toks)
    check_protected_paths(segs, cfg)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # fail open on guard bugs, but tell the user
        print(f"SDLC guard error (ignored): {exc}", file=sys.stderr)
        sys.exit(0)
