#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
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


def run_cmd_args(args: list[str], cwd: str | None = None) -> dict[str, Any]:
    p = subprocess.run(args, shell=False, capture_output=True, text=True, cwd=cwd)
    shown = " ".join(shlex.quote(a) for a in args)
    return {"cmd": shown, "rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_step_artifact(artifact_path: Path, step_id: str, step_type: str, logs: list[dict[str, Any]]) -> None:
    with artifact_path.open("w", encoding="utf-8") as f:
        f.write(f"STEP: {step_id}\nTYPE: {step_type}\nUTC:  {utc_now()}\n\n")
        for i, e in enumerate(logs, start=1):
            f.write(f"[{i}] CMD: {e['cmd']}\nRC: {e['rc']}\n")
            if e.get("stdout"):
                out = e["stdout"]
                f.write("STDOUT:\n" + out + ("" if out.endswith("\n") else "\n"))
            if e.get("stderr"):
                err = e["stderr"]
                f.write("STDERR:\n" + err + ("" if err.endswith("\n") else "\n"))
            f.write("\n" + ("-" * 80) + "\n\n")


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="agno_runner",
        description="Runner padrão (PORTIFOLIOZERO) para TASK specs.",
    )

    ap.add_argument("--task", required=False, help="Caminho do JSON da task (planning/task_specs/...).")
    ap.add_argument("--run-dir", default=None, help="Diretório de saída (default: planning/runs/<task_id>/).")
    ap.add_argument("--version", action="store_true", help="Mostra versões (python + agno) e sai.")
    args = ap.parse_args()

    if args.version:
        print(f"python={sys.version}")
        print(f"agno_version={AGNO_VERSION}")
        return 0

    if not args.task:
        ap.error("the following arguments are required: --task")

    spec_path = Path(args.task)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    task_id = spec.get("task_id", "UNKNOWN_TASK")
    repo_path = spec.get("inputs", {}).get("repo_path", None)

    run_dir = Path(args.run_dir) if args.run_dir else Path("planning/runs") / str(task_id)
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

    allowlist = spec.get("inputs", {}).get("gate_allowlist", []) or spec.get("inputs", {}).get(
        "gate_s1_allowlist", []
    )

    for step in spec.get("workflow", []):
        step_id = step.get("step_id", "NO_STEP_ID")
        step_type = step.get("type", "unknown")

        artifacts = step.get("artifacts", [])
        artifact_path = Path(artifacts[0]) if artifacts else (run_dir / f"{step_id}.txt")
        artifact_path.parent.mkdir(parents=True, exist_ok=True)

        step_pass = True
        commands_count = 0

        if step_type == "write_file":
            target = Path(step["path"])
            content = step.get("content", "")
            write_text(target, content)

            log = (
                f"STEP: {step_id}\n"
                f"TYPE: {step_type}\n"
                f"UTC:  {utc_now()}\n"
                f"TARGET: {target}\n"
                f"BYTES: {len(content.encode('utf-8'))}\n"
            )
            write_text(artifact_path, log)

        elif step_type == "shell":
            logs: list[dict[str, Any]] = []
            for cmd in step.get("commands", []):
                commands_count += 1
                entry = run_cmd(cmd, cwd=repo_path)
                logs.append(entry)
                if entry["rc"] != 0:
                    step_pass = False

            if step_id in ("S1_PROVE_REPO", "S1_GATE_ALLOWLIST") and allowlist:
                try:
                    porcelain = ""
                    for e in logs:
                        if "git status --porcelain" in e["cmd"]:
                            porcelain = e.get("stdout", "")
                            break
                    changed = parse_porcelain_paths(porcelain)
                    if not allowlist_ok(changed, allowlist):
                        step_pass = False
                except Exception:
                    step_pass = False

            write_step_artifact(artifact_path, step_id, step_type, logs)

        elif step_type == "agno":
            # CONTRATO ÚNICO: agno = payload/exec (NUNCA commands)
            if step.get("commands"):
                step_pass = False
                msg = (
                    f"STEP: {step_id}\nTYPE: agno\nUTC:  {utc_now()}\n"
                    "ERROR: step_type=agno não aceita 'commands'.\n"
                    "MIGRATION: troque para type='shell' (commands) OU use payload/mode/config.\n\n"
                    f"STEP_KEYS: {sorted(list(step.keys()))}\n"
                )
                write_text(artifact_path, msg)
            else:
                mode = str(step.get("mode", "probe"))
                payload = step.get("payload", {})
                if not isinstance(payload, dict):
                    payload = {"payload": payload}
                payload_json = json.dumps(payload, ensure_ascii=False)

                exec_script = str(step.get("executor", "scripts/agno_entrypoint_exec.py"))
                exec_args = [
                    sys.executable,
                    exec_script,
                    "--mode",
                    mode,
                    "--payload-json",
                    payload_json,
                    "--task-id",
                    str(task_id),
                    "--step-id",
                    str(step_id),
                    "--out",
                    str(artifact_path),
                ]

                cfg = step.get("config", None)
                if cfg:
                    exec_args.extend(["--config", str(cfg)])

                entry = run_cmd_args(exec_args, cwd=repo_path)
                commands_count = 1
                step_pass = entry["rc"] == 0

                # executor escreve o artifact; anexamos stdout/stderr do runner
                with artifact_path.open("a", encoding="utf-8") as f:
                    f.write("\n" + ("-" * 80) + "\n")
                    f.write("RUNNER_EXEC_STDOUT/STDERR\n\n")
                    f.write(f"CMD: {entry['cmd']}\nRC: {entry['rc']}\n")
                    if entry.get("stdout"):
                        out = entry["stdout"]
                        f.write("STDOUT:\n" + out + ("" if out.endswith("\n") else "\n"))
                    if entry.get("stderr"):
                        err = entry["stderr"]
                        f.write("STDERR:\n" + err + ("" if err.endswith("\n") else "\n"))

        else:
            step_pass = False
            write_text(
                artifact_path,
                f"STEP: {step_id}\nTYPE: {step_type}\nUTC:  {utc_now()}\nERROR: unsupported step_type\n",
            )

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
