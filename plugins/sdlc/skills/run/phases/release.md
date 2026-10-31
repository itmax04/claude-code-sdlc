# Phase: release — controlled delivery with a tested way back

**Goal:** the reviewed version reaches its users (or the owner's machine/devices) with smoke checks and rollback ready.

**Do**
1. Identify the artifact: SHA, build command, version/tag, release notes from the change.
2. Prepare `release.md` from `templates/release.md`: preflight, steps, smoke checks, stop criteria, rollback/restore, who runs what.
3. Do yourself only what the profile allows (local builds, packaging, staging with local/mock credentials, tagging if allowed).
4. **Owner-run** (`config.release.owner_run`): production deploys, remote migrations, secrets, store/sideload installs, device
   installs. Create a gate with exact numbered steps in the owner language; keep the steps copy-pasteable and safe.
5. After the owner reports back, run the smoke checks you can, record results in release.md, and close the gate.

**Exit:** released (or `prepared, awaiting owner` recorded honestly — never rename "prepared" to "released") → `sdlc advance`.
