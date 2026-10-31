# Risk → process

Process strictness follows the consequences of a mistake, not the size of the diff. Pick the highest level any factor reaches.

| Level | Typical factors | Artifacts | Checks & review | Owner gates |
|---|---|---|---|---|
| **R0** trivial | text, comments, local formatting, reversible config with no user effect | `feature.md` (intent+spec+plan in one) | relevant check + diff self-review | none |
| **R1** normal | internal feature, docs, tooling, tests; no shared data or external effect | intent, spec (short), plan (short) | tests/build, `sdlc:reviewer` on PRs | profile-defined (often none) |
| **R2** user-visible | UI/behaviour users notice, shared data formats, integrations with free external APIs, sync | full intent/spec/plan, ADR for lasting choices | reviewer on every PR, verifier for AC, CI | document acceptance if the profile asks |
| **R3** sensitive | auth, keys, personal data, payments, data migrations, production deploy, quota/cost exposure | + threat/privacy notes, rollback & restore plan, release.md | + security pass, staged release, smoke checks; human reviewer if the profile requires | owner accepts spec+plan; owner runs production steps |
| **R4** irreversible / regulated | data deletion, legal/regulatory, safety | + audit trail, restore drill | + second independent review | owner gate at every phase |

Raise the level when unsure. Lower it only with a written reason in intent.md. A change may contain steps of different levels:
apply the stricter process to those steps.
