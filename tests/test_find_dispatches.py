"""find_dispatches.py on a throwaway repository with three linked worktrees.

The fixture is a temporary git repository: commit A holds a dispatch_guard.py
without the shared counter (pre-T1), commit B one with it (T1+), and commit C
adds a tracked store under prompts/preserved/. Linked worktrees: one at A and
two at B. Each test writes untracked hook-saved files into the worktrees and
runs the tool as a subprocess from the main checkout. Not released.

    python3 -m unittest discover -s tests
"""
import datetime
import hashlib
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
TOOL = KIT / "find_dispatches.py"
GIT_ID = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
DELIM = "--- verbatim prompt follows ---"
STATUS_LINE = re.compile(r"^(in-store|record|refused|stop)\s+(\S+)(.*)$")


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *GIT_ID, *args],
                          capture_output=True, text=True, check=True).stdout


def hook_file(head, preserved, body, target="coder", type_="build"):
    return (f"HEAD: {head}\nTarget subagent: {target}\nType: {type_}\n"
            f"Preserved: {preserved} by .claude/hooks/dispatch_guard.py\n"
            f"{DELIM}\n{body}\n")


def today_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="find_dispatches_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        main = self.main = self.tmp / "main"
        main.mkdir()
        git(main, "init", "-q", "-b", "main")
        hooks = main / ".claude" / "hooks"
        hooks.mkdir(parents=True)
        guard = hooks / "dispatch_guard.py"
        guard.write_text("# numbers within its own worktree\n")
        git(main, "add", "-A")
        git(main, "commit", "-q", "-m", "A")
        self.A = git(main, "rev-parse", "HEAD").strip()
        guard.write_text("# numbers from the shared counter\nCOUNTER = 'dispatch-seq'\n")
        git(main, "add", "-A")
        git(main, "commit", "-q", "-m", "B")
        self.B = git(main, "rev-parse", "HEAD").strip()
        store = main / "prompts" / "preserved"
        store.mkdir(parents=True)
        self.store = {}
        for name, preserved in [("2026-01-10-01", "2026-01-10T08:00:00Z"),
                                ("2026-01-10-02", "2026-01-10T08:30:00Z"),
                                ("2026-01-10-03", "2026-01-10T09:30:00Z"),
                                ("2026-01-11-01", "2026-01-11T08:00:00Z")]:
            text = hook_file(self.B, preserved, f"store body {name}")
            (store / f"{name}.md").write_text(text)
            self.store[name] = text
        git(main, "add", "-A")
        git(main, "commit", "-q", "-m", "C: store")
        self.wt = []
        for i, commit in enumerate([self.A, self.B, self.B], 1):
            path = self.tmp / f"wt{i}"
            git(main, "worktree", "add", "-q", "--detach", str(path), commit)
            self.wt.append(path)

    def put(self, wt, name, text):
        """An untracked file under a worktree's prompts/preserved/."""
        d = wt / "prompts" / "preserved"
        d.mkdir(parents=True, exist_ok=True)
        p = d / name
        p.write_text(text)
        return p

    def run_tool(self):
        return subprocess.run([sys.executable, str(TOOL)], cwd=str(self.main),
                              capture_output=True, text=True)

    def items(self, out):
        return [m.groups() for m in map(STATUS_LINE.match, out.splitlines()) if m]

    def section(self, out, title):
        lines = out.splitlines()
        start = lines.index(title) + 1
        body = []
        for line in lines[start:]:
            if not line.strip() or line.endswith(":") and not line.startswith(" "):
                break
            body.append(line.strip())
        return body

    def copies(self, out):
        return [c for c in self.section(out, "Copy commands:") if c.startswith("cp ")]

    def citations(self, out):
        return [c for c in self.section(out, "Citations:") if c != "(none)"]

    def cp(self, src, name):
        return f"cp -- {shlex.quote(str(src))} prompts/preserved/{name}.md"

    # (a)
    def test_t1_file_with_free_name_keeps_it(self):
        text = hook_file(self.B, "2026-01-11T10:00:00Z", "a T1+ dispatch")
        src = self.put(self.wt[1], "2026-01-11-05.md", text)
        r = self.run_tool()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual([i[:2] for i in self.items(r.stdout)], [("record", "2026-01-11-05")])
        self.assertEqual(self.copies(r.stdout), [self.cp(src, "2026-01-11-05")])
        cites = self.citations(r.stdout)
        self.assertEqual(len(cites), 1, r.stdout)
        data = text.encode()
        for part in (str(src), f"{len(data)} bytes", hashlib.sha256(data).hexdigest(),
                     "Preserved: 2026-01-11T10:00:00Z", self.B, "coder", "build",
                     "2026-01-11-05"):
            self.assertIn(part, cites[0])

    # (b)
    def test_pre_t1_files_numbered_above_store_in_preserved_order(self):
        late = self.put(self.wt[0], "2026-01-10-01.md",
                        hook_file(self.A, "2026-01-10T12:00:00Z", "pre-T1 late"))
        # A worktree at B holding a file whose header HEAD is A.
        early = self.put(self.wt[1], "2026-01-10-07.md",
                         hook_file(self.A, "2026-01-10T09:00:00Z", "pre-T1 early"))
        r = self.run_tool()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(sorted(i[:2] for i in self.items(r.stdout)),
                         [("record", "2026-01-10-04"), ("record", "2026-01-10-05")])
        self.assertEqual(sorted(self.copies(r.stdout)),
                         sorted([self.cp(early, "2026-01-10-04"),
                                 self.cp(late, "2026-01-10-05")]))

    # (c)
    def test_file_identical_to_store_file_under_another_name_is_in_store(self):
        self.put(self.wt[2], "2026-01-12-01.md", self.store["2026-01-10-02"])
        r = self.run_tool()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual([i[:2] for i in self.items(r.stdout)], [("in-store", "2026-01-10-02")])
        self.assertEqual(self.copies(r.stdout), [])
        self.assertEqual(self.citations(r.stdout), [])

    # (d)
    def test_t1_name_taken_in_store_by_other_content_stops(self):
        self.put(self.wt[1], "2026-01-10-02.md",
                 hook_file(self.B, "2026-01-10T10:00:00Z", "different content"))
        r = self.run_tool()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual([i[0] for i in self.items(r.stdout)], ["stop"])
        self.assertEqual(self.copies(r.stdout), [])

    # (e)
    def test_t1_name_date_differs_from_preserved_date_stops(self):
        self.put(self.wt[1], "2026-01-13-01.md",
                 hook_file(self.B, "2026-01-14T10:00:00Z", "misdated"))
        r = self.run_tool()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual([i[0] for i in self.items(r.stdout)], ["stop"])
        self.assertEqual(self.copies(r.stdout), [])

    # (f)
    def test_header_head_not_in_repo_stops(self):
        self.put(self.wt[1], "2026-01-11-06.md",
                 hook_file("d" * 40, "2026-01-11T10:00:00Z", "unknown head"))
        r = self.run_tool()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual([i[0] for i in self.items(r.stdout)], ["stop"])
        self.assertEqual(self.copies(r.stdout), [])

    # (g)
    def test_file_without_hook_header_stops(self):
        cases = {
            "no delimiter": "just some notes\nHEAD: x\n",
            "no Preserved line": f"HEAD: {self.B}\nType: build\n{DELIM}\nbody\n",
            "no HEAD line": f"Preserved: 2026-01-11T10:00:00Z by x\n{DELIM}\nbody\n",
        }
        for label, text in cases.items():
            with self.subTest(label):
                p = self.put(self.wt[1], "2026-01-11-07.md", text)
                r = self.run_tool()
                p.unlink()
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                items = self.items(r.stdout)
                self.assertEqual([i[0] for i in items], ["stop"])
                self.assertIn("not hook-saved", items[0][2])
                self.assertEqual(self.copies(r.stdout), [])

    # (h)
    def test_pre_t1_file_preserved_today_is_refused(self):
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.put(self.wt[0], "2026-01-10-02.md", hook_file(self.A, now, "today's"))
        r = self.run_tool()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        items = self.items(r.stdout)
        self.assertEqual([i[0] for i in items], ["refused"])
        self.assertTrue(items[0][1].startswith(today_utc() + "-"), items)
        self.assertIn("dated today; rerun after UTC midnight", items[0][2])
        self.assertEqual(self.copies(r.stdout), [])
        self.assertEqual(self.citations(r.stdout), [])

    # (i)
    def test_same_content_in_two_worktrees_is_one_item(self):
        text = hook_file(self.B, "2026-01-11T11:00:00Z", "saved twice")
        one = self.put(self.wt[1], "2026-01-11-02.md", text)
        two = self.put(self.wt[2], "2026-01-11-02.md", text)
        r = self.run_tool()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual([i[:2] for i in self.items(r.stdout)], [("record", "2026-01-11-02")])
        self.assertEqual(len(self.copies(r.stdout)), 1, r.stdout)
        self.assertIn(str(one), r.stdout)
        self.assertIn(str(two), r.stdout)

    # (j)
    def test_running_checkouts_own_untracked_store_file_not_scanned(self):
        own = self.put(self.main, "2026-01-11-03.md",
                       hook_file(self.B, "2026-01-11T12:00:00Z", "own"))
        other = self.put(self.wt[1], "2026-01-11-04.md",
                         hook_file(self.B, "2026-01-11T13:00:00Z", "other"))
        r = self.run_tool()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        warnings = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith("warning:")]
        self.assertEqual(len(warnings), 1, r.stdout + r.stderr)
        self.assertRegex(warnings[0], r"\b1 untracked file")
        self.assertNotIn(str(own), r.stdout)
        self.assertNotIn(hashlib.sha256(own.read_bytes()).hexdigest(), r.stdout)
        self.assertEqual([i[:2] for i in self.items(r.stdout)], [("record", "2026-01-11-04")])
        self.assertEqual(self.copies(r.stdout), [self.cp(other, "2026-01-11-04")])

    # (k)
    def test_read_only(self):
        self.put(self.wt[0], "2026-01-10-01.md",
                 hook_file(self.A, "2026-01-10T12:00:00Z", "pre-T1"))
        self.put(self.wt[1], "2026-01-11-05.md",
                 hook_file(self.B, "2026-01-11T10:00:00Z", "T1+"))
        self.put(self.wt[2], "2026-01-12-01.md", self.store["2026-01-10-02"])
        self.put(self.main, "2026-01-11-03.md",
                 hook_file(self.B, "2026-01-11T12:00:00Z", "own"))

        def snapshot():
            snap = {}
            for dirpath, dirnames, filenames in os.walk(self.tmp):
                for n in dirnames + filenames:
                    p = Path(dirpath) / n
                    st = p.lstat()
                    data = p.read_bytes() if p.is_file() and not p.is_symlink() else None
                    snap[str(p)] = (data, st.st_mtime_ns if data is not None else None)
            return snap

        before = snapshot()
        r = self.run_tool()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        after = snapshot()
        self.assertEqual(sorted(before), sorted(after))
        changed = [p for p in before if before[p] != after[p]]
        self.assertEqual(changed, [])


if __name__ == "__main__":
    unittest.main()
