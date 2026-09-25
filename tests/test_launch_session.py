"""launch_session.py with fake `claude` executables.

Each test builds a temporary git checkout with a bare origin (HEAD equal to
origin/main, `.claude/kit.json` naming main, and a fixture
`.claude/hooks/session_check.py`), writes a fake `claude` (a small Python
script) into a temporary directory, and runs the launcher as a subprocess
with `--claude <fake>` and short `--timeout`/`--grace` values. Every fake
appends its argv to a log file, so a test can show that claude was never
invoked. Not released.

    python3 -m unittest discover -s tests
"""
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
TOOL = KIT / "launch_session.py"

SILENT_HOOK = "import sys\nsys.stdin.read()\n"
WARNING = "Claude-kit session_check: HEAD is 1 commit behind origin/main (fixture)."
WARNING_HOOK = ("import json, sys\nsys.stdin.read()\n"
                "print(json.dumps({'systemMessage': %r}))\n" % WARNING)

# Prelude shared by every fake: log argv, read the prompt from stdin, and
# work out the init message the launcher expects.
PRELUDE = r'''#!{python}
import json, os, signal, subprocess, sys, time
SIDE = {side!r}
with open(os.path.join(SIDE, "argv.log"), "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\n")
args = sys.argv[1:]
sid = args[args.index("--session-id") + 1] if "--session-id" in args else None
prompt = sys.stdin.read()
with open(os.path.join(SIDE, "prompt.txt"), "w") as f:
    f.write(prompt)

def emit(text):
    sys.stdout.write(text + "\n")
    sys.stdout.flush()
    with open(os.path.join(SIDE, "emitted.txt"), "a") as f:
        f.write(text + "\n")

def init(session_id=None, cwd=None):
    emit(json.dumps({{"type": "system", "subtype": "init",
                     "session_id": session_id or sid, "cwd": cwd or os.getcwd(),
                     "tools": [], "model": "fake"}}))

def save_pids(*pids):
    with open(os.path.join(SIDE, "pids.txt"), "w") as f:
        f.write(" ".join(str(p) for p in pids))
'''

BODIES = {
    "ok": '''
emit('{"type": "system", "subtype": "hook_response",   "note": "spacing kept"}')
init()
emit(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "ready"}]}}))
emit(json.dumps({"type": "result", "subtype": "success", "session_id": sid}))
sys.exit(0)
''',
    "hang": '''
init()
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
save_pids(os.getpid(), child.pid)
time.sleep(120)
''',
    "ignore_term": '''
signal.signal(signal.SIGTERM, signal.SIG_IGN)
init()
save_pids(os.getpid())
time.sleep(120)
''',
    "wrong_id": '''
init(session_id="00000000-0000-4000-8000-00000000dead")
save_pids(os.getpid())
time.sleep(120)
''',
    "wrong_cwd": '''
init(cwd="/nonexistent/elsewhere")
save_pids(os.getpid())
time.sleep(120)
''',
    "no_init": '''
save_pids(os.getpid())
time.sleep(120)
''',
    # (o), (o3): write the session log where the projects-root override says,
    # under directory names no sanitising of the cwd gives.
    "log_one": '''
root = os.environ["LAUNCH_SESSION_PROJECTS_ROOT"]
for name in ["unrelated-project-name"]:
    os.makedirs(os.path.join(root, name), exist_ok=True)
    with open(os.path.join(root, name, sid + ".jsonl"), "w") as f:
        f.write("{}\\n")
init()
emit(json.dumps({"type": "result", "subtype": "success", "session_id": sid}))
sys.exit(0)
''',
    "log_two": '''
root = os.environ["LAUNCH_SESSION_PROJECTS_ROOT"]
for name in ["unrelated-project-name", "another name_here.x"]:
    os.makedirs(os.path.join(root, name), exist_ok=True)
    with open(os.path.join(root, name, sid + ".jsonl"), "w") as f:
        f.write("{}\\n")
init()
emit(json.dumps({"type": "result", "subtype": "success", "session_id": sid}))
sys.exit(0)
''',
}


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                    "-c", "init.defaultBranch=main", *args],
                   cwd=str(cwd), check=True, capture_output=True)


def alive(pid):
    """True if pid is a live process (a zombie counts as dead)."""
    try:
        with open("/proc/%d/stat" % pid) as f:
            stat = f.read()
    except (FileNotFoundError, ProcessLookupError):
        return False
    return stat[stat.rindex(")") + 2] != "Z"


