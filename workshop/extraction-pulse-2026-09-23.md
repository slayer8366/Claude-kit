# Pulse answer: what in Forager's phase 1 is generic, for the kit repo

Reads ran from **2026-09-23T01:29:31Z to 01:33:11Z**, at Forager `main` = `b2435ef`. Each finding is marked **read** (from a file or API), **observed** (from running something) or **inferred**. Every file:line below is at `b2435ef`.

## Premises that were wrong

- **The kit repo already exists (observed).** `slayer8366/Claude-kit` is private and empty, with no default branch. It was created at 2026-09-23T01:28:08Z, about a minute before these reads began. Nothing in it could be read.
- **What was read (observed).** `b2435ef`'s tree is identical to the branch head `77c19dd`'s, so the merge added nothing. All reads used `git grep`/`git show` at `b2435ef`, never a working tree.

## Inventory

### 1. Files phase 1 added or changed

32 files changed against `b2435ef^1` = `89f53a4`, which is also the merge base (observed).

**Generic:**
- `.claude/settings.json`: runs each hook as `python3 "${CLAUDE_PROJECT_DIR}/..."` at `:9`, `:18`, `:27`, `:31`.
- `.claude/hooks/tests/harness.py`.
- `check_record.py` and `check_prompts.py`, apart from comment wording; see Question 3.

**Generic with config:**

| File | Hard-coded value |
|---|---|
| `guardlib.py` | the Android package, `:18` `FORAGER_PACKAGE = "com.zynergylabs.forager.app"`; the docstring at `:1` names Forager |
| `role_guard.py` | the planner tool allowlist, `:29-30`; the pulse tools, `:31`; the adb reads the pulse may use (Android-only) |
| `dispatch_guard.py` | which agents may be dispatched, `:31` `{"coder","pulse"}`; which type goes to which agent, `:32`; the required section names, `:33-39`; the prompt store, `:62` `prompts/preserved`; the checker's location, `:81` `<root>/check_prompts.py`; the tool names, `:30` `{"Agent","Task"}` |
| `history_guard.py` | the protected branch, `:33` `{"main","refs/heads/main"}` |
| `device_guard.py` | Android adopters only: the package, taken from `guardlib` at `:168-170`; the environment-variable prefix `FORAGER_GUARD_*`, at `:78`, `:89`, `:101`, `:104`; the Gradle flag at `:30`, which is standard Android tooling |
| `.claude/agents/coder.md` | "the coder for Forager", `:7`; the record paths at `:13`, `:31-32`, `:35`, `:44` |
| `.claude/agents/pulse.md` | "the pulse for Forager", `:7`; "Forager is the app in front", `:12` |
| `tests/test_device_guard.py` | the package, `:14`; the Samsung launcher, `:15`; a fixture serial, `R5CT`, at `:101`, `:120`, `:136`; a comment naming Forager's APK, `:50` |
| `tests/test_role_guard.py` | Resend tool names, `:24-27` and `:140`; `repos/slayer8366/Forager`, `:89`; the serial `R5CT10` and the package, `:116` |
| `tests/test_dispatch_guard.py` | expects both checkers at the repository root, `:14` and `:41` |
| `tests/test_history_guard.py` | the branch name `main`, `:17`, `:19`, `:27` |

**Forager-only:**
- `.gitignore`: the change pattern at `:34` and `:40-42` is reusable advice; the file itself isn't.
- `CLAUDE.md`.
- `RECORD.md`: every entry; the header at `:3` says "Forager's record".
- The four `docs/audits/2026-09-22-accountability-*` reports and `docs/audits/README.md`.
- `prompts/preserved/2026-09-22-01` through `-07`.
- `docs/process/accountability-design.md`: 9 mentions of Forager.
- `docs/process/accountability-autopilot.md`: generic apart from 2 mentions, at `:255` and `:261`.

### 2. What each hook assumes

**All hooks:**
- `python3` must be on PATH (`settings.json:9-31`).
- Python 3.8 or later. This is inferred from the syntax: the walrus operator at `dispatch_guard.py:65`, and `punctuation_chars` at `guardlib.py:64`, which needs 3.6 or later. Only 3.14.4 was actually run (observed).
- Scripts are found through `${CLAUDE_PROJECT_DIR}`.

| Hook | Tools it calls | Paths and environment |
|---|---|---|
| `role_guard.py` | none | none |
| `dispatch_guard.py` | `git`, `:53`; the running Python, to run `<root>/check_prompts.py`, `:84` | writes `<git toplevel of payload cwd>/prompts/preserved/`, `:62` |
| `device_guard.py` | `adb`, `aapt2`, `apksigner`, `:78-104` | `ANDROID_HOME`/`ANDROID_SDK_ROOT`, `:52` (it globs the newest `build-tools/*`); `FORAGER_GUARD_*` overrides, `:48-49` |
| `history_guard.py` | `git`, `:38` | the payload `cwd`, or a `-C` path |

`gh` is never called by any hook; `role_guard.py` only pattern-matches it.

### 3. The vendored checkers against upstream

