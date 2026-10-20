# Harness² skill — run Google's Harness² on your own agent domain

A skill that lets an agent run [Google's Harness²](https://github.com/google-research/harness2) (recursive agent harnessing, arXiv:2610.14224) on a **custom domain** — not just the three benchmarks it ships with.

Harness² improves the system around a frozen model — system prompt, guardrails, memory, tool guidance, subagents, skills, scripts, plugins/hooks — through a contrastive **Propose–Probe–Compose** loop, then stores the adopted harness and an evidence-backed lesson in a per-domain library. This skill teaches the agent how to drive that loop safely on your own agent: a red-teamer, a gateway agent, a document agent, anything you can describe with an adapter.

## What the skill does

1. **Preflight** — checks the environment and runs Harness²'s no-credential local demo before any model spend.
2. **Scaffolds a new domain** — generates a `BenchmarkAdapter` implementation (the 11-method protocol from `harness2/core/spec.py`), a valid c1–c8 base harness tree for the Codex or OpenCode substrate, a scripted toy proposer, and a toy runner.
3. **Validates with Harness²'s own gates** — `scripts/validate_harness.py` runs the same three gates the recursion applies to a proposal: `harness2.core.tree.validate()`, the adapter `validate_tree()` when `--adapter` names one, and the grader-verdict leak tripwire. It reimplements none of them. The substrate is auto-detected from the tree. Untriggered skills, frontmatter mismatches, missing scripts, over-cap always-on text, malformed hooks, and grader-verdict markers are rejected with Harness²'s own error text.
4. **Wires models explicitly** — solver, improver, and judge are separate settings. Vertex path or Codex Responses path (`HARNESS2_CODEX_BASE_URL/API_KEY/MODEL`, the route that works for OpenRouter). The skill requires a disclosure of what data leaves the machine before the first external call.
5. **Runs fail-closed** — `scripts/run_harness2.py` refuses a model-backed run without an explicit spend cap and an estimate under it, and `--dry-run` never waives the gate (it is valid for the run command only, because the judge has no dry-run mode). After a run, the wrapper tallies the spend recorded in the new summary files and reports an overrun. Dry-run first, then `k=1`, one domain, `--max-tasks 1`. Per task and mode the loop costs `R=4k` rollouts and `P=3k` improver sessions, and the summarizer flags any summary whose ledger breaks that identity.
6. **Summarizes the result** — `scripts/summarize_run.py` reads the run ledgers, fallbacks, the chosen harness, and the library lessons, so the report is the diff and the lesson, not a claim.

Safety rules encoded in the skill: no scores, rubrics, or judge verdicts ever reach a proposer or selector; candidate scripts/plugins/hooks are read as text and never executed; every run warns that executor network access is unrestricted and the Codex sandbox is disabled.

## Install

Clone Harness² (pinned at commit `1cfe254`) and this skill side by side:

```bash
git clone https://github.com/google-research/harness2.git
export HARNESS2_HOME=$PWD/harness2
```

Copy or symlink this directory into your agent's skills directory (for Muse: `~/workspace/custom-skills/harness2`, or your platform's equivalent). The skill scripts locate the harness2 clone through `HARNESS2_HOME` or common local paths.

## Quick start (no credentials, no spend)

```bash
# Validate the shipped template trees
python3 scripts/validate_harness.py templates/base-harness-codex --substrate cx
python3 scripts/validate_harness.py templates/base-harness-opencode --substrate oc

# Scaffold the toy domain and run one full loop with a scripted proposer
python3 scripts/scaffold_adapter.py --name line-count \
    --work "count lines in text files" --output /tmp/line-count
cd /tmp/line-count && python3 run_toy.py

# Full acceptance suite (demo k=2, validator rejections, scaffold run, secret scan)
python3 tests/run_acceptance.py
```

The toy domain counts lines in a text file. Its base script drops blank lines, the scripted proposer fixes exactly that, and the adopted deliverable goes from `Lines: 3` to the correct `Lines: 4` — a complete Propose–Probe–Compose cycle, selection, reflection, and a library lesson, at $0.

## How an agent uses this skill

The skill is plain Markdown plus Python scripts, so any agent that can read a `SKILL.md` and run shell commands can use it: Muse, Claude Code, or another skills-based agent. No platform-specific API is involved.

