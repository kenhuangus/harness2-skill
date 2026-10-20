"""Locate a Harness² clone and put it on sys.path. Shared by the skill scripts.

Discovery order: an explicit --harness2 path, then $HARNESS2_HOME, then the
known local clones, then a `harness2` directory under the current working
directory or the home directory. A candidate must contain
harness2/core/tree.py.

An explicit path or $HARNESS2_HOME that is set but does not point at a
harness2 clone is a hard error. Falling back to a different clone silently
would run the wrong code against the wrong configuration.
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


def _is_clone(root: Path) -> bool:
    return (root / "harness2" / "core" / "tree.py").is_file()


def find_harness2(explicit: str | None = None) -> Path:
    if explicit:
        root = Path(explicit).expanduser()
        if not _is_clone(root):
            raise SystemExit(
                f"--harness2 {explicit!r} does not point at a Harness² clone "
                "(no harness2/core/tree.py there). Refusing to fall back to a "
                "different clone."
            )
        return root.resolve()
    env = os.environ.get("HARNESS2_HOME", "").strip()
    if env:
        root = Path(env).expanduser()
        if not _is_clone(root):
            raise SystemExit(
                f"HARNESS2_HOME {env!r} does not point at a Harness² clone "
                "(no harness2/core/tree.py there). Fix it or unset it. "
                "Refusing to fall back to a different clone."
            )
        return root.resolve()
    roots = [Path(p).expanduser() for p in CANDIDATES]
    roots.append(Path.cwd() / "harness2")
    for root in roots:
        if _is_clone(root):
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
