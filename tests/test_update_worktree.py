"""update_worktree.py on throwaway repositories.

Each fixture is a bare origin, a main checkout cloned from it (on `main`,
protected in its kit.json) and a linked worktree on its own branch `feature`,
at the first commit. The main checkout then adds a store file and pushes, so
origin/main is one commit ahead of the worktree, and the worktree holds an
untracked copy of that store file with the same bytes: the copy that blocks a
plain fast-forward. The tool is run as a subprocess. Not released.

    python3 -m unittest discover -s tests
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
TOOL = KIT / "update_worktree.py"
GIT_ID = ["-c", "user.name=t", "-c", "user.email=t@example.invalid",
          "-c", "commit.gpgsign=false"]
STORE_REL = "prompts/preserved/2026-01-01-01.md"
STORE_BYTES = b"HEAD: 0000000\nPreserved: 2026-01-01T00:00:00Z\n--- verbatim prompt follows ---\nbody\n"
FOLDER_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-01$")


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *GIT_ID, *args],
                          capture_output=True, text=True, check=True).stdout


def files_under(root):
    """{relative path: bytes} for every file under root, skipping .git."""
    out = {}
    if not root.exists():
        return None
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in filenames:
            if name == ".git":
                continue
            p = Path(dirpath) / name
            out[str(p.relative_to(root))] = p.read_bytes()
    return out


class Fixture(unittest.TestCase):
    def build(self, backup=True):
        self.tmp = Path(tempfile.mkdtemp(prefix="update_worktree_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        origin = self.tmp / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
        main = self.main = self.tmp / "main"
        subprocess.run(["git", "clone", "-q", str(origin), str(main)], check=True,
                       capture_output=True)
        git(main, "checkout", "-q", "-b", "main")
        self.backups = self.tmp / "backups"
        conf = {"protected_branches": ["main"]}
        if backup:
            conf["backup_dir"] = str(self.backups)
            self.backups.mkdir()
            (self.backups / "INDEX.md").write_text("# Backups\n")
        (main / ".claude").mkdir()
        (main / ".claude" / "kit.json").write_text(json.dumps(conf) + "\n")
        (main / "README.md").write_text("readme\n")
        git(main, "add", "-A")
        git(main, "commit", "-q", "-m", "first")
        git(main, "push", "-q", "-u", "origin", "main")
        self.first = git(main, "rev-parse", "HEAD").strip()
        wt = self.wt = self.tmp / "wt"
        git(main, "worktree", "add", "-q", "-b", "feature", str(wt), self.first)
        store = main / STORE_REL
        store.parent.mkdir(parents=True)
        store.write_bytes(STORE_BYTES)
        git(main, "add", "-A")
        git(main, "commit", "-q", "-m", "store")
        git(main, "push", "-q", "origin", "main")
        self.target = git(main, "rev-parse", "origin/main").strip()
        copy = wt / STORE_REL
        copy.parent.mkdir(parents=True)
        copy.write_bytes(STORE_BYTES)

    def run_tool(self, path, *args):
        return subprocess.run([sys.executable, str(TOOL), str(path), *args],
                              capture_output=True, text=True)

    def snapshot(self):
        return {
            "main": files_under(self.main),
            "wt": files_under(self.wt),
            "backups": files_under(self.backups),
            "refs": git(self.main, "for-each-ref"),
            "main_head": git(self.main, "rev-parse", "HEAD"),
            "wt_head": git(self.wt, "rev-parse", "HEAD"),
        }

    def assertExit(self, r, code):
        self.assertEqual(r.returncode, code,
                         f"expected exit {code}; stdout:\n{r.stdout}\nstderr:\n{r.stderr}")


class TestUpdateWorktree(Fixture):
    def test_u1_dry_run_prints_plan_changes_nothing(self):
        self.build()
        before = self.snapshot()
        r = self.run_tool(self.wt)
        self.assertExit(r, 0)
        self.assertIn(STORE_REL, r.stdout)
        self.assertIn("as last fetched", r.stdout)
        self.assertIn(f"{self.first[:7]}..{self.target[:7]}", r.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_u2_apply_moves_manifest_index_fast_forward(self):
        self.build()
        index_before = (self.backups / "INDEX.md").read_text().splitlines()
        r = self.run_tool(self.wt, "--apply")
        self.assertExit(r, 0)
        folders = [p for p in self.backups.iterdir() if p.is_dir()]
        self.assertEqual(len(folders), 1, folders)
        folder = folders[0]
        self.assertRegex(folder.name, FOLDER_RE)
        self.assertEqual((folder / STORE_REL).read_bytes(), STORE_BYTES)
        listed = {}
        for line in (folder / "MANIFEST.sha256").read_text().splitlines():
            digest, name = line.split("  ", 1)
            listed[name] = digest
        self.assertEqual(set(listed), {STORE_REL})
        for name, digest in listed.items():
            self.assertEqual(hashlib.sha256((folder / name).read_bytes()).hexdigest(), digest)
        index_after = (self.backups / "INDEX.md").read_text().splitlines()
        self.assertEqual(index_after[:len(index_before)], index_before)
        added = index_after[len(index_before):]
        self.assertEqual(len(added), 1, added)
        for part in (folder.name, str(self.wt), "update_worktree.py", self.target):
            self.assertIn(part, added[0])
        self.assertEqual(git(self.wt, "rev-parse", "HEAD").strip(), self.target)
        self.assertEqual(git(self.wt, "status", "--porcelain"), "")
        self.assertIn(self.target, r.stdout)

    def test_u3_untracked_differs_stops(self):
        self.build()
        (self.wt / STORE_REL).write_bytes(STORE_BYTES + b"edited\n")
        before = self.snapshot()
        r = self.run_tool(self.wt, "--apply")
        self.assertExit(r, 1)
        self.assertIn(STORE_REL, r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_u4_own_commit_stops(self):
        self.build()
        (self.wt / "own.txt").write_text("own\n")
        git(self.wt, "add", "own.txt")
        git(self.wt, "commit", "-q", "-m", "own")
        before = self.snapshot()
        r = self.run_tool(self.wt)
        self.assertExit(r, 1)
        self.assertEqual(self.snapshot(), before)

    def test_u5_dirty_tracked_file_stops(self):
        self.build()
        (self.wt / "README.md").write_text("edited\n")
        before = self.snapshot()
        r = self.run_tool(self.wt)
        self.assertExit(r, 1)
        self.assertIn("README.md", r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_u6_protected_branch_stops(self):
        self.build()
        before = self.snapshot()
        r = self.run_tool(self.main, "--apply")
        self.assertExit(r, 1)
        self.assertIn("main", r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_u7_apply_without_backup_dir_stops(self):
        self.build(backup=False)
        before = self.snapshot()
        r = self.run_tool(self.wt, "--apply")
        self.assertExit(r, 1)
        self.assertIn("backup_dir", r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.backups.exists())

    def test_u8_untracked_not_in_target_left_in_place(self):
        self.build()
        notes = self.wt / "notes.txt"
        notes.write_text("mine\n")
        r = self.run_tool(self.wt, "--apply")
        self.assertExit(r, 0)
        self.assertEqual(notes.read_text(), "mine\n")
        self.assertEqual(git(self.wt, "rev-parse", "HEAD").strip(), self.target)
        folders = [p for p in self.backups.iterdir() if p.is_dir()]
        self.assertEqual(len(folders), 1, folders)
        self.assertFalse((folders[0] / "notes.txt").exists())
        self.assertIn("notes.txt", r.stdout)


if __name__ == "__main__":
    unittest.main()
