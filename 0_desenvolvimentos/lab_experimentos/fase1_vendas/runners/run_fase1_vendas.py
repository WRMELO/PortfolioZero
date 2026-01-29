#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="run_fase1_vendas",
        description="Runner mínimo do laboratório (fase1_vendas).",
    )
    ap.add_argument("--spec", required=True, help="Caminho do SPEC_FROZEN_MIRROR_V1.json")
    ap.add_argument("--active", required=True, help="Caminho do ACTIVE_RULESET.json")
    ap.add_argument("--out", required=True, help="Diretório de saída do run")
    args = ap.parse_args()

    spec_path = Path(args.spec)
    active_path = Path(args.active)
    out_dir = Path(args.out)

    spec = load_json(spec_path)
    active = load_json(active_path)

    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "lab_run_report.json"
    report = {
        "runner": "run_fase1_vendas",
        "status": "OK",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "spec_path": str(spec_path),
            "active_ruleset_path": str(active_path),
        },
        "active_ruleset": active,
        "spec_summary": {
            "project": spec.get("project", {}),
            "experiment_horizon": spec.get("experiment_horizon", {}),
        },
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
