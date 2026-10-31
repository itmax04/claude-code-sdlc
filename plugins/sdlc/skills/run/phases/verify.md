# Phase: verify — prove each acceptance criterion on a specific version

**Goal:** evidence per AC on an exact commit, produced by someone other than the author.

**Read:** spec.md (AC list), plan verification section, handoff.md, CI results.

**Do**
1. Fix the version: commit SHA / PR head that is being verified.
2. Delegate to the **`sdlc:verifier`** agent: give it the AC list, the commands, the SHA. It runs the checks and returns an evidence
   table; it cannot edit code. Run independent AC groups in parallel verifier calls when they do not share state.
3. Write `report.md` from `templates/report.md`: AC → method → command/observation → expected → actual →
   PASS/FAIL/NOT RUN/BLOCKED → link. Unverified areas listed explicitly. Owner-only checks (devices, live use) appear as NOT RUN
   with the gate that covers them.
4. FAIL → back to build (`sdlc advance --to build --next "fix AC-xx: …"`), then re-verify only what changed plus regressions.
5. Evals for LLM behaviour: only within `config.hard_rules` quota windows and budgets; otherwise NOT RUN with the reason.

**Exit:** no FAIL left (or each FAIL accepted by the owner as a known limitation) → `sdlc advance` (→ review).
