# Claude-kit

Role gates, dispatch preservation and a record store for Claude Code
repositories, as PreToolUse hooks, a SessionStart check and two checkers. Adopters vendor a pinned
release tag; the kit repository itself is a private workshop.

Work in progress: v0.1 is being extracted on branch `kit-v0.1`
(`RECORD.md` 2026-09-23-01). Nothing here is released yet. Step 1 imports the
source files unchanged; later steps make them generic.

## Layout (target for v0.1)

| Path | What it is | Released |
|---|---|---|
| `.claude/hooks/` | the PreToolUse guards, the SessionStart check `session_check.py`, and their tests | yes |
| `.claude/agents/` | the `coder` and `pulse` subagents | yes |
| `.claude/settings.json` | registers the hooks | yes |
| `.claude/kit.json` | this repository's own adopter config | no |
| `check_record.py`, `check_prompts.py` | the record checkers, at the repository root | yes |
| `check_kit.py` | drift check against `.claude/kit.lock` | yes |
| `find_dispatches.py` | lists hook-saved dispatches left untracked in other worktrees, with copy commands and citations; read-only | yes |
| `update_worktree.py` | fast-forwards a harness worktree to origin/<first protected branch> after moving aside untracked files the branch tracks byte for byte; dry run by default | yes |
| `session_agents.py` | lists a session log's Agent calls with their outcome, hand-backs and SendMessages, and how far each unfinished agent got; read-only | yes |
| `launch_session.py` | launches one headless `claude -p` session in a checkout under a wall-clock limit, after checking the checkout, its hooks and the session's identity; writes only its stream files | yes |
| `run_exercise.py` | runs the four live-exercise cases through `launch_session.py` in a temporary detached worktree and writes one evidence line per case from the session logs; writes only under its `--out-dir` and the worktree | yes |
| `templates/` | files an install writes only when absent | yes |
| `install.py`, `release.json` | vendors a tag into an adopter; the release set | no |
| `release_check.py` | scans the release set against the workshop denylist | no |
| `tests/` | install and drift (`test_install.py`), release_check (`test_release_check.py`), find_dispatches (`test_find_dispatches.py`), update_worktree (`test_update_worktree.py`), session_agents (`test_session_agents.py`) and launch_session (`test_launch_session.py`) tests | no |
| `workshop/` | private sources, drafts and the release denylist | no |
| `RECORD.md`, `prompts/`, `docs/` | this repository's own record | no |

## Requirements

`python3` on PATH (the hooks are run as `python3 "${CLAUDE_PROJECT_DIR}/..."`)
and `git`. Standard library only. The device guard also calls `adb`, `aapt2`
and `apksigner` when an Android package is configured.

## Config: `.claude/kit.json`

Every guard reads the `kit.json` beside its hooks directory. A missing or
invalid config makes every guard deny, naming the problem; the kit never fails
open on its own config. Unknown keys are invalid. The session check only
warns (see "Session check").

| Key | Required | Meaning |
|---|---|---|
| `android_package` | yes | the app the device guard protects, or `null` to turn the device guard off |
| `protected_branches` | yes | non-empty list; history_guard blocks merging while on one, and pushing to one |
| `dispatchable_agents` | yes | the only subagent types the dispatch hook lets through |
| `type_targets` | yes | dispatch `Type:` to the one agent it may go to; every agent must be dispatchable |
| `required_sections` | yes | dispatch `Type:` to the headings it must carry; same types as `type_targets` |
| `agent_roles` | yes | subagent name to role: `planner`, `pulse` or `coder`; every dispatchable agent needs one. role_guard restricts an agent by its role; an agent with no role, or with any other role name, is denied every tool. The main session is always `planner` |
| `approval_exempt_types` | yes | the dispatch Types that run without operator approval (may be empty); every other Type asks. Each must be a Type in `type_targets` |
| `guard_env_prefix` | no, default `KIT_GUARD_` | `<prefix>ADB`, `<prefix>AAPT2`, `<prefix>APKSIGNER` override the device guard's tools |
| `backup_dir` | no, no default | a string: the directory that holds merge backups (`~` is expanded). Unset, history_guard denies every pull-request merge. See "Merging and undoing a merge" |

This repository's own `kit.json` also requires a `Merge` section in build and
device dispatches, reading `authorised` or `not authorised`, and sets
`backup_dir`. The template does neither, so adopters opt in.

Fixed in code, not config: the prompt store `prompts/preserved/`, the three
roles and the planner and pulse tool allowlists, the pulse's adb reads, and the dispatch tool names
(`Agent`, `Task`).

When the dispatch hook saves a prompt whose text is identical to a stored
dispatch's, it adds a `Repeat-of: preserved/<name>` header line naming the
earliest such file, and `check_prompts.py` fails unless that file exists
with the same text.

## Install and drift

From a clone of this repository:

    python3 install.py --target <adopter checkout> --tag <tag>

