# Known bypasses of the kit's guards

The guards read command text and tool names. They hold the forms an agent
usually writes, not every program that could do the same thing. This table
lists the known ways past them.

- **Test.** Each row names a test in `.claude/hooks/tests/test_bypasses.py`.
  The test sends the hook the row's inputs as payloads. For an `open` or
  `accepted` row it asserts that each one still gets through (the hook gives
  no decision); for a `fixed` row, that each one is denied with a reason. A
  change that closes a bypass makes its test fail, so the row is updated in
  the same change. No input was run for real: nothing was pushed, merged or
  run on a device.
- **Citations.** Each guard's module docstring names its `open` and
  `accepted` rows on a "Known bypasses" line; a `fixed` row is not cited.
  The same test file checks that every cited ID is a row here and that
  every row's test exists.
- **Status.** The owner rules on each row. `open` means known and not yet
  ruled on. `accepted` means known and ruled acceptable: the guard stays as
  it is, and the test keeps proving the bypass. `fixed` means closed: the
  row stays as history, and its test now asserts the block.

| ID | Guard | Bypass | Status | Test |
|---|---|---|---|---|
| B-01 | history_guard | A push to a protected branch run through a wrapper, an interpreter or a path to git: `sh -c 'git push origin main'`, `env git push origin main`, `python3 -c` calling `subprocess.run(['git', 'push', 'origin', 'main'])`, `/usr/bin/git push origin main`. The push check parses only command segments whose first word is `git`. | accepted | `test_b01_push_through_wrapper_or_git_path` |
| B-02 | history_guard | An interpreter that passes git's or gh's words as separate strings, such as `python3 -c` calling `subprocess.run(['git', 'push', '--force', ...])`, `(['gh', 'pr', 'merge', '5', '--merge'])` or `(['git', 'merge', ...])` on a protected branch. The force-push, PR-merge and merge checks match the whole text with whitespace between the words. | accepted | `test_b02_interpreter_splits_words` |
| B-03 | history_guard, role_guard | A pull request merged through the REST API by the coder role: `gh api -X PUT repos/<owner>/<repo>/pulls/<N>/merge -f merge_method=merge`. The merge rule matches only `gh pr merge`, and role_guard does not restrict the coder (it denies `gh api` writes to the planner and pulse). | fixed | `test_b03_pr_merge_through_gh_api_is_blocked` |
| B-04 | history_guard | A refspec given through a shell variable: `B=main; git push origin $B`, run on a feature branch. The push check reads `$B` as written, not as the shell expands it. | accepted | `test_b04_refspec_in_shell_variable` |
| B-05 | history_guard | A heredoc marker that is not a heredoc: `<<EOF` inside quotes (`echo '<<EOF'`) or in a `#` comment. The push check drops the following lines up to a line `EOF` as a heredoc body, so a `git push origin main` among them is not checked. | fixed | `test_b05_heredoc_marker_in_quotes_or_comment_is_blocked` |
| B-06 | device_guard | adb named without the word `adb` in the command where it runs: through a variable (`A=adb; $A uninstall <package>`), split quoting (`ad''b uninstall <package>`), or an alias defined on one line and used after a `;` on a later one (`alias a=adb`, then `true; a uninstall <package>`), where the shell expands aliases. The checks are patterns that need the literal word `adb`, and a `;` ends a match. | accepted | `test_b06_adb_through_variable_quoting_or_alias` |
| B-07 | dispatch_guard | New instructions sent to a running agent with SendMessage. dispatch_guard sees only Agent and Task calls, so the message is not preserved, its sections are not checked, and no approval is asked. role_guard limits the planner's SendMessage to agents it started. | accepted | `test_b07_send_message_skips_dispatch_checks` |
| B-08 | role_guard | Reads outside the checkout by the pulse and planner roles. Both may use Read, and the pulse Grep and Glob, on any path, including outside the checkout, such as `/etc/hostname`; role_guard allows these tools by name with no path check. Only Claude Code's own permission check limits where. Evidence: T8's live case 1 (RECORD.md 2026-09-25-76), where the pulse read its worktree's `.git` and tried the main clone's `.git/worktrees/…/HEAD`, denied by Claude Code, not role_guard. | accepted | `test_b08_pulse_and_planner_read_outside_checkout` |
