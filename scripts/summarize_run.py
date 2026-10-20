#!/usr/bin/env python3
"""Summarize harness2 run output: ledgers, fallbacks, selections, lessons.

Reads summary.json files under a runs directory and EXPERIENCE.md lessons
under an optional library directory. Makes no model calls and writes nothing
unless --output is given.

Usage:
  python3 summarize_run.py <runs_dir> [--library <dir>] [--json] [--output <file>]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _ledger_line(mode: str, record: dict) -> str:
    ledger = record.get("ledger") or {}
    stages = record.get("stages") or []
    fell = [stage.get("label") for stage in stages if stage.get("fell_back")]
    kept = [stage.get("label") for stage in stages if stage.get("kept_base")]
    parts = [f"mode {mode}: R={ledger.get('R')} P={ledger.get('P')} ok={record.get('ok')}"]
    parts.append(f"finals={record.get('finals')}")
    if fell:
        parts.append(f"fell_back={fell}")
    if kept:
        parts.append(f"kept_base={kept}")
    return "  " + "; ".join(parts)


def summarize(runs_dir: Path) -> tuple[str, list[dict]]:
    summaries = sorted(runs_dir.rglob("summary.json"))
    rows: list[dict] = []
    lines: list[str] = [f"# Harness2 run summary: {runs_dir}", ""]
    if not summaries:
        lines.append("No summary.json files found. The run may not have finished a task.")
    for path in summaries:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            lines.append(f"- {path}: unreadable ({type(exc).__name__})")
            continue
        task = data.get("task_id", path.parent.name)
        lines.append(f"## task {task} (status: {data.get('status')})")
        modes = data.get("modes") or data.get("arms") or {}
        for mode, record in sorted(modes.items()):
            lines.append(_ledger_line(mode, record or {}))
        selections = data.get("selections") or {}
        for mode, sel in sorted(selections.items()):
            if not sel:
                continue
            lines.append(
                f"  selection {mode}: chosen={sel.get('chosen_label')} "
                f"base={sel.get('chosen_is_base')} ok={sel.get('ok')}"
            )
            why = (sel.get("why") or "").strip()
            if why:
                lines.append(f"    why: {why[:300]}")
            experience = sel.get("experience") or {}
            if experience.get("lesson"):
                lines.append(f"    lesson: {experience['lesson']}")
        errors = data.get("errors") or []
        for err in errors:
            lines.append(f"  error: {err}")
        lines.append("")
        rows.append(data)
    return "\n".join(lines).rstrip() + "\n", rows


def lessons(library_dir: Path) -> str:
    files = sorted(library_dir.rglob("EXPERIENCE.md"))
    if not files:
        return ""
    lines = [f"# Library lessons: {library_dir}", ""]
    for path in files:
        lines.append(f"## {path.parent.name}")
        lines.append(path.read_text(encoding="utf-8", errors="replace").strip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs_dir", type=Path)
    parser.add_argument("--library", type=Path, default=None)
    parser.add_argument("--json", action="store_true", help="print the raw summaries as JSON")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if not args.runs_dir.is_dir():
        print(f"{args.runs_dir} is not a directory")
        return 1

    if args.json:
        _, rows = summarize(args.runs_dir)
        text = json.dumps(rows, indent=2, default=str) + "\n"
    else:
        text, _ = summarize(args.runs_dir)
        if args.library and args.library.is_dir():
            extra = lessons(args.library)
            if extra:
                text += "\n" + extra

    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