`release.json` is the one definition of the release set. The installer reads
it, and every file in it, from the tag, not the working tree. It writes the
vendored files, writes `.claude/kit.json` from `templates/kit.json` only if the
adopter has none, and records the tag and each vendored file's SHA-256 in
`.claude/kit.lock`. It never writes `.claude/kit.json` over an existing one,
`RECORD.md`, `CLAUDE.md` or anything under `prompts/`. On a first install (no
`.claude/kit.lock` yet), if the adopter already has a `.claude/settings.json`
that differs from the release's, it stops and writes nothing; reconcile the
two by hand.

Upgrading is the same command with the new tag. When `.claude/kit.lock`
exists, the installer reads it as the hashes of the files as installed and
checks every path before writing anything:

- A file the new release keeps is overwritten if it is unchanged since the
  installed tag, and written if it is missing.
- A file the new release no longer ships is **removed** if it is unchanged
  (its directory stays). Each removed path is printed.
- A file the new release adds is written if absent, and left if it is
  already identical to the release's.
- `.claude/settings.json` follows the same rule, so an unedited one is
  replaced by the new release's.

The upgrade stops, lists each path with its reason and writes or removes
nothing if any kept or dropped file was edited since the installed tag, if
an adopter's own file sits at a path the new release adds, or if the lock
cannot be read or is malformed. Reconcile by hand, then install again.

In the adopter, `python3 check_kit.py` fails naming each vendored file whose
hash differs from the lock, or that is missing. It never contacts this
repository.

## Release gate

    python3 release_check.py

Scans every file in the release set (`release.json`) against the patterns in
`workshop/denylist.txt`, and fails naming each file, line and pattern that
matches. The denylist stays in the workshop and is never released, since it
names what must not be published. A release is a tag, made by the owner after
reading the release diff.

## Merging and undoing a merge

A coder merges a pull request only when its dispatch's `Merge` section reads
`authorised` (coder.md item 10). history_guard lets the merge through only
for the `coder` role, in one form (`gh pr merge <N>` with `--merge` or
`--squash`), and only after the coder has written a backup for PR N under
`backup_dir`: a folder holding a git bundle of `origin/<base branch>`,
`merge.json` (`pr`, `branch`, `sha`, `bundle`) and `MANIFEST.sha256`, with one
line in `backup_dir/INDEX.md` naming the folder, `#<N>` and the pre-merge SHA.
merge.json's `sha` must still be the tip of
`origin/<branch>`. The planner and the pulse are always denied.

After the merge, the coder updates the main checkout (the checkout on the
base branch, where the dispatch hook saves dispatches) with the
`update_worktree.py` it just merged: a dry run, then `--apply` (see
"Updating a harness worktree"). It reports both outputs and, if either
exits 1, stops there. In this repository that is
`python3 ~/Zynergy/Claude-kit-fixes/update_worktree.py ~/Zynergy/Claude-kit`,
then the same with `--apply`.

To undo a merge, find the backup folder whose `merge.json` has the PR's
number, then either:

- revert the merge or squash commit (`git revert -m 1 <merge commit>` for a
  merge commit, `git revert <commit>` for a squash); or
- reset the branch to merge.json's `sha` and force-push it. The kit's agents
  never force-push; this push is the owner's, made by hand.

If the remote is lost, restore from the bundle. `git bundle list-heads
<bundle>` names its one ref (`refs/remotes/origin/<branch>`), and in any
repository (a fresh `git init` will do) `git fetch <bundle>
refs/remotes/origin/<branch>:refs/heads/<branch>` gives the branch as it
stood at `sha`.

## Session check

`session_check.py` runs at SessionStart and never blocks: it always exits 0
and writes nothing. It reads `.claude/kit.json` in the session's repository
and compares the working tree's `.claude/hooks`, `.claude/agents`,
`.claude/settings.json` and `.claude/kit.json` with `origin/<first protected
branch>` as last fetched (it never fetches), counts commits HEAD is behind
that ref, and, where `.claude/kit.lock` exists, checks every locked file's
sha256. If anything differs, cannot be compared, or cannot be read, it shows
a short warning (`systemMessage`) and gives the session the full list and a
`git fetch` and `git merge --ff-only` command to run by hand; otherwise it is
silent. Claude Code reads hooks when a session starts, so a change to
`.claude/settings.json` takes effect only in a new session.

## Finding unrecorded dispatches

    python3 find_dispatches.py

