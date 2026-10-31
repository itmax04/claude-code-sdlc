#!/usr/bin/env python3
"""SessionStart hook: injects a compact SDLC status into the new/resumed/compacted
session so work continues from files, not from chat memory."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from hooklib import emit, read_input, sdlc_root


def main() -> None:
    data = read_input()
    root = sdlc_root(data)
    if root is None:
        return
    script = Path(__file__).resolve().parent / "sdlc.py"
    out = subprocess.run([sys.executable, str(script), "--project", str(root), "context"],
                         capture_output=True, text=True, timeout=20)
    text = out.stdout.strip()
    if not text:
        return
    if data.get("source") == "compact":
        text += ("\nContext was compacted: re-read .sdlc/state.json and the current change's handoff.md "
                 "before continuing; do not rely on memory of earlier turns.")
    emit({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}})


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"SDLC session hook error (ignored): {exc}", file=sys.stderr)
        sys.exit(0)
