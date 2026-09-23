"""install.py -- vendor one tagged release of the kit into an adopter.

    python3 install.py --target <adopter checkout> --tag <tag>

Reads the release set (release.json) and every file in it from the kit
repository at <tag>, never from the working tree, so what is installed is
exactly what the tag holds.

- Vendored files are written at their release paths and recorded in
  <target>/.claude/kit.lock with the tag and each file's SHA-256, which
  check_kit.py compares against later.
- Templates are written only where the adopter has no file yet: the first
  install writes .claude/kit.json from templates/kit.json.
- Adopter-owned files are never written: .claude/kit.json (after the first
  install), RECORD.md, CLAUDE.md and anything under prompts/.
- An existing .claude/settings.json that differs from the release's is never
  overwritten or merged. The install stops, reports it and writes nothing.

Everything is checked before anything is written. Not part of a release.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
RELEASE_SET = "release.json"
LOCK = ".claude/kit.lock"
SETTINGS = ".claude/settings.json"
ADOPTER_OWNED = (".claude/kit.json", "RECORD.md", "CLAUDE.md", "prompts/")


class InstallError(Exception):
    pass


def git(*args):
    r = subprocess.run(["git", "-C", str(KIT), *args], capture_output=True)
    if r.returncode != 0:
        raise InstallError(f"git {' '.join(args)} failed: "
                           f"{r.stderr.decode(errors='replace').strip()}")
    return r.stdout


def adopter_owned(path):
    return any(path == owned or (owned.endswith("/") and path.startswith(owned))
               for owned in ADOPTER_OWNED)


def release_at(tag):
    """(vendored {path: bytes}, templates {target path: bytes}) at the tag."""
    if subprocess.run(["git", "-C", str(KIT), "rev-parse", "--verify", "--quiet",
                       f"refs/tags/{tag}"], capture_output=True).returncode != 0:
        raise InstallError(f"{tag!r} is not a tag in {KIT}; adopters vendor a pinned tag")
    ref = f"refs/tags/{tag}"
    spec = json.loads(git("show", f"{ref}:{RELEASE_SET}").decode())
    vendored = {p: git("show", f"{ref}:{p}") for p in spec["vendored"]}
    templates = {dst: git("show", f"{ref}:{src}") for src, dst in spec["templates"].items()}
    for path in vendored:
        if adopter_owned(path):
            raise InstallError(f"the release set vendors {path}, which the adopter owns")
    return vendored, templates


def install(target, tag):
    target = Path(target)
    if not target.is_dir():
        raise InstallError(f"target {target} is not a directory")
    vendored, templates = release_at(tag)

    settings = target / SETTINGS
    if SETTINGS in vendored and settings.exists() and settings.read_bytes() != vendored[SETTINGS]:
        raise InstallError(
            f"{settings} exists and differs from the release's {SETTINGS}. The "
            f"installer never overwrites or merges an adopter's settings. Nothing "
            f"was written. Reconcile the two by hand, then install again.")

    written = []
    for path, data in vendored.items():
        dest = target / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        written.append(path)
    for path, data in templates.items():
        dest = target / path
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        written.append(f"{path} (from template)")

    lock = {"tag": tag,
            "files": {p: hashlib.sha256(d).hexdigest() for p, d in sorted(vendored.items())}}
    (target / LOCK).write_text(json.dumps(lock, indent=2) + "\n")
    written.append(LOCK)
    return written


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", required=True, help="the adopter's checkout")
    parser.add_argument("--tag", required=True, help="the kit release tag to vendor")
    args = parser.parse_args()
    try:
        written = install(args.target, args.tag)
    except InstallError as exc:
        print(f"install.py: STOPPED: {exc}", file=sys.stderr)
        return 1
    print(f"install.py: installed {args.tag} into {args.target}:")
    for path in written:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
