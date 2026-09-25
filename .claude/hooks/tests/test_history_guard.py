"""history_guard.py. Crafted Bash payloads, with cwd a throwaway
repository checked out on main or on a feature branch."""
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from harness import TEST_CONFIG, bash, run_hook

HOOK = "history_guard.py"


def make_repo(branch):
    repo = Path(tempfile.mkdtemp(prefix="history_guard_test_"))
    g = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    subprocess.run(g + ["commit", "-q", "--allow-empty", "-m", "base"], check=True)
    if branch != "main":
        subprocess.run(g + ["checkout", "-q", "-b", branch], check=True)
    return repo


class HistoryGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.on_main = make_repo("main")
        cls.on_feature = make_repo("feature")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.on_main, ignore_errors=True)
        shutil.rmtree(cls.on_feature, ignore_errors=True)

    def decide(self, command, repo, who="coder"):
        return run_hook(HOOK, bash(command, who, cwd=str(repo)))

    def assertDenied(self, command, repo, *words):
        decision, reason = self.decide(command, repo)
        self.assertEqual(decision, "deny", f"{command!r}: got {decision!r}")
        for w in words:
            self.assertIn(w, reason, command)

    def assertPasses(self, command, repo):
        decision, reason = self.decide(command, repo)
        self.assertIsNone(decision, f"{command!r}: {reason}")

    def test_force_push_denied_on_any_branch(self):
        for command in ("git push --force", "git push --force --dry-run",
                        "git push --force-with-lease origin feature",
                        "git push --force-with-lease=feature:abc origin feature",
                        "git push -f origin feature", "git push -uf origin feature"):
            with self.subTest(command):
                self.assertDenied(command, self.on_feature, "force")

    def test_merge_on_main_denied_elsewhere_allowed(self):
        self.assertDenied("git merge feature", self.on_main, "git merge", "main")
        self.assertPasses("git merge main", self.on_feature)
        self.assertPasses("git merge-base main feature", self.on_main)

    def test_merge_with_dash_c_uses_that_repository(self):
        self.assertDenied(f"git -C {self.on_main} merge feature", self.on_feature, "main")

    def test_push_to_main_denied(self):
        for command in ("git push origin main", "git push origin HEAD:main",
                        "git push origin feature:refs/heads/main",
                        "git push --dry-run origin main", "git push origin --all"):
            with self.subTest(command):
                self.assertDenied(command, self.on_feature, "main")

    def test_bare_push_on_main_denied(self):
        for command in ("git push", "git push origin", "git push origin HEAD"):
            with self.subTest(command):
                self.assertDenied(command, self.on_main, "main")

    def test_ordinary_push_on_a_branch_allowed(self):
        for command in ("git push", "git push -u origin feature",
                        "git push origin feature:feature", "git push origin HEAD"):
            with self.subTest(command):
                self.assertPasses(command, self.on_feature)

    def test_gh_pr_merge_denied(self):
        self.assertDenied("gh pr merge 112 --squash", self.on_feature, "gh pr merge")
        self.assertPasses("gh pr view 112", self.on_feature)

    def test_history_rewriting_denied(self):
        for command in ("git filter-repo --analyze", "git filter-branch --tree-filter x HEAD",
                        "git-filter-repo --path src"):
            with self.subTest(command):
                self.assertDenied(command, self.on_feature, "filter-")

    def test_applies_to_every_role(self):
        for who in (None, "pulse", "coder", "general-purpose"):
            with self.subTest(who):
                decision, _ = self.decide("git push --force", self.on_feature, who)
                self.assertEqual(decision, "deny")

    def test_protected_branches_come_from_config(self):
        config = dict(TEST_CONFIG, protected_branches=["release"])
        on_release = make_repo("release")
        try:
            def decide(command, repo):
                return run_hook(HOOK, bash(command, "coder", cwd=str(repo)), config=config)
            for command, repo in (("git merge feature", on_release),
                                  ("git push", on_release),
                                  ("git push origin release", self.on_feature),
                                  ("git push origin HEAD:refs/heads/release", self.on_feature)):
                with self.subTest(command):
                    decision, reason = decide(command, repo)
                    self.assertEqual(decision, "deny", f"{command!r}: {reason}")
                    self.assertIn("release", reason)
            # main is not protected under this config.
            for command, repo in (("git merge feature", self.on_main),
                                  ("git push origin main", self.on_feature),
                                  ("git push", self.on_main)):
                with self.subTest(command):
                    decision, reason = decide(command, repo)
                    self.assertIsNone(decision, f"{command!r}: {reason}")
        finally:
            shutil.rmtree(on_release, ignore_errors=True)

    def test_unrelated_commands_untouched(self):
        for command in ("git status", "git log --oneline", "git commit -m 'push --force later'"):
            with self.subTest(command):
                self.assertPasses(command, self.on_main)

    def test_heredoc_message_then_push_to_branch_allowed(self):
        self.assertPasses("git commit -q --allow-empty -F - <<'EOF'\nDon't block this\nEOF\n"
                          "git push origin feature", self.on_feature)

    def test_word_push_in_unparseable_text_allowed(self):
        self.assertPasses("echo don't push yet", self.on_feature)

    def test_push_to_main_after_heredoc_blocked(self):
        self.assertDenied("cat <<'EOF' > /tmp/x\nit's data\nEOF\ngit push origin main",
                          self.on_feature, "protected branch")

    def test_newline_separates_commands(self):
        for command in ("git status\ngit push origin main",
                        "cat <<EOF\ngit push origin main"):  # no closing line, so kept
            with self.subTest(command):
                self.assertDenied(command, self.on_feature, "protected branch")

    def test_unparseable_push_and_continuation_still_blocked(self):
        for command, word in (("git push origin feature && echo 'oops", "could not parse"),
                              ("git push \\\norigin main", "main")):
            with self.subTest(command):
                self.assertDenied(command, self.on_feature, word)