**The full diff is already on `main` (read, then observed).** It's in the completion report's appendix: `check_record.py` at `docs/audits/2026-09-22-accountability-phase-1-completion-report.md:555`, and `check_prompts.py` at `:721`. Both are identical to a live GNU `diff` of upstream `35e39d1` against `b2435ef`: 129 lines added and 1 removed in `check_record.py`, 124 added and 0 removed in `check_prompts.py`. A first comparison, made with Python's difflib, reported a mismatch; that came from difflib laying out hunks differently, and GNU `diff` settled it.

The changed ranges:
- `check_record.py`: `:94-139`, the `dispatch-note` constants and validator; `:191-207`, the branch that dispatches to it; `:593-608`, a test helper; `:950-1024`, checks 19–23 and the total count.
- `check_prompts.py`: `:169-185`, the rule that a note may claim only a preserved prompt; `:240-357`, its self-tests.

**What an adopter needs, and what's Forager-specific (inferred):** the logic is needed by any adopter whose dispatch hook preserves prompts. The Forager-specific part is only the comment attribution at `check_record.py:97` and `:953`, and `check_prompts.py:172` and `:244`, each citing "Forager addition (RECORD.md 2026-09-22-03)".

### 4. Tests

**Observed:** I exported only `.claude/` and the two checkers from `b2435ef` into `/tmp/kitprobe`, with no Forager app code:
- all 49 hook tests passed;
- `check_record --render-check` passed 23 of 23, and `check_prompts --render-check` passed 5 of 5;
- the hook tests passed again with `ANDROID_HOME` and `ANDROID_SDK_ROOT` unset and PATH reduced to `/usr/bin:/bin`.

**Requirements:**
- No test needs a device.
- The history, dispatch and checker tests need `git`.
- The dispatch tests need the checkers at the repository root.
- The device tests replace `adb`, `aapt2` and `apksigner` with fakes through `FORAGER_GUARD_*` (`test_device_guard.py:69-71`). The real `adb` was on PATH during that run. That it isn't called is inferred from the code; I didn't remove it to prove it.

## Things the kit must not inherit

### 5. Identifiers and personal details

**In kit-candidate files:** all of them are listed in Question 1's table. The package name appears at `guardlib.py:18`, `test_device_guard.py:14` and `test_role_guard.py:116`. The launcher is at `test_device_guard.py:15`. The `R5CT` serials are at `test_device_guard.py:101`, `:120` and `:136`, and `R5CT10` at `test_role_guard.py:116`. The owner's GitHub name is at `test_role_guard.py:89`. The Resend tool names are at `test_role_guard.py:24-27` and `:140`.

About the `R5CT` values: I made them up while writing the tests. I haven't compared them with the phone's real serial, because that would mean reading it.

**In Forager's records (read):**
- **The package name:** `docs/audits/README.md` ×4, the completion report ×4, the device run record ×1.
- **The phone's model and build:** `docs/audits/README.md` ×8, the device run record ×2, the design doc ×1, the completion report ×1.
- **The owner's paths:** the completion report `:338`, and the type-binding report `:30-31`.
- **The owner's GitHub name:** `prompts/preserved/2026-09-22-01.md`, `-02.md`, `CLAUDE.md`, and the design doc, 1 each.
- **Personal email, and account or organisation IDs:** not found.
- **The Resend account:** the flag 1 report on public `main` names the sending domain and its status, at `docs/audits/2026-09-22-accountability-phase-1-flag1-followup-report.md:24-25`. The domain's ID is not in the repo.
- **The Restricted Object:** not searched for, per `CLAUDE.md:253`. Files that carry the rule's placeholder wording, by path only: `CLAUDE.md`, `RECORD.md`, `docs/process/accountability-design.md`.

### 6. Forager incident text inside kit-candidate files (read)

**Guard messages that name Forager or its owner:**
- `device_guard.py:13`, and `:168-170`, which prints Forager's package;
- `device_guard.py:146`, "the owner's phone".

