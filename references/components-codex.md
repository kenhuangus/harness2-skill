# The 8 Components on the Codex Surface

Source: `CODEX_SURFACE` in `harness2/substrate/codex.py` at commit 1cfe254. Install mode is `codex_root`. The substrate copies `AGENTS.md`, `.agents`, `scripts`, and `.codex` to the workspace root, where `codex exec` finds them.

## File map

- c1 system prompt, c2 guardrails, c3 memory, and c4 tool guidance all live in `AGENTS.md`. It is the only always-on file. It is injected whole into every turn.

- c5 subagents live at `sub_agents/<name>/AGENT.md`. Frontmatter needs a `description:`. The runner installs each one as an agent role. A subagent runs in its own context and returns text.

- c6 skills live at `.agents/skills/<name>/SKILL.md`. YAML frontmatter is required and `description:` is required. A skill with no frontmatter is dropped silently at load. A `name:` line is optional and must match the directory, because a mismatched `name:` overrides the directory name at load and breaks every trigger line.

- c7 scripts live at `scripts/<name>.py`. Run them as `python3 scripts/<name>.py`. Skill-local helpers live at `.agents/skills/<name>/scripts/<file>.py` and Python files there are compile-checked.

- c8 hooks live in one file, `.codex/hooks.json`. It uses the Claude Code hook schema, `{"hooks": {"<Event>": [{"matcher": "...", "hooks": [{"type": "command", "command": "..."}]}]}}`. Hook types other than `command` are skipped. A `PostToolUse` command that prints `{"decision": "block", "reason": "..."}` feeds the reason back to the model.

## Caps and rules that discard a whole proposal

- `AGENTS.md` is capped at 8,000 characters by harness2 validation. Codex itself truncates it silently at 32,768 bytes, so the harness2 cap is the binding one.

- An empty `AGENTS.md` is rejected. On this surface an empty always-on file is a harness that does not exist.

- Every skill needs a trigger line in `AGENTS.md` that names it, for example: When the situation this skill handles arises, read `.agents/skills/<name>/SKILL.md` and follow it.

- Every script named in `AGENTS.md` or in a skill must ship in the same tree.

- Valid hook events are `PreToolUse`, `PostToolUse`, `PermissionRequest`, `PreCompact`, `PostCompact`, `SessionStart`, `SubagentStart`, `SubagentStop`, `UserPromptSubmit`, and `Stop`. Event names use PascalCase.

## Cost shape

- Always-on text is the expensive form. It is in context on every turn and competes with the output budget.

- Skills cost nothing until they are read. Scripts and subagents cost nothing until they run. Hooks act inside the tool loop, so the model cannot skip them, and they cost no always-on budget.
