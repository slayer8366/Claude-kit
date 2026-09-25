# Standing rulings

Decisions the owner has made once and does not want asked again. The planner
may apply a ruling here without asking, but only inside its stated scope, and
cites its ID in the dispatch (`Standing: SR-03`). A case not clearly inside a
ruling's scope is asked, as before. No ruling is extended by analogy.

This file is append-only, like `RECORD.md`: nothing written here is changed
or removed, except that an `Accepted:` line may be added to a Part A ruling,
naming the record entry where the owner accepted it. A ruling changes only by
a new owner ruling that supersedes it: the old one stays, marked with the ID
that replaced it, and the new one quotes the wording it replaces. No checker
enforces any of this; check_record.py's append-only check covers only
RECORD.md.

This file belongs to the workshop and is not part of any release. Each adopter
keeps its own.

A ruling is standing only if it is in Part A and carries an `Accepted:` field
naming the RECORD.md entry where the owner accepted it. Part B holds
proposals; nothing there is standing. Drafted by the owner from `RECORD.md` up
to 2026-09-24-12, corrected and extended against the repository at 82725c4
(RECORD.md 2026-09-25-14).

## How to read a ruling

- **Ruling:** what is decided, in the owner's words where the record has them.
- **Source:** the record entry where the owner decided it.
- **Scope:** exactly what it covers. Anything outside it is asked.
- **Enforced by:** code (with the file), GitHub settings, or convention only.
  "Unverified" means the drafter has not read the code that would enforce it.
- **Accepted:** the RECORD.md entry where the owner accepted it as standing.
  Absent means not standing.

## Part A. Rulings the owner has already made

These have an owner source in the record. Accepting them makes them standing;
it does not change what they say.

### SR-01. Only the owner tags

- **Ruling:** A release is a tag; tagging is the owner's action after reading
  the release diff; the coder does not tag.
- **Source:** 2026-09-23-01, Closed decisions ("From the dispatch (owner,
  2026-09-22 and 23)"), RECORD.md:37.
- **Scope:** Creating, moving or deleting any tag in the kit repository.
- **Enforced by:** Partly code. role_guard.py gives the planner and the pulse
  no `git tag`, since it is not on the read-only git list (role_guard.py:85-87;
  the refusal is at :132). No hook blocks the coder: `tag` does not appear in
  history_guard.py or role_guard.py at 82725c4. Convention for the coder.

### SR-02. The installer never overwrites or merges an adopter's settings

- **Ruling:** If an adopter's `.claude/settings.json` exists and differs from
  the kit's, stop and report. No merge, no replacement.
- **Source:** 2026-09-23-01, Addendum 2, ruling 4(6), RECORD.md:56-57.
- **Scope:** `install.py` and any later tool that writes into an adopter.
- **Enforced by:** Code, `install.py` (`install()`, settings check before any
  write, install.py:73-78, before the first write at :83). Tested by
  `test_differing_settings_json_stops_and_writes_nothing`
  (tests/test_install.py:139-148). A sabotage test fails when the check is
  removed (2026-09-23-02, RECORD.md:80: "sabotage of ... install.py's
  settings check ... failed a test naming the edit").
- **Superseded-by:** SR-04

### SR-03. Backups are never deleted by agents

- **Ruling:** Backups live on the local drive, outside the repository,
  indexed, created by agents and never deleted by them.
- **Source:** 2026-09-23-01, Closed decisions (Forager's accountability design
  at b2435ef, cited by meaning).
- **Scope:** Backups only. Worktrees, scratch files and branches are not
  covered here; see B-01.
- **Enforced by:** Unverified.

### SR-04. An upgrade replaces an adopter's settings only if unedited

- **Ruling:** On an upgrade, `.claude/settings.json` is replaced only if its
  sha256 equals the old lock's (the adopter never edited it); an edited one
  stops the upgrade before anything is written. No merge. On a first install,
  a `.claude/settings.json` that exists and differs from the release's still
  stops the install.
- **Source:** The owner's T13 answer "Unedited may update" (planner log
  791cc457 line 668, 2026-09-25T03:30:16.967Z) to the question at line 662,
  whose option text reads: "Narrow it: settings.json is replaced only if its
  sha256 equals the old lock's (the adopter never edited it); any edit still
  stops the upgrade, as now. This changes an owner ruling, so it would be
  recorded as superseding 2026-09-23-01 ruling 4(6)." Recorded in intent
  2026-09-25-18 (RECORD.md:1147, and its Supersedes-ruling field at :1152).
