"""release_check.py against a copy of the release set. Not released.

    python3 -m unittest discover -s tests
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
DENYLIST = KIT / "workshop" / "denylist.txt"
# Serial-shaped but made up: matches the denylist's serial pattern.
PLANTED = "R0000000000"


def copy_release(root):
    import json
    spec = json.loads((KIT / "release.json").read_text())
    shutil.copy(KIT / "release.json", root / "release.json")
    for rel in list(spec["vendored"]) + list(spec["templates"]):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(KIT / rel, root / rel)


def run(*args):
    return subprocess.run([sys.executable, str(KIT / "release_check.py"), *args],
                          capture_output=True, text=True, timeout=120)


class ReleaseCheck(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="kit_release_test_"))
        copy_release(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def check(self, denylist=DENYLIST):
        return run("--root", str(self.root), "--denylist", str(denylist))

    def test_release_set_passes(self):
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS:", r.stdout)

    def test_planted_string_fails_naming_file_and_line(self):
        target = self.root / ".claude" / "hooks" / "tests" / "test_device_guard.py"
        lines = target.read_text().splitlines()
        lines.insert(4, f"SERIAL_FROM_A_REAL_DEVICE = {PLANTED!r}")
        target.write_text("\n".join(lines) + "\n")
        r = self.check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn(f".claude/hooks/tests/test_device_guard.py:5: matches", r.stdout)
        self.assertIn(PLANTED, r.stdout)
        self.assertIn("FAIL: 1 denylisted match(es)", r.stdout)

    def test_planted_string_in_a_template_fails(self):
        target = self.root / "templates" / "kit.json"
        target.write_text(target.read_text() + f"{PLANTED}\n")
        r = self.check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("templates/kit.json:", r.stdout)

    def test_private_record_citation_fails(self):
        # Released files cite the kit by release version, never by a path
        # into the kit's private record.
        target = self.root / "check_prompts.py"
        lines = target.read_text().splitlines()
        lines.insert(4, "# Claude-kit RECORD.md 2026-09-23-01")
        target.write_text("\n".join(lines) + "\n")
        r = self.check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("check_prompts.py:5: matches", r.stdout)
        self.assertIn("Claude-kit RECORD.md", r.stdout)

    def test_missing_or_empty_denylist_fails(self):
        empty = self.root / "empty.txt"
        empty.write_text("# nothing\n\n")
        for denylist in (self.root / "absent.txt", empty):
            with self.subTest(denylist.name):
                r = self.check(denylist)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertIn("could not run", r.stdout)

    def test_missing_release_file_fails(self):
        (self.root / "check_kit.py").unlink()
        r = self.check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("check_kit.py: listed in release.json but does not exist", r.stdout)


if __name__ == "__main__":
    unittest.main()
