"""Tests for the SDLC plugin scripts and hooks (standard library only).

Run: python3 -m unittest discover -s tests -v
Each test works in a throw-away git repository; nothing outside it is touched.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "plugins" / "sdlc" / "scripts"
PY = sys.executable


def run(script: str, *args: str, stdin: dict | str | None = None, env: dict | None = None, cwd: Path | None = None):
    data = json.dumps(stdin) if isinstance(stdin, dict) else (stdin or "")
    e = dict(os.environ)
    e.update(env or {})
    return subprocess.run([PY, str(SCRIPTS / script), *args], input=data, capture_output=True,
                          text=True, env=e, cwd=str(cwd) if cwd else None, timeout=60)


class Repo:
    def __init__(self, profile: str = "generic", remote: str | None = None):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name).resolve()
        subprocess.run(["git", "init", "-q", "-b", "feat/x", str(self.path)], check=True)
        subprocess.run(["git", "-C", str(self.path), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "--allow-empty", "-m", "init"], check=True)
        if remote:
            subprocess.run(["git", "-C", str(self.path), "remote", "add", "origin", remote], check=True)
        r = run("sdlc.py", "--project", str(self.path), "init", "--profile", profile)
        assert r.returncode == 0, r.stderr

    def sdlc(self, *args):
        return run("sdlc.py", "--project", str(self.path), *args)

    def state(self):
        return json.loads((self.path / ".sdlc" / "state.json").read_text())

    def config_update(self, **kw):
        p = self.path / ".sdlc" / "config.json"
        cfg = json.loads(p.read_text())
        cfg.update(kw)
        p.write_text(json.dumps(cfg))

    def hook(self, script, payload):
        payload.setdefault("cwd", str(self.path))
        return run(script, stdin=payload, env={"CLAUDE_PROJECT_DIR": str(self.path)})

    def close(self):
        self.tmp.cleanup()


def decision(out: str) -> str:
    if not out.strip():
        return "none"
    obj = json.loads(out)
    if "hookSpecificOutput" in obj and "permissionDecision" in obj["hookSpecificOutput"]:
        return obj["hookSpecificOutput"]["permissionDecision"]
    return obj.get("decision", "none")


class StateTests(unittest.TestCase):
    def setUp(self):
        self.r = Repo()

    def tearDown(self):
        self.r.close()

    def test_init_validate_status(self):
        self.assertEqual(self.r.sdlc("validate").returncode, 0)
        out = self.r.sdlc("status").stdout
        self.assertIn("Phase: survey", out)
        self.assertTrue((self.r.path / ".sdlc" / ".gitignore").exists())

    def test_init_is_idempotent(self):
        before = self.r.state()
        out = self.r.sdlc("init").stdout
        self.assertIn("already initialized", out)
        self.assertEqual(before["change"], self.r.state()["change"])

    def test_advance_requires_artifact(self):
        r = self.r.sdlc("advance")
        self.assertEqual(r.returncode, 3)
        (self.r.path / ".sdlc" / "survey.md").write_text("baseline")
        self.assertEqual(self.r.sdlc("advance").returncode, 0)
        self.assertEqual(self.r.state()["phase"], "intent")

    def test_r0_skips_spec_and_plan(self):
        self.r.sdlc("set", "--phase", "intent", "--risk", "R0")
        cdir = self.r.path / "docs" / "changes" / "CHANGE-01"
        cdir.mkdir(parents=True)
        (cdir / "feature.md").write_text("combined")
        self.r.sdlc("advance")
        self.assertEqual(self.r.state()["phase"], "build")

    def test_gate_blocks_and_ai_cannot_decide_owner_gate(self):
        self.r.sdlc("set", "--phase", "review", "--status", "in_progress")
        self.r.sdlc("gate", "add", "H-9", "--title", "release ok", "--need", "owner", "--blocks", "release")
        cdir = self.r.path / "docs" / "changes" / "CHANGE-01"
        cdir.mkdir(parents=True)
        (cdir / "report.md").write_text("r")
        self.r.sdlc("advance")
        st = self.r.state()
        self.assertEqual((st["phase"], st["status"]), ("release", "waiting_owner"))
        r = self.r.sdlc("gate", "decide", "H-9", "accepted", "--by", "ai")
        self.assertEqual(r.returncode, 4)
        r = self.r.sdlc("gate", "decide", "H-9", "accepted", "--by", "owner")
        self.assertEqual(r.returncode, 4, "owner decisions only via /sdlc:decide")

    def test_soft_gate_ai_decision_unblocks(self):
        self.r.sdlc("gate", "add", "S-1", "--blocks", "survey", "--ai-allowed")
        self.r.sdlc("set", "--status", "waiting_owner")
        self.assertEqual(self.r.sdlc("gate", "decide", "S-1", "accepted", "--by", "ai").returncode, 0)
        self.assertEqual(self.r.state()["status"], "in_progress")

    def test_decide_raw_parses_and_is_idempotent(self):
        self.r.sdlc("gate", "add", "H-1", "--blocks", "build")
        out = self.r.sdlc("decide-raw", "--", "H-1 принимаю").stdout
        self.assertIn("принято", out)
        g = self.r.state()["gates"][0]
        self.assertEqual((g["status"], g["decided_by"]), ("accepted", "owner"))
        self.assertIn("уже записано", self.r.sdlc("decide-raw", "--", "H-1 принимаю").stdout)
        self.r.sdlc("gate", "add", "H-2", "--blocks", "build")
        self.r.sdlc("decide-raw", "--", "h-2 нет, сначала другое")
        self.assertEqual(self.r.state()["gates"][1]["status"], "rejected")
        self.r.sdlc("gate", "add", "H-3", "--blocks", "build")
        self.r.sdlc("decide-raw", "--", "H-3 вариант B")
        self.assertEqual(self.r.state()["gates"][2]["status"], "answered")

    def test_validate_catches_bad_state(self):
        p = self.r.path / ".sdlc" / "state.json"
        st = json.loads(p.read_text())
        st["phase"] = "deploy-now"
        p.write_text(json.dumps(st))
        self.assertEqual(self.r.sdlc("validate").returncode, 1)

    def test_lingo_profile_autodetect(self):
        r = Repo(profile="auto", remote="https://github.com/itmax04/lingo.git")
        try:
            st = r.state()
            self.assertEqual(st["profile"], "lingo")
            self.assertEqual(r.sdlc("validate").returncode, 0)
            self.assertTrue(any(g["id"] == "G-CHAIN" and g["status"] == "pending" for g in st["gates"]))
        finally:
            r.close()


class BashGuardTests(unittest.TestCase):
    def setUp(self):
        self.r = Repo()

    def tearDown(self):
        self.r.close()

    def bash(self, command):
        res = self.r.hook("guard_bash.py", {"tool_name": "Bash", "tool_input": {"command": command}})
        self.assertEqual(res.returncode, 0, res.stderr)
        return decision(res.stdout)

    def test_allowed_commands(self):
        for c in ["git status", "git push -u origin feat/x", "swift test", "git commit -m 'x'",
                  "gh pr create --fill", "rm -rf build", "python3 x.py --project . status",
                  "cat .sdlc/state.json"]:
            self.assertEqual(self.bash(c), "none", c)

    def test_denied_commands(self):
        for c in ["git push --force", "git push -f origin feat/x", "git push origin main",
                  "git push origin HEAD:main", "git push origin +feat/x", "git push origin :old",
                  "git reset --hard HEAD~1", "git clean -fdx", "git branch -D x", "git filter-branch",
                  "cd a && git push --force-with-lease", "gh pr merge 5 --squash", "gh repo delete x",
                  "gh secret set K", "rm -rf ~", "rm -rf /", "echo x > .sdlc/state.json",
                  "python3 /p/scripts/sdlc.py --project /x decide-raw -- 'H-1 ok'",
                  "FOO=1 git push --force"]:
            self.assertEqual(self.bash(c), "deny", c)

    def test_push_without_refspec_on_protected_branch(self):
        subprocess.run(["git", "-C", str(self.r.path), "switch", "-q", "-c", "main"], check=True)
        self.assertEqual(self.bash("git push"), "deny")

    def test_merge_policy_agent_allows_merge_but_not_admin(self):
        self.r.config_update(merge_policy="agent")
        self.assertEqual(self.bash("gh pr merge 5 --squash"), "none")
        self.assertEqual(self.bash("gh pr merge 5 --admin"), "deny")

    def test_project_deny_and_protected_paths(self):
        self.r.config_update(deny_commands=[r"wrangler\s+deploy"], protected_paths=["private/**", ".dev.vars"])
        self.assertEqual(self.bash("npx wrangler deploy"), "deny")
        self.assertEqual(self.bash("cat private/notes.pdf"), "deny")
        self.assertEqual(self.bash("cat .dev.vars"), "deny")
        self.assertEqual(self.bash("cat docs/private-notes.md"), "none")

    def test_night_only(self):
        self.r.config_update(night_only_commands=["--eval-dialog"],
                             night_window={"tz": "UTC", "start": "00:00", "end": "00:01"})
        # the window is one minute long, so practically always outside it
        from datetime import datetime, timezone
        if datetime.now(timezone.utc).strftime("%H:%M") != "00:00":
            self.assertEqual(self.bash("Lingo --eval-dialog cases out"), "deny")
        self.r.config_update(night_window={"tz": "UTC", "start": "00:00", "end": "23:59"})
        if datetime.now(timezone.utc).strftime("%H:%M") != "23:59":
            self.assertEqual(self.bash("Lingo --eval-dialog cases out"), "none")

    def test_malformed_input_fails_open(self):
        res = run("guard_bash.py", stdin="{not json", env={"CLAUDE_PROJECT_DIR": str(self.r.path)})
        self.assertEqual((res.returncode, res.stdout), (0, ""))

    def test_inactive_outside_sdlc_projects(self):
        with tempfile.TemporaryDirectory() as d:
            res = run("guard_bash.py", stdin={"tool_name": "Bash", "tool_input": {"command": "git push --force"},
                                              "cwd": d}, env={"CLAUDE_PROJECT_DIR": d})
            self.assertEqual(decision(res.stdout), "none")


class WriteGuardTests(unittest.TestCase):
    def setUp(self):
        self.r = Repo()

    def tearDown(self):
        self.r.close()

    def write(self, path, content, tool="Write"):
        ti = {"file_path": str(self.r.path / path)}
        ti.update({"content": content} if tool == "Write" else {"old_string": "a", "new_string": content})
        res = self.r.hook("guard_write.py", {"tool_name": tool, "tool_input": ti})
        self.assertEqual(res.returncode, 0, res.stderr)
        return decision(res.stdout)

    def test_secrets_blocked(self):
        self.assertEqual(self.write("a.txt", "key = gsk_" + "A" * 40), "deny")
        self.assertEqual(self.write("a.txt", "-----BEGIN OPENSSH PRIVATE KEY-----", tool="Edit"), "deny")
        self.assertEqual(self.write("a.txt", "token ghp_" + "b" * 36), "deny")

    def test_normal_content_allowed(self):
        self.assertEqual(self.write("docs/a.md", "Use GROQ_KEY from the keychain; placeholder gsk_xxx"), "none")

    def test_state_file_protected(self):
        self.assertEqual(self.write(".sdlc/state.json", "{}"), "deny")

    def test_allowlist(self):
        self.r.config_update(secret_allowlist_paths=["scripts/secret-scan.sh"])
        self.assertEqual(self.write("scripts/secret-scan.sh", "gsk_" + "A" * 40), "none")


class StopHookTests(unittest.TestCase):
    def setUp(self):
        self.r = Repo()
        self.r.sdlc("activate", "--session", "S1", "--mode", "auto")

    def tearDown(self):
        self.r.close()

    def stop(self, session="S1"):
        res = self.r.hook("stop_continue.py", {"hook_event_name": "Stop", "session_id": session,
                                               "stop_hook_active": False})
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout) if res.stdout.strip() else {}

    def test_blocks_while_in_progress_and_stops_without_progress(self):
        self.assertEqual(self.stop().get("decision"), "block")
        second = self.stop()  # no progress since the first block
        self.assertEqual(second.get("decision"), "block")
        third = self.stop()   # idle limit reached → let it stop
        self.assertNotIn("decision", third)
        self.assertIn("paused", third.get("systemMessage", ""))

    def test_progress_resets_idle_counter(self):
        for i in range(4):
            self.assertEqual(self.stop().get("decision"), "block")
            self.r.sdlc("log", f"progress {i}")

    def test_other_session_not_hijacked(self):
        self.assertEqual(self.stop(session="OTHER"), {})

    def test_waiting_owner_allows_stop(self):
        self.r.sdlc("set", "--status", "waiting_owner")
        self.assertEqual(self.stop(), {})

    def test_step_mode_allows_stop(self):
        self.r.sdlc("activate", "--session", "S1", "--mode", "step")
        self.assertEqual(self.stop(), {})

    def test_budget_limit(self):
        self.r.config_update(max_auto_continuations=2)
        results = []
        for i in range(3):
            results.append(self.stop().get("decision"))
            self.r.sdlc("log", f"p{i}")
        self.assertEqual(results, ["block", "block", None])

    def test_unknown_session_never_continues(self):
        self.r.sdlc("activate", "--session", "${CLAUDE_SESSION_ID}")
        self.assertEqual(self.stop(), {})


class SessionAndPromptHookTests(unittest.TestCase):
    def setUp(self):
        self.r = Repo()

    def tearDown(self):
        self.r.close()

    def test_session_context(self):
        res = self.r.hook("session_context.py", {"hook_event_name": "SessionStart", "source": "compact"})
        ctx = json.loads(res.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("[SDLC]", ctx)
        self.assertIn("compacted", ctx)

    def test_owner_prompt_records_decision(self):
        self.r.sdlc("gate", "add", "H-0", "--blocks", "build")
        self.r.hook("owner_prompt.py", {"hook_event_name": "UserPromptSubmit", "prompt": "/sdlc:decide H-0 принимаю"})
        g = self.r.state()["gates"][0]
        self.assertEqual((g["status"], g["decided_by"]), ("accepted", "owner"))

    def test_owner_prompt_ignores_other_prompts(self):
        self.r.sdlc("gate", "add", "H-0", "--blocks", "build")
        self.r.hook("owner_prompt.py", {"hook_event_name": "UserPromptSubmit", "prompt": "please decide H-0 for me"})
        self.assertEqual(self.r.state()["gates"][0]["status"], "pending")


if __name__ == "__main__":
    unittest.main()
