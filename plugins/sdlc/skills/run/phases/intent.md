# Phase: intent — brainstorm and agree on why and what

**Goal:** a short, testable agreement on the problem, outcome, scope and constraints. Owner decides; you propose.

**Read:** survey, the owner's request, the roadmap/queue entry, relevant feedback/incidents, accepted ADRs. Not the code in depth.

**Do**
1. Restate the goal in 2–3 sentences in the owner's language.
2. Brainstorm: list unknowns; drop those the sources answer. Ask the remaining **material** ones with `AskUserQuestion`
   (2–4 options, recommended first, consequences in the description), in small batches, as many rounds as needed.
   Do not re-ask decisions already recorded (intent decisions, `.sdlc/PROJECT.md`, owner notes in state).
3. Owner unavailable or R0–R1: write a reasoned assumption `A-xx` instead of waiting. R2+: create a gate for the open
   decision (`sdlc gate add …`) and keep preparing everything that does not depend on it.
4. Set risk R0–R4 with reasons (`reference/risk.md`) — `sdlc set --risk Rn`.
5. Write `intent.md` from `templates/intent.md` (R0: `templates/feature.md` covers intent+spec+plan in one file).
   Record owner answers as decisions `Q-xx` with date and the owner's words; assumptions `A-xx`; open questions.
6. Definition of Done for the change: observable outcome + checks + who accepts.

**Owner gate:** the owner accepts the intent (gate `H-0` or the profile's equivalent) when the profile or risk ≥ R3 requires it;
otherwise an `sdlc:reviewer` pass on the intent (mode: documents) is enough — record it with `sdlc gate decide … --by ai` only for
gates created with `--ai-allowed`.

**Exit:** `sdlc advance` (→ spec; R0 → build).
