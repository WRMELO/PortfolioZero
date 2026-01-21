#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_cmd(cmd: str, cwd: str | None = None) -> dict[str, Any]:
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return {"cmd": cmd, "rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def agno_version() -> str:
    try:
        import agno  # type: ignore

        return getattr(agno, "__version__", "?")
    except Exception:
        return "IMPORT_FAIL"


@dataclass
class StepResult:
    step_id: str
    step_type: str
    artifact: str
    passed: bool
    commands_count: int


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="agno_runner",
        description="Runner padrão (PORTIFOLIOZERO) para executar TASK specs (JSON).",
    )
    ap.add_argument("--task", required=False, help="Caminho do JSON da task (planning/task_specs/...).")
    ap.add_argument("--run-dir", default=None, help="Diretório de saída (default: planning/runs/<task_id>/).")
    ap.add_argument("--version", action="store_true", help="Mostra versões (python + agno) e sai.")
    args = ap.parse_args()

    if args.version:
        import sys

        print(f"python={sys.version}")
        print(f"agno_version={agno_version()}")
        return 0

    if not args.task:
        ap.error("--task é obrigatório (use --version para apenas ver versões).")

    spec_path = Path(args.task)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    task_id = spec.get("task_id", "UNKNOWN_TASK")
    repo_path = spec.get("inputs", {}).get("repo_path", None)

    run_dir = Path(args.run_dir) if args.run_dir else Path("planning/runs") / task_id
    run_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "task_id": task_id,
        "spec_path": str(spec_path),
        "run_dir": str(run_dir),
        "started_at": utc_now(),
        "runner": {"agno_version": agno_version()},
        "steps": [],
    }

    overall_pass = True
    step_results: list[StepResult] = []

    for step in spec.get("workflow", []):
        step_id = step.get("step_id", "NO_STEP_ID")
        step_type = step.get("type", "unknown")

        artifacts = step.get("artifacts", [])
        artifact_path = Path(artifacts[0]) if artifacts else (run_dir / f"{step_id}.txt")
        artifact_path.parent.mkdir(parents=True, exist_ok=True)

        step_pass = True
        commands_count = 0

        if step_type != "shell":
            step_pass = False
            write_text(
                artifact_path,
                f"STEP: {step_id}\nTYPE: {step_type}\nUTC:  {utc_now()}\nERROR: unsupported step_type\n",
            )
        else:
            logs: list[dict[str, Any]] = []
            for cmd in step.get("commands", []):
                commands_count += 1
                entry = run_cmd(cmd, cwd=repo_path)
                logs.append(entry)
                if entry["rc"] != 0:
                    step_pass = False

            with artifact_path.open("w", encoding="utf-8") as f:
                f.write(f"STEP: {step_id}\nTYPE: {step_type}\nUTC:  {utc_now()}\n\n")
                for i, e in enumerate(logs, start=1):
                    f.write(f"[{i}] CMD: {e['cmd']}\nRC: {e['rc']}\n")
                    if e["stdout"]:
                        f.write("STDOUT:\n" + e["stdout"] + ("" if e["stdout"].endswith("\n") else "\n"))
                    if e["stderr"]:
                        f.write("STDERR:\n" + e["stderr"] + ("" if e["stderr"].endswith("\n") else "\n"))
                    f.write("\n" + ("-" * 80) + "\n\n")

        overall_pass = overall_pass and step_pass
        sr = StepResult(
            step_id=step_id,
            step_type=step_type,
            artifact=str(artifact_path),
            passed=step_pass,
            commands_count=commands_count,
        )
        step_results.append(sr)
        report["steps"].append(
            {
                "step_id": sr.step_id,
                "type": sr.step_type,
                "artifact": sr.artifact,
                "pass": sr.passed,
                "commands_count": sr.commands_count,
            }
        )

    report["overall_pass"] = overall_pass
    report["finished_at"] = utc_now()

    report_path = run_dir / "report.json"
    write_text(report_path, json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    print("TASK:", task_id)
    print("OVERALL:", "PASS" if overall_pass else "FAIL")
    for s in step_results:
        print(f"- {s.step_id}: {'PASS' if s.passed else 'FAIL'} -> {s.artifact}")
    print("REPORT:", report_path)

    return 0 if overall_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
