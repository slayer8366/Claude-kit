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
    has one line containing all three of the folder's name, `#<N>` (not
    followed by another digit) and `sha` (the pre-merge SHA, as the
    owner's chosen option put it: "an INDEX.md line naming PR N and the
    pre-merge SHA").
(e) Freshness. `git rev-parse origin/<branch>` in the payload's cwd equals
    `sha`. The hook does not fetch; coder.md tells the coder to fetch
    first.

A merge that passes gets no decision from this check, like any other
allowed call. `git merge` handling is unchanged by this rule.

Otherwise, merging into a protected branch is the operator's approval, and
a history rewrite is run by the operator by hand. The protected branches
are the config's protected_branches. Blocked:

- git push --force, --force-with-lease, -f (alone or in a cluster), and a
  push whose refspec begins with `+`: a force push to its destination,
  whatever the destination, since the kit's agents never force-push;
- git merge while the repository is on a protected branch; the `merge` may
  follow git's global options (`-C <dir>`, `-c <k>=<v>`, `--no-pager`,
  `--git-dir=<dir>`, `--work-tree=<dir>`);
- git push to a protected branch: an explicit refspec naming one, --all or
  --mirror, or a push with no refspec (or HEAD) while on one; and a push
  with no refspec (or HEAD) from a checkout the push walk cannot determine
  (below), denied by name;
- gh pr merge, unless the merge rule above lets it through;
- a `gh api` call that writes to a pull request's merge endpoint;
- git filter-repo and git filter-branch.

The merge endpoint. A `gh api` call to a pull request's merge endpoint,
`repos/<owner>/<repo>/pulls/<N>/merge` with or without a leading `/`, is
denied for every role when it would write: `-X`/`--method` with a method
other than GET, a field flag (`-f`, `-F`, `--field`, `--raw-field`), or
`--input`. It is denied outright, not tested against the merge rule: the
one allowed route to merge is `gh pr merge` under that rule. A plain GET,
which only checks whether the pull request is merged, is let through.

Force, gh pr merge, the merge endpoint and the filters match the whole
command text. Push refspecs and the merge branch check are parsed per
command segment, so a command hidden in a quoted string (sh -c '...') is
seen by the first group and not by the second.

The push walk reads a command's segments in order and keeps an effective
directory, which starts at the payload's cwd. `cd <dir>` and `pushd <dir>`
set it, resolved as a `git -C` directory is (below) against the current
effective directory; `cd` alone and `cd ~` set it to the home directory;
`popd` restores the directory pushed last. A `cd`, `pushd` or `popd` the
walk cannot resolve (`cd -`, a `$` or backtick in the argument, a flag,
more than one argument, `pushd` alone, `popd` with nothing pushed) makes
the effective directory unknown, and a `git push` in an unknown directory
with no explicit refspec, or with `HEAD`, is denied by name: the checkout
it pushes from cannot be determined. A push there with an explicit refspec
is checked by its refspec alone. A `(` saves the directory state and the
matching `)` restores it, so a `cd` inside a subshell does not reach the
segments after it. `git -C <dir>` still overrides the effective directory
for that one command, resolved against it.

A segment's command word is found after dropping its leading tokens while
they are a shell keyword (`{`, `}`, `!`, `if`, `then`, `else`, `elif`,
`fi`, `do`, `done`, `while`, `until`), a wrapper (`time`, `command`,
`exec`, `builtin`, `nohup`, `env` with its `-i`, `-u NAME` and
`NAME=value` arguments, `nice` with `-n N`) or a `NAME=value` assignment,
for the `cd` reading and the git reading alike. A command word whose
basename is `git` (`/usr/bin/git`, `./git`) is git. `sh -c '...'` and
interpreters are not parsed (B-01).

