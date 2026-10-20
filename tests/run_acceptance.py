#!/usr/bin/env python3
"""Acceptance tests for the Harness² skill. No model is called. Nothing is spent.

Run: python3 tests/run_acceptance.py [--harness2 <clone>]

Groups:
  1. Demo k=2 completes, ledger identity R=4k / P=3k, known totals, resume is a no-op.
  2. Validator rejects an untriggered skill, a frontmatter name mismatch,
     a missing referenced script, over-cap always-on text, and bad hooks.
  3. A scaffolded toy adapter validates and completes one k=1 sequential run
     whose adopted deliverable is the corrected count.
  4. Regression: the red-team base harness from the Oct 2026 experiment
     validates unchanged on the Codex surface (skipped if not present).
  5. No secret-shaped string appears anywhere in the skill directory.
  6. Fix regressions: substrate auto-detect, grader-verdict gate, adapter
     gate, strict clone discovery, wrapper cap guards (including the judge
     dry-run bypass), spend tally, summarizer ledger identity, scaffold
     --force substrate switch and --domain validation, OpenCode toy run,
     and the Harness² naming rule.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))
from _harness2_home import find_harness2  # noqa: E402

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        FAILURES.append(name)


def run(argv: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, **kw)


def validate(tree: Path, substrate: str | None, extra: list[str] | None = None, home: Path | None = None, env: dict | None = None):
    argv = [sys.executable, str(SCRIPTS / "validate_harness.py"), str(tree)]
    if substrate:
        argv += ["--substrate", substrate]
    argv += extra or []
    if home:
        argv += ["--harness2", str(home)]
    return run(argv, env=env)


def test_demo(home: Path, tmp: Path) -> None:
    out = tmp / "demo"
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    env["PYTHONPATH"] = str(home)
    env["TMPDIR"] = str(tmp)
    argv = [sys.executable, "-m", "harness2.cli.demo", "--output", str(out), "--k", "2"]
    first = run(argv, env=env, cwd=str(home))
    check("demo k=2 exit 0", first.returncode == 0, (first.stdout + first.stderr).strip().splitlines()[-1] if (first.stdout + first.stderr).strip() else "")
    report = json.loads((out / "demo.json").read_text())
    check("demo 2 done 0 failed", (report["done"], report["failed"]) == (2, 0), f"done={report['done']} failed={report['failed']}")
    runs = out / "runs"
    for task, expected in (("ledger-1", "Total: 85.15\n"), ("ledger-2", "Total: 20.25\n")):
        summaries = list(runs.rglob(f"{task}/summary.json"))
        if not summaries:
            check(f"demo {task} summary", False, "missing")
            continue
        data = json.loads(summaries[0].read_text())
        for mode in ("agg", "seq"):
            ledger = data["modes"][mode]["ledger"]
            check(f"demo {task} {mode} ledger R=8 P=6", (ledger["R"], ledger["P"]) == (8, 6), f"R={ledger['R']} P={ledger['P']}")
        sel = data["selections"]["seq"]
        text = Path(sel["chosen_run_dir"], "answer.txt").read_text()
        check(f"demo {task} adopted total", text == expected, repr(text))
    executions = report["execution_count"]
    second = run(argv, env=env, cwd=str(home))
    report2 = json.loads((out / "demo.json").read_text())
    # The second process builds a fresh adapter, so its counter counts only
    # executions in that process. A clean resume executes nothing and still
    # reports both tasks done, with every task row skipped.
    statuses = [row.get("status") for row in report2.get("tasks", [])]
    check(
        "demo resume adds no executions",
        second.returncode == 0
        and report2["execution_count"] == 0
        and report2["done"] == 2
        and statuses == ["skipped", "skipped"],
        f"first run {executions} executions, resume {report2['execution_count']}, statuses {statuses}",
    )


def _copy_template(tmp: Path, name: str) -> Path:
    dst = tmp / name
    shutil.copytree(SKILL / "templates" / "base-harness-codex", dst)
    return dst


def test_validator_rejections(home: Path, tmp: Path) -> None:
    base = validate(_copy_template(tmp, "ok"), "cx", home=home)
    check("validator accepts clean codex tree", base.returncode == 0)

    tree = _copy_template(tmp, "untriggered")
    agents = tree / "AGENTS.md"
    agents.write_text(agents.read_text().replace("example-workflow", "renamed-away"))
    result = validate(tree, "cx", home=home)
    check("validator rejects untriggered skill", result.returncode == 1 and "never named" in result.stdout, result.stdout.strip()[:120])

    tree = _copy_template(tmp, "name-mismatch")
    skill = tree / ".agents" / "skills" / "example-workflow" / "SKILL.md"
    skill.write_text(skill.read_text().replace("description:", "name: other-name\ndescription:"))
    result = validate(tree, "cx", home=home)
    check("validator rejects frontmatter name mismatch", result.returncode == 1 and "OVERRIDES" in result.stdout, result.stdout.strip()[:120])

    tree = _copy_template(tmp, "missing-script")
    agents = tree / "AGENTS.md"
    agents.write_text(agents.read_text() + "\nRun `python3 scripts/does_not_exist.py` first.\n")
    result = validate(tree, "cx", home=home)
    check("validator rejects missing referenced script", result.returncode == 1 and "not in the harness" in result.stdout, result.stdout.strip()[:120])

    tree = _copy_template(tmp, "over-cap")
    agents = tree / "AGENTS.md"
    agents.write_text(agents.read_text() + "\n" + ("padding line\n" * 600))
    result = validate(tree, "cx", home=home)
    check("validator rejects over-cap always-on", result.returncode == 1 and "over the 8000 cap" in result.stdout, result.stdout.strip()[:120])

    tree = _copy_template(tmp, "bad-hooks")
    hooks = tree / ".codex" / "hooks.json"
    hooks.write_text('{"hooks": {"NotAnEvent": []}}')
    result = validate(tree, "cx", home=home)
    check("validator rejects unknown hook event", result.returncode == 1 and "unknown event" in result.stdout, result.stdout.strip()[:120])


def test_scaffold(home: Path, tmp: Path) -> None:
    refusal = run([
        sys.executable, str(SCRIPTS / "scaffold_adapter.py"),
        "--name", "bad", "--work", "improve the rubric score", "--output", str(tmp / "bad"),
    ])
    check("scaffold refuses a measurement-word work description", refusal.returncode == 1, refusal.stdout.strip()[:100])

    project = tmp / "toy"
    made = run([
        sys.executable, str(SCRIPTS / "scaffold_adapter.py"),
        "--name", "line-count", "--work", "count lines in text files",
        "--output", str(project), "--substrate", "cx",
    ])
    check("scaffold writes a project", made.returncode == 0, made.stdout.strip().splitlines()[0] if made.stdout.strip() else made.stderr[:200])
    valid = validate(project / "base_harness", "cx", home=home)
    check("scaffolded base harness validates", valid.returncode == 0, valid.stdout.strip()[:120])

    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    env["HARNESS2_HOME"] = str(home)
    env["TMPDIR"] = str(tmp)
    toy = run([sys.executable, "run_toy.py"], cwd=str(project), env=env)
    check("toy k=1 sequential run exit 0", toy.returncode == 0, (toy.stdout + toy.stderr).strip().splitlines()[-1] if (toy.stdout + toy.stderr).strip() else "")
    report_path = project / "runs-toy" / "toy.json"
    if report_path.is_file():
        report = json.loads(report_path.read_text())
        check("toy run 1 done 0 failed", (report["done"], report["failed"]) == (1, 0))
        summaries = list((project / "runs-toy" / "runs").rglob("summary.json"))
        if summaries:
            data = json.loads(summaries[0].read_text())
            sel = data["selections"]["seq"]
            text = Path(sel["chosen_run_dir"], "answer.txt").read_text()
            check("toy adopted deliverable counts the blank line", text == "Lines: 4\n", repr(text))
            lesson = (sel.get("experience") or {}).get("lesson", "")
            check("toy library lesson recorded", "blank" in lesson, lesson[:80])
        else:
            check("toy summary exists", False)
    else:
        check("toy report exists", False)


def test_redteam_regression(home: Path) -> None:
    base = Path("~/workspace/harness2-experiment/src/redteam/base_harness").expanduser()
    if not base.is_dir():
        print("SKIP  redteam regression (experiment tree not present)")
        return
    result = validate(base, "cx", extra=["--require-file", "scripts/send_to_victim.py"], home=home)
    check("redteam base harness validates unchanged", result.returncode == 0, result.stdout.strip()[:160] or result.stderr[:160])


def test_validator_autodetect_and_gates(home: Path, tmp: Path) -> None:
    template = SKILL / "templates" / "base-harness-codex"
    auto = validate(template, None, home=home)
    ok_auto = False
    if auto.returncode == 0:
        try:
            ok_auto = json.loads(auto.stdout).get("substrate_detected") is True
        except json.JSONDecodeError:
            ok_auto = False
    check("validator auto-detects the codex surface", ok_auto, auto.stdout.strip()[:100])
    wrong = validate(template, "oc", home=home)
    check("validator rejects a tree validated on the wrong surface", wrong.returncode == 1, wrong.stdout.strip()[:100])

    tree = _copy_template(tmp, "verdict")
    agents = tree / "AGENTS.md"
    agents.write_text(agents.read_text() + '\nResult so far: {"pass_rate": 1}\n')
    result = validate(tree, "cx", home=home)
    check("validator rejects grader-verdict markers in a tree", result.returncode == 1 and "grader" in result.stdout.lower(), result.stdout.strip()[:140])

    adapter_file = tmp / "mini_adapter.py"
    adapter_file.write_text(
        "class Gate:\n"
        "    def __init__(self, root):\n"
        "        pass\n"
        "    def validate_tree(self, tree):\n"
        "        raise ValueError('domain invariant broken for this test')\n",
        encoding="utf-8",
    )
    gated = validate(template, "cx", extra=["--adapter", f"{adapter_file}:Gate"], home=home)
    check("validator runs the adapter validate_tree gate", gated.returncode == 1 and "domain invariant broken" in gated.stdout, gated.stdout.strip()[:140])
    adapter_file.write_text(
        "class Gate:\n"
        "    def __init__(self, root):\n"
        "        pass\n"
        "    def validate_tree(self, tree):\n"
        "        return None\n",
        encoding="utf-8",
    )
    passed = validate(template, "cx", extra=["--adapter", f"{adapter_file}:Gate"], home=home)
    ok_adapter = False
    if passed.returncode == 0:
        try:
            ok_adapter = json.loads(passed.stdout).get("adapter_validated") is True
        except json.JSONDecodeError:
            ok_adapter = False
    check("validator passes a tree the adapter accepts", ok_adapter, passed.stdout.strip()[:100])


def test_home_strictness(home: Path, tmp: Path) -> None:
    template = SKILL / "templates" / "base-harness-codex"
    bad_explicit = validate(template, "cx", home=tmp / "no-such-clone")
    check("an invalid --harness2 path is a hard error, not a fallback", bad_explicit.returncode != 0 and "fall back" in (bad_explicit.stdout + bad_explicit.stderr), (bad_explicit.stdout + bad_explicit.stderr).strip()[:140])
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    env["HARNESS2_HOME"] = str(tmp / "no-such-clone")
    bad_env = validate(template, "cx", env=env)
    check("an invalid HARNESS2_HOME is a hard error, not a fallback", bad_env.returncode != 0 and "fall back" in (bad_env.stdout + bad_env.stderr), (bad_env.stdout + bad_env.stderr).strip()[:140])


def test_wrapper_guards(tmp: Path) -> None:
    wrapper = str(SCRIPTS / "run_harness2.py")
    judge_dry = run([sys.executable, wrapper, "--command", "judge", "--dry-run", "--", "--bench", "lab"])
    check("wrapper refuses --dry-run for judge (no cap bypass)", judge_dry.returncode == 2 and "never waived" in judge_dry.stdout or (judge_dry.returncode == 2 and "dry-run" in judge_dry.stdout), judge_dry.stdout.strip()[:140])
    check_no_bench = run([sys.executable, wrapper, "--command", "check"])
    check("wrapper refuses check without --bench", check_no_bench.returncode == 2 and "--bench" in check_no_bench.stdout, check_no_bench.stdout.strip()[:140])
    sys.path.insert(0, str(SCRIPTS))
    import run_harness2 as wrapper_module

    runs = tmp / "fake-runs"
    task_dir = runs / "ns" / "task-1"
    task_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "task_id": "task-1",
        "k": 1,
        "status": "ok",
        "modes": {"seq": {"ok": True, "ledger": {"R": 4, "P": 3}, "finals": ["c1"],
                          "stages": [{"label": "inv1", "usd": 4.0}, {"label": "c1", "usd": 3.0}]}},
        "selections": {"seq": {"chosen_label": "c1", "ok": True, "usd": 1.5}},
    }
    (task_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    total, files = wrapper_module.tally_recorded_spend([runs], 0)
    check("spend tally sums stages and selection from summaries", files == 1 and abs(total - 8.5) < 1e-9, f"total={total} files={files}")
    out = run([sys.executable, str(SCRIPTS / "summarize_run.py"), str(runs)])
    check("summarizer marks a sound ledger identity OK", "ledger identity OK" in out.stdout, out.stdout.strip()[:160])
    summary["modes"]["seq"]["ledger"] = {"R": 99, "P": 3}
    (task_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    out = run([sys.executable, str(SCRIPTS / "summarize_run.py"), str(runs)])
    check("summarizer flags a broken ledger identity", "LEDGER IDENTITY MISMATCH" in out.stdout, out.stdout.strip()[:160])


def test_scaffold_repairs(home: Path, tmp: Path) -> None:
    bad_domain = run([
        sys.executable, str(SCRIPTS / "scaffold_adapter.py"),
        "--name", "ok-name", "--work", "count lines in text files",
        "--domain", 'bad"domain', "--output", str(tmp / "bad-domain"),
    ])
    check("scaffold rejects a domain that would break generated code", bad_domain.returncode == 1, bad_domain.stdout.strip()[:120])

    project = tmp / "switch"
    made = run([
        sys.executable, str(SCRIPTS / "scaffold_adapter.py"),
        "--name", "line-count", "--work", "count lines in text files",
        "--output", str(project), "--substrate", "cx",
    ])
    switched = run([
        sys.executable, str(SCRIPTS / "scaffold_adapter.py"),
        "--name", "line-count", "--work", "count lines in text files",
        "--output", str(project), "--substrate", "oc", "--force",
    ])
    tree = project / "base_harness"
    clean = (
        made.returncode == 0
        and switched.returncode == 0
        and (tree / "systemprompt.md").is_file()
        and not (tree / "AGENTS.md").exists()
    )
    check("scaffold --force substrate switch leaves no stale tree", clean, switched.stdout.strip()[:120])
    valid = validate(tree, None, home=home)
    check("switched opencode base harness validates by auto-detect", valid.returncode == 0, valid.stdout.strip()[:120])

    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    env["HARNESS2_HOME"] = str(home)
    env["TMPDIR"] = str(tmp)
    toy = run([sys.executable, "run_toy.py"], cwd=str(project), env=env)
    ok = toy.returncode == 0
    detail = (toy.stdout + toy.stderr).strip().splitlines()[-1] if (toy.stdout + toy.stderr).strip() else ""
    if ok:
        summaries = list((project / "runs-toy" / "runs").rglob("summary.json"))
        if summaries:
            data = json.loads(summaries[0].read_text())
            sel = data["selections"]["seq"]
            text = Path(sel["chosen_run_dir"], "answer.txt").read_text()
            ok = text == "Lines: 4\n"
            detail = repr(text)
        else:
            ok = False
            detail = "no summary"
    check("opencode toy run adopts the corrected count", ok, detail)


def test_naming() -> None:
    bare = "Harness" + "2"  # split so this test file does not trip its own scan
    offenders: list[str] = []
    for path in SKILL.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if path.suffix not in (".md", ".py", ".yaml", ".tmpl"):
            continue
        if bare in path.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(str(path.relative_to(SKILL)))
    check(f"no bare {bare} spelling remains (prose uses Harness²)", not offenders, ", ".join(offenders))
    skill_md = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    check("SKILL.md title and hard rules use Harness²", skill_md.startswith("# Harness²") and "superscript" in skill_md)


SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"gho_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[A-Z0-9]{16}"),
    re.compile(r"(API_KEY|TOKEN|SECRET)\s*=\s*['\"][^'\"]{12,}['\"]"),
)


def test_secret_scan() -> None:
    hits: list[str] = []
    for path in SKILL.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                hits.append(f"{path.relative_to(SKILL)}: {match.group(0)[:24]}...")
    check("no secret-shaped strings in the skill", not hits, "; ".join(hits[:3]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness2", default=None)
    args = parser.parse_args()
    home = find_harness2(args.harness2)
    print(f"Harness² clone: {home}")
    tmp = Path(tempfile.mkdtemp(prefix="harness2-skill-test-", dir=str(Path.home() / "tmp") if (Path.home() / "tmp").is_dir() else None))
    print(f"scratch: {tmp}")
    for sub in ("demo-work", "validator", "scaffold", "gates", "wrapper", "repairs"):
        (tmp / sub).mkdir(exist_ok=True)
    test_demo(home, tmp / "demo-work")
    test_validator_rejections(home, tmp / "validator")
    test_scaffold(home, tmp / "scaffold")
    test_validator_autodetect_and_gates(home, tmp / "gates")
    test_home_strictness(home, tmp)
    test_wrapper_guards(tmp / "wrapper")
    test_scaffold_repairs(home, tmp / "repairs")
    test_redteam_regression(home)
    test_naming()
    test_secret_scan()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        return 1
    print("ALL ACCEPTANCE TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
