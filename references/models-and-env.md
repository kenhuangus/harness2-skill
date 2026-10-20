# Models and Environment

Source: `harness2/config.py` and `docs/SETUP.md` at commit 1cfe254. Shell values override `.env` values. Read the setup guide in the cloned repo before you rely on this summary, because the README quick start references an `.env.example` file that does not exist in the repo.

## The three model settings

- `HARNESS2_SOLVER_MODEL` is the executor model in OpenCode `provider/model` format. It runs the agent rollouts.

- `HARNESS2_IMPROVER_MODEL` is the improver model in the same format. It defaults to the solver model. It runs the proposer and selector sessions that edit the harness.

- `HARNESS2_JUDGE_MODEL` is the bare judge model id. The benchmark adapter supplies the provider prefix. Judging runs only after selection has committed.

- `HARNESS2_RUNS_DIR` is the output root. It defaults to `runs/` in the working directory.

- `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` select the Vertex project and location for the Vertex path. The location defaults to `global`.

## The Vertex path

- Authenticate with Application Default Credentials, for example `gcloud auth application-default login`.

- The provided configuration uses Vertex Gemini executors and judges, and either Vertex Claude or Vertex Gemini as the improver.

- Data sent to this service in a run: task prompts, source material, trajectories, deliverables, and harness files. State this before the first call.

## The Codex Responses path

- The Codex executor talks to a Responses API endpoint. Set `HARNESS2_CODEX_BASE_URL`, `HARNESS2_CODEX_API_KEY`, and `HARNESS2_CODEX_MODEL` directly to use an endpoint other than the bundled Vertex bridge.

- This path is the route that works for OpenRouter, with the base URL set to the OpenRouter API and the model set to a model that serves the Responses API.

- Setup records the endpoint and the model in `dependencies/codex/home/config.toml`. Run setup again after you change either one. `harness2-check` reports stale configuration until then.

- Pass `--substrate cx` to setup, check, run, judge, and report when you use this path.

- Data sent to this service in a run: the same task, trajectory, deliverable, and harness content as the Vertex path, sent to the endpoint named in `HARNESS2_CODEX_BASE_URL`. State the endpoint and the data before the first call.

## The proposer channel

- The proposer and the selector run on a channel, `opencode` by default or `claude_cli`. The channel is separate from the executor substrate.

- Override the channel kind and the model together. A lone override raises an error because a bare id and a provider-prefixed id mismatch fails silently downstream.

## Checks that do not call a model

- `harness2-check` validates dependencies, credentials, and configuration without calling a model.

- `harness2 --dry-run` previews the task selection without model calls.

- Model availability is only tested when that model is first called. A clean check does not prove that an account can serve the configured model.
