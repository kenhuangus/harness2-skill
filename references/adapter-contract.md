# Adapter Contract

Source: `harness2/core/spec.py` in google-research/harness2 at commit 1cfe254. The adapter is the only seam between Harness²'s method and a new domain. Implement the adapter and the whole method works. Nothing in the adapter may contain method logic from `harness2/core/`.

## The 11 methods

- `tasks(split)` returns the task ids for a split in stable order. Library state must be reproducible, so the order may not change between runs.

- `domain_of(task_id)` returns the grouping unit, such as a practice area, an occupation, or an attack scenario. Reflection and the library are scoped by this value.

- `task_prompt(task_id)` returns the task as the agent received it, with criteria and the expected output stripped out.

- `task_files(task_id)` returns the source material directory for the task, or `None`.

- `execute(task_id, harness_dir, run_id, timeout=None)` runs one rollout and returns its run directory. It must be idempotent by `run_id`. `harness_dir=None` means the unmodified base harness.

- `delivered(run_dir)` returns true when the rollout produced the artifact the task asked for.

- `trajectory(run_dir, obs_trunc)` returns the readable trajectory in the shared `[ACTION]` / `[OBSERVATION]` / `[ERROR]` grammar.

- `deliverable_files(run_dir)` returns a filename to extracted text map, one entry per artifact produced.

- `deliverable_text(run_dir)` returns the artifact as text, extracted from agent-authored bytes only.

- `base_harness()` returns the directory that holds the unmodified c1 to c8 tree the domain starts from.

- `validate_tree(tree)` raises `ValueError` listing every domain invariant problem in actionable prose. Harness² feeds that message back to the proposer verbatim as retry feedback, so write it for the proposer.

- `score(run_dir, task_id)` judges one run and returns a dict, or `None` when the judge failed. A `None` result is not a zero and is never cached as one. Only `core.judge` calls it, and only after selection has committed.

## BenchSpec and BenchPrompts

- `BenchSpec` is a value, not a code path. It carries the run root, the install mode, the prompt pack, the proposer and selector channels, the leak globs, whether subagents are allowed, reserved script names, and the observation truncation floor of 10,000 characters.

- `BenchPrompts` carries the domain text the shared prompts interpolate. Describe the work, the invariant levers, the domain levers, and the yardstick in practitioner language.

- `BenchPrompts` rejects any visible slot that contains the words benchmark, evaluation, grader, rubric, or score. Say what the practitioner needs, not how the work is measured.

- `ChannelSpec` pairs a channel kind, `opencode` or `claude_cli`, with a model id. Override the kind and the model together or not at all. The OpenCode channel needs a provider-prefixed model id. The Claude CLI channel needs a bare Anthropic model id.

## Install modes

- `workspace_agents_md` and `workspace_config` and `home_dir_jinja` belong to the OpenCode substrate.

- `codex_root` belongs to the Codex substrate.

- Install modes are delivery channels for the always-on text and they are not interchangeable. Changing the mode a domain uses moves that domain's baseline.

## Proven minimal adapters

- `harness2/demo.py` in the upstream repo is a deterministic local adapter with a scripted proposer. It runs the real recursion and library workflow with no model credentials.

- A red-team adapter built with this contract froze a target agent and let Harness² evolve only the attacker harness on the Codex surface. Its domain invariant was one required script, enforced through `validate_tree()`.
