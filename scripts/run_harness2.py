#!/usr/bin/env python3
"""Fail-closed wrapper around the harness2 command line tools.

Commands: demo, check, run, judge, report.

- demo and check make no model calls and need no cap.
- run and judge call models. They refuse to start without --cap-usd and an
  --estimated-usd at or below the cap. Pass the harness2 flags after `--`,
  for example:
    python3 run_harness2.py --command run --cap-usd 5 --estimated-usd 2 \
        -- --bench lab --k 1 --mode parallel --only-domains X --max-tasks 1
- The wrapper prints the network and sandbox warning before a model-backed
  run. It never reads or prints a credential value.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
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
        help="preview only. Adds --dry-run for the run command and skips the cap gate",
    )
    args, extra = parser.parse_known_args()
    passthrough = [item for item in extra if item != "--"]

    root = find_harness2(args.harness2)

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
        print(
            f"Spend guard: estimate ${args.estimated_usd:.2f} within cap ${args.cap_usd:.2f}."
        )
        print(WARNING)

    argv = [sys.executable, "-m", MODULES[args.command], *passthrough]
    if args.dry_run and args.command == "run" and "--dry-run" not in passthrough:
        argv.append("--dry-run")

    env = dict(os.environ)
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    home_tmp = Path.home() / "tmp"
    if "TMPDIR" not in env and home_tmp.is_dir():
        env["TMPDIR"] = str(home_tmp)

    print("Running:", " ".join(argv))
    completed = subprocess.run(argv, env=env, cwd=str(root))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