Run from a checkout's root. Lists every untracked file under
`prompts/preserved/` in the clone's other worktrees (`git worktree list`),
with its size, sha256 and hook header, and gives each one a status:
`in-store` (its sha256 equals a tracked store file's, which it names),
`record` (a proposed store name, a copy command and a citation line),
`refused` (the proposed name is dated today, UTC; rerun after UTC midnight)
or `stop` (stop and ask: not hook-saved, an unknown header HEAD, or a name
clash). A file saved by a hook with the shared counter keeps its name; an
older one is numbered after the store's highest for its Preserved date. The
tool writes nothing and never reads the dispatch counter; it copies nothing,
so the operator runs the copy commands. It exits 1 if any item is `stop`.

## Updating a harness worktree

    python3 update_worktree.py <worktree path> [--apply]

The tool fast-forwards a harness worktree, or the main checkout, to
`origin/<first protected branch>`. A checkout on that branch itself (the main
checkout) is updated the same way as a worktree on an unprotected branch;
coder.md item 10 runs it on the main checkout after every merge. This is not
a way around history_guard: a fast-forward to origin's own tip changes
nothing on the remote and merges nothing new into the branch.

A dispatch the hook saved sits untracked in the main checkout; once its
store copy is on the default branch, that untracked file blocks
`git merge --ff-only`. By default the tool is a read-only dry run against
`origin/<first protected branch>` as last fetched: it lists the untracked
files byte-identical to that branch's copies (to move), the other untracked
files (left alone) and the fast-forward range. `--apply` fetches, moves the
identical files into a new `<backup_dir>/<UTC date>-NN/` folder with a
`MANIFEST.sha256` and one `INDEX.md` line, then runs `git merge --ff-only`.
It stops before moving anything, exit 1, on a detached HEAD, on a protected
branch other than the target, on commits of the worktree's own (not a
fast-forward), on changes to tracked files, on an
untracked file that differs from the branch's copy, and (with `--apply`)
without `backup_dir`. Ignored files are never touched and nothing is deleted.
The rules are in the script's docstring.

## Backups

`backup_dir` in `.claude/kit.json` names the directory that holds backups
(`~` is expanded). It has no default. Unset, history_guard denies every pull
request merge and `update_worktree.py --apply` stops.

Each backup is a new folder `<backup_dir>/<UTC date>-NN/`, NN the next free
number for that date. The folder holds the backed-up files and a
`MANIFEST.sha256` listing them in `sha256sum -c` format. Each backup appends
one line to `<backup_dir>/INDEX.md` naming its folder. Agents create
backups and never delete them; pruning is the owner's, by hand.

- **Merge backups** (coder.md item 10), written by a coder before it merges
  PR N, after `git fetch`: a bundle of `origin/<base branch>` (`git bundle
  create`), `merge.json` (`pr`, `branch`, `sha` of `origin/<base branch>`,
  `bundle`), and `MANIFEST.sha256` over both. The INDEX.md line names the
  folder, `#<N>` and the pre-merge SHA. history_guard checks all of this
  before it lets the merge through (see "Merging and undoing a merge").
- **update_worktree.py's moves** (`--apply`): each untracked file that is
  byte-identical to `origin/<branch>`'s copy is moved into the folder under
  its repo-relative path, never overwriting. `MANIFEST.sha256` lists the
  moved files. The INDEX.md line names the folder, the worktree path,
  update_worktree.py and `origin/<branch>`'s SHA. With nothing to move, no
  folder or line is written.

**"Created after" means birth time.** Where a backup rule or a check asks
whether a file was created after some moment, "created" is the file's birth
time (`statx` btime), never its modification time (mtime). Where the
filesystem gives no birth time, the backup's record says so. It never falls
back to mtime.

## Blocked calls in the session log

When dispatch_guard or role_guard blocks a dispatch (an Agent call), the
session log does not record a `deny` decision for it. The block shows as a
`toolDenialKind` field on the tool_result, for example `"permission-rule"`.
Anything that reads a session log for blocked calls must match on
`toolDenialKind`, not on a `deny` decision. Evidence: RECORD.md 2026-09-23-10,
where a Type/target mismatch and a general-purpose dispatch were each blocked
and logged with `toolDenialKind` permission-rule.

## Resuming after a disconnect

A session that drops (a network error, a closed terminal) can leave agents
it sent running, finished or dead. Settle every one of them before
re-sending anything:

1. Find the lost session's log:
   `~/.claude/projects/<project>/<sessionId>.jsonl`. `<project>` is named
   from the session's working directory: every character outside
   [A-Za-z0-9] becomes `-`; per the installed Claude Code 2.1.282, a name
   over 200 characters is cut and given a hash suffix (read from the
   binary, not verified). The tools find logs by session id rather than by
   computing the name: `ls ~/.claude/projects/*/<sessionId>.jsonl`. Its
   subagents' transcripts are in `<sessionId>/subagents/` beside it.
2. Run `python3 session_agents.py <that log>`. For each Agent call it prints
   the timestamp, tool_use id, type, description, foreground or background,
   agentId, the outcome (`completed`, `failed: ...`, `denied: ...`,
   `launched, no completion notice`, `no result`), hand-backs and
   SendMessages, and for an unfinished agent how far its transcript got.
