"""Locate a harness2 clone and put it on sys.path. Shared by the skill scripts.

Discovery order: $HARNESS2_HOME, then the known local clones, then a
`harness2` directory under the current working directory or the home
directory. A candidate must contain harness2/core/tree.py.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

CANDIDATES = (
    "~/workspace/harness2-experiment/repo",
    "~/tmp/harness2-fresh",
    "~/harness2",
)


def find_harness2(explicit: str | None = None) -> Path:
    roots: list[Path] = []
    if explicit:
        roots.append(Path(explicit).expanduser())
    env = os.environ.get("HARNESS2_HOME", "").strip()
    if env:
        roots.append(Path(env).expanduser())
    roots.extend(Path(p).expanduser() for p in CANDIDATES)
    roots.append(Path.cwd() / "harness2")
    for root in roots:
        if (root / "harness2" / "core" / "tree.py").is_file():
            return root.resolve()
    raise SystemExit(
        "No harness2 clone found. Clone https://github.com/google-research/harness2 "
        "at commit 1cfe254 and set HARNESS2_HOME to its path, or pass --harness2."
    )


def import_harness2(explicit: str | None = None) -> Path:
    root = find_harness2(explicit)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root
