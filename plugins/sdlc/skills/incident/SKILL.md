---
name: incident
description: Start the SDLC incident flow for a real problem (broken main, failing production, data-loss risk, leaked secret) from any phase. Use for "/sdlc:incident <what happened>" or "у нас инцидент".
argument-hint: "<what happened>"
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sdlc.py *)
---

Signal from the owner: `$ARGUMENTS`

1. Remember the interrupted work: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sdlc.py --project "${CLAUDE_PROJECT_DIR}" log "incident started during <phase> of <change>: $ARGUMENTS"`.
2. Switch: `… set --phase incident --status in_progress --next "contain: <first action>"`.
3. Follow `${CLAUDE_PLUGIN_ROOT}/skills/run/phases/incident.md`. A leaked secret is S1: the owner revokes it first — give exact
   steps immediately; never print the value.
4. When contained and fixed, return to the interrupted change (`… set --phase <previous> --next "…"`) and continue with `/sdlc:run`.