def snapshot(root):
    found = {}
    for dirpath, _dirs, files in os.walk(str(root)):
        for name in files:
            p = os.path.join(dirpath, name)
            with open(p, "rb") as f:
                found[p] = hashlib.sha256(f.read()).hexdigest()
    return found


class LaunchSessionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(os.path.realpath(self._tmp.name))
        self.side = self.tmp / "side"
        self.side.mkdir()
        self.outdir = self.tmp / "out"
        self.outdir.mkdir()
        self.out = self.outdir / "stream.jsonl"
        self.prompt = self.tmp / "prompt.txt"
        self.prompt.write_text("Reply with the single word ready.\n", encoding="utf-8")

    def tearDown(self):
        pids = self.side / "pids.txt"
        if pids.exists():
            for pid in pids.read_text().split():
                try:
                    os.kill(int(pid), 9)
                except (ProcessLookupError, PermissionError):
                    pass
        self._tmp.cleanup()

    def make_repo(self, hook=SILENT_HOOK):
        origin = self.tmp / "origin.git"
        git(self.tmp, "init", "-q", "--bare", str(origin))
        repo = self.tmp / "repo"
        repo.mkdir()
        git(repo, "init", "-q")
        (repo / ".claude" / "hooks").mkdir(parents=True)
        (repo / ".claude" / "kit.json").write_text(
            json.dumps({"protected_branches": ["main"]}), encoding="utf-8")
        if hook is not None:
            (repo / ".claude" / "hooks" / "session_check.py").write_text(hook, encoding="utf-8")
        (repo / "file.txt").write_text("one\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "one")
        git(repo, "remote", "add", "origin", str(origin))
        git(repo, "push", "-q", "-u", "origin", "main")
        self.repo = repo
        return repo

    def make_fake(self, body):
        fake = self.tmp / "fakes" / ("fake_claude_%s.py" % body)
        fake.parent.mkdir(exist_ok=True)
        fake.write_text(PRELUDE.format(python=sys.executable, side=str(self.side))
                        + BODIES[body], encoding="utf-8")
        fake.chmod(0o755)
        return fake

    def launch_args(self, *extra, claude=None, timeout="30", grace="2", cwd=None):
        args = [sys.executable, str(TOOL), "--cwd", str(cwd or self.repo),
                "--prompt-file", str(self.prompt), "--out", str(self.out),
                "--timeout", timeout, "--grace", grace]
        if claude is not None:
            args += ["--claude", str(claude)]
        return args + list(extra)

    def launch(self, *extra, claude=None, timeout="30", grace="2", cwd=None, env=None):
        args = self.launch_args(*extra, claude=claude, timeout=timeout, grace=grace, cwd=cwd)
        start = time.monotonic()
        p = subprocess.run(args, cwd=str(self.tmp), capture_output=True, text=True,
                           timeout=120, env=env)
        p.elapsed = time.monotonic() - start
        return p

    def assertExit(self, p, code):
        self.assertEqual(p.returncode, code, "exit %d\nstdout:\n%s\nstderr:\n%s"
                         % (p.returncode, p.stdout, p.stderr))

    def argv_calls(self):
        log = self.side / "argv.log"
        if not log.exists():
            return []
        return [json.loads(l) for l in log.read_text().splitlines()]

    def assertGone(self, pids):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and any(alive(p) for p in pids):
            time.sleep(0.1)
        self.assertEqual([p for p in pids if alive(p)], [], "processes left")

    def pids(self):
        return [int(p) for p in (self.side / "pids.txt").read_text().split()]

    # (a)
    def test_a_finished_stream_verbatim(self):
        self.make_repo()
        p = self.launch(claude=self.make_fake("ok"))
        self.assertExit(p, 0)
        self.assertEqual(self.out.read_bytes(), (self.side / "emitted.txt").read_bytes())
        self.assertIn(b'"spacing kept"}', self.out.read_bytes())
        self.assertEqual((self.side / "prompt.txt").read_text(),
                         "Reply with the single word ready.\n")
        calls = self.argv_calls()
        self.assertEqual(len(calls), 1)
        argv = calls[0]
        sid = argv[argv.index("--session-id") + 1]
        for flag in ("-p", "--verbose"):
            self.assertIn(flag, argv)
        self.assertEqual(argv[argv.index("--output-format") + 1], "stream-json")
        self.assertEqual(argv[argv.index("--permission-prompts") + 1], "none")
        self.assertIn("session id: %s" % sid, p.stdout)
        self.assertIn("claude exit code: 0", p.stdout)
        self.assertIn("outcome: finished", p.stdout)
        self.assertTrue(os.path.exists(str(self.out) + ".stderr"))

    # (b)
    def test_b_hanging_with_child_timed_out_group_gone(self):
        self.make_repo()
        p = self.launch(claude=self.make_fake("hang"), timeout="2", grace="3")
        self.assertExit(p, 3)
        pids = self.pids()
        self.assertEqual(len(pids), 2)
        self.assertGone(pids)
        self.assertLess(p.elapsed, 2 + 3 + 8)
        self.assertGreaterEqual(p.elapsed, 2)
        self.assertIn("outcome: timed out", p.stdout)
        self.assertNotIn("left", p.stdout.split("outcome:")[1])

    # (c)
    def test_c_sigterm_ignored_sigkill_after_grace(self):
        self.make_repo()
        p = self.launch(claude=self.make_fake("ignore_term"), timeout="1", grace="2")
        self.assertExit(p, 3)
        self.assertGone(self.pids())
        self.assertGreaterEqual(p.elapsed, 1 + 2)
        self.assertIn("SIGKILL", p.stdout)

    # (d)
    def test_d_session_id_differs(self):
        self.make_repo()
        p = self.launch(claude=self.make_fake("wrong_id"), timeout="30", grace="2")
        self.assertExit(p, 4)
        self.assertIn("session_id", p.stdout)
        self.assertLess(p.elapsed, 20)
        self.assertGone(self.pids())

    # (e)
    def test_e_cwd_differs(self):
        self.make_repo()
        p = self.launch(claude=self.make_fake("wrong_cwd"), timeout="30", grace="2")
        self.assertExit(p, 4)
        self.assertIn("/nonexistent/elsewhere", p.stdout)
        self.assertLess(p.elapsed, 20)
        self.assertGone(self.pids())

    # (f)
    def test_f_session_check_warns_claude_never_invoked(self):
        self.make_repo(hook=WARNING_HOOK)
        p = self.launch(claude=self.make_fake("ok"))
        self.assertExit(p, 4)
        self.assertIn(WARNING, p.stdout)
        self.assertEqual(self.argv_calls(), [])
        self.assertFalse(self.out.exists())

    # (f2)
    def test_f2_session_check_missing_claude_never_invoked(self):
        self.make_repo(hook=None)
        p = self.launch(claude=self.make_fake("ok"))
        self.assertExit(p, 4)
        self.assertIn("session_check.py", p.stdout)
        self.assertEqual(self.argv_calls(), [])
        self.assertFalse(self.out.exists())

    # (g)
    def test_g_head_not_expected_commit(self):
        repo = self.make_repo()
        (repo / "file.txt").write_text("two\n", encoding="utf-8")
        git(repo, "commit", "-q", "-am", "two")
        p = self.launch(claude=self.make_fake("ok"))
        self.assertExit(p, 4)
        self.assertIn("HEAD", p.stdout)
        self.assertEqual(self.argv_calls(), [])
        # an explicit --expect-commit that HEAD matches passes the check
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo),
                              capture_output=True, text=True).stdout.strip()
        p = self.launch("--expect-commit", head, claude=self.make_fake("ok"))
        self.assertExit(p, 0)

    # (h)
    def test_h_tracked_change(self):
        repo = self.make_repo()
        (repo / "file.txt").write_text("changed\n", encoding="utf-8")
        p = self.launch(claude=self.make_fake("ok"))
        self.assertExit(p, 4)
        self.assertIn("file.txt", p.stdout)
        self.assertEqual(self.argv_calls(), [])

    # (i)
    def test_i_no_init_before_limit(self):
        self.make_repo()
        p = self.launch(claude=self.make_fake("no_init"), timeout="2", grace="1")
        self.assertExit(p, 5)
        self.assertIn("failed to start", p.stdout)
        self.assertGone(self.pids())

    # (j)
    def test_j_missing_claude(self):
        self.make_repo()
        p = self.launch(claude=self.tmp / "no" / "such" / "claude")
        self.assertExit(p, 5)
        self.assertIn("failed to start", p.stdout)
        self.assertFalse(self.out.exists())

    # (k)
    def test_k_bad_arguments(self):
        self.make_repo()
        cases = {
            "no arguments": [sys.executable, str(TOOL)],
            "timeout zero": None,
            "out exists": None,
        }
        for name in cases:
            with self.subTest(name):
                if name == "no arguments":
                    p = subprocess.run(cases[name], capture_output=True, text=True,
                                       timeout=60)
                elif name == "timeout zero":
                    p = self.launch(claude=self.make_fake("ok"), timeout="0")
                else:
                    self.out.write_text("keep me\n", encoding="utf-8")
                    p = self.launch(claude=self.make_fake("ok"))
                    self.assertEqual(self.out.read_text(), "keep me\n")
                self.assertExit(p, 2)
                self.assertIn("usage:", p.stderr)
        self.assertEqual(self.argv_calls(), [])

    # (l)
    def test_l_writes_only_out_and_stderr(self):
        self.make_repo()
        fake = self.make_fake("ok")
        watched = [self.repo, self.tmp / "origin.git", self.tmp / "fakes", self.outdir]
        before = {}
        for d in watched:
            before.update(snapshot(d))
        before[str(self.prompt)] = hashlib.sha256(self.prompt.read_bytes()).hexdigest()
        p = self.launch(claude=fake)
        self.assertExit(p, 0)
        after = {}
        for d in watched:
            after.update(snapshot(d))
        after[str(self.prompt)] = hashlib.sha256(self.prompt.read_bytes()).hexdigest()
        added = sorted(set(after) - set(before))
        self.assertEqual(added, [str(self.out), str(self.out) + ".stderr"])
        self.assertEqual(sorted(set(before) - set(after)), [])
        changed = [k for k in before if before[k] != after[k]]
        self.assertEqual(changed, [])

    # (m), (n)
    def interrupt(self, sig):
        self.make_repo()
        args = self.launch_args(claude=self.make_fake("hang"), timeout="60", grace="3")
        launcher = subprocess.Popen(args, cwd=str(self.tmp), stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True)
        try:
            pidfile = self.side / "pids.txt"
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and not (
                    pidfile.exists() and len(pidfile.read_text().split()) == 2):
                time.sleep(0.1)
            pids = self.pids()
            self.assertEqual(len(pids), 2)
            launcher.send_signal(sig)
            out, err = launcher.communicate(timeout=60)
        finally:
            if launcher.poll() is None:
                launcher.kill()
                launcher.wait()
        self.assertGone(pids)
        self.assertEqual(launcher.returncode, 130,
                         "exit %d\nstdout:\n%s\nstderr:\n%s" % (launcher.returncode, out, err))
        self.assertIn("outcome: interrupted", out)

    def test_m_sigint_stops_group(self):
        self.interrupt(signal.SIGINT)

    def test_n_sigterm_stops_group(self):
        self.interrupt(signal.SIGTERM)

    # (o), (o2), (o3)
    def projects_env(self):
        root = self.tmp / "projects root"
        root.mkdir()
        return root, dict(os.environ, LAUNCH_SESSION_PROJECTS_ROOT=str(root))

    def session_id(self):
        argv = self.argv_calls()[0]
        return argv[argv.index("--session-id") + 1]

    def test_o_log_found_by_session_id(self):
        self.make_repo()
        root, env = self.projects_env()
        p = self.launch(claude=self.make_fake("log_one"), env=env)
        self.assertExit(p, 0)
        path = root / "unrelated-project-name" / (self.session_id() + ".jsonl")
        self.assertTrue(path.exists())
        self.assertIn("log: %s" % path, p.stdout)
        self.assertNotIn("not found", p.stdout)

    def test_o2_log_not_found_names_glob(self):
        self.make_repo()
        root, env = self.projects_env()
        p = self.launch(claude=self.make_fake("ok"), env=env)
        self.assertExit(p, 0)
        self.assertIn("not found", p.stdout)
        self.assertIn(os.path.join(str(root), "*", self.session_id() + ".jsonl"), p.stdout)

    def test_o3_two_logs_ambiguous(self):
        self.make_repo()
        root, env = self.projects_env()
        p = self.launch(claude=self.make_fake("log_two"), env=env)
        self.assertExit(p, 0)
        sid = self.session_id()
        self.assertIn("ambiguous", p.stdout)
        for name in ("unrelated-project-name", "another name_here.x"):
            self.assertIn(str(root / name / (sid + ".jsonl")), p.stdout)


if __name__ == "__main__":
    unittest.main()
