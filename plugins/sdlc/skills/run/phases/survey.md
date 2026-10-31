# Phase: survey — establish the real starting point

**Goal:** know what actually exists before deciding anything. Read-only except `.sdlc/survey.md` and the state.

**Read:** `.sdlc/PROJECT.md`, `.sdlc/state.json` (`next`, `queue`, `legacy`), the project's instructions as loaded, README,
the current change folder if any. Use the `Explore` agent for a broad map; do not read everything.

**Do**
1. Git baseline: `git status --short --branch`, `git rev-parse HEAD`, `git worktree list`, `git log --oneline -5`; open PRs and
   issues (`gh pr list`, `gh issue list`) when the project uses GitHub. Never discard someone else's changes.
2. Environment: which commands from `config.commands` exist and run (try the cheap ones: build/test help, versions). Record
   PASS/FAIL/NOT RUN; do not install anything that needs the owner.
3. Compare documents with reality: what is implemented, declared only, or unverified. Note contradictions with file:line.
4. Legacy material (`state.legacy`, if present): read only its index/handoff; import what is still needed into the repository
   (branch + commit) instead of keeping work outside version control.
5. Decide the risk (`reference/risk.md`) and whether the queued change can start; list owner-only blockers as gates
   (`sdlc gate add …`) with exact steps and a recommended option.

**Output:** `.sdlc/survey.md` (≤ 1 page: baseline SHA/branch, environment table, discrepancies, risks, gates, next step).
Refresh it when older than the current HEAD by more than a few merges — don't rewrite history in it.

**Exit:** `sdlc advance` (→ intent). Skip straight to the phase in `state.next` if the survey shows the change is already
further along (`sdlc advance --to <phase> --next "…"`, with the reason in survey.md).
