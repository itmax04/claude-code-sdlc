# Phase: incident — safe recovery from a real signal (any time)

**Goal:** stop the damage, restore service, understand the cause, prevent recurrence. Triggered by `/sdlc:incident` or a real
signal (failing production, data loss risk, leaked secret, broken main).

**Do**
1. Record `incident.md` (`templates/incident.md`): signal, time, impact, severity S1–S4, affected version.
2. Containment you may do yourself: revert/disable on a branch + PR, stop your own running jobs, mark the release not-ready.
   Owner-only: production rollback, key rotation, account actions, data restore — exact steps + gate, immediately.
3. A leaked secret is always S1: tell the owner to revoke/rotate it first; never print the value; remove it from the tree;
   history rewriting needs the owner.
4. Reproduce, find the cause with evidence (no guessing), fix via the normal build → verify → review loop with a regression test/eval.
5. Postmortem section: timeline, cause, what detected it, what changes (test, hook, doc, alert).

**Exit:** `sdlc advance` (→ intent for any follow-up change), then return to the interrupted change (`sdlc set --phase …`).
