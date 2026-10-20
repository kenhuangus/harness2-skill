#!/usr/bin/env python3
"""Fail-closed wrapper around the Harness² command line tools.

Commands: demo, check, run, judge, report.

- demo makes no model calls and needs no cap.
- check needs a benchmark, for example `-- --bench lab`. It validates an
  installed upstream benchmark. It does not work for a custom domain.
- run and judge call models. They refuse to start without --cap-usd and an
  --estimated-usd at or below the cap. The estimate is a pre-flight gate,
  not an in-flight control. After the command finishes, the wrapper tallies
  the spend recorded in the new summary.json files and exits 3 when the
  recorded total exceeds the cap. In-flight enforcement needs a provider
  spend check between tasks. See references/safety-and-cost.md.
- --dry-run is valid for the run command only. It never waives the cap gate
  for judge, because harness2-judge has no dry-run mode.
- report reads finished runs and calls no model.

Pass the harness2 flags after `--`, for example:
  python3 run_harness2.py --command run --cap-usd 5 --estimated-usd 2 \
      -- --bench lab --k 1 --mode parallel --only-domains X --max-tasks 1
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness2_home import find_harness2  # noqa: E402

MODULES = {
    "demo": "harness2.cli.demo",
    "check": "harness2.cli.check",
    "run": "harness2.cli.run_sweep",
    "judge": "harness2.cli.judge",
    "report": "harness2.cli.report",
}
PAID = ("run", "judge")

WARNING = (
    "WARNING: executor network access is unrestricted and the Codex executor "
    "runs with its sandbox disabled. For a measured run, block "
    "huggingface.co, hf.co, github.com, and raw.githubusercontent.com for "
    "the executor after setup. See references/safety-and-cost.md."
)


def tally_recorded_spend(roots: list[Path], since: float) -> tuple[float, int]:
    """Sum the improver spend recorded in summary.json files written since `since`.

    Counts each mode's stage costs plus the selection cost in every summary
    modified after the run started. Rollout cost recorded by a benchmark
    adapter may not be in the summary, so treat the total as a floor.
    """
    total = 0.0
    files = 0
    seen: set[Path] = set()
    for root in roots:
        if not root or not Path(root).is_dir():
            continue
        for path in Path(root).rglob("summary.json"):
            if path in seen or path.stat().st_mtime < since:
                continue
            seen.add(path)
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            files += 1
            modes = data.get("modes") or data.get("arms") or {}
            for record in modes.values():
                for stage in (record or {}).get("stages") or []:
                    total += float(stage.get("usd") or 0.0)
            for sel in (data.get("selections") or {}).values():
                if sel:
                    total += float(sel.get("usd") or 0.0)
    return total, files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", choices=tuple(MODULES), default="check")
    parser.add_argument("--harness2", default=None, help="path to the harness2 clone")
    parser.add_argument("--cap-usd", type=float, default=None, help="hard spend cap for run and judge")
    parser.add_argument(
        "--estimated-usd", type=float, default=None, help="estimated cost of this invocation"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="preview only. Valid for the run command only, where it adds --dry-run",
    )
    args, extra = parser.parse_known_args()
    passthrough = list(extra)
    if passthrough and passthrough[0] == "--":
        passthrough = passthrough[1:]

    root = find_harness2(args.harness2)

    if args.dry_run and args.command != "run":
        print(
            f"REFUSED: --dry-run is only valid for the run command. The {args.command} "
            "command has no dry-run mode in harness2, so running it would spend "
            "for real. The cap gate is never waived by --dry-run."
        )
        return 2

    if args.command == "check" and "--bench" not in passthrough:
        print(
            "REFUSED: the check command needs a benchmark, for example "
            "`--command check -- --bench lab`. Check covers the upstream "
            "benchmarks only (jb, lab, wb). For a custom domain, preflight is "
            "validate_harness.py on the base tree plus the local demo."
        )
        return 2

    if args.command in PAID and not args.dry_run:
        if args.cap_usd is None:
            print(
                "REFUSED: --cap-usd is required for a model-backed run. "
                "Set an explicit cap first. The demo and check commands need no cap."
            )
            return 2
        if args.estimated_usd is None:
            print(
                "REFUSED: --estimated-usd is required so the cap can be checked "
                "before any spend. Estimate from the run shape: tasks x modes x "
                "(4k rollouts + 3k improver sessions)."
            )
            return 2
        if args.estimated_usd > args.cap_usd:
            print(
                f"REFUSED: estimated ${args.estimated_usd:.2f} exceeds the cap "
                f"${args.cap_usd:.2f}. Reduce k, the task selection, or raise the cap."
            )
            return 2
        print(f"Spend guard: estimate ${args.estimated_usd:.2f} within cap ${args.cap_usd:.2f}.")
        print(WARNING)

    argv = [sys.executable, "-m", MODULES[args.command], *passthrough]
    if args.dry_run and args.command == "run" and "--dry-run" not in passthrough:
        argv.append("--dry-run")

    env = dict(os.environ)
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    if "TMPDIR" not in env:
        # This machine's /tmp is a small tmpfs. A full sweep can fill it and
        # fail in ways that look like code regressions. Keep temp work on disk.
        home_tmp = Path.home() / "tmp"
        home_tmp.mkdir(parents=True, exist_ok=True)
        env["TMPDIR"] = str(home_tmp)

    started = time.time()
    print("Running:", " ".join(argv))
    completed = subprocess.run(argv, env=env, cwd=str(root))
    if completed.returncode != 0:
        return completed.returncode

    if args.command in PAID and not args.dry_run and args.cap_usd is not None:
        runs_env = env.get("HARNESS2_RUNS_DIR", "")
        roots = [Path(runs_env).expanduser()] if runs_env else [root / "runs", Path.cwd() / "runs"]
        total, files = tally_recorded_spend(roots, started - 5)
        if files:
            print(f"Recorded improver spend in {files} new summary file(s): ${total:.2f}.")
            if total > args.cap_usd:
                print(
                    f"SPEND CAP EXCEEDED: recorded ${total:.2f} is above the cap "
                    f"${args.cap_usd:.2f}. The gate is pre-flight and the tally is "
                    "post-run, so this detects an overrun, it does not undo it. "
                    "Add a provider spend check between tasks for in-flight control."
                )
                return 3
        else:
            print(
                "Spend tally: no new summary.json found under the runs root, so the "
                "recorded spend could not be checked against the cap."
            )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