3. Run `python3 find_dispatches.py` for dispatches the hook saved that no
   store copy holds yet.
4. Settle each agent, before re-sending anything:
   - Handed back: read the hand-back.
   - Completed with no hand-back: read its transcript.
   - Failed, or no completion notice: check its branch, pull request and CI
     (`git ls-remote origin <branch>`, `gh pr view <branch>`), then decide
     whether to continue its intent (coder.md item 7) or re-send the
     dispatch (item 11).
5. Cite calls by tool_use id and timestamp, not line number: resuming a
   session can rewrite its log, which shifts line numbers, sorts keys and
   drops queue-operation records.

Example (T14-T16, RECORD.md 2026-09-25-60 to -64): the coder died at 15:26Z
with an API error and no hand-back. The helper shows its call as
`failed: ... (EAI_AGAIN) ...`, with hand-backs 0 and a transcript ending in
an API error after its last message, "Opening the PR now so CI runs on the
fix commit." Its pull request was open and green, so a new coder continued
its intent (2026-09-25-63) rather than re-sending it.

## Launching a session

`launch_session.py` starts one headless Claude Code session in a checkout,
under a wall-clock limit, and only after checking that it is the session
you meant to start:

    python3 launch_session.py --cwd <checkout> --prompt-file <file> \
        --out <stream file> [--expect-commit <sha>] [--timeout 600] \
        [--max-budget-usd <n>] [--model <m>] [--claude <path>] [--grace 15]

It runs these steps in order. Each check stops the run with a reason.

1. **The checkout.** `--cwd` must be a git work tree with no tracked
   changes, and its HEAD must equal `--expect-commit`. The default is
   `origin/<first protected branch in .claude/kit.json>` as last fetched;
   the launcher never fetches. This guards against the v0.1 failure: the
   first live-exercise sessions each started in a new harness worktree at
   `9390407`, so they ran v0.1's hooks instead of the fixes (RECORD.md
   2026-09-23-07; store 2026-09-23-10.md).
2. **The hooks.** It runs `python3 <cwd>/.claude/hooks/session_check.py`
   itself, with the SessionStart input Claude Code would give it. Any
   output, a nonzero exit, or a missing hook file means a stale or
   unexpected checkout, and nothing starts. `claude --init-only` does run
   the hook, but on Claude Code 2.1.282 it shows the hook's output only in a
   `--debug-file` log, and the flag is not in `claude --help` (RECORD.md
   2026-09-25-71).
3. **The launch.** `claude -p --session-id <new uuid> --output-format
   stream-json --verbose --permission-prompts none`, plus `--max-budget-usd`
   and `--model` when given. The prompt goes on stdin, and the session runs
   in its own process group. Nobody can answer a permission prompt, so any
   prompt is denied. The stream is written to `--out` line by line, verbatim,
   and stderr to `<out>.stderr`.
4. **The identity.** The stream's first `system`/`init` message must show the
   launcher's uuid as `session_id` and the real path of `--cwd` as `cwd`.
   Otherwise the group is stopped as in step 5.
5. **The time limit.** `--timeout` seconds from launch, 600 by default. At the
   limit: SIGTERM to the whole process group, up to `--grace` seconds (15 by
   default) for it to exit, then SIGKILL. Then it confirms that no process of
   the group is left, and names any that are. A timed-out command is killed
   with everything it started. This guards against the hung pre-check
   `claude remote-control --help`, which printed nothing for more than 2
   minutes (RECORD.md 2026-09-23-07) and left its process, PID 100263,
   behind until the next morning (2026-09-23-11).
6. **Interruption.** SIGINT (Ctrl-C), SIGTERM or SIGHUP to the launcher while
   the hooks check or the session is running stops that process group the
   same way as step 5, prints the report with the outcome
   `interrupted by <signal>`, and exits 130. The session runs in its own
   process group, so without this a Ctrl-C would end the launcher and leave
   the session running. A signal that arrives while nothing is running (the
   pre-check, between the hooks check and the launch, or after the session
   has exited) exits 130 at once, with one line on stderr, and kills
   nothing. A signal that arrives while a group is already being stopped is
   ignored, and that stop goes on.

Then it prints one line per fact:
- the session id
- the session log, found by its session id as the one file matching
  `<projects root>/*/<uuid>.jsonl`, or "not found" with that pattern, or
  "ambiguous" with every match. The projects root is
  `$LAUNCH_SESSION_PROJECTS_ROOT` when set (the tests use it), else
  `$CLAUDE_CONFIG_DIR/projects` when CLAUDE_CONFIG_DIR is set (inferred),
  else `~/.claude/projects`. The launcher does not compute the directory
  name. Claude Code names it from the cwd: every character outside
  [A-Za-z0-9] becomes `-`; per the installed Claude Code 2.1.282, a name over
  200 characters is cut and given a hash suffix (read from the binary, not
  verified).
