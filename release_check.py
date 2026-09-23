"""release_check.py -- scan the release set for identifiers that must not
be published.

    python3 release_check.py [--denylist workshop/denylist.txt] [--root .]

Reads the release set from release.json (every vendored file and every
template source) and matches each line of each file against every pattern in
the denylist. Prints file:line and the pattern for each match and exits 1 if
there is any. A missing or empty denylist, a pattern that does not compile,
or a release file that does not exist also exits 1: a release check that
could not run has not passed. Not part of a release.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_denylist(path):
    patterns = []
    for n, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            patterns.append(re.compile(line))
        except re.error as exc:
            raise ValueError(f"{path}:{n}: pattern {line!r} does not compile: {exc}")
    if not patterns:
        raise ValueError(f"{path} holds no patterns")
    return patterns


def release_files(root):
    spec = json.loads((Path(root) / "release.json").read_text())
    return list(spec["vendored"]) + list(spec["templates"])


def scan(root, patterns):
    """(problems, files_scanned, lines_scanned)."""
    problems, lines_scanned = [], 0
    files = release_files(root)
    for rel in files:
        path = Path(root) / rel
        if not path.is_file():
            problems.append(f"{rel}: listed in release.json but does not exist")
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            lines_scanned += 1
            for pattern in patterns:
                m = pattern.search(line)
                if m:
                    problems.append(f"{rel}:{n}: matches {pattern.pattern!r} "
                                    f"({m.group(0)!r})")
    return problems, len(files), lines_scanned


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--denylist", default=str(HERE / "workshop" / "denylist.txt"))
    parser.add_argument("--root", default=str(HERE))
    args = parser.parse_args()
    try:
        patterns = load_denylist(args.denylist)
        problems, files, lines = scan(args.root, patterns)
    except (OSError, ValueError) as exc:
        print(f"FAIL: the release check could not run: {type(exc).__name__}: {exc}")
        return 1
    if problems:
        print(f"FAIL: {len(problems)} denylisted match(es) in the release set:")
        for p in problems:
            print(f" - {p}")
        return 1
    print(f"PASS: {files} release file(s), {lines} line(s), {len(patterns)} "
          f"denylist pattern(s), no match.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
