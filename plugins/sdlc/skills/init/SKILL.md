---
name: init
description: Set up the SDLC plugin in the current project — creates .sdlc/ (config, project profile, state) from a profile (auto-detected, or "generic"/"lingo"). Use for "/sdlc:init" or before the first /sdlc:run in a new project.
argument-hint: "[profile] [--force]"
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sdlc.py *), Bash(git status *), Bash(git remote *)
---

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sdlc.py --project "${CLAUDE_PROJECT_DIR}" init --profile <profile named in the arguments, else auto>` (add `--force`
   only if the owner asked to re-create the state; it overwrites `.sdlc/` from the profile).
   Available profiles: `ls ${CLAUDE_PLUGIN_ROOT}/profiles`.
2. For the `generic` profile, finish the setup instead of leaving placeholders:
   - fill `.sdlc/config.json` → `commands` with the project's real build/test/lint commands (read package.json, Makefile, CI files),
     `protected_branches`, `merge_policy` (default `owner`), `owner_language`, `repo_language`, `changes_dir`;
   - write `.sdlc/PROJECT.md` (≤ 60 lines): purpose, users, hard rules, sources of truth with paths, where artifacts live.
   Use `AskUserQuestion` only for what the repository cannot tell you (merge policy, owner language, hard budget/privacy rules).
3. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sdlc.py --project "${CLAUDE_PROJECT_DIR}" validate`.
4. Commit `.sdlc/` on a branch (`chore/sdlc-setup`) — not on a protected branch — and tell the owner, in their language, that the
   project is ready and the next command is `/sdlc:run`.