**Loading.** The agent's platform matches the `skill.yaml` description to the request. Requests that should load this skill sound like: "optimize this agent's harness with Harness²", "build a Harness² adapter for my document agent", "evolve the red-teamer, keep the model frozen", or "run the Harness² demo". On loading, the agent reads `SKILL.md` in full, then the reference file for the step it is on. It does not improvise the workflow from memory.

**A working session, in order:**

1. **Preflight.** Confirm the Harness² clone (`HARNESS2_HOME`), Python 3.12, and the local demo: `python3 scripts/run_harness2.py --command demo -- --output runs/demo --k 2`. No credentials, no spend.
2. **Define the domain in the user's words.** What work does the target agent do, what does a good deliverable look like, which files can it never lose, where are the answer keys that must never reach a proposer (`leak_globs`).
3. **Scaffold and adapt.** `python3 scripts/scaffold_adapter.py --name <slug> --work "<the work>" --output <dir>`, then replace the toy adapter's methods with the real domain, starting from `templates/adapter.py.tmpl` and `references/adapter-contract.md`.
4. **Build the base harness.** Write the c1–c8 tree for the chosen substrate using the matching components reference and template tree. Prefer skills and scripts over always-on prose.
5. **Validate.** `python3 scripts/validate_harness.py <base_harness> --adapter <adapter.py:ClassName> --require-file <file the domain cannot lose>`. Fix every error and rerun until it passes. Do not start a run on an unvalidated tree.
6. **Disclose and wire models.** Before the first external call, tell the user which service will be called and exactly what data goes to it: task prompts, source material, trajectories, deliverables, and harness files. Set the solver, improver, and judge per `references/models-and-env.md`. Keys come from the environment only.
7. **Run small.** Dry run first, then `python3 scripts/run_harness2.py --command run --cap-usd <cap> --estimated-usd <estimate> -- <flags>` with `k=1`, one domain, `--max-tasks 1`. Judge and report afterwards with the identical settings.
8. **Report the diff, not a verdict.** `python3 scripts/summarize_run.py <runs_dir> --library <library_dir>`. Show the user which components changed, which stages fell back, what the run cost against the cap, and the lesson the library kept. Adoption of the evolved harness into the real agent is the user's call, or a call the user has pre-approved in writing.

**What the agent must never do with this skill:** start a paid run without a cap, give a proposer or selector a score or rubric, execute a script or plugin found inside a candidate harness, write a secret into any file, or present an evolved harness as adopted before the user has seen the diff.

## How Muse uses this skill to improve itself

"Himself" needs a precise meaning here, because part of an agent is not editable. The base model and the platform system prompt are frozen — the same position Harness² puts every target in. What *is* editable is the working harness the agent carries in its workspace, and it maps onto the same 8 components:

| Harness² component | In Muse's own workspace |
|---|---|
| c1 system prompt, c2 guardrails | Operating rules in `AGENTS.md`, per-skill instructions in each `SKILL.md` |
| c3 memory | `MEMORY.md`, daily notes, and the lesson-learned protocol that mines corrections into proposed rules |
| c4 tool guidance | Skill workflow sections that say which tool to reach for and when |
| c5 subagents | The briefs Muse writes when it delegates work to a subagent |
| c6 skills | The custom skills under `~/workspace/custom-skills/` |
| c7 scripts | The helper scripts inside those skills |
| c8 plugins/hooks | Scheduled checks and validation gates that run inside the work loop, such as this skill's acceptance suite |

The self-improvement loop Muse runs with this skill:

1. **Pick one surface and freeze the rest.** One skill, or one subagent brief, or one workflow's instructions. Improving everything at once makes the evidence unreadable.
2. **Define tasks with inspectable deliverables.** A small set of real past tasks for that surface, each with a deliverable a checker can verify (a file, a total, a test result). Answer keys go behind `leak_globs`. If a task's quality cannot be inspected from its trajectory and deliverable, it does not go in the set.
3. **Write the adapter.** `execute()` runs the agent, or a spawned subagent, with the candidate harness installed. `delivered()` checks the artifact exists and is complete. `trajectory()` renders the run log. `validate_tree()` carries the invariants that surface cannot break, for example "never publish live" in a publishing skill.
4. **Validate the base tree, rehearse at $0.** Scripted proposer and demo first. Only then a model-backed run: `k=1`, sequential, one task, explicit cap, after the disclosure step from the session protocol.
5. **Read the evidence.** `summarize_run.py` gives the component-by-component diff, the fallbacks, and the library lesson. A change with no trajectory evidence behind it is a guess, and it is reported as one.
6. **Adoption is a gate, not an output.** The evolved tree is a proposal. Muse shows the user the diff and the evidence, and only approved changes land in the real skill or rules file. The skill's acceptance tests run again after adoption. The library `EXPERIENCE.md` lessons are kept and read before the next round, which is the same mechanism as the lesson-learned sweep, with run evidence attached.
7. **Repeat on the next surface.** Each round is small, measured, and reversible with git.

