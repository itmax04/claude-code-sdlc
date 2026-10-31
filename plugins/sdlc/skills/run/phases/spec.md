# Phase: spec — observable behaviour and acceptance criteria

**Goal:** turn the intent into behaviour anyone can verify. `spec.md` is the only place requirements live.

**Read:** intent.md, the code and contracts the change touches, design sources (DESIGN.md, mock-ups, Figma links), existing ADRs.

**Do**
1. Scenarios (given/when/then) for success, errors, empty data, offline/unavailable, concurrency, permissions, accessibility —
   only those that apply.
2. Numbered requirements `R-xx` and acceptance criteria `AC-xx`, each with **how it is checked** (command, test, eval, device,
   owner observation). Every AC must be checkable by the verifier or an explicit owner check.
3. Threat/privacy notes when data, auth, keys or external services are involved.
4. Architecture decisions with long-term effect → ADR (`templates/adr.md`) in the project's decisions folder; local choices stay in
   spec "Decisions".
5. Do not invent UI details absent from the design sources — list them as open questions or assumptions.
6. Run the **`sdlc:reviewer`** agent in documents mode on intent+spec (R1+): untestable AC, gaps, contradictions. Fix P0/P1.

**Owner gate:** R3+ or profile rule → owner accepts spec (one gate for spec+plan is fine; create it now, blocks `build`).

**Exit:** `sdlc advance` (→ plan).
