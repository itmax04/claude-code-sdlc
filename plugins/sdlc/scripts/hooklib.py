"""Shared helpers for the SDLC plugin hooks (standard library only).

Hooks must fail open on their own bugs (never brick a session) but fail closed
on a positive policy match. Every hook exits 0 and prints JSON when it decides.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def read_input() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (OSError, ValueError):
        return {}


def project_dir(data: dict) -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd())


def sdlc_root(data: dict) -> Path | None:
    """Nearest directory (from the project dir upwards) that contains .sdlc/."""
    start = project_dir(data).resolve()
    for d in [start, *start.parents]:
        if (d / ".sdlc" / "state.json").exists() or (d / ".sdlc" / "config.json").exists():
            return d
    return None


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def config(data: dict) -> dict:
    root = sdlc_root(data)
    return load(root / ".sdlc" / "config.json") if root else {}


def emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False))
    sys.stdout.flush()


def deny(reason: str) -> None:
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                 "permissionDecision": "deny",
                                 "permissionDecisionReason": reason}})
    sys.exit(0)


def ask(reason: str) -> None:
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                 "permissionDecision": "ask",
                                 "permissionDecisionReason": reason}})
    sys.exit(0)
