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


TAG2 = "v0.0.1-test"
DROPPED = "find_dispatches.py"
CHANGED_HOOK = ".claude/hooks/role_guard.py"
NEW_FILE = "kit_new_tool.py"


def make_second_tag(kit, drop=False, change_hook=False, change_settings=False,
                    add_new=False):
    """Commit changes on top of TAG in the throwaway kit copy and tag TAG2:
    DROPPED leaves the release set, CHANGED_HOOK gains a line, settings.json
    gains a trailing newline (still valid JSON), NEW_FILE joins the release
    set. Only the copy is tagged."""
    spec = json.loads((kit / "release.json").read_text())
    if drop:
        spec["vendored"].remove(DROPPED)
        (kit / DROPPED).unlink()
    if change_hook:
        hook = kit / CHANGED_HOOK
        hook.write_bytes(hook.read_bytes() + b"# changed in " + TAG2.encode() + b"\n")
    if change_settings:
        settings = kit / ".claude" / "settings.json"
        settings.write_bytes(settings.read_bytes() + b"\n")
    if add_new:
        spec["vendored"].append(NEW_FILE)
        (kit / NEW_FILE).write_text(f"# new in {TAG2}\n")
    (kit / "release.json").write_text(json.dumps(spec, indent=2) + "\n")
    git(kit, "add", "-A")
    git(kit, "commit", "-q", "-m", "kit, second tag")
    git(kit, "tag", TAG2)


def snapshot(root):
    """{relative path: bytes} for every file under root."""
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


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