- claude's exit code (negative means killed by that signal)
- the elapsed seconds
- the signals sent and any processes left, when there are any
- the outcome

Exit codes:

| Code | Outcome |
|---|---|
| 0 | finished: the session exited on its own before the limit, after a correct init. Claude's own exit code is on its report line. |
| 2 | usage error: bad arguments, an existing `--out` or `<out>.stderr`, a missing `--out` directory, or an unreadable `--prompt-file` |
| 3 | timed out |
| 4 | wrong session: the checkout, the hooks or the init's identity |
| 5 | failed to start: claude not found or not runnable, or no init message before claude exited or the limit passed |
| 130 | interrupted: SIGINT, SIGTERM or SIGHUP (step 6) |

It deletes nothing: no session log, no output file and no worktree. It
writes only `--out` and `<out>.stderr`, and it creates both new at launch,
so a failed check writes nothing and an existing file is never overwritten.
A session killed at the limit keeps its log and stream as evidence.

## Live exercise

`run_exercise.py` checks the dispatch hooks end to end in real sessions.
It makes four dispatches, one per headless session, and reads the evidence
from each session's log:

    python3 run_exercise.py --repo <checkout> --out-dir <dir> \
        [--model claude-opus-5-5] [--max-budget-usd 2.00] [--timeout 600] \
        [--cases 1,2,3,4] [--claude <path>]

It creates a detached worktree of `origin/<first protected branch>` as last
fetched (it never fetches) at `<out-dir>/worktree`, so every case runs the
hooks of that commit. For each case it writes `<out-dir>/case-N.prompt` and
runs `launch_session.py` in the worktree, with the stream in
`<out-dir>/case-N.jsonl`. Each prompt asks the session for exactly one
Agent call, in the foreground, sending the text below a marker line
unchanged, and then a stop.

| Case | Dispatch | What it proves |
|---|---|---|
| 1 | `Type: pulse` to `pulse` (a Read-only question) | an approval-exempt type runs: dispatch_guard allows it, saves it, and the pulse's result comes back |
| 2 | `Type: build` to `coder`, every build section present | a type that needs approval is held: dispatch_guard saves it and asks, and it does not run unless someone approves |
| 3 | `Type: pulse` to `coder` | a Type cannot be sent to another agent to skip approval: blocked |
| 4 | `Type: pulse` to `general-purpose` | a built-in agent type cannot be dispatched: blocked |

The evidence rules:
- The case's call is the first Agent tool_use to its subagent type, and
  its prompt must equal the case's text. The decision is read from
  dispatch_guard's `hook_success` attachment (hookName `PreToolUse:Agent`)
  with that call's toolUseID, and the outcome from the call's tool_result.
  Every log line is parsed as JSON; key order and line numbers are never
  matched.
- A blocked call (cases 3 and 4) is matched on the tool_result's
  `toolDenialKind`, never on a `deny` decision (see "Blocked calls in the
  session log"). A hook that blocks leaves no decision in the log, and a
  log that shows a `deny` decision without a `toolDenialKind` fails.
- Case 1 passes on decision `allow`, then a completed result with an agentId
  and a result text or a hand-back. Case 2 passes on decision `ask`, then an
  error tool_result with a `toolDenialKind`, whose value is reported, and
  no agent run for the call. Case 3 passes on `permission-rule` with
  dispatch_guard's Type/target text; case 4 on `permission-rule` with the
  unknown-agent text of dispatch_guard or role_guard, and the line names
  which.

Case 2 is denied automatically. The launcher runs `claude` with
`--permission-prompts none`, so nobody can answer dispatch_guard's approval
prompt and the prompt is denied. In the v0.1 exercise, run by hand, the
owner declined it, and the log showed `toolDenialKind` "user-rejected". An
automatic denial proves the same thing, that the build did not run without
approval, but its `toolDenialKind` may differ, so the runner does not
require a particular value.

The output is `<out-dir>/evidence.txt`, one line per case, and the same lines
on stdout:

    case N | session <id> | log <path> | tool_use <id> | decision <d> | toolDenialKind <k> | result "<first 150 characters>" | PASS

A failing case ends in `FAIL: <reason>` in place of `PASS`. A launcher exit
other than 0 is that case's FAIL, with the launcher's report quoted. The
exit status is 0 if every case run passes, 1 if any fails, and 2 on a usage
error, when nothing is run. The launcher's reports go to stderr.

Cost: each case is one session capped by `--max-budget-usd`, $2.00 by
default, so four cases cost at most $8.00. Case 1 costs the most, since its
pulse runs as a subagent. The model defaults to `claude-opus-5-5`.

Clean-up: the runner deletes nothing. The worktree is kept, because cases 1
and 2 leave dispatch_guard's copies in its `prompts/preserved/`. Record
them first: `find_dispatches.py`, run from the main checkout, lists them
with copy commands. Then remove the worktree with
`git worktree remove <out-dir>/worktree`. The worktree shares the clone's
dispatch counter, so its copies are numbered in the same sequence as the
main checkout's.

## Tests

    python3 -m unittest discover -s .claude/hooks/tests
    python3 check_record.py --render-check
    python3 check_prompts.py --render-check
    python3 -m unittest discover -s tests

`tests/` is not released. It holds seven test files: `test_install.py`
(install and drift), `test_release_check.py` (release_check),
`test_find_dispatches.py` (find_dispatches), `test_update_worktree.py`
(update_worktree), `test_session_agents.py` (session_agents, on
hand-built session logs), `test_launch_session.py` (launch_session, with
fake `claude` executables, including one that hangs with a sleeping child
and one that ignores SIGTERM) and `test_run_exercise.py` (run_exercise,
with a fake `claude` that writes a fixture session log for the session id
it is given). The install tests tag only a throwaway copy of this
repository, never this repository.

The hook tests never read the repository's own `kit.json`: the harness copies
the hooks into a temporary `.claude/hooks/` with a test config beside them.

## Checkers: diff from upstream

`check_record.py` and `check_prompts.py` are EGD's (E-GD-Philosophy
`35e39d1`), with the dispatch-note entry kind added: 129 lines added and 1
changed in `check_record.py`, 124 added in `check_prompts.py`. The full diff:

