# Phase: maintain — close the loop and pick the next change

**Goal:** learn from the release, update the sources of truth and start the next change without losing context.

**Do**
1. Collect signals that exist (owner feedback, metrics logs, CI history, open issues). Do not invent telemetry.
2. Close the change: report.md final, handoff.md "Done", roadmap/status docs updated, issues closed with links.
3. Repeated problems → improve the harness: a test, an eval case, a hook rule, a CLAUDE.md/AGENTS.md line, or a skill tweak
   (propose plugin changes as a note in handoff — the plugin lives in its own repository).
4. Next change: take the head of `state.queue` (or the owner's new idea) → `sdlc new-change <ID> --title … --stage …`.
   Its brainstorm happens in the next intent phase; do not start implementation without it.

**Exit:** `sdlc advance` → done for this change; in auto mode continue with the new change's intent phase if the queue has one
and nothing owner-only blocks it.
