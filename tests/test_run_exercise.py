"""run_exercise.py with a fake `claude`.

Each test builds a temporary git checkout with a bare origin (`.claude/kit.json`
naming main and a silent fixture `.claude/hooks/session_check.py`), writes a
fake `claude` (a small Python script) and runs run_exercise.py as a subprocess
with `--claude <fake>`. The launcher passes the fake a `--session-id`; the fake
prints a matching init and writes a fixture session log for that id under
`$LAUNCH_SESSION_PROJECTS_ROOT/fixture-project/`, built from the case number
and the text below the marker in the prompt it was given. FAKE_SCENARIO (JSON,
case number -> variant) picks a variant per case; the default is the expected
log. Not released.

    python3 -m unittest discover -s tests
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
TOOL = KIT / "run_exercise.py"

FAKE = r'''#!{python}
import json, os, re, sys
SIDE = {side!r}
args = sys.argv[1:]
with open(os.path.join(SIDE, "argv.log"), "a") as f:
    f.write(json.dumps(args) + "\n")
sid = args[args.index("--session-id") + 1]
prompt = sys.stdin.read()
case = re.search(r"case (\d)", prompt).group(1)
marker = "--- text to send: everything below this line, unchanged ---\n"
text = prompt.split(marker, 1)[1]
target = {{"1": "pulse", "2": "coder", "3": "coder", "4": "general-purpose"}}[case]
variant = json.loads(os.environ.get("FAKE_SCENARIO", "{{}}")).get(case, "ok")

def emit(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

if variant == "wrong_id":
    emit({{"type": "system", "subtype": "init", "cwd": os.getcwd(),
          "session_id": "00000000-0000-4000-8000-00000000dead"}})
    sys.exit(0)

tid = "toolu_fixture_case" + case
recs = [{{"type": "user", "message": {{"role": "user", "content": prompt}}}},
        {{"type": "assistant", "message": {{"role": "assistant", "content": [
            {{"type": "tool_use", "id": tid, "name": "Agent",
              "input": {{"subagent_type": target, "description": "case " + case,
                        "prompt": text, "run_in_background": False}}}}]}}}}]

def hook(decision):
    out = {{"hookSpecificOutput": {{"hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": "dispatch_guard: fixture " + decision}}}}
    recs.append({{"type": "attachment", "attachment": {{
        "type": "hook_success", "hookName": "PreToolUse:Agent", "toolUseID": tid,
        "hookEvent": "PreToolUse", "stdout": json.dumps(out) + "\n", "exitCode": 0,
        "command": "python3 \"${{CLAUDE_PROJECT_DIR}}/.claude/hooks/dispatch_guard.py\""}}}})

def result(text, is_error=False, denial=None, tur=None):
    rec = {{"type": "user", "message": {{"role": "user", "content": [
        {{"type": "tool_result", "tool_use_id": tid, "content": text,
          "is_error": is_error}}]}}, "toolUseResult": tur if tur is not None else "Error: " + text}}
    if denial is not None:
        rec["toolDenialKind"] = denial
    recs.append(rec)

def completed(text):
    result([{{"type": "text", "text": text}}],
           tur={{"status": "completed", "agentId": "afixture" + case,
                "content": [{{"type": "text", "text": text}}]}})

MISMATCH = "PreToolUse:Agent hook error: dispatch_guard: Type 'pulse' may only be dispatched to 'pulse', not 'coder'."
UNKNOWN = ("PreToolUse:Agent hook error: dispatch_guard: subagent type 'general-purpose' "
           "may not be dispatched. Only coder, pulse may; built-in agent types are blocked.")

if case == "1":
    hook("allow")
    if variant != "no_result":
        completed("The first line of README.md is `# Fixture`.")
elif case == "2":
    hook("ask")
    if variant == "ran":
        completed("exercise case 2")
    else:
        result("Permission to use Agent has been denied.", True, "fixture-denial")
elif case == "3":
    if variant == "deny_no_kind":
        hook("deny")
        result(MISMATCH, True)
    else:
        result(MISMATCH, True, "permission-rule")
else:
    result(UNKNOWN, True, "permission-rule")

root = os.environ["LAUNCH_SESSION_PROJECTS_ROOT"]
os.makedirs(os.path.join(root, "fixture-project"), exist_ok=True)
with open(os.path.join(root, "fixture-project", sid + ".jsonl"), "w") as f:
    for i, rec in enumerate(recs):
        rec.setdefault("timestamp", "2026-01-01T00:00:%02d.000Z" % i)
        f.write(json.dumps(rec, sort_keys=(i % 2 == 0)) + "\n")
emit({{"type": "system", "subtype": "init", "cwd": os.getcwd(), "session_id": sid}})
emit({{"type": "result", "subtype": "success", "session_id": sid, "total_cost_usd": 0}})
'''


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                           "-c", "init.defaultBranch=main", *args],
                          cwd=str(cwd), check=True, capture_output=True,
                          universal_newlines=True).stdout


def snapshot(root, skip):
    """sha256 of every file under root, except under the paths in skip."""
    found = {}
    for dirpath, dirs, files in os.walk(str(root)):
        dirs[:] = [d for d in dirs if os.path.join(dirpath, d) not in skip]
        for name in files:
            p = os.path.join(dirpath, name)
            with open(p, "rb") as f:
                found[p] = hashlib.sha256(f.read()).hexdigest()
    return found


class RunExerciseTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(os.path.realpath(self._tmp.name))
        self.side = self.tmp / "side"
        self.side.mkdir()
        self.projects = self.tmp / "projects"
        self.out = self.tmp / "out"
        origin = self.tmp / "origin.git"
        git(self.tmp, "init", "-q", "--bare", str(origin))
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        (self.repo / ".claude" / "hooks").mkdir(parents=True)
        (self.repo / ".claude" / "kit.json").write_text(
            json.dumps({"protected_branches": ["main"]}), encoding="utf-8")
        (self.repo / ".claude" / "hooks" / "session_check.py").write_text(
            "import sys\nsys.stdin.read()\n", encoding="utf-8")
        (self.repo / "README.md").write_text("# Fixture\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "one")
        git(self.repo, "remote", "add", "origin", str(origin))
        git(self.repo, "push", "-q", "-u", "origin", "main")
        self.fake = self.side / "fake_claude_exercise.py"
        self.fake.write_text(FAKE.format(python=sys.executable, side=str(self.side)),
                             encoding="utf-8")
        self.fake.chmod(0o755)

    def tearDown(self):
        wt = self.out / "worktree"
        if wt.exists():
            subprocess.run(["git", "-C", str(self.repo), "worktree", "remove", "--force",
                            str(wt)], capture_output=True)
        self._tmp.cleanup()

    def run_tool(self, *extra, scenario=None, args=None):
        env = dict(os.environ, LAUNCH_SESSION_PROJECTS_ROOT=str(self.projects))
        env.pop("FAKE_SCENARIO", None)
        if scenario:
            env["FAKE_SCENARIO"] = json.dumps(scenario)
        if args is None:
            args = ["--repo", str(self.repo), "--out-dir", str(self.out),
                    "--claude", str(self.fake), "--timeout", "30", *extra]
        return subprocess.run([sys.executable, str(TOOL), *args], cwd=str(self.tmp),
                              env=env, capture_output=True, universal_newlines=True,
                              timeout=300)

    def evidence(self, r):
        return [l for l in r.stdout.splitlines() if l.startswith("case ")]

    def test_a_all_four_pass(self):
        r = self.run_tool()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        lines = self.evidence(r)
        self.assertEqual(len(lines), 4, r.stdout)
        for n, line in enumerate(lines, 1):
            self.assertTrue(line.startswith("case %d " % n), line)
            self.assertTrue(line.endswith("PASS"), line)
            self.assertIn("toolu_fixture_case%d" % n, line)
        self.assertIn("decision allow", lines[0])
        self.assertIn("decision ask", lines[1])
        self.assertIn("toolDenialKind fixture-denial", lines[1])
        self.assertIn("toolDenialKind permission-rule", lines[2])
        self.assertIn("dispatch_guard", lines[3])
        written = (self.out / "evidence.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(written, lines)
        for n in range(1, 5):
            self.assertTrue((self.out / ("case-%d.prompt" % n)).is_file())
            self.assertTrue((self.out / ("case-%d.jsonl" % n)).is_file())

    def test_b_deny_without_denial_kind_fails(self):
        r = self.run_tool(scenario={"3": "deny_no_kind"})
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        lines = self.evidence(r)
        self.assertIn("FAIL", lines[2])
        self.assertIn("toolDenialKind", lines[2].split("FAIL", 1)[1])
        for i in (0, 1, 3):
            self.assertTrue(lines[i].endswith("PASS"), lines[i])

    def test_c_case2_call_ran_fails(self):
        r = self.run_tool(scenario={"2": "ran"})
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        lines = self.evidence(r)
        self.assertIn("FAIL", lines[1])
        self.assertTrue(lines[0].endswith("PASS"), lines[0])

    def test_d_case1_no_result_fails(self):
        r = self.run_tool(scenario={"1": "no_result"})
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        lines = self.evidence(r)
        self.assertIn("FAIL", lines[0])
        self.assertIn("no tool_result", lines[0])

    def test_e_launcher_exit_4_fails_quoting_report(self):
        r = self.run_tool(scenario={"2": "wrong_id"})
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        lines = self.evidence(r)
        self.assertIn("FAIL: launcher exit 4", lines[1])
        self.assertIn("outcome: wrong session: init session_id", lines[1])
        for i in (0, 2, 3):
            self.assertTrue(lines[i].endswith("PASS"), lines[i])

    def test_f_cases_option_runs_only_those(self):
        r = self.run_tool("--cases", "3")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        lines = self.evidence(r)
        self.assertEqual(len(lines), 1, r.stdout)
        self.assertTrue(lines[0].startswith("case 3 "), lines[0])
        self.assertEqual(len((self.side / "argv.log").read_text().splitlines()), 1)
        self.assertEqual(sorted(p.name for p in self.out.iterdir()),
                         ["case-3.jsonl", "case-3.jsonl.stderr", "case-3.prompt",
                          "evidence.txt", "worktree"])

    def test_g_worktree_detached_at_origin_and_kept(self):
        r = self.run_tool("--cases", "1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        wt = self.out / "worktree"
        self.assertTrue((wt / "README.md").is_file())
        listing = git(self.repo, "worktree", "list", "--porcelain")
        block = [b for b in listing.split("\n\n") if ("worktree %s" % wt) in b]
        self.assertEqual(len(block), 1, listing)
        self.assertIn("detached", block[0])
        self.assertIn("HEAD %s" % git(self.repo, "rev-parse", "origin/main").strip(), block[0])
        self.assertIn(str(wt), r.stdout)
        self.assertIn("git worktree remove", r.stdout)
        self.assertIn("find_dispatches.py", r.stdout)

    def test_h_writes_nothing_outside_out_dir(self):
        skip = {str(self.out), str(self.side), str(self.projects),
                str(self.repo / ".git" / "worktrees")}
        before = snapshot(self.tmp, skip)
        kit_before = snapshot(KIT, {str(KIT / ".git")})
        r = self.run_tool()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(snapshot(self.tmp, skip), before)
        self.assertEqual(snapshot(KIT, {str(KIT / ".git")}), kit_before)

    def test_i_bad_arguments_exit_2(self):
        cases = {
            "no --repo": ["--out-dir", str(self.out)],
            "no --out-dir": ["--repo", str(self.repo)],
            "case 5": ["--repo", str(self.repo), "--out-dir", str(self.out), "--cases", "5"],
            "empty cases": ["--repo", str(self.repo), "--out-dir", str(self.out), "--cases", ""],
            "budget 0": ["--repo", str(self.repo), "--out-dir", str(self.out),
                         "--max-budget-usd", "0"],
            "timeout x": ["--repo", str(self.repo), "--out-dir", str(self.out),
                          "--timeout", "x"],
        }
        problems = []
        for name, args in cases.items():
            r = self.run_tool(args=args)
            if r.returncode != 2:
                problems.append("%s: exit %d" % (name, r.returncode))
            if "usage:" not in r.stderr:
                problems.append("%s: 'usage:' not found in %r" % (name, r.stderr))
            if self.out.exists():
                problems.append("%s: %s was created" % (name, self.out))
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
