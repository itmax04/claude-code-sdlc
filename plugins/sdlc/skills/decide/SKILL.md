---
name: decide
description: Record the owner's decision on an SDLC gate (H-0, H-1, G-…) — typed by the owner only, e.g. "/sdlc:decide H-0 принимаю".
argument-hint: "[GATE-ID] [принимаю | отклоняю | свой ответ]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sdlc.py *)
---

# Owner decision (recorded before you saw this message)

The owner typed: `$ARGUMENTS`

Result recorded by the plugin (this ran as pre-processing, not as your tool call):

!`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sdlc.py --project "${CLAUDE_PROJECT_DIR}" decide-raw -- "$ARGUMENTS" 2>&1 || true`

Now:
1. Read the updated state: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sdlc.py --project "${CLAUDE_PROJECT_DIR}" status`.
2. Copy the decision into the change's `intent.md` (Decisions table, owner's exact words, date) or `handoff.md` if it is an
   operational checkpoint, and commit that documentation change on the working branch.
3. If the result is "answered" (a free-form choice), interpret it against the gate's options; if it is ambiguous, ask one
   clarifying question with `AskUserQuestion` instead of guessing.
4. Confirm to the owner in one or two sentences (owner language) what was recorded and what happens next. If the run is no longer
   blocked, continue it by following the `/sdlc:run` protocol (invoke the `sdlc:run` skill).
