# Phase: build — implement step by step with continuous checks

**Goal:** working, tested increments that map to plan steps; every step leaves the repository green and documented.

**Read:** accepted spec + plan, handoff.md "Next step", the code of the current step, project rules. Re-check `git status` first.

**Loop per step `P-xx`**
1. Branch `<type>/<issue>-<slug>` from the up-to-date default branch (or stack on the previous step's branch while its PR waits).
   Parallel independent steps → one git worktree per step (`claude -w`/`git worktree add`); never touch another session's worktree.
2. For a bug: write the failing test first when feasible.
3. Implement the smallest change that satisfies the step's AC. No silent scope growth; no new dependency outside the allow-list.
4. Run the relevant checks from `config.commands` (build, tests, lint, secret scan, language/format checks). On failure:
   read the full error, fix the cause, re-run. Never weaken a test. Three failed attempts on the same problem → record hypotheses
   in handoff, mark the step blocked, move to an independent step.
5. Review your own diff (`git diff`): only intended files, no secrets, no stray formatting. Commit with a clear message.
6. Push the branch, open/update the PR (template, linked issue, checks with real output, risk, rollback, screenshots for UI).
7. Run **`sdlc:reviewer`** on the PR diff. Fix P0/P1 findings, re-run checks, re-review. P2/P3 → fix if cheap or record.
8. Merge only when `config.merge_policy` is `agent` and: CI green · reviewer approves · AC evidence for the step recorded ·
   no pending gate blocks it. Otherwise mark ready and move on (stacked branch).
9. Update handoff.md (step, PR, checks, decisions D-xx, next) and `sdlc set --next "…"`.

**Owner checkpoints:** when a step needs the owner (H-x), give exact steps in the owner language and continue other steps.

**Exit:** all plan steps done or explicitly deferred with reason → `sdlc advance` (→ verify).
