---
name: status
description: Show where the project's SDLC stands — current change, product stage, phase, status, risk, pending owner gates and the next action. Use for "/sdlc:status", "где мы", "что дальше по SDLC".
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sdlc.py *), Bash(git status *), Bash(git log *), Bash(gh pr list *)
---

!`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sdlc.py --project "${CLAUDE_PROJECT_DIR}" status 2>&1 || true`

Summarise this for the owner in their language (`.sdlc/config.json` → `owner_language`) in at most 8 lines:
where the work is, what is waiting for the owner (with the exact `/sdlc:decide <ID> <ответ>` command and the recommended answer),
and the next step. If useful, add the open PRs (`gh pr list`) and the working-tree state. Change nothing.
