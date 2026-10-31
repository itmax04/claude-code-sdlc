#!/usr/bin/env python3
"""Stop hook: keeps an active SDLC auto-run going until it reaches a real stop.

Continues the turn only when ALL are true:
  * the project has .sdlc/state.json with run.active = true and mode = auto;
  * the run was activated by this session (run.session matches, when recorded);
  * status is in_progress (not waiting_owner / blocked / done);
  * progress was made since the previous continuation (state, HEAD or the
    working tree changed) — otherwise it stops after 2 idle continuations;
  * the per-run continuation budget (config.max_auto_continuations) is not used up.
Claude Code itself also caps consecutive stop-hook continuations.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys

from hooklib import emit, load, read_input, sdlc_root

IDLE_LIMIT = 2


def fingerprint(root) -> str:
    h = hashlib.sha256()
    try:
        h.update((root / ".sdlc" / "state.json").read_bytes())
    except OSError:
        pass
    for args in (["rev-parse", "HEAD"], ["status", "--porcelain"]):
        try:
            out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=10)
            h.update(out.stdout.encode())
        except (OSError, subprocess.SubprocessError):
            pass
    return h.hexdigest()


def main() -> None:
    data = read_input()
    root = sdlc_root(data)
    if root is None:
        return
    st = load(root / ".sdlc" / "state.json")
    cfg = load(root / ".sdlc" / "config.json")
    run = st.get("run") or {}
    if not run.get("active") or (st.get("mode") or run.get("mode")) != "auto":
        return
    if not run.get("session") or run.get("session") != data.get("session_id"):
        return  # only the session that started the run is kept going; never hijack another one
    if st.get("status") != "in_progress" or st.get("phase") == "done":
        return

    rt_dir = root / ".sdlc" / "runtime"
    rt_dir.mkdir(parents=True, exist_ok=True)
    rt_path = rt_dir / "stop.json"
    rt = load(rt_path)
    fp = fingerprint(root)
    idle = rt.get("idle", 0) + 1 if rt.get("fingerprint") == fp else 0
    count = rt.get("count", 0) + 1
    limit = int(cfg.get("max_auto_continuations", 60))

    if idle >= IDLE_LIMIT or count > limit:
        why = "no progress after repeated continuations" if idle >= IDLE_LIMIT else f"continuation budget ({limit}) used up"
        rt_path.write_text(json.dumps({"fingerprint": fp, "idle": 0, "count": 0}), encoding="utf-8")
        emit({"systemMessage": f"SDLC auto-run paused: {why}. Run /sdlc:run to resume or /sdlc:status to inspect."})
        return

    rt_path.write_text(json.dumps({"fingerprint": fp, "idle": idle, "count": count}), encoding="utf-8")
    nxt = st.get("next") or "continue the current phase"
    reason = (
        f"SDLC auto-run is active (change {st.get('change')}, phase {st.get('phase')}, status in_progress). "
        f"Next: {nxt}. Keep working per the /sdlc:run protocol. Stop only when the change is done or "
        "genuinely blocked: then record it first with sdlc.py (`set --status waiting_owner|blocked --next ...` "
        "or `advance`), report to the owner, and end the turn."
    )
    emit({"decision": "block", "reason": reason})


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # never trap the user in a loop because of a hook bug
        print(f"SDLC stop hook error (ignored): {exc}", file=sys.stderr)
        sys.exit(0)
