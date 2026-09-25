"""PreToolUse on Bash, every role: history is the operator's.

The merge rule. A Bash command containing `gh pr merge` is denied unless
every condition holds, and each denial names the condition that failed:

(a) Role. The calling agent's role (the config's agent_roles, looked up by
    the payload's agent_type) is `coder`. The main session, with no
    agent_type, is the planner and is denied.
(b) Form. The command is one segment, with no other command in it. Its
    tokens are `gh pr merge <N>`, N all digits, and exactly one method
    flag: `--merge`/`-m` or `--squash`/`-s`. The only other flags allowed
    are `--subject`/`-t <text>`, `--body`/`-b <text>` and
    `--match-head-commit <sha>`. Anything else is denied by name:
    `--rebase`/`-r`, `--auto`, `--admin`, `--delete-branch`/`-d`,
    `--repo`/`-R`, `--disable-auto`, any unknown flag, and a missing N.
(c) Config. backup_dir is set in kit.json (`~` is expanded). Unset, the
    merge is denied with a message saying to set it.
(d) The backup. Exactly one folder directly under backup_dir holds a
    merge.json with `"pr": N`. That file is a JSON object with `pr` (int),
    `branch` (string), `sha` (40 lowercase hex) and `bundle` (a file name
    in that folder). In that folder, MANIFEST.sha256 lists at least
    merge.json and the bundle, and every listed file's sha256 matches;
    `git bundle list-heads <bundle>` lists `sha`; and backup_dir/INDEX.md
    has a line containing the folder's name.
(e) Freshness. `git rev-parse origin/<branch>` in the payload's cwd equals
    `sha`. The hook does not fetch; coder.md tells the coder to fetch
    first.

A merge that passes gets no decision from this check, like any other
allowed call. `git merge` handling is unchanged by this rule.

Otherwise, merging into a protected branch is the operator's approval, and
a history rewrite is run by the operator by hand. The protected branches
are the config's protected_branches. Blocked:

- git push --force, --force-with-lease, -f (alone or in a cluster);
- git merge while the repository is on a protected branch;
- git push to a protected branch: an explicit refspec naming one, --all or
  --mirror, or a push with no refspec (or HEAD) while on one;
- gh pr merge, unless the merge rule above lets it through;
- git filter-repo and git filter-branch.

Force, gh pr merge and the filters match the whole command text. Push
refspecs and the merge branch check are parsed per command segment, so a
command hidden in a quoted string (sh -c '...') is seen by the first group
and not by the second.

Before the push check parses a command, heredoc bodies are removed. For
each `<<WORD`, `<<-WORD`, `<<'WORD'` or `<<"WORD"`, the lines after that
line, up to and including the first line that is only WORD (after `<<-`,
leading tabs are allowed), are data, not commands, and are dropped. A
heredoc with no such closing line is not removed. Newlines outside quotes
then separate commands as `;` does; a backslash before a newline continues
the line and does not separate. A command that still cannot be parsed is
blocked only if it contains a git push call (`git`, git's global options,
then `push`). Any other unparseable command is let through by this check.
The force, `gh pr merge`, filter and merge checks above still read the
whole, unstripped text.
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guardlib as g  # noqa: E402

GIT_OPTS = r"(?:\s+(?:-C\s+\S+|-c\s+\S+|--no-pager|--git-dir=\S+|--work-tree=\S+))*"
FORCE_PUSH = re.compile(
    r"\bgit\b" + GIT_OPTS + r"\s+push\b[^;&|]*?\s"
    r"(--force(?:-with-lease)?(?:=\S*)?|-[A-Za-z]*f[A-Za-z]*)(?=\s|$)")
PR_MERGE = re.compile(r"\bgh\b[^;&|]*\spr\s+merge\b")
FILTERS = re.compile(r"\bgit(?:\s+|-)(filter-(?:repo|branch))\b")
MERGE = re.compile(r"\bgit\b((?:\s+(?:-C\s+\S+|-c\s+\S+|--no-pager))*)\s+merge\b(?!-)")
PUSH_OPTS_WITH_VALUE = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
GIT_PUSH = re.compile(r"\bgit\b" + GIT_OPTS + r"\s+push\b")
HEREDOC = re.compile(r"<<(-?)(['\"]?)(\w+)\2")


def strip_heredocs(command):
    """The command with heredoc bodies removed, per the module docstring:
    for each heredoc operator, the lines after its line up to and including
    the first line that is only WORD (leading tabs allowed after <<-). A
    heredoc with no closing line is kept."""
    lines = command.split("\n")
    drop = set()
    for i, line in enumerate(lines):
        if i in drop:
            continue
        for m in HEREDOC.finditer(line):
            tabs_ok, word = m.group(1), m.group(3)
            for j in range(i + 1, len(lines)):
                if (lines[j].lstrip("\t") if tabs_ok else lines[j]) == word:
                    drop.update(range(i + 1, j + 1))
                    break
    return "\n".join(line for i, line in enumerate(lines) if i not in drop)


def command_lines(text):
    """text split at newlines that separate commands: those outside single
    and double quotes, not escaped by a backslash (a continuation), and not
    inside a # comment's text. The states follow shlex's posix ones, so a
    quote that shlex would see as open keeps its newlines too."""
    pieces, cur, quote, i, n = [], [], None, 0, len(text)
    while i < n:
        c = text[i]
        if quote == "'":
            if c == "'":
                quote = None
        elif quote == '"':
            if c == "\\" and i + 1 < n:
                cur.append(c)
                i += 1
                c = text[i]
            elif c == '"':
                quote = None
        elif c == "\\" and i + 1 < n:
            cur.append(c)
            i += 1
            c = text[i]
        elif c in "'\"":
            quote = c
        elif c == "#":
            end = text.find("\n", i)
            end = n if end < 0 else end
            cur.append(text[i:end])
            i = end
            continue
        elif c == "\n":
            pieces.append("".join(cur))
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    pieces.append("".join(cur))
    return pieces


def current_branch(directory):
    r = subprocess.run(["git", "-C", directory, "symbolic-ref", "--short", "-q", "HEAD"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        return r.stdout.strip(), None
    if r.returncode == 1 and not r.stderr.strip():
        return "(detached HEAD)", None
    return None, r.stderr.strip() or f"git exited {r.returncode}"


def segments(tokens):
    seg = []
    for t in tokens:
        if g.PUNCTUATION.match(t):
            if seg:
                yield seg
            seg = []
        else:
            seg.append(t)
    if seg:
        yield seg


def git_invocation(seg):
    """(directory override or None, subcommand, args) for a segment that
    runs git, else None."""
    if not seg or seg[0] != "git":
        return None
    i, directory = 1, None
    while i < len(seg) and seg[i].startswith("-"):
        if seg[i] in ("-C", "-c") and i + 1 < len(seg):
            if seg[i] == "-C":
                directory = seg[i + 1]
            i += 2
        else:
            i += 1
    if i >= len(seg):
        return None
    return directory, seg[i], seg[i + 1:]


def push_targets_protected(args, branch, protected):
    refs = set(protected) | {f"refs/heads/{b}" for b in protected}
    positional, i = [], 0
    while i < len(args):
        a = args[i]
        if a in ("--all", "--mirror"):
            return (f"`git push {a}` pushes {', '.join(protected)} along with every "
                    f"other branch")
        if a in PUSH_OPTS_WITH_VALUE:
            i += 2
            continue
        if not a.startswith("-"):
            positional.append(a)
        i += 1
    refspecs = positional[1:]
    if not refspecs:
        return (f"a push with no refspec pushes the current branch, which is {branch}"
                if branch in protected else None)
    for spec in refspecs:
        spec = spec.lstrip("+")
        src, _, dst = spec.partition(":")
        dst = dst or src
        if dst == "HEAD":
            dst = branch
        if dst in refs:
            return f"refspec {spec!r} pushes to {dst}"
    return None


def guard(payload):
    if payload.get("tool_name") != "Bash":
        return None
    command = g.command_of(payload)
    cwd = payload.get("cwd") or "."
    protected = g.CONFIG["protected_branches"]

    m = FORCE_PUSH.search(command)
    if m:
        return ("deny", f"history_guard: force-push (`{m.group(1)}`) rewrites "
                        f"history on the remote and is never run by an agent.")
    if PR_MERGE.search(command):
        return ("deny", "history_guard: `gh pr merge` is blocked. Merging is the "
                        "operator's approval.")
    m = FILTERS.search(command)
    if m:
        return ("deny", f"history_guard: `git {m.group(1)}` rewrites history and "
                        f"is run by the operator by hand: history rewriting is guarded.")

    for m in MERGE.finditer(command):
        dash_c = re.search(r"-C\s+(\S+)", m.group(1) or "")
        directory = dash_c.group(1).strip("'\"") if dash_c else cwd
        branch, err = current_branch(directory)
        if err:
            return ("deny", f"history_guard: `git merge` blocked: could not read "
                            f"the current branch of {directory} ({err}).")
        if branch in protected:
            return ("deny", f"history_guard: `git merge` while on {branch} is blocked. "
                            f"Merging into a protected branch is the operator's approval.")

    text = strip_heredocs(command)
    try:
        tokens = []
        for piece in command_lines(text):
            tokens += g.shell_tokens(piece) + [";"]
    except ValueError as exc:
        if GIT_PUSH.search(text):
            return ("deny", f"history_guard: could not parse this push ({exc}), "
                            f"so its target cannot be checked.")
        return None
    for seg in segments(tokens):
        inv = git_invocation(seg)
        if not inv or inv[1] != "push":
            continue
        directory, _, args = inv
        branch, err = current_branch(directory or cwd)
        if err:
            return ("deny", f"history_guard: push blocked: could not read the "
                            f"current branch ({err}).")
        problem = push_targets_protected(args, branch, protected)
        if problem:
            return ("deny", f"history_guard: push to a protected branch blocked: "
                            f"{problem}. A protected branch changes only through a PR "
                            f"the operator merges.")
    return None


if __name__ == "__main__":
    sys.exit(g.run(guard))