```diff
--- EGD 35e39d1 check_record.py
+++ Claude-kit check_record.py
@@ -94,6 +94,46 @@
 SUPPLIED_FIELD = "Prediction-outcome-supplied"
 
 
+# Claude-kit v0.1 addition.
+# A dispatch-note records a dispatch that opens no intent -- a pulse, a
+# build the operator declined, a live exercise of the dispatch hook -- so
+# the prompt the hook preserved for it is still claimed by an entry. It
+# opens and closes nothing and carries no prediction or finish line, so
+# carrying any of those fields is an error rather than an ignored extra.
+NOTE_KIND = "dispatch-note"
+NOTE_REQUIRED = ["Kind", "ID", "Dispatch-file", "Type", "Outcome", "Report"]
+NOTE_TYPES = {"build", "device", "pulse"}
+NOTE_OUTCOMES = {"answered", "declined", "exercise"}
+NOTE_FORBIDDEN = ["Closes", "Superseded-by", "Finish line",
+                  "Prediction (outcome — planner)",
+                  "Prediction (mechanism — coder)"]
+
+
+def _validate_note(fields, entry_id, label_for_errors):
+    errors = []
+    if entry_id and not ID_RE.match(entry_id):
+        errors.append(f"{NOTE_KIND} {entry_id}: malformed ID (expected "
+                      f"YYYY-MM-DD-NN)")
+    for req_label in NOTE_REQUIRED:
+        if not fields.get(req_label, "").strip():
+            errors.append(f"{NOTE_KIND} {label_for_errors}: missing required "
+                          f"field {req_label!r}")
+    note_type = fields.get("Type", "").strip()
+    if note_type and note_type not in NOTE_TYPES:
+        errors.append(f"{NOTE_KIND} {label_for_errors}: Type {note_type!r} is "
+                      f"not one of {sorted(NOTE_TYPES)}")
+    outcome = fields.get("Outcome", "").strip()
+    if outcome and outcome not in NOTE_OUTCOMES:
+        errors.append(f"{NOTE_KIND} {label_for_errors}: Outcome {outcome!r} "
+                      f"is not one of {sorted(NOTE_OUTCOMES)}")
+    for label in NOTE_FORBIDDEN:
+        if label in fields:
+            errors.append(f"{NOTE_KIND} {label_for_errors}: carries field "
+                          f"{label!r}, but a dispatch-note opens and closes "
+                          f"nothing and has no prediction or finish line")
+    return errors
+
+
 def split_entries(text):
     """Raw text blocks for each entry, found after the '## Entries'
     heading and separated by bare '---' lines. Header/format
@@ -151,6 +191,17 @@
         entry_id = fields.get("ID", "").strip()
         label_for_errors = entry_id or f"entry #{i + 1} (no ID)"
 
+        if kind == NOTE_KIND:
+            errors.extend(_validate_note(fields, entry_id, label_for_errors))
+            if entry_id:
+                if entry_id in seen_ids:
+                    errors.append(f"duplicate ID {entry_id}: used by entry "
+                                  f"#{seen_ids[entry_id] + 1} and entry #{i + 1}")
+                else:
+                    seen_ids[entry_id] = i
+            entries.append({"kind": kind, "id": entry_id, "fields": fields})
+            continue
+
         if kind not in ("intent", "terminal"):
             errors.append(f"{label_for_errors}: missing or invalid Kind "
                           f"(got {kind!r})")
@@ -542,6 +593,16 @@
     return _render_entry(fields)
 
 
+def _minimal_note(id_="2026-01-01-05", **overrides):
+    fields = {
+        "Kind": "dispatch-note", "ID": id_,
+        "Dispatch-file": "preserved/2026-01-01-05.md", "Type": "pulse",
+        "Outcome": "answered", "Report": "none",
+    }
+    fields.update(overrides)
+    return _render_entry(fields)
+
+
 def _minimal_record(*entries):
     parts = ["# RECORD.md", "", "## Entries", "", "---", ""]
     for e in entries:
@@ -889,8 +950,75 @@
           "intent ID is accepted",
           check18)
 
+    # ---- Checks 19-23: dispatch-note entries (Claude-kit v0.1 addition) ---------
+    def check19():
+        text = _minimal_record(_minimal_intent(), _minimal_note())
+        entries, errors, unterminated, _ = validate_entries(text)
+        assert not errors, f"a well-formed dispatch-note produced errors: {errors}"
+        assert len(entries) == 2
+        assert unterminated == ["2026-01-01-01"], (
+            f"a dispatch-note was counted as opening or closing an intent: "
+            f"{unterminated}")
+
+    check("check19_well_formed_dispatch_note_accepted",
+          "a well-formed dispatch-note is rejected as an invalid Kind, or "
+          "is counted as opening or closing an intent",
+          check19)
+
+    def check20():
+        text = _minimal_record(_minimal_note(Report=None))
+        _, errors, _, _ = validate_entries(text)
+        assert any("2026-01-01-05" in e and "'Report'" in e for e in errors), (
+            f"dispatch-note missing 'Report' not reported by ID and field: {errors}")
+
+    check("check20_dispatch_note_missing_field_names_fault",
+          "a dispatch-note missing a required field is accepted, or the "
+          "error does not name both the entry and the field",
+          check20)
+
+    def check21():
+        text = _minimal_record(_minimal_note(Outcome="completed"))
+        _, errors, _, _ = validate_entries(text)
+        assert any("2026-01-01-05" in e and "Outcome" in e and "'completed'" in e
+                   for e in errors), (
+            f"dispatch-note with an Outcome outside answered/declined/exercise "
+            f"was accepted: {errors}")
+
+    check("check21_dispatch_note_rejects_unknown_outcome",
+          "a dispatch-note whose Outcome is not answered, declined or "
+          "exercise is accepted",
+          check21)
+
+    def check22():
+        text = _minimal_record(_minimal_note(Type="audit"))
+        _, errors, _, _ = validate_entries(text)
+        assert any("2026-01-01-05" in e and "Type" in e and "'audit'" in e
+                   for e in errors), (
+            f"dispatch-note with a Type outside build/device/pulse was "
+            f"accepted: {errors}")
+
+    check("check22_dispatch_note_rejects_unknown_type",
+          "a dispatch-note whose Type is not build, device or pulse is "
+          "accepted",
+          check22)
+
+    def check23():
+        text = _minimal_record(_minimal_intent(),
+                               _minimal_note(Closes="2026-01-01-01"))
+        _, errors, unterminated, _ = validate_entries(text)
+        assert any("2026-01-01-05" in e and "'Closes'" in e for e in errors), (
+            f"a dispatch-note carrying Closes was accepted: {errors}")
+        assert unterminated == ["2026-01-01-01"], (
+            f"a dispatch-note's Closes field closed an intent: {unterminated}")
+
+    check("check23_dispatch_note_cannot_close_an_intent",
+          "a dispatch-note carrying a Closes field is accepted, or closes "
+          "the intent it names",
+          check23)
+
+    total = 23
     print(f"\n{'FAIL' if failures else 'PASS'}: {len(failures)} of "
-          f"{18} checks failed{': ' + ', '.join(failures) if failures else ''}")
+          f"{total} checks failed{': ' + ', '.join(failures) if failures else ''}")
     return 1 if failures else 0
 
 
```

