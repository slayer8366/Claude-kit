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
| B-01 | history_guard | A push to a protected branch run through a shell or an interpreter: `sh -c 'git push origin main'`, `python3 -c` calling `subprocess.run(['git', 'push', 'origin', 'main'])`. The push check parses command segments, not the quoted program a shell or interpreter is given. (Until review fix R2 this row also held `env git push origin main` and `/usr/bin/git push origin main`, now B-10, fixed.) | accepted | `test_b01_push_through_wrapper_or_git_path` |
| B-02 | history_guard | An interpreter that passes git's or gh's words as separate strings, such as `python3 -c` calling `subprocess.run(['git', 'push', '--force', ...])`, `(['gh', 'pr', 'merge', '5', '--merge'])` or `(['git', 'merge', ...])` on a protected branch. The force-push, PR-merge and merge checks match the whole text with whitespace between the words. | accepted | `test_b02_interpreter_splits_words` |
| B-03 | history_guard, role_guard | A pull request merged through the REST API by the coder role: `gh api -X PUT repos/<owner>/<repo>/pulls/<N>/merge -f merge_method=merge`. The merge rule matches only `gh pr merge`, and role_guard does not restrict the coder (it denies `gh api` writes to the planner and pulse). | fixed | `test_b03_pr_merge_through_gh_api_is_blocked` |
| B-04 | history_guard | A refspec given through a shell variable: `B=main; git push origin $B`, run on a feature branch. The push check reads `$B` as written, not as the shell expands it. | accepted | `test_b04_refspec_in_shell_variable` |
| B-05 | history_guard | A heredoc marker that is not a heredoc: `<<EOF` inside quotes (`echo '<<EOF'`) or in a `#` comment. The push check drops the following lines up to a line `EOF` as a heredoc body, so a `git push origin main` among them is not checked. Also `<<<` here-strings (batch 4). | fixed | `test_b05_heredoc_marker_in_quotes_or_comment_is_blocked` |
| B-06 | device_guard | adb named without the word `adb` in the command where it runs: through a variable (`A=adb; $A uninstall <package>`), split quoting (`ad''b uninstall <package>`), or an alias defined on one line and used after a `;` on a later one (`alias a=adb`, then `true; a uninstall <package>`), where the shell expands aliases. The checks are patterns that need the literal word `adb`, and a `;` ends a match. | accepted | `test_b06_adb_through_variable_quoting_or_alias` |
| B-07 | dispatch_guard | New instructions sent to a running agent with SendMessage. dispatch_guard sees only Agent and Task calls, so the message is not preserved, its sections are not checked, and no approval is asked. role_guard limits the planner's SendMessage to agents it started. | accepted | `test_b07_send_message_skips_dispatch_checks` |
| B-08 | role_guard | Reads outside the checkout by the pulse and planner roles. Both may use Read, and the pulse Grep and Glob, on any path, including outside the checkout, such as `/etc/hostname`; role_guard allows these tools by name with no path check. Only Claude Code's own permission check limits where. Evidence: T8's live case 1 (RECORD.md 2026-09-25-76), where the pulse read its worktree's `.git` and tried the main clone's `.git/worktrees/…/HEAD`, denied by Claude Code, not role_guard. | accepted | `test_b08_pulse_and_planner_read_outside_checkout` |
| B-09 | history_guard, role_guard | A pull request merged through the REST API with `curl` (or another HTTP client), such as `curl -X PUT -H "Authorization: …" https://api.github.com/repos/<owner>/<repo>/pulls/<N>/merge`, which neither the `gh pr merge` rule nor B-03's `gh api` check sees. | accepted | `test_b09_pr_merge_through_curl` |
| B-10 | history_guard | A push to a protected branch behind a directory change, a shell keyword, a wrapper, an assignment or a path to git: `cd <main checkout> && git push origin`, `pushd <main checkout> && git push origin && popd`, `{ git push origin main; }`, `time git push origin main`, `GIT_TRACE=1 git push origin main`, `/usr/bin/git push origin main`. The push check judged every segment against the payload's cwd and saw git only as a segment's first word. Fixed in review fix R2: the walk keeps an effective directory that follows `cd`, `pushd` and `popd` (an unresolvable one makes a bare or `HEAD` push denied by name), drops leading keywords, wrappers and assignments, and takes a command word whose basename is `git` as git. | fixed | `test_b10_push_behind_cd_keyword_wrapper_assignment_or_git_path_is_blocked` |
| B-11 | history_guard | A force push by refspec: `git push origin +main`, `git push origin +feature`. The push check stripped the `+` and read the refspec as an ordinary push, so `+feature` passed and `+main` was denied as a protected-branch push, not as a force. Fixed in review fix R2: a refspec beginning with `+` is denied as a force push to its destination, whatever the destination. | fixed | `test_b11_plus_refspec_is_blocked_as_force` |
| B-12 | history_guard | `git merge` on a protected branch behind `--git-dir=` or `--work-tree=`: `git --git-dir=.git merge x`, `git --work-tree=. merge x`. The merge check's option group knew `-C`, `-c` and `--no-pager` only (`--git-dir=.git` was caught by accident, `git` in `.git` followed by ` merge`). Fixed in review fix R2: the merge check takes the same global options as the push check's `GIT_OPTS`. | fixed | `test_b12_merge_behind_git_dir_or_work_tree_is_blocked` |
