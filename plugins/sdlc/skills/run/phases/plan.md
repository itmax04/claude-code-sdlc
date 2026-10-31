# Phase: plan — how, in what order, how to check and undo

**Goal:** a dependency-ordered list of small, verifiable steps that covers every AC.

**Read:** spec.md, the code areas involved, `config.commands`, CI configuration.

**Do**
1. Steps `P-xx`: files/components, requirement and AC ids covered, check command, rollback, size (aim for PRs ≤ ~600 lines).
2. Dependencies between steps (no cycles); mark steps that can run in parallel (separate worktrees, see `reference/autonomy.md`).
3. Owner checkpoints `H-x` only where the owner is truly needed (accounts, keys, devices, live tests, production, acceptance).
   Add each as a gate now: `sdlc gate add H-x --title … --need "<exact owner steps>" --blocks <phase>`.
4. Verification plan: which AC are checked by tests, evals, verifier, devices; what will be NOT RUN and why.
5. Risks with a detection signal and a fallback; release/rollback outline if anything ships.
6. If the profile uses GitHub issues (`config.github.issues`), create one issue per step (title `[CHANGE P-xx] …`, labels,
   milestone, AC checklist) — idempotently: search before creating.
7. `sdlc:reviewer` (documents mode) on the plan for R2+: coverage of every AC, ordering, missing rollback.

**Owner gate:** document acceptance (H-0 or equivalent) when required by the profile or risk ≥ R3 — one gate for intent+spec+plan.
While it is pending, keep preparing (branch, scaffolding that is safe to discard, test fixtures) but do not merge product code.

**Exit:** `sdlc advance` (→ build).