- **Scope:** `install.py` and any later tool that writes into an adopter.
- **Enforced by:** Code, `install.py` at 742d10f. An upgrade classifies every
  path before writing (`plan_upgrade`, install.py:161-180): a kept path whose
  sha256 differs from the old lock's is a stop (:170-171), an unchanged one is
  written (:172-173), and any stop raises before the first write (:200-205).
  A first install keeps the old check (:191-197). Tested by
  `test_u4_unedited_settings_json_is_replaced` (tests/test_install.py:270-277)
  and `test_u5_edited_settings_json_stops` (:279-285); the first-install case
  by `test_differing_settings_json_stops_and_writes_nothing` (:176).
- **Supersedes:** SR-02, whose ruling reads: "If an adopter's
  `.claude/settings.json` exists and differs from the kit's, stop and report.
  No merge, no replacement."

## Part B. Practices waiting for an owner ruling

These appear in dispatch after dispatch, but the record shows them written by
the planner per dispatch, not ruled by the owner as standing. Each needs the
owner's yes, no or changed wording before it moves to Part A.

### B-01. Agents delete nothing

- **Proposed ruling:** No agent deletes a worktree, branch or store file, or
  any file another agent or the owner may need. Cleanup means stopping
  processes and recording what was left. An agent may delete its own scratch
  files under `/tmp`, provided each deletion is reported in its hand-back.
- **Evidence:** "delete nothing in it" (2026-09-23-01, Addendum 1, ruling 3,
  about the existing clone, RECORD.md:38); "Nothing deleted" in later scope
  boundaries (2026-09-24-01, -03, -06, -09 and -11, RECORD.md:275, 305, 345,
  385 and 416); "Scratch files are left in /tmp" in terminals 2026-09-24-10
  and -12 (RECORD.md:404 and 436). The T9 coder's deletion of `/tmp/t9_fd.txt`
  appears only in its hand-back ("I deleted one scratch file of my own,
  `/tmp/t9_fd.txt`", planner log 791cc457 line 356, 2026-09-25T01:38:40Z),
  not in the record; its terminal, 2026-09-25-08, does not mention it. The
  same path was listed as its own scratch file by the first T9 coder, D5, in
  its hand-back (line 339, 01:25:48Z). Whether the deleted file was D5's or a
  new one of the same name is not established.
- **Why ask:** Ruling 3 covers one clone. The `/tmp` exemption is proposed by
  the planner, following the owner's suggestion; T7's cleanup depends on this
  ruling.
- **Superseded-by:** B-12

### B-02. Two failed fixes on one symptom, then data only

- **Proposed ruling:** After two failed fixes on the same symptom, the coder
  stops changing code and reports what it observed.
- **Evidence:** Abort conditions of every intent from 2026-09-23-01 to
  2026-09-24-11, except 2026-09-23-06 (RECORD.md:177), which has none; also
  every intent from 2026-09-24-14 to 2026-09-25-13.
- **Why ask:** Already stated in coder.md's Non-negotiables ("**Two misses,
  then data.** After two failed fixes on one symptom, no third hypothesis:
  logs, instrumentation, a minimal repro.", coder.md:80-81 at 82725c4), which
  ships to every adopter. Open: whether the owner adopts that text as a
  standing ruling.

### B-03. A bug outside scope is recorded and flagged, not fixed

- **Proposed ruling:** A defect found outside a dispatch's scope boundary goes
  into the hand-back and the record, and gets its own task. It is not fixed in
  the dispatch that found it.
- **Evidence:** 2026-09-23-01 scope boundary ("a bug the port exposes is
  recorded and flagged, not fixed", RECORD.md:33); flags in 2026-09-23-02
  ("Flagged, not fixed (scope boundary)", RECORD.md:81).
- **Why ask:** Already stated in coder.md's Non-negotiables ("**Scope is a
  wall.** Work outside the scope boundary is flagged, not done.", coder.md:82
  at 82725c4), which ships to every adopter. Open: whether the owner adopts
  that text as a standing ruling.

### B-04. Tests fail first

- **Proposed ruling:** Every behaviour change lands with a tests-only commit
  that fails for the predicted reason, before the fix.
- **Evidence:** Practice in every build since v0.1; the owner's T12 message
  names specific failing-first tests (quoted in 2026-09-24-11, RECORD.md:418:
  "Tests fail first: a heredoc commit message with an apostrophe followed by
  a push to a feature branch; ...").
- **Why ask:** Already stated in coder.md's Non-negotiables ("**Checks fail
  first, for the stated reason.** State the expected failure, see it fail,
  confirm the failure matches, then fix and see it pass.", coder.md:78-79 at
  82725c4), which ships to every adopter. Open: whether the owner adopts that
  text as a standing ruling.

### B-05. Messages and stops are approved before they are sent

- **Proposed ruling:** Every message the planner sends to an agent, and every
  stop it makes, is approved by the owner before it is sent: the owner writes
  or requests it, or the planner offers it and the owner agrees. Never on the
  planner's own initiative.
- **Source:** The owner, planner log 791cc457 line 324 (2026-09-25T01:23:48Z):
  "There is an approval step for a message, but it's already established
  before the message is sent. So it does exist, but not in the order you
  first proposed." and line 330 (01:24:51Z): "Almost. The message is approved
  before being sent, upon the operator constructing it. Or the planner offers
  first. Never on a whim." Recorded in 2026-09-25-07 (RECORD.md:564). The
  planner applied the same rule to TaskStop; that extension is the
  planner's, recorded as such in 2026-09-25-11 (RECORD.md:653) and
  2026-09-25-12 (RECORD.md:742).
- **Scope:** The planner's SendMessage and TaskStop calls.
- **Enforced by:** Convention; the hook cannot check it. The rule is stated in
  role_guard.py's docstring (role_guard.py:22-27 for messages, :33-35 for
  stops).

