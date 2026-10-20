# Role

You are an agent that does the work named in the task. Follow the procedure in this file and use the components listed here.

# Rules

- Deliver the shape the task asks for. Do not add columns, sections, or explanations the task did not ask for.
- Run deterministic work with a script instead of doing it by hand.
- When the work needs a line count of a text file, read .agents/skills/example-workflow/SKILL.md and follow it.

# Tools

- Read and write files in the workspace.
- Run `python3 scripts/<name>.py` for helper scripts in `scripts/`.

# Durable facts

- Add facts that hold across every task in this domain here, and keep this file short. Every line here is in context on every turn.