```diff
--- EGD 35e39d1 check_prompts.py
+++ Claude-kit check_prompts.py
@@ -169,6 +169,17 @@
                 f"{DISPATCH_FIELD!r} field: {', '.join(ids)}")
     errors.extend(duplicate_errors)
 
+    # Claude-kit v0.1 addition: a dispatch-note claims
+    # exactly one *preserved* prompt -- the hook's verbatim capture -- never
+    # a recovered one.
+    for entry_id, value in claims:
+        kind = kind_closes.get(entry_id, ("", ""))[0]
+        if kind == cr.NOTE_KIND and not value.startswith(f"{PROVENANCE_DIRS[0]}/"):
+            errors.append(
+                f"entry {entry_id}: a {cr.NOTE_KIND} may only claim a prompt "
+                f"under {PROMPTS_DIR}/{PROVENANCE_DIRS[0]}/, but its "
+                f"{DISPATCH_FIELD!r} names {value!r}")
+
     missing = []
     for entry_id, value in claims:
         if value not in on_disk:
@@ -229,5 +240,118 @@
     return 1
 
 
+# --------------------------------------------------------------------------
+# Self-tests (Claude-kit v0.1 addition). Store-level fixtures under a temp dir,
+# checked by both this script's binding check and check_record.py's entry
+# validation, because a dispatch-note is only a valid claim if it is also a
+# valid entry.
+# --------------------------------------------------------------------------
+
+def _store(tmp, files, entries):
+    root = Path(tmp)
+    for rel in files:
+        path = root / PROMPTS_DIR / rel
+        path.parent.mkdir(parents=True, exist_ok=True)
+        path.write_text(f"prompt {rel}\n")
+    text = cr._minimal_record(*entries)
+    (root / RECORD_NAME).write_text(text)
+    return text
+
+
+def _store_errors(tmp, files, entries):
+    """Binding errors plus entry-validation errors, for one fixture store."""
+    text = _store(tmp, files, entries)
+    _, binding_errors, _, _ = check_binding(tmp)
+    _, entry_errors, _, _ = cr.validate_entries(text)
+    return binding_errors, entry_errors
+
+
+def render_check():
+    import tempfile
+    print("check_prompts.py --render-check")
+    failures = []
+
+    def check(name, expect_fail_msg, fn):
+        print(f"\n[{name}] expected failure mode if broken: {expect_fail_msg}")
+        try:
+            fn()
+            print(f"[{name}] PASS")
+        except Exception as e:
+            print(f"[{name}] FAIL: {e!r}")
+            failures.append(name)
+
+    pulse = "preserved/2026-01-01-05.md"
+
+    def p1():
+        tmp = tempfile.mkdtemp(prefix="check_prompts_render_check_")
+        binding, _ = _store_errors(tmp, [pulse], [cr._minimal_intent()])
+        assert any(pulse in e and "no RECORD.md entry" in e for e in binding), (
+            f"an unclaimed pulse prompt was not reported: {binding}")
+
+    check("p1_unclaimed_pulse_prompt_fails",
+          "a preserved prompt no entry claims passes the binding check",
+          p1)
+
+    def p2():
+        tmp = tempfile.mkdtemp(prefix="check_prompts_render_check_")
+        binding, entry = _store_errors(
+            tmp, [pulse], [cr._minimal_intent(), cr._minimal_note()])
+        assert not binding, f"a dispatch-note's claim was not accepted: {binding}"
+        assert not entry, f"the claiming dispatch-note is not a valid entry: {entry}"
+
+    check("p2_pulse_prompt_with_its_note_passes",
+          "a pulse prompt claimed by a well-formed dispatch-note fails "
+          "either the binding check or entry validation",
+          p2)
+
+    def p3():
+        tmp = tempfile.mkdtemp(prefix="check_prompts_render_check_")
+        stray = "recovered/2026-01-01-05.md"
+        binding, _ = _store_errors(
+            tmp, [stray],
+            [cr._minimal_note(**{"Dispatch-file": stray})])
+        assert any("2026-01-01-05" in e and "preserved/" in e for e in binding), (
+            f"a dispatch-note claiming a prompt outside preserved/ was "
+            f"accepted: {binding}")
+
+    check("p3_sabotaged_note_outside_preserved_fails",
+          "a dispatch-note claiming a prompt outside prompts/preserved/ "
+          "is accepted as a claim",
+          p3)
+
+    def p4():
+        tmp = tempfile.mkdtemp(prefix="check_prompts_render_check_")
+        _, entry = _store_errors(
+            tmp, [pulse], [cr._minimal_note(Outcome="done")])
+        assert any("Outcome" in e and "'done'" in e for e in entry), (
+            f"a dispatch-note with a sabotaged Outcome was accepted: {entry}")
+
+    check("p4_sabotaged_note_outcome_fails",
+          "a dispatch-note with an Outcome outside answered, declined and "
+          "exercise is accepted",
+          p4)
+
+    def p5():
+        tmp = tempfile.mkdtemp(prefix="check_prompts_render_check_")
+        binding, _ = _store_errors(
+            tmp, [pulse],
+            [cr._minimal_intent(**{"Dispatch-file": pulse}), cr._minimal_note()])
+        assert any("claimed by more than one" in e for e in binding), (
+            f"a prompt claimed by both an intent and a dispatch-note was "
+            f"accepted: {binding}")
+
+    check("p5_note_and_intent_on_one_prompt_fails",
+          "one prompt claimed by both an intent and a dispatch-note is "
+          "accepted",
+          p5)
+
+    total = 5
+    print(f"\n{'FAIL' if failures else 'PASS'}: {len(failures)} of "
+          f"{total} checks failed{': ' + ', '.join(failures) if failures else ''}")
+    return 1 if failures else 0
+
+
 if __name__ == "__main__":
+    if "--render-check" in sys.argv:
+        sys.exit(render_check())
     sys.exit(main())
```
