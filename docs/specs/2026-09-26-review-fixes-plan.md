# Claude-kit review fixes: plan

Written by the planner on 2026-09-25/26; committed by R1's coder from dispatch 2026-09-25-47 (`prompts/preserved/2026-09-25-47.md`).

Source: the Fable 5.1 review of PRs #25 to #32 (store copy 2026-09-25-44, note 2026-09-25-87). Read at 671b05d; re-read by the planner at 0319ccd.

## Decisions taken by the owner (planner log F, 2026-09-25/26)
- D1: option B. Coders merge; the human gate is a merge dispatch approved after the PR exists; GitHub protection on main and pre-main (pull request required, enforced for admins, both CI checks). pre-main is the working trunk, main the release trunk; promotion by PR after the owner's evidence gate; leaving out by revert; coder deferral to a list.
- D3: the `sh -c`, `env` and `/usr/bin/git` forms of B-01 move to `fixed` in R2/R3.
- D4: history_guard checks freshness with one `ls-remote`, timed out and failing closed.
- D5: the v0.2 tag waits until R4 is promoted to main.

## Tasks, in order
| Task | Findings | Files | Size |
|---|---|---|---|
| R1 | P3, P12 text, N5, branch model | check_record.py, kit.json, coder.md, README, this plan | L |
| R2 | P2, P9, N1 | history_guard.py, tests, BYPASSES | M |
| R3 | P4, P7, newline reach | history_guard.py, role_guard.py, tests, BYPASSES | L |
| R4 | P5, P6, N4, README undo | history_guard.py, tests, README | M |
| R6 | P10 | hooks, settings.json, README | S |
| R5 | P8 | update_worktree.py, tests | S |
| R7 | P11, P15, P16 | tests/, run_exercise.py, docstrings | M |

- R1: Kind `merge` and `revert`, terminal outcome `partial` with `Deferred`, note outcome `merged`; a build's finish line ends at PR open, CI green, backup written; the next sweep records merges; pre-main first in protected_branches; coder.md items 1, 3, 10, 12.
- R2: the segment walk tracks `cd` and `pushd`, strips shell keywords and wrappers before looking for git, treats any command whose basename is git as git, denies `+` refspecs as force pushes; MERGE gains --git-dir and --work-tree; new fixed rows.
- R3: whole-text regexes (FORCE_PUSH, PR_MERGE, GH_API, FILTERS, MERGE) move onto the segment walk at command position; strings given to `sh -c` and friends are parsed as nested commands; GraphQL mergePullRequest and `gh alias set` denied; role_guard's named patterns match the command word and subcommand from tokens; B-02 stays accepted.
- R4: the bundle must list the pair of SHA and origin ref; INDEX lines match whole tokens; freshness by ls-remote; README says what the check proves and rewrites the undo procedure.
- R5: step 1 proves or disproves the ignored-file clobber; if it clobbers, survey refuses on ignored files at paths the range adds.
- R6: timeouts on history_guard's three and dispatch_guard's two subprocess calls, device_guard's below 60, explicit hook timeouts in settings.json.
- R7: the named tests test what they name; case 1 checks the saved dispatch; the launcher's three untested paths; no wall-clock bounds; P15 and P16 as docstring limits.
- Then: the T3 backlog (D2, D5, W's copies), the v0.2 completion report with the review's findings and their status, the tag.

## Planner practice
A premise pulse before each build; "or line drift" in every abort list; the planner authors the outcome prediction; a met abort condition is a stop; owner questions carry no marked recommendation, with the planner's view and its strongest counter on a separate line.
