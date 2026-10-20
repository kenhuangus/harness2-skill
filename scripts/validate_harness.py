#!/usr/bin/env python3
"""Validate a harness tree with Harness²'s own validator. Do not reimplement it.

This runs the same three gates Harness²'s recursion applies to a proposal in
`core/recursion.py` (`_accept_tree`):
  1. `harness2.core.tree.validate()` for the substrate surface.
  2. The adapter's `validate_tree()`, when --adapter names one.
  3. `context.assert_tree_has_no_grader_verdicts()`, the leak tripwire.

One difference from the recursion path: the recursion repairs missing skill
trigger lines automatically before it validates. This pre-flight check is
strict and reports them instead, so a human sees the defect before a run.

Usage:
  python3 validate_harness.py <tree_dir> [--substrate cx|oc]
      [--harness2 <clone>] [--require-file <rel>]... [--no-subagents]
      [--adapter <adapter.py:ClassName> --adapter-root <dir>]

Without --substrate the surface is detected from the tree: an AGENTS.md
means Codex (cx), a systemprompt.md means OpenCode (oc). Passing the wrong
substrate explicitly is an error the output will show as off-surface files.

Exit 0 and a JSON census on success. Exit 1 and Harness²'s own error text,
which is written for a proposer to act on, on failure.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness2_home import import_harness2  # noqa: E402


def detect_substrate(tree: Path) -> str | None:
    has_cx = (tree / "AGENTS.md").is_file()
    has_oc = (tree / "systemprompt.md").is_file()
    if has_cx and not has_oc:
        return "cx"
    if has_oc and not has_cx:
        return "oc"
    return None


def load_adapter(spec: str, root: Path):
    """Load <file.py:ClassName> and instantiate it with one Path argument."""
    file_part, _, class_name = spec.rpartition(":")
    if not file_part or not class_name:
        raise ValueError("--adapter must look like path/to/adapter.py:ClassName")
    path = Path(file_part).expanduser()
    if not path.is_file():
        raise ValueError(f"--adapter file {file_part!r} does not exist")
    module_spec = importlib.util.spec_from_file_location("skill_adapter_check", path)
    if module_spec is None or module_spec.loader is None:
        raise ValueError(f"could not load --adapter file {file_part!r}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    cls = getattr(module, class_name, None)
    if cls is None:
        raise ValueError(f"--adapter class {class_name!r} not found in {file_part!r}")
    return cls(Path(root))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tree", type=Path, help="harness tree directory")
    parser.add_argument(
        "--substrate",
        choices=("cx", "oc"),
        default=None,
        help="surface to validate against. Default: detect from the tree",
    )
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
    parser.add_argument(
        "--adapter",
        default=None,
        help="adapter to run validate_tree() with, as path/to/adapter.py:ClassName",
    )
    parser.add_argument(
        "--adapter-root",
        type=Path,
        default=None,
        help="root passed to the adapter constructor. Default: the tree's parent directory",
    )
    args = parser.parse_args()

    import_harness2(args.harness2)
    from harness2.core import context as harness_context
    from harness2.core import tree as HT

    if not args.tree.is_dir():
        print(f"INVALID: {args.tree} is not a directory")
        return 1

    substrate = args.substrate or detect_substrate(args.tree)
    if substrate is None:
        print(
            "INVALID: could not detect the substrate from the tree (found both or neither "
            "of AGENTS.md and systemprompt.md). Pass --substrate cx or --substrate oc."
        )
        return 1
    detected = args.substrate is None

    if substrate == "cx":
        from harness2.substrate.codex import CODEX_SURFACE as surface
    else:
        from harness2.substrate.opencode import OPENCODE_SURFACE as surface

    rejected: list[str] = []
    harness = HT.read_tree(surface, args.tree, rejected=rejected)
    if rejected:
        print(
            "INVALID: these files are off the editable surface and would not be applied: "
            + ", ".join(sorted(rejected))
            + (
                ". The tree may belong to the other substrate."
                if not detected
                else ""
            )
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
        harness_context.assert_tree_has_no_grader_verdicts(harness)
    except ValueError as exc:
        print(f"INVALID: {exc}")
        return 1

    if args.adapter:
        root = args.adapter_root or args.tree.parent
        try:
            adapter = load_adapter(args.adapter, root)
            adapter.validate_tree(harness)
        except Exception as exc:
            print(
                "INVALID: adapter validate_tree could not pass this tree: "
                f"{type(exc).__name__}: {exc}"
            )
            return 1

    missing = [rel for rel in args.require_file if rel not in harness]
    if missing:
        print("INVALID: required file(s) missing from the harness: " + ", ".join(missing))
        return 1

    census = {
        "ok": True,
        "substrate": surface.name,
        "substrate_detected": detected,
        "tree": str(args.tree),
        "adapter_validated": bool(args.adapter),
        **census,
    }
    if args.require_file:
        census["required_files"] = args.require_file
    print(json.dumps(census, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
