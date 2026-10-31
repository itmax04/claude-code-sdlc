# Phase: review — independent judgement and release readiness

**Goal:** a fresh-context assessment of the whole change (not just one PR) and a go/no-go for release.

**Do**
1. Run the **`sdlc:reviewer`** agent in change mode: intent/spec/plan vs. merged diff vs. report.md. Severity P0–P3
   (`reference/evidence.md`). For R3+ also ask it for a security/privacy pass; if the profile requires a human reviewer at this risk,
   create an owner gate instead of pretending the AI review is enough.
2. Fix P0/P1 in build (feedback loop), re-verify affected AC, re-review. Record P2/P3 decisions.
3. Write `review.md` (or a "Review" section in report.md): reviewed version, findings and their resolution, residual risks,
   verdict: `ready` / `ready with limits` / `not ready`.
4. Release readiness: what ships, migrations, config/secrets the owner must set, rollback, smoke checks.

**Exit:** verdict `ready`/`ready with limits` → `sdlc advance` (→ release, or → maintain when the profile has no release).
