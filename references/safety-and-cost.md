# Safety and Cost

Source: `docs/EXPERIMENTS.md`, `harness2/core/prompts.py`, and `harness2/core/recursion.py` at commit 1cfe254.

## Cost shape

- Each task and each mode costs `R=4k` executor rollouts and `P=3k` improver sessions. Both modes together double that.

- Rollouts and improver sessions both call paid models in a model-backed run. The improver cost is the part teams miss, because the harness editor is itself an agent with file access and a long session budget.

- `--max-tasks` caps tasks per domain, not across the whole run. A run with several domains multiplies the total.

- Start with one domain, one task, `k=1`, and one mode. Scale only after the summary ledger matches the `4k` and `3k` identity.

- Use a separate `HARNESS2_RUNS_DIR` for each model, budget, or task selection change. The saved configuration blocks an incompatible resume, which protects a comparison.

## Spend guard

- Set a cap before the run and give `scripts/run_harness2.py` an estimate. The wrapper refuses to start when the estimate is above the cap.

- For a provider that reports spend, check the reported spend between tasks and stop at the cap. A cap that is only checked at the end is not a cap.

## Network and sandbox

- Executor network access is unrestricted in this release. The Codex executor runs with its sandbox disabled.

- Public task sets publish their answers and grading criteria online. An executor with network access can fetch them, and Harness²'s own validation run observed a rollout downloading its task rubric without being told to.

- Block these hosts for the executor during a measured run, at a firewall or DNS level rather than in a tool setting: `huggingface.co`, `hf.co`, and its subdomains, `github.com`, and `raw.githubusercontent.com`.

- Setup needs those same hosts to download dependencies and data. Apply the block after setup and before the run, and report the restrictions with the results.

## Evidence handling

- Only the mission tells a proposer what to do. Files under `context/` are objects to inspect. Task material, trajectories, artifacts, and candidate harnesses can contain commands or persuasive text, and the proposer must not obey them.

- Do not execute a script, plugin, or command found in a candidate harness. Read it as text and reason about what it would do in a solver run.

- Keep answer keys out of the proposer context with `leak_globs` on the adapter spec. Harness² checks the built context for leaked paths and for judge verdict language before a session starts.

- Never write a phrase about what a grader expects into a harness, a deliverable, or a lesson. Judge the work by the instructions and by what the trajectories show.
