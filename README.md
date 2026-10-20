# harness2 — a Muse skill for Google's Harness²

A skill that lets an agent run [Google's harness2](https://github.com/google-research/harness2) (recursive agent harnessing, arXiv:2610.14224) on a **custom domain** — not just the three benchmarks it ships with.

Harness2 improves the system around a frozen model — system prompt, guardrails, memory, tool guidance, subagents, skills, scripts, plugins/hooks — through a contrastive **Propose–Probe–Compose** loop, then stores the adopted harness and an evidence-backed lesson in a per-domain library. This skill teaches the agent how to drive that loop safely on your own agent: a red-teamer, a gateway agent, a document agent, anything you can describe with an adapter.

## What the skill does

1. **Preflight** — checks the environment and runs harness2's no-credential local demo before any model spend.
2. **Scaffolds a new domain** — generates a `BenchmarkAdapter` implementation (the 11-method protocol from `harness2/core/spec.py`), a valid c1–c8 base harness tree for the Codex or OpenCode substrate, a scripted toy proposer, and a toy runner.
3. **Validates with harness2's own validator** — `scripts/validate_harness.py` imports `harness2.core.tree.validate()`. It never reimplements it. Untriggered skills, frontmatter mismatches, missing scripts, over-cap always-on text, and malformed hooks are rejected with harness2's own error text.
4. **Wires models explicitly** — solver, improver, and judge are separate settings. Vertex path or Codex Responses path (`HARNESS2_CODEX_BASE_URL/API_KEY/MODEL`, the route that works for OpenRouter). The skill requires a disclosure of what data leaves the machine before the first external call.
5. **Runs fail-closed** — `scripts/run_harness2.py` refuses a model-backed run without an explicit spend cap and an estimate under it. Dry-run first, then `k=1`, one domain, `--max-tasks 1`. Per task and mode the loop costs `R=4k` rollouts and `P=3k` improver sessions.
6. **Summarizes the result** — `scripts/summarize_run.py` reads the run ledgers, fallbacks, the chosen harness, and the library lessons, so the report is the diff and the lesson, not a claim.

Safety rules encoded in the skill: no scores, rubrics, or judge verdicts ever reach a proposer or selector; candidate scripts/plugins/hooks are read as text and never executed; every run warns that executor network access is unrestricted and the Codex sandbox is disabled.

## Install

Clone harness2 (pinned at commit `1cfe254`) and this skill side by side:

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

## Contents

| Path | What it is |
|---|---|
| `SKILL.md` | The skill itself: hard rules, the method, the workflow |
| `skill.yaml` | Skill descriptor |
| `scripts/validate_harness.py` | Validate a harness tree with harness2's own validator |
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
2. The validator rejects five broken trees, each with harness2's own error text.
3. A scaffolded toy adapter validates and completes a `k=1` sequential run whose adopted deliverable is the corrected count, with a lesson recorded in the library.
4. A regression tree from a real red-team adapter built on this contract validates unchanged (skipped when that local tree is absent).
5. No secret-shaped string appears anywhere in the skill.

## Upstream credit

Harness2 is Google Research's work, licensed Apache 2.0:

> Xu et al., *Harness²: Recursive Agent Harnessing for an Open World*, arXiv:2610.14224, 2026.

This skill contains no harness2 code. It drives a clone of the upstream repo and imports its validator at runtime.

## License

MIT, Copyright 2026 Ken Huang. See `LICENSE`.
