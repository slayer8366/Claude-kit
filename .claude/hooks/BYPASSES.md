# Known bypasses of the kit's guards

The guards read command text and tool names. They hold the forms an agent
usually writes, not every program that could do the same thing. This table
lists the known ways past them.

- **Test.** Each row names a test in `.claude/hooks/tests/test_bypasses.py`.
  The test sends the hook the row's inputs as payloads and asserts that each
  one still gets through (the hook gives no decision). A change that closes a
  bypass makes its test fail, so the row is updated in the same change. No
  input was run for real: nothing was pushed, merged or run on a device.
- **Citations.** Each guard's module docstring names its rows on a "Known
  bypasses" line. The same test file checks that every cited ID is a row
  here and that every row's test exists.
- **Status.** `open` means known and not yet ruled on. The owner rules on
  each row: accepted, or fixed.

| ID | Guard | Bypass | Status | Test |
|---|---|---|---|---|
| B-01 | history_guard | A push to a protected branch run through a wrapper, an interpreter or a path to git: `sh -c 'git push origin main'`, `env git push origin main`, `python3 -c` calling `subprocess.run(['git', 'push', 'origin', 'main'])`, `/usr/bin/git push origin main`. The push check parses only command segments whose first word is `git`. | open | `test_b01_push_through_wrapper_or_git_path` |
| B-02 | history_guard | An interpreter that passes git's or gh's words as separate strings, such as `python3 -c` calling `subprocess.run(['git', 'push', '--force', ...])`, `(['gh', 'pr', 'merge', '5', '--merge'])` or `(['git', 'merge', ...])` on a protected branch. The force-push, PR-merge and merge checks match the whole text with whitespace between the words. | open | `test_b02_interpreter_splits_words` |
| B-03 | history_guard, role_guard | A pull request merged through the REST API by the coder role: `gh api -X PUT repos/<owner>/<repo>/pulls/<N>/merge -f merge_method=merge`. The merge rule matches only `gh pr merge`, and role_guard does not restrict the coder (it denies `gh api` writes to the planner and pulse). | open | `test_b03_pr_merge_through_gh_api_as_coder` |
| B-04 | history_guard | A refspec given through a shell variable: `B=main; git push origin $B`, run on a feature branch. The push check reads `$B` as written, not as the shell expands it. | open | `test_b04_refspec_in_shell_variable` |
| B-05 | history_guard | A heredoc marker that is not a heredoc: `<<EOF` inside quotes (`echo '<<EOF'`) or in a `#` comment. The push check drops the following lines up to a line `EOF` as a heredoc body, so a `git push origin main` among them is not checked. | open | `test_b05_heredoc_marker_in_quotes_or_comment` |
| B-06 | device_guard | adb named without the word `adb` in the command where it runs: through a variable (`A=adb; $A uninstall <package>`), split quoting (`ad''b uninstall <package>`), or an alias defined on one line and used after a `;` on a later one (`alias a=adb`, then `true; a uninstall <package>`), where the shell expands aliases. The checks are patterns that need the literal word `adb`, and a `;` ends a match. | open | `test_b06_adb_through_variable_quoting_or_alias` |
| B-07 | dispatch_guard | New instructions sent to a running agent with SendMessage. dispatch_guard sees only Agent and Task calls, so the message is not preserved, its sections are not checked, and no approval is asked. role_guard limits the planner's SendMessage to agents it started. | open | `test_b07_send_message_skips_dispatch_checks` |
