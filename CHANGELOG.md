# Changelog

## 1.0.0 — 2026-10-31
- First release: the Codex packet SDLC for Lingo is reworked as a Claude Code plugin with a marketplace.
- `/sdlc:run` orchestrator with 10 phase procedures, risk R0–R4, autonomy contract, evidence rules and templates.
- `/sdlc:status`, `/sdlc:decide` (owner-only through a UserPromptSubmit hook), `/sdlc:init`, `/sdlc:incident`.
- Agents `reviewer` and `verifier` (fresh context, no write tools).
- Hooks: Bash and Write guards, Stop continuation with progress and budget limits, SessionStart status.
- Profiles `generic` and `lingo` (current owner decisions, gates, queue, legacy packet pointers).
- 31 unit tests; `claude plugin validate --strict` passes for the plugin and the marketplace.