class Upgrade(unittest.TestCase):
    """Installing TAG, then TAG2 over it (install.py reads the old lock)."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="kit_upgrade_test_"))
        self.kit = make_kit_copy(self.root)
        self.adopter = make_adopter(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def install(self, tag):
        return run([str(self.kit / "install.py"), "--target", str(self.adopter),
                    "--tag", tag], self.kit)

    def first_install(self):
        r = self.install(TAG)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def lock(self):
        return json.loads((self.adopter / ".claude" / "kit.lock").read_text())

    def assert_stopped_unchanged(self, r, before, paths):
        """Exit 1, each path named, and every file under the adopter the same
        as before, bytes and presence."""
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        for path in paths:
            self.assertIn(path, r.stderr)
        self.assertEqual(snapshot(self.adopter), before)

    def append(self, rel, text="# local edit\n"):
        f = self.adopter / rel
        f.write_bytes(f.read_bytes() + text.encode())

    def test_u1_unchanged_dropped_file_is_removed(self):
        self.first_install()
        make_second_tag(self.kit, drop=True)
        r = self.install(TAG2)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.adopter / DROPPED).exists())
        lock = self.lock()
        self.assertEqual(lock["tag"], TAG2)
        self.assertNotIn(DROPPED, lock["files"])
        self.assertIn(DROPPED, r.stdout)

    def test_u2_edited_kept_file_stops(self):
        self.first_install()
        make_second_tag(self.kit, change_hook=True)
        self.append(CHANGED_HOOK)
        before = snapshot(self.adopter)
        r = self.install(TAG2)
        self.assert_stopped_unchanged(r, before, [CHANGED_HOOK])
        self.assertIn("edited since the installed tag", r.stderr)

    def test_u3_edited_dropped_file_stops(self):
        self.first_install()
        make_second_tag(self.kit, drop=True)
        self.append(DROPPED)
        before = snapshot(self.adopter)
        r = self.install(TAG2)
        self.assert_stopped_unchanged(r, before, [DROPPED])
        self.assertIn("edited since the installed tag", r.stderr)

    def test_u4_unedited_settings_json_is_replaced(self):
        self.first_install()
        make_second_tag(self.kit, change_settings=True)
        r = self.install(TAG2)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.adopter / ".claude" / "settings.json").read_bytes(),
                         (self.kit / ".claude" / "settings.json").read_bytes())
        self.assertEqual(self.lock()["tag"], TAG2)

    def test_u5_edited_settings_json_stops(self):
        self.first_install()
        make_second_tag(self.kit, change_settings=True)
        self.append(".claude/settings.json", " ")
        before = snapshot(self.adopter)
        r = self.install(TAG2)
        self.assert_stopped_unchanged(r, before, [".claude/settings.json"])

    def test_u6_adopter_file_at_new_path_stops(self):
        self.first_install()
        make_second_tag(self.kit, add_new=True)
        (self.adopter / NEW_FILE).write_text("# the adopter's own\n")
        before = snapshot(self.adopter)
        r = self.install(TAG2)
        self.assert_stopped_unchanged(r, before, [NEW_FILE])
        self.assertIn("exists and is not the kit's", r.stderr)

    def test_u7_changed_hook_only_upgrade_succeeds_and_check_kit_passes(self):
        self.first_install()
        make_second_tag(self.kit, change_hook=True)
        r = self.install(TAG2)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.adopter / CHANGED_HOOK).read_bytes(),
                         (self.kit / CHANGED_HOOK).read_bytes())
        self.assertEqual(self.lock()["tag"], TAG2)
        c = run([str(self.adopter / "check_kit.py")], self.adopter)
        self.assertEqual(c.returncode, 0, c.stdout + c.stderr)
        self.assertIn(f"(kit {TAG2})", c.stdout)

    def test_u8_malformed_lock_stops(self):
        self.first_install()
        make_second_tag(self.kit, change_hook=True)
        (self.adopter / ".claude" / "kit.lock").write_text("{not json\n")
        before = snapshot(self.adopter)
        r = self.install(TAG2)
        self.assert_stopped_unchanged(r, before, [".claude/kit.lock"])

    def test_u9_lock_path_outside_the_kit_stops(self):
        # Each case gets its own kit copy and adopter in a subdirectory of the
        # test's temporary root. An outside file sits beside that adopter,
        # never at a real path.
        cases = {
            "absolute": lambda case: (case / "outside_abs.txt",
                                      str(case / "outside_abs.txt")),
            "dotdot": lambda case: (case / "outside.txt", "../outside.txt"),
            "owned": lambda case: (case / "adopter" / "RECORD.md", "RECORD.md"),
        }
        for name, where in cases.items():
            with self.subTest(name):
                case = self.root / name
                case.mkdir()
                self.kit = make_kit_copy(case)
                self.adopter = make_adopter(case)
                self.first_install()
                victim, key = where(case)
                self.assertIn(self.root.resolve(), victim.resolve().parents)
                content = f"# not the kit's ({name})\n".encode()
                victim.write_bytes(content)
                lock = self.lock()
                lock["files"][key] = hashlib.sha256(content).hexdigest()
                (self.adopter / ".claude" / "kit.lock").write_text(
                    json.dumps(lock, indent=2) + "\n")
                make_second_tag(self.kit, change_hook=True)
                before = snapshot(self.adopter)
                r = self.install(TAG2)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertTrue(victim.exists())
                self.assertEqual(victim.read_bytes(), content)
                self.assertIn(".claude/kit.lock", r.stderr)
                self.assertIn(key, r.stderr)
                self.assertEqual(snapshot(self.adopter), before)

    def test_u10_lock_path_checked_where_it_lands(self):
        # A key spelled to dodge the owned-path test, or reaching outside the
        # adopter through a symlinked directory. Each case gets its own kit
        # copy and adopter in a subdirectory of the test's temporary root;
        # every file and symlink it creates lies under that root.
        def dot_record(case):
            return case / "adopter" / "RECORD.md", "./RECORD.md"

        def dot_prompts(case):
            (case / "adopter" / "prompts").mkdir()
            return case / "adopter" / "prompts" / "x.md", "./prompts/x.md"

        def symlinked_dir(case):
            outside = case / "outside_dir"
            outside.mkdir()
            link = case / "adopter" / "ext"
            link.symlink_to(outside, target_is_directory=True)
            self.assertIn(self.root.resolve(), link.parent.resolve().parents)
            self.assertIn(self.root.resolve(), link.resolve().parents)
            return outside / "outside.txt", "ext/outside.txt"

        def double_slash_prompts(case):
            (case / "adopter" / "prompts").mkdir()
            return case / "adopter" / "prompts" / "x.md", "prompts//x.md"

        cases = {
            "dot_record": dot_record,
            "dot_prompts": dot_prompts,
            "symlinked_dir": symlinked_dir,
            "double_slash_prompts": double_slash_prompts,
        }
        for name, where in cases.items():
            with self.subTest(name):
                case = self.root / name
                case.mkdir()
                self.kit = make_kit_copy(case)
                self.adopter = make_adopter(case)
                self.first_install()
                victim, key = where(case)
                self.assertIn(self.root.resolve(), victim.resolve().parents)
                content = f"# not the kit's ({name})\n".encode()
                victim.write_bytes(content)
                lock = self.lock()
                lock["files"][key] = hashlib.sha256(content).hexdigest()
                (self.adopter / ".claude" / "kit.lock").write_text(
                    json.dumps(lock, indent=2) + "\n")
                make_second_tag(self.kit, change_hook=True)
                r = self.install(TAG2)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertTrue(victim.exists())
                self.assertEqual(victim.read_bytes(), content)
                self.assertIn(".claude/kit.lock", r.stderr)
                self.assertIn(key, r.stderr)


if __name__ == "__main__":
    unittest.main()
