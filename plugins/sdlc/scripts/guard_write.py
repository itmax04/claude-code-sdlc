#!/usr/bin/env python3
"""PreToolUse(Write|Edit|MultiEdit|NotebookEdit) guard for SDLC projects.

Blocks: secrets in written content, writes to protected paths, direct edits of
.sdlc/state.json (state changes go through sdlc.py so owner decisions cannot be
forged by an edit). Active only inside a project that has .sdlc/.
"""
from __future__ import annotations

import fnmatch
import os
import re
import sys

from hooklib import config, deny, read_input, sdlc_root

SECRET_PATTERNS = [
    (r"gsk_[A-Za-z0-9]{20,}", "Groq API key"),
    (r"sk-ant-[A-Za-z0-9_\-]{20,}", "Anthropic API key"),
    (r"sk-or-v1-[A-Za-z0-9]{20,}", "OpenRouter API key"),
    (r"sk-proj-[A-Za-z0-9_\-]{20,}", "OpenAI project key"),
    (r"\bsk-[A-Za-z0-9]{32,}\b", "API secret key"),
    (r"\bAKIA[0-9A-Z]{16}\b", "AWS access key"),
    (r"\bAIza[0-9A-Za-z_\-]{35}\b", "Google API key"),
    (r"\bgh[pousr]_[A-Za-z0-9]{36,}\b", "GitHub token"),
    (r"\bgithub_pat_[A-Za-z0-9_]{40,}\b", "GitHub fine-grained token"),
    (r"\bxox[abprs]-[A-Za-z0-9\-]{10,}", "Slack token"),
    (r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----", "private key"),
]


def written_text(tool: str, ti: dict) -> str:
    if tool == "Write":
        return ti.get("content", "") or ""
    if tool == "Edit":
        return ti.get("new_string", "") or ""
    if tool == "MultiEdit":
        return "\n".join((e or {}).get("new_string", "") for e in ti.get("edits", []) or [])
    if tool == "NotebookEdit":
        return ti.get("new_source", "") or ""
    return ""


def rel(path: str, root) -> str:
    try:
        return os.path.relpath(os.path.abspath(path), str(root))
    except ValueError:
        return path


def main() -> None:
    data = read_input()
    tool = data.get("tool_name", "")
    if tool not in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        return
    root = sdlc_root(data)
    if root is None:
        return
    cfg = config(data)
    ti = data.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path") or ""
    rpath = rel(path, root) if path else ""

    if rpath.replace("\\", "/") == ".sdlc/state.json":
        deny("SDLC guard: change .sdlc/state.json only through sdlc.py (set/advance/gate); "
             "owner decisions are recorded by the owner with /sdlc:decide.")

    for pat in cfg.get("protected_paths") or []:
        base = pat.rstrip("*").rstrip("/")
        if fnmatch.fnmatch(rpath, pat) or (base and (rpath == base or rpath.startswith(base + "/"))):
            deny(f"SDLC guard: {rpath} is a protected path ({pat}).")

    allow = cfg.get("secret_allowlist_paths") or []
    if any(fnmatch.fnmatch(rpath, a) for a in allow):
        return
    text = written_text(tool, ti)
    for pat, label in SECRET_PATTERNS:
        if re.search(pat, text):
            deny(f"SDLC guard: the content looks like a real secret ({label}). Secrets never go into files — "
                 "use a placeholder; the owner stores real values in the keychain or the provider's secret store.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"SDLC write guard error (ignored): {exc}", file=sys.stderr)
        sys.exit(0)
