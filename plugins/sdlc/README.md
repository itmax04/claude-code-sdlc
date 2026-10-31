# sdlc — Claude Code plugin

Risk-based AI-native SDLC for Claude Code. `/sdlc:run` resumes the project's state from `.sdlc/state.json` and drives
survey → intent → spec → plan → build ↔ verify → review → release → maintain (plus incident) until the change is done or an
owner gate is reached. Includes `/sdlc:status`, `/sdlc:decide` (owner-only decisions), `/sdlc:init`, `/sdlc:incident`,
the `sdlc:reviewer` and `sdlc:verifier` agents, guardrail hooks (destructive git, protected branches, secrets, protected paths,
quota windows) and a Stop hook that keeps an active run going while it makes progress. Hooks are no-ops outside projects with
a `.sdlc/` folder. Documentation (Russian): see the repository root `README.md` and `docs/`.