def git_in(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t",
                           "-c", "user.email=t@example.invalid"] + list(args),
                          check=True, capture_output=True, text=True).stdout.strip()


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class MergeRule(unittest.TestCase):
    """The merge rule: a coder's PR merge passes only with a verified,
    fresh backup under backup_dir. Each test gets its own bare origin, a
    clone with origin/main fetched, and an empty backup directory."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="history_guard_merge_"))
        self.origin = self.root / "origin.git"
        self.work = self.root / "work"
        self.backups = self.root / "backups"
        self.backups.mkdir()
        subprocess.run(["git", "init", "-q", "--bare", str(self.origin)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.work)], check=True)
        git_in(self.work, "commit", "-q", "--allow-empty", "-m", "base")
        git_in(self.work, "remote", "add", "origin", str(self.origin))
        git_in(self.work, "push", "-q", "origin", "main")
        git_in(self.work, "fetch", "-q", "origin")
        self.config = dict(TEST_CONFIG, backup_dir=str(self.backups))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write_backup(self, pr, index=True):
        """A backup as coder.md item 10 describes it, for origin/main."""
        folder = self.backups / f"2026-01-01-pr{pr}"
        folder.mkdir()
        sha = git_in(self.work, "rev-parse", "origin/main")
        git_in(self.work, "bundle", "create", "-q", str(folder / "main.bundle"),
               "origin/main")
        (folder / "merge.json").write_text(json.dumps(
            {"pr": pr, "branch": "main", "sha": sha, "bundle": "main.bundle"}))
        (folder / "MANIFEST.sha256").write_text("".join(
            f"{sha256_of(folder / name)}  {name}\n"
            for name in ("merge.json", "main.bundle")))
        with open(self.backups / "INDEX.md", "a") as f:
            f.write(f"- {folder.name}: PR {pr}, main at {sha}\n" if index
                    else "- some other backup\n")
        return folder

    def decide(self, command, who="coder", config=None):
        return run_hook(HOOK, bash(command, who, cwd=str(self.work)),
                        config=self.config if config is None else config)

    def assertMergeDenied(self, command, *words, config=None):
        decision, reason = self.decide(command, config=config)
        self.assertEqual(decision, "deny", f"{command!r}: got {decision!r} {reason}")
        for w in words:
            self.assertIn(w, reason, command)

    def test_m1_coder_merge_commit_with_valid_backup_allowed(self):
        self.write_backup(12)
        decision, reason = self.decide("gh pr merge 12 --merge")
        self.assertIsNone(decision, reason)

    def test_m2_coder_squash_with_valid_backup_allowed(self):
        self.write_backup(12)
        decision, reason = self.decide("gh pr merge 12 --squash")
        self.assertIsNone(decision, reason)

    def test_m3_backup_dir_unset_denied(self):
        self.write_backup(12)
        self.assertMergeDenied("gh pr merge 12 --merge", "(c) config", "backup_dir",
                               config=TEST_CONFIG)

    def test_m4_no_backup_for_that_pr_denied(self):
        self.write_backup(7)
        self.assertMergeDenied("gh pr merge 8 --merge", "(d) backup", "merge.json")

    def test_m5_bundle_altered_after_manifest_denied(self):
        folder = self.write_backup(12)
        with open(folder / "main.bundle", "ab") as f:
            f.write(b"x")
        self.assertMergeDenied("gh pr merge 12 --merge", "(d) backup", "MANIFEST.sha256")

    def test_m6_origin_moved_since_backup_denied(self):
        self.write_backup(12)
        git_in(self.work, "commit", "-q", "--allow-empty", "-m", "later")
        git_in(self.work, "push", "-q", "origin", "main")
        git_in(self.work, "fetch", "-q", "origin")
        self.assertMergeDenied("gh pr merge 12 --merge", "(e) freshness")

    def test_m7_index_without_the_folder_denied(self):
        self.write_backup(12, index=False)
        self.assertMergeDenied("gh pr merge 12 --merge", "(d) backup", "INDEX.md")

    def test_m8_forms_denied_by_name(self):
        self.write_backup(12)
        for command, word in (("gh pr merge 12 --rebase", "--rebase"),
                              ("gh pr merge 12 --merge --auto", "--auto"),
                              ("gh pr merge 12 --merge --admin", "--admin"),
                              ("gh pr merge 12 --merge --delete-branch", "--delete-branch"),
                              ("gh pr merge 12 --merge -R x/y", "-R"),
                              ("gh pr merge --merge", "pull request number"),
                              ("gh pr merge 12 --merge && echo done", "one command")):
            with self.subTest(command):
                self.assertMergeDenied(command, "(b) form", word)

    def test_m9_planner_and_pulse_denied_even_with_a_backup(self):
        self.write_backup(12)
        for who in (None, "pulse"):
            with self.subTest(who):
                decision, _ = self.decide("gh pr merge 12 --merge", who)
                self.assertEqual(decision, "deny")


if __name__ == "__main__":
    unittest.main()
