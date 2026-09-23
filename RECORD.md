# RECORD.md

Claude-kit's record of dispatched work on the kit itself. Each piece of work
opens with an intent entry, written before anything is built, stating what will
change, where the change stops, what it is expected to do, and when it counts as
finished or abandoned. It closes with exactly one terminal entry saying what
happened. Dispatches that open no intent (a pulse, a build the operator
declined, a live exercise of the dispatch hook) are recorded by a dispatch
note, so every preserved prompt under `prompts/preserved/` is accounted for by
some entry.

This file is append-only. Nothing already committed is edited or removed; a
correction is a new entry that points at the one it corrects.

What makes an entry well formed is defined in `check_record.py`, and how
entries bind to preserved prompts in `check_prompts.py`, not here. Run both
before committing a change to this file.

This record belongs to the kit's private workshop. It is not part of any
release and is never vendored into an adopter; each adopter keeps its own
`RECORD.md`.

## Entries

---

**Kind:** intent
**ID:** 2026-09-23-01
**Timestamp:** 2026-09-23T03:45:05Z
**Title:** Extract Claude-kit v0.1 from Forager's accountability phase 1
**Dispatch-file:** preserved/2026-09-23-01.md
**Change:** Port Forager's accountability phase 1 (hooks, hook tests, agents, settings.json, check_record.py, check_prompts.py) into this repository as a generic kit, with every Forager-specific value moved into one adopter config, `.claude/kit.json`; add `install.py` (vendor a pinned tag into an adopter, writing `.claude/kit.lock`), `check_kit.py` (drift check against the lock), `release_check.py` (denylist scan of the release set) and CI. Nine steps, one commit each, on branch kit-v0.1.
**Scope boundary:** A faithful port, made generic: same behaviour as Forager b2435ef, with Forager's specifics moved into config. No new guards and no fixes to known gaps; a bug the port exposes is recorded and flagged, not fixed. Nothing in Forager, forager-app or forager-forecast changes. No tag.
**Baseline:** Claude-kit origin/main ff54f06048b639fd3e7f52d766720252a3d05015 (one README, created by the owner), branch kit-v0.1. Source: Forager main b2435efffc8cb6cac3c29f850c20581227ccbecf, read with git show / git archive at that hash, never from a working tree.
**Bootstrap:** This run is unguarded. The kit repository had no hooks when it started, as Forager's phase 1 had none at its first commit. It runs in the clone at ~/Zynergy/Claude-kit (cloned by an earlier session while the repository was empty, confirmed clean with no local commits before branching), not in any Forager worktree. `main` was created by the owner, with a README, after the dispatch was first written. The dispatch file under `prompts/preserved/` is a byte-identical copy of the prompt Forager's dispatch hook preserved as `prompts/preserved/2026-09-23-03.md` in the Forager checkout it was sent from (sha256 965fdefa17532a7a2cc023544d6ae8fd76ea52c91fb97893109b683711949bda); it carries that hook's header, which names Forager's HEAD, not this repository's. The sweep is vacuous: this store held no prompt before this one. Forager's own record steps for this dispatch (its sweep of 2026-09-23-01 to -03) are deferred by the owner's ruling 4 below.
**Sources:** Forager main b2435ef (the 32 phase 1 files, of which 16 are ported). The extraction pulse answer read 2026-09-23T01:29:31Z to 01:33:11Z at b2435ef, committed verbatim at `workshop/extraction-pulse-2026-09-23.md` (checked against the planner's session log message of 2026-09-23T01:34:40Z; identical apart from one trailing newline). Upstream EGD checkers at E-GD-Philosophy 35e39d1.
**Closed decisions:** From the dispatch (owner, 2026-09-22 and 23): the kit repository is private, and the privacy covers its workshop only; released files are vendored into public adopters, so everything released must be fit to publish. A release is a tag; tagging is the owner's action after reading the release diff; the coder does not tag. Adopters vendor a pinned tag with a lock file of hashes; their CI and the drift checker never reach the kit repository. The design the kit implements is Forager's accountability design at b2435ef, cited by meaning: the planner is read-only; builds and device runs need operator approval, pulses run unapproved; the record store is EGD's RECORD.md and checkers, vendored; `.claude/` is tracked in git with settings, agents and hooks re-included; existing permission allows are left untouched and precedence is settled by experiment; history rewriting is guarded; backups live on the local drive, outside the repository, indexed, created by agents and never deleted by them.
Addendum 1, owner rulings relayed by the planner (2026-09-23): (1) Execute this dispatch; `main` now exists on slayer8366/Claude-kit, created by the owner with a README (head ff54f06, verified); branch from it; "empty, no default branch" is superseded. (2) The checkers stay at the repository root; `checkers/` is dropped from the layout; no path logic changes in the checkers; the checker-location config default stays "repository root". (3) Reuse the existing clone at ~/Zynergy/Claude-kit, confirm it clean with no local commits, fetch main and branch kit-v0.1 from it; delete nothing in it. (4) Forager's record steps are deferred: the sweep rule does not apply to Forager in this dispatch; the sweep, intent and terminal entries all happen in this RECORD.md. (5) Known conflict: dropping Grep and Glob from the planner allowlist makes two subtests of b2435ef's `test_allowlisted_tools_pass` fail the behaviour diff; those two are the expected, attributable difference, and any other behaviour-diff failure is the abort condition.
Addendum 2, the owner's ruling on the first run's stop, verbatim:
Operator ruling, 2026-09-23 (kit v0.1, before step 1).

1. Option A. The intent entry's Dispatch-file claims the saved
   dispatch; its terminal may too. No dispatch-note for an
   executed build. (Planner error in step 1's wording.)
2. Commit the kit repo's own .claude/kit.json: package null,
   protected branch main, agents coder and pulse, Forager's
   section lists, checkers at root, prefix KIT_GUARD_. It is not
   in the release set.
3. Drop the prompt-store key. The store stays prompts/preserved
   in the hook and the checkers alike. (Planner error in the key
   list.)
4. Proposals 3-8 approved, except:
   (5) kit.json lives at .claude/kit.json, outside the vendored
       set, as dispatched.
   (6) The installer never overwrites an existing adopter
       settings.json. If one exists and differs from the kit's,
       stop and report. No merge, no replacement. Add a test.
   Commit the extraction pulse answer into workshop/ as the
   source the record cites.
5. Record this ruling in the intent entry's closed decisions.

Tally: two planner errors (step 1 claim wording, prompt-store
key). Prediction 2 confirmed, on the dispatch.
Proposals 3 to 8 as the planner summarised them in the dispatch: (3) config keys are only the ones the dispatch lists, minus the prompt store; the planner allowlist, the pulse tools, the pulse's adb reads and the dispatch tool names stay in code. (4) Grep and Glob are dropped only from the planner allowlist; they stay in role_guard's pulse allowlist and in both agents' tools lines, and are flagged there. (5) Hooks read `.claude/kit.json`, the file beside the hooks directory; unknown keys make the config invalid; the checker location and the environment-variable prefix are optional with the stated defaults, every other key is required; a null package turns off all of device_guard; the template ships a null package. (6) Vendored and locked: the hooks, the hook tests, the agents, settings.json, both checkers and check_kit.py; templates/kit.json is written as .claude/kit.json only if absent; not released: install.py, release_check.py, README.md, workshop/, and the install and release tests. (7) The install and drift tests tag only a throwaway temporary copy of the kit repository, never the kit repository itself. (8) The upstream checker docstrings naming OSCam and ~/imx stay as they are and are not denylisted.
**Provenance:** Incident history removed from the ported files, recorded here with the Forager record it comes from. Device guard (Forager `.claude/hooks/device_guard.py:1-5` at b2435ef): Forager's device run of 2026-09-22, where connectedAndroidTest uninstalled the app and wiped the owner's data, taps landed in another app, and a screenshot caught personal data (Forager `docs/process/accountability-design.md`, "What it answers"; Forager `docs/audits/2026-09-22-accountability-phase-1-device-items-run-record.md`). Dispatch preservation to `prompts/preserved/<date>-<seq>.md` and the dispatch-note entry kind: operator rulings (1) and (3) in Forager `RECORD.md` entry 2026-09-22-03. The dispatch hook's restriction to the named subagents: a live test on 2026-09-22 showed a planner dispatching the built-in general-purpose agent, which ran an MCP call (Forager `RECORD.md` entries 2026-09-22-07 to -09; Forager `docs/audits/2026-09-22-accountability-phase-1-flag1-followup-report.md`). Type bound to target: a pulse-typed dispatch to coder ran without approval (Forager `RECORD.md` entries 2026-09-22-10 and -11; Forager `docs/audits/2026-09-22-accountability-phase-1-type-binding-report.md`). The planner allowlist and the role split by `agent_type`: step 0 observations on Claude Code 2.1.280 and the operator's allowlist ruling, ruling (4) in Forager `RECORD.md` 2026-09-22-03. History rewriting guarded: Forager's closed decision on filter-repo and filter-branch, Forager `RECORD.md` 2026-09-22-03. The checkers' dispatch-note logic (check_record.py checks 19 to 23, check_prompts.py's preserved-only claim rule and its self-tests) is Forager's addition to upstream EGD, from Forager `RECORD.md` 2026-09-22-03; in this kit it is attributed to this entry. The planner allowlist in Forager's design (`docs/process/accountability-design.md`, closed decision A) and ruling (4) of Forager `RECORD.md` 2026-09-22-03 listed Grep and Glob in error: neither exists as a tool on Claude Code 2.1.280 (Forager `docs/audits/2026-09-22-accountability-phase-1-completion-report.md:506`); this port drops them from the planner allowlist.
**Planner prediction (stated in the dispatch, not withheld):** 1. The 49 hook tests port with no logic change, only fixture and config changes. 2. At least one Forager value is hard-coded somewhere the pulse missed, and it turns up when a test sets a different value. 3. Python 3.8 passes.
**Prediction (outcome — planner):** not authored
**Prediction (mechanism — coder):** (a) b2435ef's 49 hook tests, run unchanged against the ported hooks with a kit.json carrying Forager's values and the env prefix FORAGER_GUARD_, pass with exactly two failures: the Grep and Glob subtests of test_allowlisted_tools_pass ('deny' is not None). No fixture change is needed for that run, because the prefix and package are config. (b) Values the pulse's table missed, each found by a test that sets a different value: history_guard compares the current branch to the literal "main" in two more places than MAIN_REFS (the merge-while-on check and the bare-push check), so a protected branch other than main is still merged into and bare-pushed to until both change; dispatch_guard's approval split is the literal type names build and device, not config; check_record.py's dispatch-note Types are the literal set build, device, pulse; role_guard restricts the literal role name pulse. The last three stay in code under Proposal 3 and the scope boundary, and are flagged rather than made configurable. (c) Each config-value test fails first against the hard-coded hooks with an assertion on the decision (for example a foreground check against com.example.kittest returning 'deny' where None is expected), not with a crash. (d) Missing or invalid config: the b2435ef hooks ignore it and return their normal decisions, so the new config-error tests fail first on a missing deny. (e) Python 3.8 runs the hooks and checkers (the walrus operator is the newest syntax in them), but a 3.8 interpreter is not offered for ubuntu-24.04 by actions/setup-python, so the 3.8 CI job needs an older runner image; if that image is unavailable too, the documented minimum rises.
**Finish line:** Steps 1 to 9 committed and pushed on kit-v0.1; CI green; a PR open against main; the release check passing on the release set; a completion report in docs/audits/; a terminal entry closing this intent, with both checkers passing after it. No tag.
**Abort conditions:** Any behaviour change the port needs in order to pass a test. The release check flagging something that cannot be made generic without a design decision. Two failed fixes on one symptom, after which data only. Any behaviour-diff failure other than the two Grep and Glob subtests.

---

**Kind:** terminal
**ID:** 2026-09-23-02
**Timestamp:** 2026-09-23T04:04:43Z
**Closes:** 2026-09-23-01
**Outcome:** completed
**Report:** docs/audits/2026-09-23-kit-v0.1-extraction-completion-report.md
**Observed:** Steps 1 to 9 committed and pushed on kit-v0.1 (a829f13, ed81959, 982d772, d43a1fe, 6fa0315, 4166cb2, c67b26d, bc7d037, 715ecf5), then the commit carrying this entry and the report. PR #1 open against main. CI green at 715ecf5 on Python 3.8.18 and 3.14.7, ubuntu-24.04 (run 35816606081). Behaviour diff: b2435ef's 49 hook tests, unchanged, against the ported hooks with Forager's values in kit.json: 49 ran, 2 failed, exactly the Grep and Glob subtests of test_allowlisted_tools_pass. Every config value has a test that failed first against the hard-coded hooks (68 config-error failures, 16 config-value failures, on the decision or the message); install, drift and release tests failed first with their scripts absent; sabotage of check_kit.py's hash comparison, install.py's settings check and release_check.py's pattern match each failed a test naming the edit. Release check on the release set: PASS, 18 files, 3389 lines, 16 patterns. No tag. Planner prediction: 1 confirmed (the 49 needed no change at all), 2 confirmed (history_guard compared the branch to the literal main at b2435ef history_guard.py:93 and :130, found when a test protected another branch), 3 confirmed. Coder prediction: (a) to (d) confirmed; (e) wrong, since setup-python offers 3.8.18 on ubuntu-24.04.
**Deviations:** Step 1 imported the source files unchanged rather than empty placeholders; the config-value tests landed in step 3 with the hooks, so they could fail against the hard-coded hooks first; the README grew across steps 1, 6, 7 and 8; workshop/behaviour_diff.py and release.json were added as the tools the checks and the one release-set definition need. Flagged, not fixed (scope boundary): the approval split on the literal types build and device (a config-added type runs without approval), check_record.py's fixed dispatch-note Types, role_guard's literal role name pulse, a non-default checkers_dir that the checkers, installer and tests do not follow, and no pruning on reinstall. The full lists are in the report's "Decisions I made" and "Flags outside scope".

---

**Kind:** intent
**ID:** 2026-09-23-03
**Timestamp:** 2026-09-23T07:24:11Z
**Title:** Kit v0.1 fixes before any tag (owner ruling items 1-6)
**Dispatch-file:** preserved/2026-09-23-02.md
**Change:** Five fixes, one commit each, in the order 3, 1, 2, 6, 4, on branch kit-v0.1-fixes. Item 3: drop the `checkers_dir` key; the dispatch hook runs `<root>/check_prompts.py`, and a kit.json still carrying the key is invalid as an unknown key. Item 1: new required key `approval_exempt_types`; every dispatch Type not listed there asks for approval, listed ones are allowed. Item 2: new required key `agent_roles` (agent -> role); role_guard restricts by role (planner, pulse, coder, defined in code), and denies every tool to an agent with no role or an unknown role. Item 6: `SubagentHandback` joins the pulse role's allowlist only. Item 4: released files cite the kit as "Claude-kit v0.1 addition", with the pattern `(?i)claude-kit[^\n]{0,40}RECORD\.md` added to `workshop/denylist.txt`. Then a copy of the named `/tmp` scratch to ~/forager-backups, and a live exercise in a kit-repo session that the owner runs.
**Scope boundary:** Items 1-4 and 6, the scratch copy, and item 5's live-exercise evidence and record. A change to a kit.json key lands in the same commit as the hook and validator that read it, across `.claude/kit.json`, `templates/kit.json`, `.claude/hooks/tests/harness.py` (TEST_CONFIG) and `workshop/behaviour_diff.py`. Nothing in Forager, forager-app or forager-forecast. No tag. Deferred to v0.2 and not built here (owner ruling): history_guard over-blocking on unparseable push commands; a dispatch-note outcome `stopped`; upgrades removing dropped files; a kit bypass table. Also out of scope: `NOTE_TYPES` in check_record.py, the upstream checker docstrings, and where Grep and Glob sit.
**Baseline:** Claude-kit origin/main 93904076a95498b3a877438f6d354fc1b1b88419 (the PR #1 merge), verified against the remote at 2026-09-23T07:22Z; no tags on the remote or locally. Worktree ~/Zynergy/Claude-kit-fixes, branch kit-v0.1-fixes. Old test counts: 68 hook tests; 16 install and release tests.
**Bootstrap:** This run is unguarded (owner's Option B). The dispatch was sent from a planner session in the harness worktree ~/Zynergy/Claude-kit/.claude/worktrees/bridge-cse_017qto3G4Cp8mMH47GPv2RCL, which sits at ff54f06 (the initial commit, no `.claude/`). So no kit hook ran, nothing preserved the prompt, and no approval prompt appeared. The owner's approval ("Approve. Option B, go ahead and dispatch it.") is in that session's chat, as quoted in the dispatch. The coder saved the prompt as `prompts/preserved/2026-09-23-02.md`, taken byte-for-byte from the first user message of its own subagent transcript, ~/.claude/projects/-home-zynergy-labs-Zynergy-Claude-kit--claude-worktrees-bridge-cse-017qto3G4Cp8mMH47GPv2RCL/ffddbdd3-46b7-55a7-9543-3f866eb4544b/subagents/agent-a6a6ce766ed39f887.jsonl. The prompt text is 12473 bytes, sha256 d72bdbef1657cdb4487612d4c7c35828f038c80e8617aa4f3f25e52dcd20f3d4. That hash equals the `prompt` of both Agent tool calls in the planner's log (ffddbdd3-46b7-55a7-9543-3f866eb4544b.jsonl, 2026-09-23T07:02:01Z and 07:21:38Z). The first of those calls (subagent agent-a454baf1b307803c6) ran one read-only command, which verified the base, and was then interrupted by the user; it made no file or git change. Its prompt is this same text and is not preserved separately. The file's header follows the hook's format; its HEAD is ff54f06048b639fd3e7f52d766720252a3d05015, the HEAD of the checkout the dispatch was sent from. The sweep is vacuous: before this file the store held only `2026-09-23-01.md`, already claimed by intent 2026-09-23-01 (check_prompts.py, run before this entry, reported only `2026-09-23-02.md` as unclaimed).
**Closed decisions:** Owner ruling 2026-09-23, verbatim:
```
Kit v0.1, owner ruling, 2026-09-23.

Merge PR #1 as it stands. No tag.

Fix dispatch before any tag, planned from a session in the
Claude-kit checkout:
1. Approval fails closed: every dispatch type requires approval
   unless kit.json explicitly exempts it (default: pulse only).
2. Agents map to roles in kit.json. Role restrictions come from
   the role. An unknown agent or role is denied everything.
3. Drop the checkers_dir key. Checkers stay at the root.
4. Released files cite the kit by release version, not by a
   private record path. Add the pattern to release_check.
5. Live exercise in a kit-repo session: a pulse, a build
   awaiting approval, a blocked mismatch, and a blocked
   unknown agent.
Each fix failing-first with sabotage.

Recorded for v0.2: history_guard over-blocking on unparseable
push commands; dispatch-note outcome `stopped`; upgrades
removing dropped files; a kit bypass table.

Scratch in /tmp (kitsrc-b2435ef, egd-35e39d1, kit_*, first-run
scratch): copy into ~/forager-backups with an INDEX.md line. Do
not delete.
```
Item 6, confirmed by the owner after the ruling: the pulse role's allowlist blocks the hand-back tool `SubagentHandback`; add it to the pulse role only. Planner decisions D1-D8, approved by the owner ("Approve. Option B, go ahead and dispatch it."): D1 `approval_exempt_types` is required, a list of Types that may be empty, each a Type in `type_targets`; `["pulse"]` in both kit.json files and TEST_CONFIG; messages name the Type. D2 `agent_roles` is required; the roles planner, pulse and coder are defined in code; the main session is always planner; every dispatchable agent must have a role (validator); an agent with no role, or a role that is not one of the kit's, is denied every tool at runtime (not a config error); coder is unrestricted; `dispatchable_agents` is kept; `{"coder": "coder", "pulse": "pulse"}` in both files and TEST_CONFIG. D3 `checkers_dir` is removed, and a kit.json carrying it is invalid as an unknown key; coder.md and the README say the checkers sit at the root. D4 the denylist pattern above; "Claude-kit v0.1 addition" wording; README quoted diffs updated; a release_check test that plants `Claude-kit RECORD.md 2026-09-23-01`. D5 SubagentHandback for pulse only, tested allowed for pulse and denied for planner. D6 one commit per item, in the order 3, 1, 2, 6, 4, each with its failing-first test. D7 the live "unknown agent" case is a dispatch to `general-purpose`; role_guard's unknown-agent deny is proven by unit tests only; the "mismatch" case is a `Type: pulse` prompt to coder. D8 this build's scratch goes in `/tmp/kitfix_*`, and the scratch copy runs before any new scratch is made.
**Planner prediction (stated in the dispatch, not withheld):** Item 1: a TEST_CONFIG with an added Type `review` -> coder, not exempt, fails on v0.1 with `'allow' != 'ask'`. Item 2: an agent `reader` mapped to `pulse` calling Write fails on v0.1 with `None != 'deny'`, and so do `general-purpose` calling Read and an agent mapped to role `nosuch`. Item 3: a kit.json with `checkers_dir` fails on v0.1 with `None != 'deny'`. Item 4: after the pattern is added, release_check.py fails on exactly check_record.py:97, check_prompts.py:172 and .claude/hooks/tests/test_role_guard.py:41. Item 6: `tool("SubagentHandback", "pulse")` fails on v0.1 with `'deny' is not None`. Behaviour diff: still exactly 49 source tests, and the only failures are the Grep and Glob subtests of test_allowlisted_tools_pass.
**Prediction (outcome — planner):** not authored
**Prediction (mechanism — coder):** (a) Items 1 and 2 add required keys, and the v0.1 validator rejects any key it does not know (guardlib.py:53-55). So a new test run against v0.1 with a config carrying `approval_exempt_types` or `agent_roles` fails on the config-error deny, not on the guard's decision. The planner's `'allow' != 'ask'` and `None != 'deny'` appear only when the new test runs against v0.1 with v0.1's harness (a config without the new keys). For `reader` and `nosuch` that config cannot express the mapping, so against v0.1 those tests fail on an assertion over role_guard's own message, not on the decision. Each role test therefore asserts role_guard's wording (for example "role_guard:" and the agent's name), so a config-error deny cannot pass it. (b) Item 3: removing the key from CONFIG_DEFAULTS is enough to reject it, through the existing unknown-key check. test_checker_location_comes_from_config and the checkers_dir cases in test_config.py go, since the behaviour they test is removed. (c) Item 1: the approval split becomes membership in `approval_exempt_types`; the existing build and device "ask" tests pass unchanged. (d) Item 2: `guardlib.role()` has one caller (role_guard.py:168), so the role lookup can live in role_guard without touching the other hooks. (e) Item 6: against v0.1 the deny reason is "the pulse role may not use SubagentHandback". (f) Behaviour diff: exactly 49 tests and only the two expected failures. b2435ef's role tests use only the agent types coder and pulse and the main session; its `general-purpose` case is in test_history_guard.py, which does not run role_guard.
**Finish line:** Items 3, 1, 2, 6 and 4 committed and pushed on kit-v0.1-fixes, each with a failing-first test and a sabotage run; the scratch copied and indexed; a stop reporting "ready for live exercise"; after the owner resumes, the live-exercise hook messages quoted from the session log, dispatch-notes swept for the preserved pulse and the declined build, a completion report in docs/audits/, a terminal entry closing this intent, and a PR kit-v0.1-fixes -> main with CI green on its final commit. No tag.
**Abort conditions:** A premise in the dispatch's "Base and state" is wrong. Any behaviour-diff failure beyond the two expected ones. The prompt cannot be recovered byte-for-byte from the transcript. Any need to edit outside the worktree (other than the backup step) or to touch Forager. Two failed fixes on one CI symptom, after which data only.

---
