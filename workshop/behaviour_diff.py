"""Behaviour diff: the source repository's phase 1 hook tests, unchanged, run
against this kit's ported hooks.

Builds a throwaway tree holding the kit's hooks (.claude/hooks/*.py), the
source's hook tests taken with `git show` at the pinned source commit, the
kit's checkers at the root, and a .claude/kit.json whose values are read
out of the source's own hooks at that commit (so this file names none of
them). Then runs the source tests there and compares the failures with the
one expected difference: the planner allowlist no longer carries Grep and
Glob, so those two subtests of test_allowlisted_tools_pass fail.

Workshop only; never released. Usage:
    python3 workshop/behaviour_diff.py --source <path to the source clone>
Exit 0 when the tests ran and the failures are exactly the expected ones.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE_COMMIT = "b2435efffc8cb6cac3c29f850c20581227ccbecf"
KIT = Path(__file__).resolve().parent.parent
HOOK_FILES = ["guardlib.py", "role_guard.py", "dispatch_guard.py",
              "device_guard.py", "history_guard.py"]
TEST_FILES = ["harness.py", "test_device_guard.py", "test_dispatch_guard.py",
              "test_history_guard.py", "test_role_guard.py"]
EXPECTED = {("test_allowlisted_tools_pass", "Grep"),
            ("test_allowlisted_tools_pass", "Glob")}
EXPECTED_COUNT = 49
FAILURE = re.compile(r"^(FAIL|ERROR): (\w+) \(([\w.]+)\)(?: \[(.*)\])?\s*$", re.M)


def show(source, path):
    return subprocess.run(["git", "-C", str(source), "show", f"{SOURCE_COMMIT}:{path}"],
                          capture_output=True, text=True, check=True).stdout


def source_config(source):
    """Kit config values read from the source hooks' own constants."""
    probe = Path(tempfile.mkdtemp(prefix="behaviour_diff_probe_"))
    try:
        for name in HOOK_FILES:
            (probe / name).write_text(show(source, f".claude/hooks/{name}"))
        sys.path.insert(0, str(probe))
        import guardlib, dispatch_guard, history_guard  # noqa: E401
        prefix = re.search(r'tool\("(\w+?)ADB", "adb"\)',
                           (probe / "device_guard.py").read_text()).group(1)
        config = {
            "android_package": guardlib.FORAGER_PACKAGE,
            "protected_branches": sorted(r for r in history_guard.MAIN_REFS
                                         if not r.startswith("refs/")),
            "dispatchable_agents": sorted(dispatch_guard.DISPATCHABLE),
            "type_targets": dict(dispatch_guard.TARGET_FOR_TYPE),
            "required_sections": {k: list(v) for k, v in dispatch_guard.REQUIRED.items()},
            "guard_env_prefix": prefix,
        }
        sys.path.remove(str(probe))
        for mod in ("guardlib", "dispatch_guard", "history_guard"):
            sys.modules.pop(mod, None)
        return config
    finally:
        shutil.rmtree(probe, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="a clone holding the source commit")
    parser.add_argument("--keep", action="store_true", help="keep the tree for inspection")
    args = parser.parse_args()

    config = source_config(args.source)
    tree = Path(tempfile.mkdtemp(prefix="behaviour_diff_"))
    hooks = tree / ".claude" / "hooks"
    (hooks / "tests").mkdir(parents=True)
    for name in HOOK_FILES:
        shutil.copy(KIT / ".claude" / "hooks" / name, hooks / name)
    for name in TEST_FILES:
        (hooks / "tests" / name).write_text(show(args.source, f".claude/hooks/tests/{name}"))
    for name in ("check_record.py", "check_prompts.py"):
        shutil.copy(KIT / name, tree / name)
    (tree / ".claude" / "kit.json").write_text(json.dumps(config, indent=2))

    print(f"source tests: {SOURCE_COMMIT[:10]} ({', '.join(TEST_FILES)})")
    print(f"kit hooks and checkers: working tree of {KIT}")
    print(f"config keys derived from the source: {', '.join(sorted(config))}")
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s",
                        ".claude/hooks/tests"], cwd=tree, capture_output=True, text=True)
    out = r.stdout + r.stderr
    ran = re.search(r"^Ran (\d+) tests?", out, re.M)
    failures = {(m.group(2), m.group(4) or "") for m in FAILURE.finditer(out)}
    print(out if args.keep else "\n".join(l for l in out.splitlines()
                                          if FAILURE.match(l) or l.startswith(("Ran ", "OK", "FAILED"))
                                          or "Error:" in l))
    if args.keep:
        print(f"tree kept at {tree}")
    else:
        shutil.rmtree(tree, ignore_errors=True)

    ok = True
    if not ran or int(ran.group(1)) != EXPECTED_COUNT:
        print(f"\nBEHAVIOUR DIFF FAIL: expected {EXPECTED_COUNT} tests to run, "
              f"got {ran.group(1) if ran else 'no test count'}")
        ok = False
    unexpected = sorted(failures - EXPECTED)
    missing = sorted(EXPECTED - failures)
    if unexpected:
        print(f"\nBEHAVIOUR DIFF FAIL: unexpected failures: {unexpected}")
        ok = False
    if missing:
        print(f"\nBEHAVIOUR DIFF FAIL: expected failures that did not happen "
              f"(the check may not be running what it claims): {missing}")
        ok = False
    if ok:
        print(f"\nBEHAVIOUR DIFF PASS: {EXPECTED_COUNT} source tests ran; the only "
              f"failures are the expected {sorted(EXPECTED)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
