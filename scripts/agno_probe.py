#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import pkgutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from importlib import metadata as importlib_metadata  # py>=3.8
except Exception:  # pragma: no cover
    import importlib_metadata  # type: ignore


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_cmd(cmd: str, cwd: str | None = None) -> dict[str, Any]:
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return {"cmd": cmd, "rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


@dataclass
class AgnoSnapshot:
    captured_at_utc: str
    python_version: str
    python_executable: str
    agno_version: str
    agno_file: str
    agno_has_path: bool
    agno_dir_top: list[str]
    agno_submodules: list[str]
    dist_name: str
    dist_version: str
    dist_location: str
    entrypoints_console_scripts: list[dict[str, str]]
    entrypoints_all: list[dict[str, str]]
    cli_agno_help: dict[str, Any]
    cli_python_m_agno_help: dict[str, Any]


def safe_list_dir(obj: Any, limit: int = 80) -> list[str]:
    try:
        names = [n for n in dir(obj) if not n.startswith("_")]
        names_sorted = sorted(names)
        return names_sorted[:limit]
    except Exception:
        return []


def main() -> int:
    ap = argparse.ArgumentParser(description="Captura snapshot de capacidades do pacote agno no .venv.")
    ap.add_argument(
        "--out",
        required=True,
        help="Caminho do JSON de saída (ex: planning/runs/TASK_A_003/agno_probe.json).",
    )
    ap.add_argument(
        "--repo",
        default=None,
        help="Repo path (opcional) para comandos CLI; se omitido, usa cwd.",
    )
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    agno = importlib.import_module("agno")
    agno_version = getattr(agno, "__version__", "?")
    agno_file = getattr(agno, "__file__", "?")
    agno_has_path = hasattr(agno, "__path__")

    submods: list[str] = []
    if agno_has_path:
        try:
            for m in pkgutil.iter_modules(agno.__path__):  # type: ignore[attr-defined]
                submods.append(m.name)
        except Exception:
            submods = []

    # Distribuição (entrypoints)
    dist_name = "agno"
    dist_version = "?"
    dist_location = "?"
    eps_all: list[dict[str, str]] = []
    eps_console: list[dict[str, str]] = []

    try:
        dist = importlib_metadata.distribution(dist_name)
        dist_version = dist.version
        dist_location = str(dist.locate_file(""))
        try:
            # entry_points pode variar por versão, então normalizamos em dicts simples
            for ep in dist.entry_points:
                eps_all.append({"group": ep.group, "name": ep.name, "value": ep.value})
                if ep.group == "console_scripts":
                    eps_console.append({"name": ep.name, "value": ep.value})
        except Exception:
            eps_all = []
            eps_console = []
    except Exception:
        pass

    # CLI probes (não supõe que exista; apenas registra)
    repo = args.repo
    cli1 = run_cmd("command -v agno && agno --help", cwd=repo)
    cli2 = run_cmd(f"{sys.executable} -m agno --help", cwd=repo)

    snap = AgnoSnapshot(
        captured_at_utc=utc_now(),
        python_version=sys.version,
        python_executable=sys.executable,
        agno_version=str(agno_version),
        agno_file=str(agno_file),
        agno_has_path=bool(agno_has_path),
        agno_dir_top=safe_list_dir(agno, limit=120),
        agno_submodules=sorted(submods)[:500],
        dist_name=dist_name,
        dist_version=str(dist_version),
        dist_location=str(dist_location),
        entrypoints_console_scripts=sorted(eps_console, key=lambda x: x["name"])[:200],
        entrypoints_all=sorted(eps_all, key=lambda x: (x["group"], x["name"]))[:600],
        cli_agno_help=cli1,
        cli_python_m_agno_help=cli2,
    )

    out_path.write_text(json.dumps(asdict(snap), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("WROTE:", out_path)
    print("agno_version:", snap.agno_version)
    print("console_scripts:", len(snap.entrypoints_console_scripts))
    print("submodules:", len(snap.agno_submodules))
    print("agno_cli_rc:", snap.cli_agno_help.get("rc"))
    print("python_-m_agno_rc:", snap.cli_python_m_agno_help.get("rc"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
