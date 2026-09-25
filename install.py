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

First install (the target has no .claude/kit.lock): vendored files are
written over whatever is there, except that an existing
.claude/settings.json that differs from the release's is never overwritten
or merged. The install stops, reports it and writes nothing.

Upgrade (the target has a .claude/kit.lock): the lock's files map holds the
hashes as installed. Every path is classified before anything is written:

- Kept (in the old lock and in the new release): if its SHA-256 still
  equals the old lock's it is unchanged and is overwritten; if it is missing
  it is written; if it differs it was edited since the installed tag, and
  the upgrade stops. .claude/settings.json follows this rule on an upgrade,
  so an unedited one is replaced by the new release's.
- Dropped (in the old lock, not in the new release): if unchanged it is
  REMOVED (its directory stays); if missing there is nothing to do; if
  edited the upgrade stops.
- New (in the new release, not in the old lock): if absent it is written;
  if present and byte-identical to the release's it is left; if present and
  different it is the adopter's file, not the kit's, and the upgrade stops.

A stop lists every stopping path with its reason, exits 1 and leaves the
target exactly as it was. Otherwise the writes and removals are applied,
templates are written as above, and the new lock is written last; each
removed path is printed. An unreadable or malformed lock also stops the
upgrade before anything is written; it is never treated as a first install.

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


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_lock(target):
    """The old lock's {path: sha256}, or None when there is no lock."""
    lock_path = target / LOCK
    if not lock_path.exists():
        return None
    try:
        lock = json.loads(lock_path.read_text())
        files = lock["files"]
        if not isinstance(lock["tag"], str) or not isinstance(files, dict) or not all(
                isinstance(p, str) and isinstance(h, str) for p, h in files.items()):
            raise ValueError("expected a string tag and a files map of path to sha256")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise InstallError(
            f"{lock_path} ({LOCK}) is unreadable or malformed: {type(exc).__name__}: "
            f"{exc}. Nothing was written. Repair or remove the lock by hand, then "
            f"install again.")
    return files


def on_disk(dest):
    """The file's bytes, or None if nothing is there. Anything that is not a
    regular file reads as b"" so that it never matches a hash or a release."""
    if not dest.exists() and not dest.is_symlink():
        return None
    if not dest.is_file():
        return b""
    return dest.read_bytes()


def plan_upgrade(target, old, vendored):
    """(writes, removals, stops) for an upgrade from the old lock's hashes."""
    writes, removals, stops = [], [], []
    for path in sorted(set(old) | set(vendored)):
        data = on_disk(target / path)
        if path in old:
            if data is None:
                if path in vendored:
                    writes.append(path)
            elif sha256(data) != old[path]:
                stops.append(f"{path}: edited since the installed tag")
            elif path in vendored:
                writes.append(path)
            else:
                removals.append(path)
        elif data is None:
            writes.append(path)
        elif data != vendored[path]:
            stops.append(f"{path}: exists and is not the kit's")
    return writes, removals, stops


def install(target, tag):
    """(written, removed)."""
    target = Path(target)
    if not target.is_dir():
        raise InstallError(f"target {target} is not a directory")
    vendored, templates = release_at(tag)
    old = read_lock(target)

    if old is None:
        settings = target / SETTINGS
        if SETTINGS in vendored and settings.exists() and settings.read_bytes() != vendored[SETTINGS]:
            raise InstallError(
                f"{settings} exists and differs from the release's {SETTINGS}. The "
                f"installer never overwrites or merges an adopter's settings. Nothing "
                f"was written. Reconcile the two by hand, then install again.")
        writes, removals = list(vendored), []
    else:
        writes, removals, stops = plan_upgrade(target, old, vendored)
        if stops:
            raise InstallError(
                f"the upgrade to {tag} stops on these paths. Nothing was written or "
                f"removed. Reconcile each by hand, then install again:\n"
                + "\n".join(f"  {s}" for s in stops))

    written = []
    for path in writes:
        dest = target / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(vendored[path])
        written.append(path)
    for path in removals:
        (target / path).unlink()
    for path, data in templates.items():
        dest = target / path
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        written.append(f"{path} (from template)")

    lock = {"tag": tag,
            "files": {p: sha256(d) for p, d in sorted(vendored.items())}}
    (target / LOCK).write_text(json.dumps(lock, indent=2) + "\n")
    written.append(LOCK)
    return written, removals


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", required=True, help="the adopter's checkout")
    parser.add_argument("--tag", required=True, help="the kit release tag to vendor")
    args = parser.parse_args()
    try:
        written, removed = install(args.target, args.tag)
    except InstallError as exc:
        print(f"install.py: STOPPED: {exc}", file=sys.stderr)
        return 1
    print(f"install.py: installed {args.tag} into {args.target}:")
    for path in written:
        print(f"  {path}")
    for path in removed:
        print(f"  removed {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
