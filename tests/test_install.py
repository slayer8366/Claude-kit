"""install.py and check_kit.py, end to end in temporary git repositories.

Each test builds a throwaway copy of this kit repository from the working
tree, tags that copy (never this repository), installs the tag into a
throwaway adopter and runs the adopter's own check_kit.py. Not released.

    python3 -m unittest discover -s tests
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
TAG = "v0.0.0-test"
GIT_ID = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *GIT_ID, *args],
                          capture_output=True, text=True, check=True).stdout


def release_set():
    return json.loads((KIT / "release.json").read_text())


def make_kit_copy(root):
    """A git repository holding the release files, release.json and
    install.py from the working tree, committed and tagged TAG."""
    kit = root / "kit"
    kit.mkdir()
    spec = release_set()
    for rel in list(spec["vendored"]) + list(spec["templates"]) + ["release.json", "install.py"]:
        src = KIT / rel
        if src.exists():  # a missing file is left for install.py to report
            (kit / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, kit / rel)
    subprocess.run(["git", "init", "-q", str(kit)], check=True)
    git(kit, "add", "-A")
    git(kit, "commit", "-q", "-m", "kit")
    git(kit, "tag", TAG)
    return kit


def make_adopter(root):
    adopter = root / "adopter"
    adopter.mkdir()
    subprocess.run(["git", "init", "-q", str(adopter)], check=True)
    return adopter


def run(args, cwd):
    return subprocess.run([sys.executable, *args], cwd=str(cwd), capture_output=True,
                          text=True, timeout=300)


class InstallAndDrift(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="kit_install_test_"))
        self.kit = make_kit_copy(self.root)
        self.adopter = make_adopter(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def install(self, tag=TAG):
        return run([str(self.kit / "install.py"), "--target", str(self.adopter),
                    "--tag", tag], self.kit)

    def check(self):
        return run([str(self.adopter / "check_kit.py")], self.adopter)

    def installed(self):
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_install_then_check_passes(self):
        self.installed()
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f"PASS: {len(release_set()['vendored'])} vendored file(s)", r.stdout)

    def test_lock_records_tag_and_every_vendored_hash(self):
        self.installed()
        lock = json.loads((self.adopter / ".claude" / "kit.lock").read_text())
        self.assertEqual(lock["tag"], TAG)
        expected = {rel: hashlib.sha256((KIT / rel).read_bytes()).hexdigest()
                    for rel in release_set()["vendored"]}
        self.assertEqual(lock["files"], expected)

    def test_edited_vendored_file_fails_naming_it(self):
        self.installed()
        target = self.adopter / ".claude" / "hooks" / "role_guard.py"
        target.write_text(target.read_text() + "\n# local edit\n")
        r = self.check()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn(".claude/hooks/role_guard.py: sha256", r.stdout)
        self.assertIn("FAIL: 1 vendored file(s) differ", r.stdout)

    def test_missing_vendored_file_fails_naming_it(self):
        self.installed()
        (self.adopter / "check_prompts.py").unlink()
        r = self.check()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("check_prompts.py: missing", r.stdout)

    def test_edited_kit_json_still_passes(self):
        self.installed()
        config = self.adopter / ".claude" / "kit.json"
        data = json.loads(config.read_text())
        data["protected_branches"] = ["main", "release"]
        config.write_text(json.dumps(data))
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_first_install_writes_kit_json_from_template(self):
        self.installed()
        self.assertEqual((self.adopter / ".claude" / "kit.json").read_bytes(),
                         (KIT / "templates" / "kit.json").read_bytes())
        self.assertIsNone(json.loads((KIT / "templates" / "kit.json").read_text())
                          ["android_package"])

    def test_adopter_owned_files_never_overwritten(self):
        owned = {".claude/kit.json": '{"mine": true}\n', "RECORD.md": "# mine\n",
                 "CLAUDE.md": "# mine\n", "prompts/preserved/2026-01-01-01.md": "mine\n"}
        for rel, text in owned.items():
            (self.adopter / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.adopter / rel).write_text(text)
        self.installed()
        for rel, text in owned.items():
            with self.subTest(rel):
                self.assertEqual((self.adopter / rel).read_text(), text)

    def test_differing_settings_json_stops_and_writes_nothing(self):
        settings = self.adopter / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text('{"hooks": {}}\n')
        r = self.install()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("settings.json exists and differs", r.stderr)
        self.assertEqual(settings.read_text(), '{"hooks": {}}\n')
        self.assertEqual(sorted(p.name for p in settings.parent.iterdir()), ["settings.json"])
        self.assertFalse((self.adopter / "check_kit.py").exists())

    def test_identical_settings_json_is_accepted(self):
        settings = self.adopter / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        shutil.copy(KIT / ".claude" / "settings.json", settings)
        self.installed()

    def test_only_a_tag_installs(self):
        branch = git(self.kit, "rev-parse", "--abbrev-ref", "HEAD").strip()
        r = self.install(tag=branch)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("is not a tag", r.stderr)
        self.assertFalse((self.adopter / ".claude").exists())

    def test_vendored_hook_tests_pass_in_the_adopter(self):
        # The vendored set carries everything its own tests need.
        self.installed()
        r = run(["-m", "unittest", "discover", "-s", ".claude/hooks/tests"], self.adopter)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr[-3000:])


if __name__ == "__main__":
    unittest.main()