### B-06. The planner messages and stops only agents its session started

- **Proposed ruling:** The planner may send a message to, or stop, only an
  agent its own session started.
- **Source:** The owner's T9 answer, "Only its own agents (Recommended)"
  (planner log 791cc457 line 310, 2026-09-25T01:21:10Z), recorded in
  2026-09-25-07 (RECORD.md:564) and applied to TaskStop in 2026-09-25-11
  (RECORD.md:652).
- **Scope:** The planner's SendMessage and TaskStop targets.
- **Enforced by:** Code, role_guard.py: `check_send_message`
  (role_guard.py:237-256) and `check_task_stop` (:265-290), both against
  `own_agent_ids` (:207-234), called from `guard` (:322-329). TaskStop's
  `shell_id` is always denied (:270-272).

### B-07. Only the owner merges pull requests

- **Proposed ruling:** Only the owner merges a pull request. No agent merges.
- **Evidence:** No owner ruling in the record. "No merge, no tag" appears in
  every build dispatch in `prompts/preserved/` from 2026-09-23-07 on, written
  by the planner; the v0.1 build dispatches before it (2026-09-23-01 to -06)
  do not prohibit merging. The handover
  message that opens the current planner session (planner log 791cc457
  line 25, 2026-09-24T22:31:06Z) says "Coders never merge or tag."; it is not
  in the record.
- **Scope:** Merging any pull request, or any branch into a protected branch,
  in the kit repository.
- **Enforced by:** Partly code, not GitHub:
  - role_guard.py: the planner and the pulse have no `git merge`
    (role_guard.py:76, a named pattern) and no `gh pr merge` (not on the
    read-only gh list, :90-93).
  - history_guard.py, for every role including the coder: `gh pr merge` is
    blocked (history_guard.py:192-194), and so is `git merge` while the
    repository is on a protected branch (:200-209).
  - GitHub: main is not protected (the branches API gave `"protected":
    false` on 2026-09-25 at about 03:25Z; the rulesets API answered that
    rulesets are not available on the repository's plan). The GitHub web interface and any tool the hooks do not cover can
    merge.
- **Superseded-by:** B-11

### B-08. A push the guard cannot parse stays blocked

- **Proposed ruling:** A command that cannot be parsed and contains a git
  push call is blocked.
- **Source:** The owner, T12 handover (planner log a5d14103 line 25,
  2026-09-24T21:32:03Z): "The task list's T12 done-when is amended in T12's
  own commit: an unparseable push is still blocked. The owner accepted
  this." Recorded in 2026-09-24-11 (RECORD.md:418).
- **Scope:** history_guard.py's push check.
- **Enforced by:** Code, history_guard.py:212-219 (stated in its docstring,
  :19-29).

### B-09. Store names

- **Proposed ruling:** A dispatch's copy in `prompts/preserved/` keeps the
  name the dispatch hook gave it, and every store file's name carries the UTC
  date of its header's `Preserved:` line. Files named before 2026-09-24-05
  are exempt.
- **Source:** The owner's T2 answers ("Date rule for all (Recommended)" and
  "Cutoff by name (Recommended)", planner log a5d14103 line 138,
  2026-09-24T21:37:55Z; the owner's "I'll take your recommendations" for
  "The store copy keeps the name the hook gave it", planner log a4155372
  line 231, 21:30:18Z), recorded in 2026-09-24-09 (RECORD.md:387).
- **Scope:** Names of files under `prompts/preserved/`.
- **Enforced by:** Code, check_prompts.py's store-name check
  (`store_name_errors`, check_prompts.py:85-125, cutoff at :82, called at
  :260; stated in its docstring, :54-60), and coder.md item 5 (coder.md:47-54
  at 82725c4).

### B-10. Copy-versus-notes order

- **Proposed ruling:** A build's commits go: the sweep (dispatch-notes for
  unclaimed store files), then one commit holding the dispatch's store copy
  with its intent or continuation, then the work.