This is not hypothetical. The red-team experiment this skill grew out of froze a target agent and let Harness² evolve only the attacker's harness: the loop cut the system prompt from 8 messages to 6 and replaced a broken hooks file with a valid `SessionStart` hook, and both changes were kept because probe trajectories showed they worked, not because they sounded better. The review round on this skill itself ran the same discipline in miniature: 11 flaws found by reading the code against the upstream source, each fix landed with a regression test, suite from 25 to 42 checks.

The limits, stated plainly: this loop cannot change the base model, the platform system prompt, or anything outside the workspace harness. It cannot adopt its own proposals — the user approves self-modification, the same way they approve merges and publishing. And it obeys its own rules when it is the target: caps before spend, no ground truth in the proposer's context, candidate code read and never executed.

## Contents

| Path | What it is |
|---|---|
| `SKILL.md` | The skill itself: hard rules, the method, the workflow |
| `skill.yaml` | Skill descriptor |
| `scripts/validate_harness.py` | Validate a harness tree with Harness²'s own validator |
| `scripts/scaffold_adapter.py` | Generate a toy domain: adapter + base harness + proposer + runner |
| `scripts/run_harness2.py` | Fail-closed wrapper for demo / check / run / judge / report |
| `scripts/summarize_run.py` | Summarize ledgers, selections, and library lessons from run output |
| `references/adapter-contract.md` | The 11 adapter methods, BenchSpec/BenchPrompts, install modes |
| `references/components-codex.md` | The 8 components on the Codex surface (files, caps, hook schema) |
| `references/components-opencode.md` | The 8 components on the OpenCode surface |
| `references/models-and-env.md` | Solver / improver / judge settings, Vertex and Responses paths |
| `references/safety-and-cost.md` | Cost identity, spend guard, network and sandbox warnings |
| `templates/adapter.py.tmpl` | Annotated adapter skeleton for a real domain |
| `templates/base-harness-codex/` | A valid Codex base harness (passes the validator) |
| `templates/base-harness-opencode/` | A valid OpenCode base harness (passes the validator) |
| `tests/run_acceptance.py` | The acceptance suite described below |

## Acceptance tests

`tests/run_acceptance.py` verifies, with no model calls:

1. The upstream demo at `k=2` finishes 2/0, every ledger reads `R=8, P=6`, the adopted totals are the known-correct `85.15` and `20.25`, and a rerun resumes with zero new executions.
2. The validator rejects five broken trees, each with Harness²'s own error text.
3. A scaffolded toy adapter validates and completes a `k=1` sequential run whose adopted deliverable is the corrected count, with a lesson recorded in the library.
4. A regression tree from a real red-team adapter built on this contract validates unchanged (skipped when that local tree is absent).
5. No secret-shaped string appears anywhere in the skill.
6. The fix regressions: substrate auto-detect and wrong-surface rejection, the grader-verdict and adapter gates, strict clone discovery (an invalid `HARNESS2_HOME` is a hard error, never a silent fallback), the wrapper cap guards including the judge dry-run bypass, the spend tally, the summarizer ledger identity, scaffold `--force` substrate switching and `--domain` validation, an OpenCode toy run, and the Harness² naming rule.

## Upstream credit

Harness² is Google Research's work, licensed Apache 2.0:

> Xu et al., *Harness²: Recursive Agent Harnessing for an Open World*, arXiv:2610.14224, 2026.

This skill contains no code from Harness². It drives a clone of the upstream repo and imports its validator at runtime.

## License

MIT, Copyright 2026 Ken Huang. See `LICENSE`.
