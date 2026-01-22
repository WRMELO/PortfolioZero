#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import agno  # type: ignore

    AGNO_VERSION = getattr(agno, "__version__", "?")
except Exception:
    AGNO_VERSION = "IMPORT_FAIL"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_cmd(cmd: str, cwd: str | None = None) -> dict[str, Any]:
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return {"cmd": cmd, "rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_porcelain_paths(porcelain_text: str) -> list[str]:
    paths: list[str] = []
    for line in porcelain_text.splitlines():
        if not line.strip():
            continue
        tail = line[3:].strip()
        if " -> " in tail:
            tail = tail.split(" -> ", 1)[1].strip()
        paths.append(tail)
    return paths


def allowlist_ok(changed: list[str], allowlist: list[str]) -> bool:
    def allowed(path: str) -> bool:
        for a in allowlist:
            if a.endswith("/") and path.startswith(a):
                return True
            if path == a:
                return True
        return False

    return all(allowed(p) for p in changed)


@dataclass
class StepResult:
    step_id: str
    step_type: str
    artifact: str
    passed: bool
    commands_count: int


def write_shell_artifact(path: Path, step_id: str, step_type: str, logs: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write(f"STEP: {step_id}\nTYPE: {step_type}\nUTC:  {utc_now()}\n\n")
        for i, e in enumerate(logs, start=1):
            f.write(f"[{i}] CMD: {e['cmd']}\nRC: {e['rc']}\n")
            if e["stdout"]:
                f.write("STDOUT:\n" + e["stdout"] + ("" if e["stdout"].endswith("\n") else "\n"))
            if e["stderr"]:
                f.write("STDERR:\n" + e["stderr"] + ("" if e["stderr"].endswith("\n") else "\n"))
            f.write("\n" + ("-" * 80) + "\n\n")


def main() -> int:
    ap = argparse.ArgumentParser(prog="agno_runner", description="Runner padrão (PORTIFOLIOZERO) para TASK specs.")
    ap.add_argument("--task", required=True, help="Caminho do JSON da task (planning/task_specs/...).")
    ap.add_argument("--run-dir", default=None, help="Diretório de saída (default: planning/runs/<task_id>/).")
    ap.add_argument("--version", action="store_true", help="Mostra versões (python + agno) e sai.")
    args = ap.parse_args()

    if args.version:
        print(f"python={sys.version}")
        print(f"agno_version={AGNO_VERSION}")
        return 0

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
        "runner": {"agno_version": AGNO_VERSION},
        "steps": [],
    }

    overall_pass = True
    step_results: list[StepResult] = []

    allowlist = spec.get("inputs", {}).get("gate_allowlist", []) or spec.get("inputs", {}).get("gate_s1_allowlist", [])

    for step in spec.get("workflow", []):
        step_id = step.get("step_id", "NO_STEP_ID")
        step_type = step.get("type", "unknown")

        artifacts = step.get("artifacts", [])
        artifact_path = Path(artifacts[0]) if artifacts else (run_dir / f"{step_id}.txt")
        artifact_path.parent.mkdir(parents=True, exist_ok=True)

        step_pass = True
        commands_count = 0

        if step_type == "shell":
            logs: list[dict[str, Any]] = []
            for cmd in step.get("commands", []):
                commands_count += 1
                entry = run_cmd(cmd, cwd=repo_path)
                logs.append(entry)
                if entry["rc"] != 0:
                    step_pass = False

            # Gate allowlist: aplica se houver allowlist e o step executar git status --porcelain
            if allowlist:
                status_out = ""
                for e in logs:
                    if "git status --porcelain" in e["cmd"]:
                        status_out = e["stdout"]
                        break
                if status_out.strip() or any("git status --porcelain" in e["cmd"] for e in logs):
                    changed = parse_porcelain_paths(status_out)
                    if not allowlist_ok(changed, list(allowlist)):
                        step_pass = False

            write_shell_artifact(artifact_path, step_id, step_type, logs)

        elif step_type == "agno":
            # Delegação ao entrypoint selecionado, via script dedicado
            payload = step.get("payload", {})
            mode = step.get("mode", "probe")
            payload_json = json.dumps(payload, ensure_ascii=False)

            cmd = (
                f"{sys.executable} scripts/agno_entrypoint_exec.py "
                f"--mode {mode} "
                f"--task-id {task_id} "
                f"--step-id {step_id} "
                f"--payload-json {json.dumps(payload_json)} "
                f"--out {artifact_path}"
            )
            # json.dumps(payload_json) garante escaping seguro como string literal (com aspas)
            logs = [run_cmd(cmd, cwd=repo_path)]
            commands_count = 1
            step_pass = logs[0]["rc"] == 0

            # Complementa artifact com stdout/stderr do exec (sem sobrescrever a parte principal)
            with artifact_path.open("a", encoding="utf-8") as f:
                f.write("\n")
                f.write("-" * 80 + "\n")
                f.write("RUNNER_EXEC_STDOUT/STDERR\n\n")
                e = logs[0]
                f.write(f"CMD: {e['cmd']}\nRC: {e['rc']}\n")
                if e["stdout"]:
                    f.write("STDOUT:\n" + e["stdout"] + ("" if e["stdout"].endswith("\n") else "\n"))
                if e["stderr"]:
                    f.write("STDERR:\n" + e["stderr"] + ("" if e["stderr"].endswith("\n") else "\n"))

        else:
            step_pass = False
            write_text(artifact_path, f"STEP: {step_id}\nTYPE: {step_type}\nUTC: {utc_now()}\nERROR: unsupported step_type\n")

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
