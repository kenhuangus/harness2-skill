# The 8 Components on the OpenCode Surface

Source: `OPENCODE_SURFACE` in `harness2/substrate/opencode.py` at commit 1cfe254.

## File map

- c1 system prompt lives at `systemprompt.md`. It holds the role and the procedure and it is always on.

- c2 guardrails live at `guardrails.md`. It holds the standing rules and it is always on. Harness2 writes automatic skill trigger lines into this file.

- c3 memory lives at `LongTermMEMORY.md`. It holds durable domain facts and it is always on.

- c4 tool guidance lives at `tool_descriptions/tool_guidance.md`. It holds the prose that explains how to use the tools and it is always on.

- c5 subagents live at `sub_agents/<name>/AGENT.md`. Frontmatter needs `mode: subagent` and a `description:`. A subagent is invoked with the `task` tool, runs in its own context, and returns text.

- c6 skills live at `skills/<name>/SKILL.md`. Frontmatter needs a `name:` that matches the directory and a `description:`. A mismatch or a missing description drops the skill silently at load. A skill is loaded on demand with the `skill` tool.

- c7 scripts live at `scripts/<name>.py`. Run them as `python3 scripts/<name>.py`. Skill-local helpers live at `skills/<name>/scripts/<file>.py`.

- c8 plugins live at `plugin/<name>.ts`. A plugin is always registered and acts inside the tool loop. It is the only component that can enforce something the model cannot skip.

## Caps and rules that discard a whole proposal

- The four always-on files together are capped at 24,000 characters. Every token there competes with the agent's own output budget.

- Every skill needs a trigger line naming it in `systemprompt.md` or `guardrails.md`, for example: When the situation this skill handles arises, load the `<name>` skill. Harness2 can add the line automatically, and a line that would break the cap is skipped instead.

- Every script named in an always-on file or in a skill must ship in the same tree, at `scripts/<file>.py` or inside the skill that calls it.

- On the `home_dir_jinja` install mode the composed prompt is rendered with Jinja and StrictUndefined. Always-on text and skill or subagent descriptions may not contain a doubled brace or a brace-percent tag anywhere except the single instruction placeholder at the end.

## Install modes

- `workspace_agents_md` appends the always-on text to `AGENTS.md` in the workspace and adds `.opencode` skills and agents plus the scripts.

- `home_dir_jinja` composes a prompt template for a container agent.

- `workspace_config` renders the composition and applies the `opencode.json` tool gate.

## Cost shape

- Always-on text is the expensive form. Skills, subagents, and scripts cost nothing until they are invoked. Plugins cost no context budget and act inside the loop.
