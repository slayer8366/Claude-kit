# Claude-kit

Role gates, dispatch preservation and a record store for Claude Code
repositories, as PreToolUse hooks and two checkers. Adopters vendor a pinned
release tag; the kit repository itself is a private workshop.

Work in progress: v0.1 is being extracted on branch `kit-v0.1`
(`RECORD.md` 2026-09-23-01). Nothing here is released yet. Step 1 imports the
source files unchanged; later steps make them generic.

## Layout (target for v0.1)

| Path | What it is | Released |
|---|---|---|
| `.claude/hooks/` | the PreToolUse guards and their tests | yes |
| `.claude/agents/` | the `coder` and `pulse` subagents | yes |
| `.claude/settings.json` | registers the hooks | yes |
| `.claude/kit.json` | this repository's own adopter config | no |
| `check_record.py`, `check_prompts.py` | the record checkers, at the repository root | yes |
| `check_kit.py` | drift check against `.claude/kit.lock` | yes |
| `templates/` | files an install writes only when absent | yes |
| `install.py`, `release.json` | vendors a tag into an adopter; the release set | no |
| `release_check.py` | scans the release set against the workshop denylist | no |
| `tests/` | install, drift and release-check tests | no |
| `workshop/` | private sources, drafts and the release denylist | no |
| `RECORD.md`, `prompts/`, `docs/` | this repository's own record | no |

## Requirements

`python3` on PATH (the hooks are run as `python3 "${CLAUDE_PROJECT_DIR}/..."`)
and `git`. Standard library only. The device guard also calls `adb`, `aapt2`
and `apksigner` when an Android package is configured.

## Config: `.claude/kit.json`

Every hook reads the `kit.json` beside its hooks directory. A missing or
invalid config makes every hook deny, naming the problem; the kit never fails
open on its own config. Unknown keys are invalid.

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

Fixed in code, not config: the prompt store `prompts/preserved/`, the three
roles and the planner and pulse tool allowlists, the pulse's adb reads, and the dispatch tool names
(`Agent`, `Task`).

## Install and drift

From a clone of this repository:

    python3 install.py --target <adopter checkout> --tag <tag>

`release.json` is the one definition of the release set. The installer reads
it, and every file in it, from the tag, not the working tree. It writes the
vendored files, writes `.claude/kit.json` from `templates/kit.json` only if the
adopter has none, and records the tag and each vendored file's SHA-256 in
`.claude/kit.lock`. It never writes `.claude/kit.json` over an existing one,
`RECORD.md`, `CLAUDE.md` or anything under `prompts/`. If the adopter already
has a `.claude/settings.json` that differs from the release's, it stops and
writes nothing; reconcile the two by hand.

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

## Tests

    python3 -m unittest discover -s .claude/hooks/tests
    python3 check_record.py --render-check
    python3 check_prompts.py --render-check
    python3 -m unittest discover -s tests

`tests/` (install, drift and release checks) is not released. The install
tests tag only a throwaway copy of this repository, never this repository.

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
 
+    # ---- Checks 19-23: dispatch-note entries (Claude-kit addition) ---------
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
+# Self-tests (Claude-kit addition). Store-level fixtures under a temp dir,
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