**Incident history in docstrings and comments:**
- `device_guard.py:1-4`: "Traced to the 2026-09-22 device run…";
- `dispatch_guard.py:7`, `:97-99` (flag 1's live test), `:114-115`;
- `guardlib.py:50`: Step 0's observation on 2.1.280;
- `role_guard.py:3`, `:8`: operator rulings.

**Forager's decision letters in user-facing messages:**
- `dispatch_guard.py:137-141`, "decision B";
- `history_guard.py:4` and `:121`, "decision F".

**Also Forager-specific:** the checker comments listed in Question 3, and the agent prompts listed in Question 1.

## Evidence the kit's design depends on

### 7. How PR #114 was merged

**The route (read):** the GitHub REST API, `PUT repos/slayer8366/Forager/pulls/114/merge`, with `merge_method=merge` and pinned to the head commit. It was run by a Claude session, this one, working in the `bridge-cse_019uZR3mJKzHkDaCv5fGnsuk` worktree, which has no `.claude/` hooks. So of the pulse's options, both "`gh api` or REST" and "a session in a checkout without guards" are true.

**The session log:** `~/.claude/projects/-home-zynergy-labs-Zynergy-Forager--claude-worktrees-bridge-cse-019uZR3mJKzHkDaCv5fGnsuk/1b897011-9b08-5256-851d-e0b3c0141e2e.jsonl`. It is **not** in `~/forager-backups/`.
- The owner's instruction to merge is at line 1121 (01:18:10Z).
- The merge call is at line 1130 (01:18:38Z). It's the only one.
- Lines 1207 and 1215 also match a search for that endpoint. They are this pulse's own search commands, not merges.

**GitHub's record (read):** the `merged` event is by `slayer8366` at 01:18:42Z; `merged_by` is `slayer8366`; the merge commit's committer is GitHub. GitHub can't tell this merge apart from one the owner made by hand.

**The guards on this route (observed),** run on `gh api -X PUT repos/o/r/pulls/1/merge -f merge_method=merge`:
- `history_guard.py`, called as the coder: no decision, so the command would go through.
- `role_guard.py`, called as the coder: no decision.
- `role_guard.py`, called as the planner: denied, because `gh api` is given `-X`.

So even from a guarded checkout, the coder could merge this way. The guard only catches the literal `gh pr merge` (`history_guard.py:31`).

### 8. Settings that only take effect outside the repo's `.claude/settings.json`

Read from docs fetched on 2026-09-22 and not re-fetched.

**Only honored at user, managed or command-line level:**
- **`sandbox.network.strictAllowlist`**, https://code.claude.com/docs/en/sandboxing line 525.
- **`mask` credential entries**, same page line 381: "ignores `mask` entries in a repository's…".
- **`allowAppleEvents`** (macOS), same page line 687.

**Launch-time options that switch phase 1's project hooks off,** which the repo cannot prevent (https://code.claude.com/docs/en/permissions):
- `--bare`, at line 681;
- `--settings '{"disableAllHooks": true}'`, at line 682.

**A launch-time option that escapes the planner restriction:** `claude --agent coder`. Observed on 2.1.280: the hook payload then carries `agent_type` = the agent's name and `agent_id: null`.

**Phase 1 needs no user-level setting to work (observed).** All of its gates are hooks in the project's `settings.json`, and they held against your user-level allows (`git push:*`, `git filter-repo:*`). `disableBypassPermissionsMode` works from any scope (permissions line 624) and phase 1 doesn't set it. Project `permissions.allow` rules are held until the folder is trusted (line 670); phase 1 has none.

## 9. Adopter readiness (read, over `gh`)

| | Forager | Forager-app | forager-forecast |
|---|---|---|---|
| Visibility | **public** | **public** | private |
| Default branch, head | main, `b2435ef` | main, `0172c33` | main, `82f28b6` |
| `.claude/` tracked | agents, hooks, settings.json | none | none |
| `.gitignore` on `.claude` | `:34` `.claude/*`, re-including `:40-42` | nothing | **`:85` `.claude/`** (the whole directory) |
| CLAUDE.md | present | absent anywhere in the tree | absent anywhere in the tree |
| CI workflows | `.github/workflows/ci.yml` | none | `.github/workflows/ci.yml` |
| Open PRs touching `.gitignore` or `.claude/` | #109 (`.gitignore`); #104 (`.gitignore`, `.claude/skills/*`) | none (0 open) | none (0 open) |
| Android or adb | yes: `README.md:5`, `app/build.gradle.kts:11`, `AndroidManifest.xml:53`, and others | yes: `app/build.gradle.kts:6`, `build.gradle.kts:2`, `persistence/build.gradle.kts:6` | none found (5 build files and READMEs checked) |

Forager-app has no README anywhere in its tree.

## Could not determine

- Whether the `R5CT` fixtures match the phone's real serial. Checking would mean reading the serial, which the pulse rules out.
- Whether the hooks run on your Windows host, since no Windows host was read.

## Unrequested findings

1. **The merge route bypasses the guard (observed; see Question 7).** A guard that matches command text can't cover every way to call the API. Branch protection on GitHub, plus a separate agent identity (already recorded for phase 2), would. That last point is inferred.
2. **The kit's contents become public in effect.** `Claude-kit` is private, but Forager and Forager-app are public. Anything vendored into them is published.
3. **Account details are already public.** The Resend domain and its status sit on public Forager `main` (Question 5).
4. **forager-forecast would need decision D again.** Its `.gitignore:85` ignores all of `.claude/`, so kit files there can't be committed until the entry is narrowed, as Forager's was.
5. **Forager-app has nowhere to run the kit's tests.** It has no CI, no CLAUDE.md and no README.
6. **The planner allowlist names tools that don't exist.** `role_guard.py:29` lists `Grep` and `Glob`, which don't exist on 2.1.280 (observed during phase 1). The entries are harmless but misleading in a kit.
7. **A leftover from this pulse.** It created `/tmp/kitprobe`: an export of the kit files, one survey script, and two diff inputs. I haven't deleted it, following the earlier tally.
