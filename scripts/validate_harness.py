#!/usr/bin/env python3
"""Validate a harness tree with harness2's own validator. Do not reimplement it.

Usage:
  python3 validate_harness.py <tree_dir> [--substrate cx|oc]
      [--harness2 <clone>] [--require-file <rel>]... [--no-subagents]

Exit 0 and a JSON census on success. Exit 1 and harness2's own error text,
which is written for a proposer to act on, on failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness2_home import import_harness2  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tree", type=Path, help="harness tree directory")
    parser.add_argument("--substrate", choices=("cx", "oc"), default="cx")
    parser.add_argument("--harness2", default=None, help="path to the harness2 clone")
    parser.add_argument(
        "--require-file",
        action="append",
        default=[],
        help="a file the domain cannot lose, repeatable",
    )
    parser.add_argument(
        "--no-subagents",
        action="store_true",
        help="reject sub_agents in the tree (adapter allow_subagents=False)",
    )
    args = parser.parse_args()

    import_harness2(args.harness2)
    from harness2.core import tree as HT

    if args.substrate == "cx":
        from harness2.substrate.codex import CODEX_SURFACE as surface
    else:
        from harness2.substrate.opencode import OPENCODE_SURFACE as surface

    if not args.tree.is_dir():
        print(f"INVALID: {args.tree} is not a directory")
        return 1

    rejected: list[str] = []
    harness = HT.read_tree(surface, args.tree, rejected=rejected)
    if rejected:
        print(
            "INVALID: these files are off the editable surface and would not be applied: "
            + ", ".join(sorted(rejected))
        )
        return 1
    if not harness:
        print(f"INVALID: no editable files found under {args.tree} for surface {surface.name}")
        return 1

    try:
        census = HT.validate(
            surface,
            harness,
            allow_subagents=not args.no_subagents,
        )
    except ValueError as exc:
        print(f"INVALID: {exc}")
        return 1

    missing = [rel for rel in args.require_file if rel not in harness]
    if missing:
        print("INVALID: required file(s) missing from the harness: " + ", ".join(missing))
        return 1

    census = {"ok": True, "substrate": surface.name, "tree": str(args.tree), **census}
    if args.require_file:
        census["required_files"] = args.require_file
    print(json.dumps(census, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
