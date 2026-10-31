#!/usr/bin/env python3
"""SDLC state manager for the Claude Code SDLC plugin.

Single source of run state: <project>/.sdlc/state.json (+ config.json).
Standard library only, Python 3.9+. Every command is idempotent and prints
a short human-readable result; `--json` prints machine-readable output.

Commands:
  init      create .sdlc/ from a profile (auto-detected or --profile)
  status    show the current change, phase, gates and next action
  context   compact status for the SessionStart hook
  validate  check config.json and state.json
  set       update phase/status/next/risk/change/title/stage/mode
  advance   move to the next phase (checks artifacts and blocking gates)
  gate      add | decide | list owner/AI gates
  decide-raw  record an owner answer typed via /sdlc:decide (owner path only)
  activate / deactivate   start or stop the auto-run for a session
  log       append a history note
  new-change  start a new change (intent phase) and push the old one to history
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PHASES = ["survey", "intent", "spec", "plan", "build", "verify", "review",
          "release", "maintain", "incident"]
TERMINAL = "done"
STATUSES = ["in_progress", "waiting_owner", "blocked", "done"]
RISKS = ["R0", "R1", "R2", "R3", "R4"]
MODES = ["auto", "step"]
GATE_STATUSES = ["pending", "accepted", "rejected", "answered", "waived"]
HISTORY_CAP = 40

# Artifacts that must exist (in the change folder) before leaving a phase.
# Alternatives are separated by "|"; "@sdlc/" means the project's .sdlc folder.
EXIT_ARTIFACTS = {
    "survey": ["@sdlc/survey.md"],
    "intent": ["intent.md|feature.md"],
    "spec": ["spec.md|feature.md"],
    "plan": ["plan.md|feature.md"],
    "build": ["handoff.md"],
    "verify": ["report.md"],
    "review": ["review.md|report.md"],
    "release": ["release.md"],
    "maintain": [],
    "incident": ["incident.md"],
}

PLUGIN_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------- helpers
def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def die(msg: str, code: int = 1) -> None:
    print(f"sdlc: {msg}", file=sys.stderr)
    sys.exit(code)


def project_root(explicit: str | None = None) -> Path:
    base = Path(explicit or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    try:
        out = subprocess.run(["git", "-C", str(base), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return base


def sdlc_dir(root: Path) -> Path:
    return root / ".sdlc"


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die(f"cannot read {path}: {exc}")


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_state(root: Path) -> dict:
    st = load_json(sdlc_dir(root) / "state.json")
    if st is None:
        die("SDLC is not initialized here: run `sdlc.py init` (or /sdlc:init)", 2)
    return st


def load_config(root: Path) -> dict:
    return load_json(sdlc_dir(root) / "config.json", {}) or {}


def save_state(root: Path, st: dict, event: str | None = None) -> None:
    st["updated"] = now()
    if event:
        hist = st.setdefault("history", [])
        hist.append({"at": st["updated"], "phase": st.get("phase"), "event": event})
        del hist[:-HISTORY_CAP]
    save_json(sdlc_dir(root) / "state.json", st)


def git(root: Path, *args: str) -> str:
    try:
        out = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                             text=True, timeout=15)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def change_dir(root: Path, cfg: dict, st: dict) -> Path:
    return root / cfg.get("changes_dir", "docs/changes") / str(st.get("change", "CHANGE-01"))


def pending_gates(st: dict, phase: str | None = None) -> list:
    out = []
    for g in st.get("gates", []):
        if g.get("status") != "pending":
            continue
        blocks = g.get("blocks") or ["*"]
        if phase is None or "*" in blocks or phase in blocks:
            out.append(g)
    return out


def find_gate(st: dict, gate_id: str) -> dict | None:
    for g in st.get("gates", []):
        if g.get("id", "").lower() == gate_id.lower():
            return g
    return None


# ---------------------------------------------------------------- phases
def default_next(st: dict, cfg: dict) -> str:
    phase = st.get("phase", "survey")
    risk = st.get("risk", cfg.get("risk_default", "R1"))
    release_enabled = (cfg.get("release") or {}).get("enabled", True)
    if phase == "incident":
        return "intent"
    if phase == TERMINAL:
        return TERMINAL
    if phase == "maintain":
        return TERMINAL
    order = PHASES[:9]  # without incident
    idx = order.index(phase) if phase in order else 0
    nxt = order[idx + 1] if idx + 1 < len(order) else TERMINAL
    # R0: one feature.md covers intent+spec+plan.
    if risk == "R0" and phase == "intent":
        nxt = "build"
    if nxt == "release" and not release_enabled:
        nxt = "maintain"
    if risk == "R0" and nxt == "maintain":
        nxt = TERMINAL
    return nxt


def missing_artifacts(root: Path, cfg: dict, st: dict, phase: str) -> list:
    missing = []
    cdir = change_dir(root, cfg, st)
    release_enabled = (cfg.get("release") or {}).get("enabled", True)
    for spec in EXIT_ARTIFACTS.get(phase, []):
        if phase == "release" and not release_enabled:
            continue
        options = spec.split("|")
        found = False
        for opt in options:
            path = sdlc_dir(root) / opt[len("@sdlc/"):] if opt.startswith("@sdlc/") else cdir / opt
            if path.exists() and path.stat().st_size > 0:
                found = True
                break
        if not found:
            missing.append(" or ".join(options))
    return missing


# ---------------------------------------------------------------- profiles
def detect_profile(root: Path) -> str:
    remote = git(root, "remote", "get-url", "origin")
    if re.search(r"github\.com[:/]itmax04/lingo(\.git)?$", remote):
        return "lingo"
    return "generic"


def detect_commands(root: Path) -> dict:
    cmds: dict = {}
    if (root / "package.json").exists():
        try:
            scripts = json.loads((root / "package.json").read_text()).get("scripts", {})
        except (OSError, json.JSONDecodeError):
            scripts = {}
        for key in ("build", "test", "lint", "typecheck"):
            if key in scripts:
                cmds[key] = f"npm run {key}" if key != "test" else "npm test"
    if (root / "Package.swift").exists():
        cmds.setdefault("build", "swift build")
        cmds.setdefault("test", "swift test")
    if (root / "pyproject.toml").exists() or (root / "pytest.ini").exists():
        cmds.setdefault("test", "python3 -m pytest -q")
    if (root / "Cargo.toml").exists():
        cmds.setdefault("build", "cargo build")
        cmds.setdefault("test", "cargo test")
    if (root / "go.mod").exists():
        cmds.setdefault("build", "go build ./...")
        cmds.setdefault("test", "go test ./...")
    return cmds


def cmd_init(a) -> None:
    root = project_root(a.project)
    sd = sdlc_dir(root)
    if (sd / "state.json").exists() and not a.force:
        print(f"SDLC already initialized in {root} (use --force to re-create from a profile)")
        return
    profile = a.profile if a.profile and a.profile != "auto" else detect_profile(root)
    pdir = PLUGIN_ROOT / "profiles" / profile
    if not pdir.is_dir():
        die(f"unknown profile '{profile}'; available: "
            + ", ".join(sorted(p.name for p in (PLUGIN_ROOT / "profiles").iterdir() if p.is_dir())))
    sd.mkdir(parents=True, exist_ok=True)
    for name in ("config.json", "PROJECT.md", "state.json"):
        src = pdir / name
        if src.exists():
            shutil.copyfile(src, sd / name)
    cfg = load_json(sd / "config.json", {}) or {}
    if profile == "generic":
        detected = detect_commands(root)
        cfg.setdefault("commands", {}).update({k: v for k, v in detected.items()
                                                if not cfg["commands"].get(k)})
        cfg["project"] = cfg.get("project") or root.name
        save_json(sd / "config.json", cfg)
    st = load_json(sd / "state.json", {}) or {}
    st.setdefault("version", 1)
    st["project"] = cfg.get("project", root.name)
    st["profile"] = profile
    st.setdefault("run", {"active": False, "session": None, "mode": "auto", "continuations": 0})
    st.setdefault("history", [])
    save_state(root, st, f"initialized from profile '{profile}'")
    (sd / ".gitignore").write_text("runtime/\n*.tmp\n", encoding="utf-8")
    print(f"SDLC initialized in {sd} (profile: {profile})")
    print_status(root, st, cfg)


# ---------------------------------------------------------------- status
def summary_lines(root: Path, st: dict, cfg: dict) -> list:
    lines = [
        f"Project: {st.get('project', root.name)}  ·  profile: {st.get('profile', '?')}",
        f"Change: {st.get('change', '-')} — {st.get('title', '')}".rstrip(" —"),
    ]
    if st.get("stage"):
        lines.append(f"Product stage: {st['stage']}")
    lines.append(f"Phase: {st.get('phase')}  ·  status: {st.get('status')}  ·  risk: {st.get('risk')}"
                 f"  ·  mode: {st.get('mode', 'auto')}")
    run = st.get("run") or {}
    lines.append(f"Auto-run: {'active' if run.get('active') else 'off'}")
    pend = pending_gates(st)
    if pend:
        lines.append("Pending gates:")
        for g in pend:
            owner = "owner" if g.get("owner_only", True) else "owner/AI"
            rec = f" · recommended: {g['recommended']}" if g.get("recommended") else ""
            lines.append(f"  - {g['id']} ({owner}, blocks {','.join(g.get('blocks') or ['*'])}): "
                         f"{g.get('title', '')} — needs: {g.get('need', '')}{rec}")
    if st.get("next"):
        lines.append(f"Next: {st['next']}")
    q = st.get("queue") or []
    if q:
        lines.append("Queue: " + " → ".join(q[:6]) + (" → …" if len(q) > 6 else ""))
    return lines


def print_status(root: Path, st: dict, cfg: dict) -> None:
    print("\n".join(summary_lines(root, st, cfg)))


def cmd_status(a) -> None:
    root = project_root(a.project)
    if not (sdlc_dir(root) / "state.json").exists():
        print("SDLC: not initialized in this project. Run /sdlc:run (auto-init) or /sdlc:init.")
        return
    st, cfg = load_state(root), load_config(root)
    if a.json:
        print(json.dumps({"state": st, "pending": pending_gates(st)}, ensure_ascii=False, indent=2))
    else:
        print_status(root, st, cfg)


def cmd_context(a) -> None:
    root = project_root(a.project)
    if not (sdlc_dir(root) / "state.json").exists():
        return
    st, cfg = load_state(root), load_config(root)
    lines = ["[SDLC] This project is driven by the Claude Code SDLC plugin (/sdlc:run)."]
    lines += summary_lines(root, st, cfg)
    run = st.get("run") or {}
    if run.get("active") and st.get("status") == "in_progress":
        lines.append("The auto-run is active: continue it with /sdlc:run (state in .sdlc/state.json).")
    lines.append(f"Talk to the owner in {cfg.get('owner_language', 'the owner language')}; "
                 f"write repository files in {cfg.get('repo_language', 'the repository language')}.")
    text = "\n".join(lines)
    print(text[:2000])


# ---------------------------------------------------------------- validate
def validate(root: Path) -> list:
    errs = []
    cfg = load_json(sdlc_dir(root) / "config.json")
    st = load_json(sdlc_dir(root) / "state.json")
    if cfg is None:
        errs.append("config.json missing")
    if st is None:
        errs.append("state.json missing")
        return errs
    if st.get("phase") not in PHASES + [TERMINAL]:
        errs.append(f"state.phase invalid: {st.get('phase')}")
    if st.get("status") not in STATUSES:
        errs.append(f"state.status invalid: {st.get('status')}")
    if st.get("risk") not in RISKS:
        errs.append(f"state.risk invalid: {st.get('risk')}")
    if st.get("mode", "auto") not in MODES:
        errs.append(f"state.mode invalid: {st.get('mode')}")
    ids = set()
    for g in st.get("gates", []):
        if not g.get("id"):
            errs.append("gate without id")
        elif g["id"].lower() in ids:
            errs.append(f"duplicate gate id {g['id']}")
        ids.add(g.get("id", "").lower())
        if g.get("status") not in GATE_STATUSES:
            errs.append(f"gate {g.get('id')} has invalid status {g.get('status')}")
        for b in g.get("blocks") or ["*"]:
            if b != "*" and b not in PHASES + [TERMINAL]:
                errs.append(f"gate {g.get('id')} blocks unknown phase {b}")
    if cfg is not None:
        for pat in cfg.get("deny_commands", []):
            try:
                re.compile(pat)
            except re.error as exc:
                errs.append(f"config.deny_commands bad regex {pat!r}: {exc}")
        if cfg.get("merge_policy", "owner") not in ("owner", "agent"):
            errs.append("config.merge_policy must be 'owner' or 'agent'")
    return errs


def cmd_validate(a) -> None:
    root = project_root(a.project)
    errs = validate(root)
    if errs:
        for e in errs:
            print(f"ERROR: {e}")
        sys.exit(1)
    print("SDLC config and state: OK")


# ---------------------------------------------------------------- mutations
def cmd_set(a) -> None:
    root = project_root(a.project)
    st = load_state(root)
    changes = []
    for key, allowed in (("phase", PHASES + [TERMINAL]), ("status", STATUSES),
                         ("risk", RISKS), ("mode", MODES)):
        val = getattr(a, key)
        if val is not None:
            if val not in allowed:
                die(f"{key} must be one of {allowed}")
            st[key] = val
            changes.append(f"{key}={val}")
    for key in ("next", "change", "title", "stage"):
        val = getattr(a, key)
        if val is not None:
            st[key] = val
            changes.append(f"{key} updated")
    if a.mode is not None:
        st.setdefault("run", {})["mode"] = a.mode
    if not changes:
        die("nothing to set")
    save_state(root, st, a.note or ("set " + ", ".join(changes)))
    print_status(root, st, load_config(root))


def cmd_advance(a) -> None:
    root = project_root(a.project)
    st, cfg = load_state(root), load_config(root)
    current = st.get("phase")
    target = a.to or default_next(st, cfg)
    if target not in PHASES + [TERMINAL]:
        die(f"unknown phase {target}")
    if not a.force and current in EXIT_ARTIFACTS:
        miss = missing_artifacts(root, cfg, st, current)
        if miss:
            print(f"Cannot leave '{current}': missing artifact(s) in "
                  f"{change_dir(root, cfg, st).relative_to(root)}: {'; '.join(miss)}")
            sys.exit(3)
    blocking = pending_gates(st, target)
    st["phase"] = target
    if target == TERMINAL:
        st["status"] = "done"
        st["next"] = a.next or "Change complete. Start the next change from the queue (/sdlc:run new …)."
        save_state(root, st, f"{current} → done")
        print_status(root, st, cfg)
        return
    if blocking:
        st["status"] = "waiting_owner"
        ids = ", ".join(g["id"] for g in blocking)
        st["next"] = a.next or f"Waiting for owner decision(s): {ids}. Continue independent work meanwhile."
        save_state(root, st, f"{current} → {target} (blocked by {ids})")
    else:
        st["status"] = "in_progress"
        if a.next:
            st["next"] = a.next
        save_state(root, st, f"{current} → {target}")
    print_status(root, st, cfg)


def cmd_gate(a) -> None:
    root = project_root(a.project)
    st = load_state(root)
    if a.gate_cmd == "list":
        for g in st.get("gates", []):
            print(f"{g['id']}: {g.get('status')} — {g.get('title', '')}"
                  + (f" (decided {g.get('decided_at')} by {g.get('decided_by')})" if g.get("decided_at") else ""))
        return
    if a.gate_cmd == "add":
        if find_gate(st, a.id):
            die(f"gate {a.id} already exists")
        blocks = [b.strip() for b in (a.blocks or "*").split(",") if b.strip()]
        for b in blocks:
            if b != "*" and b not in PHASES + [TERMINAL]:
                die(f"unknown phase in --blocks: {b}")
        st.setdefault("gates", []).append({
            "id": a.id, "title": a.title or "", "need": a.need or "",
            "status": "pending", "owner_only": not a.ai_allowed, "blocks": blocks,
            "recommended": a.recommended or "", "created_at": now(),
        })
        save_state(root, st, f"gate {a.id} added")
        print(f"gate {a.id} added (pending)")
        return
    if a.gate_cmd == "decide":
        g = find_gate(st, a.id)
        if not g:
            die(f"no gate {a.id}")
        if a.status not in GATE_STATUSES or a.status == "pending":
            die("status must be accepted, rejected, answered or waived")
        if a.by == "ai" and g.get("owner_only", True):
            die(f"gate {g['id']} is owner-only: the owner records it with /sdlc:decide", 4)
        if a.by == "owner":
            die("owner decisions are recorded only through /sdlc:decide (typed by the owner)", 4)
        g.update({"status": a.status, "decided_at": now(), "decided_by": a.by, "note": a.note or ""})
        _unblock_if_possible(st)
        save_state(root, st, f"gate {g['id']} {a.status} by {a.by}")
        print(f"gate {g['id']}: {a.status} (by {a.by})")


def _unblock_if_possible(st: dict) -> None:
    if st.get("status") == "waiting_owner" and not pending_gates(st, st.get("phase")):
        st["status"] = "in_progress"


ACCEPT_WORDS = r"(принят[оа]?|принимаю|согласен|согласна|да|ок|ok|okay|yes|accept(ed)?|approve(d)?|go)"
REJECT_WORDS = r"(отклон(ено|яю)|нет|не\s+принимаю|reject(ed)?|no|stop)"


def cmd_decide_raw(a) -> None:
    """Owner path: called only from the /sdlc:decide skill via `!` pre-processing."""
    root = project_root(a.project)
    st = load_state(root)
    text = " ".join(a.text).strip().strip('"').strip()
    if not text:
        pend = pending_gates(st)
        print("Нет текста решения. Ожидающие решения:" if pend else "Ожидающих решений нет.")
        for g in pend:
            print(f"- {g['id']}: {g.get('title', '')} — {g.get('need', '')}"
                  + (f" (рекомендация: {g['recommended']})" if g.get("recommended") else ""))
        return
    first, _, rest = text.partition(" ")
    g = find_gate(st, first.strip(":,."))
    if g is None:
        pend = pending_gates(st)
        if len(pend) == 1:
            g, rest = pend[0], text
        else:
            st.setdefault("owner_notes", []).append({"at": now(), "text": text})
            save_state(root, st, "owner note recorded")
            print(f"Записано как общее решение владельца: «{text}».")
            return
    rest = rest.strip()
    if g.get("decided_by") == "owner" and g.get("note", "") == rest and g.get("decided_at"):
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(g["decided_at"])).total_seconds()
        except ValueError:
            age = 1e9
        if age < 600:
            print(f"Решение по {g['id']} уже записано.")
            return
    low = rest.lower()
    if re.match(REJECT_WORDS + r"\b", low):
        status = "rejected"
    elif re.match(ACCEPT_WORDS + r"\b", low) or not rest:
        status = "accepted"
    else:
        status = "answered"
    g.update({"status": status, "decided_at": now(), "decided_by": "owner", "note": rest})
    _unblock_if_possible(st)
    save_state(root, st, f"gate {g['id']} {status} by owner")
    label = {"accepted": "принято", "rejected": "отклонено", "answered": "ответ записан"}[status]
    print(f"Решение по {g['id']} записано: {label}" + (f" — «{rest}»" if rest else "") + ".")


def cmd_activate(a) -> None:
    root = project_root(a.project)
    st = load_state(root)
    run = st.setdefault("run", {})
    session = a.session if a.session and not a.session.startswith("${") else None
    run.update({"active": True, "session": session, "mode": a.mode,
                "started": now(), "continuations": 0})
    st["mode"] = a.mode
    rt = sdlc_dir(root) / "runtime" / "stop.json"
    if rt.exists():
        rt.unlink()
    save_state(root, st, f"auto-run activated ({a.mode})")
    note = "" if session else " Session id unknown: the Stop hook will not auto-continue; keep going manually."
    print(f"Auto-run activated (mode: {a.mode}).{note}")


def cmd_deactivate(a) -> None:
    root = project_root(a.project)
    st = load_state(root)
    st.setdefault("run", {})["active"] = False
    save_state(root, st, "auto-run deactivated" + (f": {a.reason}" if a.reason else ""))
    print("Auto-run deactivated.")


def cmd_log(a) -> None:
    root = project_root(a.project)
    st = load_state(root)
    save_state(root, st, " ".join(a.text))
    print("logged")


def cmd_new_change(a) -> None:
    root = project_root(a.project)
    st = load_state(root)
    done = st.setdefault("completed_changes", [])
    if st.get("change"):
        done.append({"change": st.get("change"), "title": st.get("title"), "phase": st.get("phase"),
                     "status": st.get("status"), "closed_at": now()})
    st.update({"change": a.id, "title": a.title or "", "phase": a.phase, "status": "in_progress",
               "risk": a.risk or load_config(root).get("risk_default", "R1"),
               "next": a.next or "Brainstorm with the owner and write the intent."})
    if a.stage:
        st["stage"] = a.stage
    q = st.get("queue") or []
    if q and a.id in q[0]:
        q.pop(0)
    save_state(root, st, f"new change {a.id}")
    print_status(root, st, load_config(root))


# ---------------------------------------------------------------- CLI
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sdlc.py", description=__doc__.splitlines()[0])
    p.add_argument("--project", help="project directory (default: $CLAUDE_PROJECT_DIR or cwd)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init")
    s.add_argument("--profile", default="auto")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("status")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_status)

    sub.add_parser("context").set_defaults(func=cmd_context)
    sub.add_parser("validate").set_defaults(func=cmd_validate)

    s = sub.add_parser("set")
    for key in ("phase", "status", "risk", "mode", "next", "change", "title", "stage", "note"):
        s.add_argument(f"--{key}")
    s.set_defaults(func=cmd_set)

    s = sub.add_parser("advance")
    s.add_argument("--to")
    s.add_argument("--next")
    s.add_argument("--force", action="store_true", help="skip the artifact check (record why in --next)")
    s.set_defaults(func=cmd_advance)

    s = sub.add_parser("gate")
    gs = s.add_subparsers(dest="gate_cmd", required=True)
    gs.add_parser("list")
    ga = gs.add_parser("add")
    ga.add_argument("id")
    ga.add_argument("--title")
    ga.add_argument("--need")
    ga.add_argument("--blocks", help="comma-separated phases or *")
    ga.add_argument("--recommended")
    ga.add_argument("--ai-allowed", action="store_true",
                    help="soft gate: an AI review may decide it (never for owner-only matters)")
    gd = gs.add_parser("decide")
    gd.add_argument("id")
    gd.add_argument("status")
    gd.add_argument("--by", default="ai", choices=["ai", "owner"])
    gd.add_argument("--note")
    s.set_defaults(func=cmd_gate)

    s = sub.add_parser("decide-raw")
    s.add_argument("text", nargs="*")
    s.set_defaults(func=cmd_decide_raw)

    s = sub.add_parser("activate")
    s.add_argument("--session")
    s.add_argument("--mode", default="auto", choices=MODES)
    s.set_defaults(func=cmd_activate)

    s = sub.add_parser("deactivate")
    s.add_argument("--reason")
    s.set_defaults(func=cmd_deactivate)

    s = sub.add_parser("log")
    s.add_argument("text", nargs="+")
    s.set_defaults(func=cmd_log)

    s = sub.add_parser("new-change")
    s.add_argument("id")
    s.add_argument("--title")
    s.add_argument("--stage")
    s.add_argument("--risk", choices=RISKS)
    s.add_argument("--phase", default="intent", choices=PHASES)
    s.add_argument("--next")
    s.set_defaults(func=cmd_new_change)
    return p


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
