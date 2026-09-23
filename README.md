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
| `install.py` | vendors a tag into an adopter | no |
| `workshop/` | private sources, drafts and the release denylist | no |
| `RECORD.md`, `prompts/`, `docs/` | this repository's own record | no |