- **Source:** The owner's T4 answer "coder.md + amend (Recommended)" (planner
  log 791cc457 line 489, 2026-09-25T02:41:10Z), recorded in 2026-09-25-13
  (RECORD.md:801 and 803). coder.md item 9 (coder.md:69-74 at 82725c4).
- **Scope:** The order of a build's commits.
- **Enforced by:** Convention; no checker. CI checks out a single commit with
  no history (check_record.py:62-66; coder.md:73-74 at 82725c4).

### B-11. Coders merge at the planner's discretion, after a backup

- **Proposed ruling:** In the owner's words (planner log 791cc457 line 712):
  "coders should be able to merge at the discretion of the planner. All
  merged work must contain a backup, so any merge should be able to be undone
  by the owner later on". The backup: before merging, the coder writes a git
  bundle of the target branch as it stands, with the pre-merge SHA and the PR
  number, in a new ~/forager-backups folder with MANIFEST.sha256 and one
  INDEX.md line. history_guard checks it.
- **Source:** The owner, planner log 791cc457 line 712
  (2026-09-25T03:33:54.808Z), point 2, and the owner's answers at line 717
  (03:34:45.988Z) to the questions at line 716: "Bundle in forager-backups
  (Recommended)", "history_guard checks (Recommended)" and "Next, after T13
  (Recommended)". The owner approved this entry's ruling wording at line 903
  (05:07:45.503Z, "That works as written"). Recorded in 2026-09-25-24.
- **Scope:** Merges of pull requests into the protected branch.
- **Enforced by:** Not yet. Today history_guard blocks `gh pr merge` for every
  role, the coder included (history_guard.py:192-194 at 742d10f). Task T17
  adds the check: the coder only, a backup for that PR indexed with a passing
  manifest, and its SHA equal to the branch tip.
- **Evidence:** The handover that opened planner session 791cc457 (line 25,
  2026-09-24T22:31:06Z) says "Coders never merge or tag."; it is not the
  owner's (line 712, point 1, as the planner read it at line 715). The owner's
  own T12 handover (planner log a5d14103 line 25, 2026-09-24T21:32:03Z) said
  "Coders never merge or tag."; the owner confirmed that handover as theirs
  ("That one is mine", 791cc457 lines 853 and 882), and line 712 replaces
  that statement. So B-07's "No owner ruling in the record" was wrong: the
  owner's statement was in the a5d14103 handover, not in the record.
- **Supersedes:** B-07, whose proposed ruling reads: "Only the owner merges a
  pull request. No agent merges."

### B-12. Agents delete nothing

- **Proposed ruling:** No agent deletes a worktree, branch or store file, or
  any file another agent or the owner may need. Cleanup means stopping
  processes and recording what was left. An agent may delete its own scratch
  files under `/tmp`, provided each deletion is reported in its hand-back.
- **Source:** No owner ruling; proposed by the planner, as B-01 was.
- **Scope:** Deletion by any agent of worktrees, branches, store files and
  files another agent or the owner may need. The exception is an agent's own
  scratch files under `/tmp`, each reported. Backups are SR-03's.
- **Enforced by:** Partly code, for the planner and the pulse only:
  role_guard.py blocks `rm` by name (role_guard.py:77) and allows
  `git worktree` only with `list` (:130-131). The coder is not checked by
  role_guard (:308-309). Convention for the coder.
- **Evidence:** Everything in B-01's Evidence, and:
  - The owner on `/tmp/t9_fd.txt`, answering the planner's "Whose file was
    `/tmp/t9_fd.txt`?" (planner log 791cc457 line 683): "1 I don't know who
    wrote it, it's not mine." (line 712, 2026-09-25T03:33:54.808Z). The file
    was not the owner's; whose it was is unknown.
  - The T13 coders deleted `/tmp` scratch of their own and reported it.
    Terminal 2026-09-25-19 (RECORD.md:1221) records its coder making and
    deleting `/tmp/t13_adhoc_*`; its hand-back (planner log line 738) lists
    the scratch files it left in place (`/tmp/t13_dump.py`,
    `/tmp/t13_cmp.py`, `/tmp/t13_terminal.md`, `/tmp/t13_revert_HeqF`).
    Terminals 2026-09-25-21 (RECORD.md:1326, `/tmp/t13fu_revert_71iZ`) and
    2026-09-25-23 (RECORD.md:1428, `/tmp/t13fu2_revert_2ZOb`) each record the
    coder making its revert directory and deleting it.
- **Supersedes:** B-01, whose proposed ruling reads: "No agent deletes a
  worktree, branch or store file, or any file another agent or the owner may
  need. Cleanup means stopping processes and recording what was left. An
  agent may delete its own scratch files under `/tmp`, provided each deletion
  is reported in its hand-back."

## Superseded rulings

- SR-02, superseded by SR-04.
- B-01, superseded by B-12.
- B-07, superseded by B-11.
