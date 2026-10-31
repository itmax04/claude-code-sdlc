#!/usr/bin/env python3
"""UserPromptSubmit hook: records owner decisions typed as `/sdlc:decide …`.

Runs on the owner's own prompt text (the model cannot trigger it), so gate
decisions are owner-authored by construction. Idempotent with the skill's
pre-processing path (sdlc.py decide-raw ignores an identical repeat).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from hooklib import read_input, sdlc_root

PATTERN = re.compile(r"^\s*/sdlc:decide\b(.*)$", re.S)


def main() -> None:
    data = read_input()
    m = PATTERN.match(data.get("prompt", "") or "")
    if not m:
        return
    root = sdlc_root(data)
    if root is None:
        return
    text = m.group(1).strip()
    script = Path(__file__).resolve().parent / "sdlc.py"
    subprocess.run([sys.executable, str(script), "--project", str(root), "decide-raw", "--", text],
                   capture_output=True, text=True, timeout=20)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"SDLC owner-prompt hook error (ignored): {exc}", file=sys.stderr)
        sys.exit(0)