The branch is read in the repository that `git -C <dir>` names, or else in
the effective directory (for the `git merge` check, which does not follow
`cd`, the payload's cwd). A leading `~` or `~user` in a directory is
expanded with os.path.expanduser, as the shell would, before the branch is
read, for the push check and the `git merge` check alike. Nothing else is
expanded: `$VAR` stays as written (B-04). After that expansion, a relative
directory is resolved against the effective directory (for the `git merge`
check, the payload's cwd), where git would run it, not the hook process's
own directory; an absolute one, or one starting with `~`, is used as it
is. A quoted `~` (`git -C '~/x'`) is expanded as well, unlike in the shell:
such a command fails in git anyway, so the check errs toward reading the
home-directory repo.

Before the push check parses a command, heredoc bodies are removed. For
each `<<WORD`, `<<-WORD`, `<<'WORD'` or `<<"WORD"` that stands outside
single quotes, double quotes and `#` comments (the states that separate
commands below, carried from one kept line to the next; a marker inside
quotes or a comment opens nothing), and that is not part of a `<<<`
here-string (a `<<` preceded or followed by `<` is no marker), the lines
after that line, up to and including the first line that is only WORD
(after `<<-`, leading tabs are allowed), are data, not commands, and are dropped. A
heredoc with no such closing line is not removed. Newlines outside quotes
then separate commands as `;` does; a backslash before a newline continues
the line and does not separate. A command that still cannot be parsed is
blocked only if it contains a git push call (`git`, git's global options,
then `push`). Any other unparseable command is let through by this check.
The force, `gh pr merge`, filter and merge checks above still read the
whole, unstripped text.

Known bypasses: .claude/hooks/BYPASSES.md B-01, B-02, B-04, B-09
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guardlib as g  # noqa: E402

# The merge rule's form, condition (b).
MERGE_METHODS = {"--merge", "-m", "--squash", "-s"}
MERGE_VALUE_FLAGS = {"--subject", "-t", "--body", "-b", "--match-head-commit"}
MERGE_FORBIDDEN = {"--rebase", "-r", "--auto", "--admin", "--delete-branch", "-d",
                   "--repo", "-R", "--disable-auto"}
SHA40 = re.compile(r"[0-9a-f]{40}")
MANIFEST_LINE = re.compile(r"([0-9a-fA-F]{64}) [ *](.+)")

GIT_OPTS = r"(?:\s+(?:-C\s+\S+|-c\s+\S+|--no-pager|--git-dir=\S+|--work-tree=\S+))*"
FORCE_PUSH = re.compile(
    r"\bgit\b" + GIT_OPTS + r"\s+push\b[^;&|]*?\s"
    r"(--force(?:-with-lease)?(?:=\S*)?|-[A-Za-z]*f[A-Za-z]*)(?=\s|$)")
PR_MERGE = re.compile(r"\bgh\b[^;&|]*\spr\s+merge\b")
FILTERS = re.compile(r"\bgit(?:\s+|-)(filter-(?:repo|branch))\b")
MERGE = re.compile(r"\bgit\b(" + GIT_OPTS + r")\s+merge\b(?!-)")
PUSH_OPTS_WITH_VALUE = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
GIT_PUSH = re.compile(r"\bgit\b" + GIT_OPTS + r"\s+push\b")
HEREDOC = re.compile(r"<<(-?)(['\"]?)(\w+)\2")
# The push walk's vocabulary (module docstring): the tokens dropped before a
# segment's command word, the directory words it follows, and what makes a
# directory argument unresolvable.
SHELL_KEYWORDS = {"{", "}", "!", "if", "then", "else", "elif", "fi", "do", "done",
                  "while", "until"}
WRAPPERS = {"time", "command", "exec", "builtin", "nohup"}
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
DIRECTORY_WORDS = ("cd", "pushd", "popd")
UNRESOLVED = re.compile(r"[$`]")
# The merge endpoint check: a gh api call's text (up to ; & |, as PR_MERGE),
# the endpoint in it, and the flags that make the call a write.
GH_API = re.compile(r"\bgh\b[^;&|]*?\sapi\b[^;&|]*")
MERGE_ENDPOINT = re.compile(
    r"(?<![\w-])/?repos/[^\s/'\"]+/[^\s/'\"]+/pulls/[^\s/'\"]+/merge(?![\w/.-])")
API_METHOD = re.compile(r"(?<![^\s'\"])(?:-X|--method)(?:=|\s+)?['\"]?([A-Za-z]+)")
API_WRITE_FLAG = re.compile(
    r"(?<![^\s'\"])(-[fF]|(?:--field|--raw-field|--input)(?=[\s='\"]|$))")


def heredoc_markers(line, quote):
    """(the HEREDOC matches on line that start outside quotes and # comments,
    the quote state at the line's end). quote is the state the line starts
    in. The states and their changes are command_lines'."""
    code, i, n = set(), 0, len(line)
    while i < n:
        c = line[i]
        if quote == "'":
            if c == "'":
                quote = None
        elif quote == '"':
            if c == "\\" and i + 1 < n:
                i += 1
            elif c == '"':
                quote = None
        elif c == "\\" and i + 1 < n:
            i += 1
        elif c in "'\"":
            quote = c
        elif c == "#":
            break
        else:
            code.add(i)
        i += 1
    # A `<<` preceded or followed by `<` is part of a `<<<` here-string.
    return ([m for m in HEREDOC.finditer(line)
             if m.start() in code and m.start() + 1 in code
             and line[m.start() - 1:m.start()] != "<"
             and line[m.start() + 2:m.start() + 3] != "<"], quote)


def strip_heredocs(command):
    """The command with heredoc bodies removed, per the module docstring:
    for each heredoc operator outside quotes and # comments, the lines after
    its line up to and including the first line that is only WORD (leading
    tabs allowed after <<-). A heredoc with no closing line is kept. The
    quote state carries from one kept line to the next; dropped lines are
    data and change no state."""
    lines = command.split("\n")
    drop = set()
    quote = None
    for i, line in enumerate(lines):
        if i in drop:
            continue
        markers, quote = heredoc_markers(line, quote)
        for m in markers:
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


def dash_c_directory(directory, cwd):
    """The directory a `git -C <directory>` run from cwd works in: `~`
    expanded first, then a relative path joined to cwd."""
    expanded = os.path.expanduser(directory)
    if directory.startswith("~") or os.path.isabs(expanded):
        return expanded
    return os.path.join(cwd, expanded)


def current_branch(directory):
    r = subprocess.run(["git", "-C", directory, "symbolic-ref", "--short", "-q", "HEAD"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        return r.stdout.strip(), None
    if r.returncode == 1 and not r.stderr.strip():
        return "(detached HEAD)", None
    return None, r.stderr.strip() or f"git exited {r.returncode}"


def command_start(seg):
    """The index of seg's command word: its leading tokens are dropped while
    they are a shell keyword, a wrapper (with env's and nice's own
    arguments) or a NAME=value assignment, per the module docstring."""
    i = 0
    while i < len(seg):
        t = seg[i]
        if t in SHELL_KEYWORDS or t in WRAPPERS or ASSIGNMENT.match(t):
            i += 1
        elif t == "env":
            i += 1
            while i < len(seg):
                if seg[i] == "-i" or ASSIGNMENT.match(seg[i]):
                    i += 1
                elif seg[i] == "-u" and i + 1 < len(seg):
                    i += 2
                else:
                    break
        elif t == "nice":
            i += 1
            if seg[i:i + 1] == ["-n"] and i + 1 < len(seg):
                i += 2
        else:
            break
    return i


def resolve_directory(directory, effective):
    """dash_c_directory against the effective directory, or None when that
    is unknown and directory is relative."""
    if effective is None and not (directory.startswith("~") or os.path.isabs(directory)):
        return None
    return dash_c_directory(directory, effective)


def follow_directory_change(seg, state):
    """Apply a `cd`, `pushd` or `popd` segment to state, {"dir": the
    effective directory or None when unknown, "stack": the directories
    pushd left}. True when seg was one of them."""
    seg = seg[command_start(seg):]
    if not seg or seg[0] not in DIRECTORY_WORDS:
        return False
    word, args = seg[0], seg[1:]
    if word == "popd":
        state["dir"] = state["stack"].pop() if not args and state["stack"] else None
        return True
    if word == "pushd":
        state["stack"].append(state["dir"])
    if not args:
        state["dir"] = os.path.expanduser("~") if word == "cd" else None
    elif len(args) != 1 or args[0].startswith("-") or UNRESOLVED.search(args[0]):
        state["dir"] = None
    else:
        state["dir"] = resolve_directory(args[0], state["dir"])
    return True


def git_invocation(seg):
    """(directory override or None, subcommand, args) for a segment that
    runs git, else None. The command word is read after command_start's
    drop, and is git when its basename is `git`."""
    seg = seg[command_start(seg):]
    if not seg or os.path.basename(seg[0]) != "git":
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
    """(kind, problem) for a push that is denied, else None. kind is
    "force" (a refspec beginning with `+`, whatever its destination),
    "unknown" (the push needs the current branch and branch is None, the
    checkout being undetermined) or "protected" (a protected destination,
    --all or --mirror)."""
    refs = set(protected) | {f"refs/heads/{b}" for b in protected}
    positional, i = [], 0
    while i < len(args):
        a = args[i]
        if a in ("--all", "--mirror"):
            return ("protected", f"`git push {a}` pushes {', '.join(protected)} along "
                                 f"with every other branch")
        if a in PUSH_OPTS_WITH_VALUE:
            i += 2
            continue
        if not a.startswith("-"):
            positional.append(a)
        i += 1
    refspecs = positional[1:]
    if not refspecs:
        if branch is None:
            return ("unknown", "a push with no refspec pushes the current branch, and "
                               "the checkout it pushes from cannot be determined")
        return (("protected", f"a push with no refspec pushes the current branch, "
                              f"which is {branch}")
                if branch in protected else None)
    for spec in refspecs:
        src, _, dst = spec.partition(":")
        dst = dst or src
        if spec.startswith("+"):
            return ("force", f"refspec {spec!r} is a force push to {dst.lstrip('+')}")
        if dst == "HEAD":
            if branch is None:
                return ("unknown", f"refspec {spec!r} pushes the current branch, and "
                                   f"the checkout it pushes from cannot be determined")
            dst = branch
        if dst in refs:
            return ("protected", f"refspec {spec!r} pushes to {dst}")
    return None


def push_segment(seg, state, protected):
    """One segment of the push walk: follows a directory change, or checks
    a git push against the effective directory (or its `git -C`). The deny
    reason, or None."""
    if follow_directory_change(seg, state):
        return None
    inv = git_invocation(seg)
    if not inv or inv[1] != "push":
        return None
    directory, _, args = inv
    effective = resolve_directory(directory, state["dir"]) if directory else state["dir"]
    branch = None
    if effective is not None:
        branch, err = current_branch(effective)
        if err:
            return f"history_guard: push blocked: could not read the current branch ({err})."
    found = push_targets_protected(args, branch, protected)
    if not found:
        return None
    kind, problem = found
    if kind == "force":
        return (f"history_guard: force-push ({problem}) rewrites history on the remote "
                f"and is never run by an agent.")
    if kind == "unknown":
        return (f"history_guard: push blocked: {problem}: the `cd`, `pushd` or `popd` "
                f"before it could not be followed, so its target cannot be checked.")
    return (f"history_guard: push to a protected branch blocked: {problem}. A protected "
            f"branch changes only through a PR the operator merges.")


def push_problem(tokens, cwd, protected):
    """The push walk of the module docstring over a command's tokens: the
    reason the first denied push is denied, else None. Punctuation tokens
    end a segment; in them, each `(` saves the directory state and each
    `)` restores the state saved last."""
    state = {"dir": cwd, "stack": []}
    saved, seg = [], []
    for t in tokens + [";"]:
        if not g.PUNCTUATION.match(t):
            seg.append(t)
            continue
        if seg:
            problem = push_segment(seg, state, protected)
            if problem:
                return problem
            seg = []
        for c in t:
            if c == "(":
                saved.append((state["dir"], list(state["stack"])))
            elif c == ")" and saved:
                state["dir"], state["stack"] = saved.pop()
    return None


def merge_role_problem(payload):
    """Condition (a): the caller's role, found the way role_guard finds it."""
    agent = payload.get("agent_type")
    if not agent:
        return "the main session is the planner, and only the coder role may merge"
    role = g.CONFIG["agent_roles"].get(agent)
    if role is None:
        return f"agent {agent!r} has no role in agent_roles; only the coder role may merge"
    if role != "coder":
        return f"agent {agent!r} has role {role!r}; only the coder role may merge"
    return None


def merge_form(command):
    """Condition (b): (N, None) for an allowed form, else (None, problem)."""
    pieces = [p for p in command_lines(command) if p.strip()]
    if len(pieces) != 1:
        return None, "it must be one command, with nothing else on another line"
    try:
        tokens = g.shell_tokens(pieces[0])
    except ValueError as exc:
        return None, f"it could not be parsed ({exc})"
    if any(g.PUNCTUATION.match(t) for t in tokens):
        return None, "it must be one command, with no other command, pipe or redirection in it"
    if tokens[:3] != ["gh", "pr", "merge"]:
        return None, "it must start with `gh pr merge`, with nothing before it"
    number, methods, i = None, [], 3
    while i < len(tokens):
        a = tokens[i]
        name = a.split("=", 1)[0] if a.startswith("--") else a
        if name in MERGE_FORBIDDEN:
            return None, f"`{name}` is not allowed"
        if a in MERGE_METHODS:
            methods.append(a)
        elif a in MERGE_VALUE_FLAGS:
            if i + 1 >= len(tokens):
                return None, f"`{a}` needs a value"
            i += 1
        elif a.startswith("-"):
            return None, f"unknown flag `{a}` is not allowed"
        elif number is not None:
            return None, f"a second argument `{a}`; only one pull request number is allowed"
        elif not re.fullmatch(r"[0-9]+", a):
            return None, f"`{a}` is not a pull request number (digits only)"
        else:
            number = int(a)
        i += 1
    if number is None:
        return None, "no pull request number"
    if len(methods) != 1:
        return None, (f"exactly one of --merge/-m or --squash/-s is required, "
                      f"got {len(methods)}")
    return number, None


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def merge_backup_problem(number, cwd):
    """Conditions (c), (d) and (e): (label, problem) or None."""
    setting = g.CONFIG.get("backup_dir")
    if setting is None or not setting.strip():
        return ("(c) config", "backup_dir is not set. Set it in .claude/kit.json to the "
                              "directory that holds merge backups.")
    root = Path(os.path.expanduser(setting))
    if not root.is_dir():
        return ("(d) backup", f"backup_dir {root} is not a directory, so it holds no "
                              f"merge.json for PR {number}")
    found = []
    for child in sorted(root.iterdir()):
        path = child / "merge.json"
        if not (child.is_dir() and path.is_file()):
            continue
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and type(data.get("pr")) is int and data["pr"] == number:
            found.append((child, data))
    if not found:
        return ("(d) backup", f"no folder directly under {root} holds a merge.json "
                              f"with \"pr\": {number}")
    if len(found) > 1:
        return ("(d) backup", f"more than one folder under {root} holds a merge.json "
                              f"with \"pr\": {number}: "
                              f"{', '.join(c.name for c, _ in found)}")
    folder, data = found[0]
    branch, sha, bundle = data.get("branch"), data.get("sha"), data.get("bundle")
    if not (isinstance(branch, str) and branch.strip()):
        return ("(d) backup", f"{folder}/merge.json has no string `branch`")
    if not (isinstance(sha, str) and SHA40.fullmatch(sha)):
        return ("(d) backup", f"{folder}/merge.json's `sha` is not 40 lowercase hex")
    if not (isinstance(bundle, str) and bundle not in ("", ".", "..")
            and "/" not in bundle and os.sep not in bundle
            and (folder / bundle).is_file()):
        return ("(d) backup", f"{folder}/merge.json's `bundle` is not the name of a "
                              f"file in that folder")

    manifest = folder / "MANIFEST.sha256"
    if not manifest.is_file():
        return ("(d) backup", f"{folder} has no MANIFEST.sha256")
    listed = {}
    for line in manifest.read_text().splitlines():
        if not line.strip():
            continue
        m = MANIFEST_LINE.fullmatch(line)
        if not m:
            return ("(d) backup", f"MANIFEST.sha256 in {folder} has a line it cannot "
                                  f"read: {line!r}")
        listed[m.group(2)] = m.group(1).lower()
    for name in ("merge.json", bundle):
        if name not in listed:
            return ("(d) backup", f"MANIFEST.sha256 in {folder} does not list {name}")
    for name, digest in listed.items():
        path = folder / name
        if not path.is_file():
            return ("(d) backup", f"MANIFEST.sha256 in {folder} lists {name}, which "
                                  f"is missing")
        if sha256_of(path) != digest:
            return ("(d) backup", f"MANIFEST.sha256 in {folder} does not match {name}: "
                                  f"the file changed after the manifest was written")

    r = subprocess.run(["git", "bundle", "list-heads", str(folder / bundle)], cwd=cwd,
                       capture_output=True, text=True)
    if r.returncode != 0:
        return ("(d) backup", f"`git bundle list-heads` could not read {folder / bundle} "
                              f"({r.stderr.strip() or f'git exited {r.returncode}'})")
    if sha not in {line.split()[0] for line in r.stdout.splitlines() if line.split()}:
        return ("(d) backup", f"the bundle {folder / bundle} does not list {sha}")

    index = root / "INDEX.md"
    if not index.is_file():
        return ("(d) backup", f"{index} does not exist")
    pr_mark = re.compile(r"#%d(?![0-9])" % number)
    if not any(folder.name in line and pr_mark.search(line) and sha in line
               for line in index.read_text().splitlines()):
        return ("(d) backup", f"INDEX.md in {root} has no line naming {folder.name}, "
                              f"#{number} and {sha}")

    r = subprocess.run(["git", "-C", cwd, "rev-parse", "--verify", "--quiet",
                        f"origin/{branch}"], capture_output=True, text=True)
    tip = r.stdout.strip()
    if r.returncode != 0 or not tip:
        return ("(e) freshness", f"origin/{branch} could not be read in {cwd}. Fetch "
                                 f"first, then write the backup.")
    if tip != sha:
        return ("(e) freshness", f"origin/{branch} is {tip}, not merge.json's sha {sha}: "
                                 f"the branch moved after the backup, or the backup "
                                 f"predates the last fetch. Fetch, then write a new backup.")
    return None


def merge_problem(payload, command, cwd):
    """The merge rule in the module docstring: None if the merge may go on,
    else the reason, naming the failed condition."""
    problem = merge_role_problem(payload)
    if problem:
        return f"(a) role: {problem}."
    number, problem = merge_form(command)
    if problem:
        return f"(b) form: {problem}."
    found = merge_backup_problem(number, cwd)
    if found:
        return f"{found[0]}: {found[1]}"
    return None


def merge_endpoint_write(command):
    """(endpoint, what makes it a write) for a gh api call that writes to a
    pull request's merge endpoint, per the module docstring, else None."""
    for span in GH_API.finditer(command):
        text = span.group(0)
        endpoint = MERGE_ENDPOINT.search(text)
        if not endpoint:
            continue
        for m in API_METHOD.finditer(text):
            if m.group(1).upper() != "GET":
                return endpoint.group(0), f"method {m.group(1)}"
        m = API_WRITE_FLAG.search(text)
        if m:
            return endpoint.group(0), f"`{m.group(1)}`"
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
        problem = merge_problem(payload, command, cwd)
        if problem:
            return ("deny", f"history_guard: `gh pr merge` denied, {problem}")
    found = merge_endpoint_write(command)
    if found:
        return ("deny", f"history_guard: `gh api` write to a pull request's merge "
                        f"endpoint ({found[0]}, {found[1]}) is denied for every role. "
                        f"The one allowed route to merge is `gh pr merge`, under the "
                        f"merge rule (T17: role, form, backup, freshness).")
    m = FILTERS.search(command)
    if m:
        return ("deny", f"history_guard: `git {m.group(1)}` rewrites history and "
                        f"is run by the operator by hand: history rewriting is guarded.")

    for m in MERGE.finditer(command):
        dash_c = re.search(r"-C\s+(\S+)", m.group(1) or "")
        directory = dash_c_directory(dash_c.group(1).strip("'\""), cwd) if dash_c else cwd
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
    problem = push_problem(tokens, cwd, protected)
    if problem:
        return ("deny", problem)
    return None


if __name__ == "__main__":
    sys.exit(g.run(guard))
