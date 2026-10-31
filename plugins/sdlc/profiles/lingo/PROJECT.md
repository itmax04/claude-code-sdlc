# Lingo — SDLC project profile

Personal voice tutor for spoken English and German (explanations in Russian only on request) for one owner (`itmax04`):
Lingo for Mac (Swift, on-device whisper) + Lingo Web (PWA) + Lingo Engine (Cloudflare Worker + D1), all on free tiers.

**Canonical guide:** `AGENTS.md` (loaded via CLAUDE.md) — repository map, commands, rules, pitfalls. This profile does not
duplicate it; it adds only what the SDLC run needs. The repository process `docs/process/SDLC.md` is executed by this plugin
(roles, DoD §6, Git §7, reporting §10 stay valid); where they differ, the owner decisions below win.

## Where things live
| Fact | Source of truth |
|---|---|
| Roadmap and stage order | `docs/ROADMAP.md`, `docs/plans/UPGRADE-PLAN-2026-10-28.md` (branch `docs/upgrade-plan`, PR #34 until merged) |
| Current change | `docs/changes/<ID>/` — intent, spec, plan, handoff, report, evidence/ |
| Stage prompts (historic) | `docs/process/STAGE-PROMPTS.md` — superseded by `/sdlc:run`; keep only as content reference |
| Architecture / ADRs / contracts | `docs/architecture/`, `docs/decisions/`, `packages/contracts/` |
| Design | `DESIGN.md`, `design/redesign-2026/` (PR #33, LINGO-07) |
| Run state | `.sdlc/state.json` (this plugin) |
| Legacy Codex packets (read-only archive) | `~/Desktop/Lingo-SDLC-Complete-2026-10-29` — import needed content into Git, never continue the packet workflow |

Working copy: `~/Developer/lingo` (+ worktrees `~/Developer/lingo-*`). The old iCloud copy `~/Desktop/1/lingo` is obsolete.

## Owner decisions in force (newest first; record new ones in the change's intent.md)
- 2026-10-29 **DG-03 = A**: own docs PR + its merge after AI checks; no manual owner review of documents; AI checks stay.
- 2026-10-29 **DG-02 / H-0 (LINGO-03 intent/spec/plan v2) accepted**; **DG-01 / H-U (upgrade plan v1 + P-00 amendment) accepted**.
- **D04-01**: AI-only review for R2/R3; no mandatory human reviewer.
- Executor may merge ready PRs of accepted stages after CI + AI review + gates (merge_policy = agent); not the old chain without G-CHAIN.
- **D01-01**: Mac first run in Russian; language choice Russian / English / System.
- Offline web = read-only history (no offline composer); WS-09 checked with seeded queue fixtures.
- Production deploys and remote migrations are owner-run; accounts/keys/settings/devices are owner-only.
- A brainstorm opens every new stage (only material questions, no round limit); within an accepted stage the executor works to
  DoD without per-step approvals.

## Owner checkpoints (from the upgrade plan; each change re-states its own)
H-U ✔ · H-0 ✔ · H-07a/H-07b (redesign limit & visual acceptance) · H-1 (Stage 0: 30-min stability, memory/latency/backup/language)
· H-2a/H-2b (accounts/keys/bindings, privacy/retention, test release) · H-3 (device voice feasibility) · H-4a/H-4b (web pipeline,
two real days 4 × 30) · H-5 (LINGO-03 acceptance) · H-04-*, H-05-*, H-06-* (future changes).

## Legacy phase mapping (Codex packets → this plugin)
00-preparation → survey · 01-brainstorm-intent → intent · 02-design-spec → spec · 03-plan → plan · 04-build → build ·
05-verification → verify · 06-review → review · 07-deploy → release · 08-maintain → maintain · 09-incident → incident.
Folder hand-offs, ZIP packets, `packet.py`, manifests and per-phase chats are no longer used: state lives in Git and `.sdlc/`.
