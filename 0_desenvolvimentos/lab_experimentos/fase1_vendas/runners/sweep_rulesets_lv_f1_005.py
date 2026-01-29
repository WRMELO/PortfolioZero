#!/usr/bin/env python3
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_repo_root(spec_path: Path) -> Path:
    spec = load_json(spec_path)
    repo_root = spec.get("project", {}).get("repo_root", "/home/wilson/PortfolioZero")
    return Path(repo_root)


def rel_to_repo(repo_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def write_active_tmp(path: Path, ruleset_path: str) -> None:
    path.write_text(json.dumps({"use_ruleset_file": ruleset_path}, indent=2), encoding="utf-8")


def run_ruleset(
    repo_root: Path,
    runner_path: Path,
    spec_path: Path,
    ruleset_path: Path,
    out_dir: Path,
) -> tuple[bool, dict | None, dict | None]:
    out_dir.mkdir(parents=True, exist_ok=True)
    active_tmp = out_dir / "active_tmp.json"
    write_active_tmp(active_tmp, rel_to_repo(repo_root, ruleset_path))
    cmd = [
        sys.executable,
        str(runner_path),
        "--spec",
        str(spec_path),
        "--active",
        str(active_tmp),
        "--out",
        str(out_dir),
    ]
    result = subprocess.run(cmd, cwd=str(repo_root))
    if result.returncode != 0:
        return False, None, None
    report_path = out_dir / "lab_run_report.json"
    metrics_path = out_dir / "metrics" / "portfolio_summary.json"
    if not report_path.exists() or not metrics_path.exists():
        return False, None, None
    report = load_json(report_path)
    metrics = load_json(metrics_path)
    return bool(report.get("overall_pass", False)), report, metrics


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="sweep_rulesets_lv_f1_005",
        description="Executa sweep dos 5 rulesets e gera sumario.",
    )
    ap.add_argument("--spec", required=True)
    ap.add_argument("--runner", required=True)
    ap.add_argument("--rulesets-dir", required=True)
    ap.add_argument("--out-root", required=True)
    args = ap.parse_args()

    spec_path = Path(args.spec)
    runner_path = Path(args.runner)
    rulesets_dir = Path(args.rulesets_dir)
    out_root = Path(args.out_root)

    repo_root = resolve_repo_root(spec_path)

    ruleset_files = sorted(rulesets_dir.glob("SELL_RULESET_*.json"))
    if len(ruleset_files) < 5:
        print("ERROR: expected 5 rulesets, found", len(ruleset_files))
        return 2

    rows = []
    all_ok = True
    for ruleset_path in ruleset_files:
        ruleset_id = ruleset_path.stem
        out_dir = out_root / ruleset_id
        ok, report, metrics = run_ruleset(repo_root, runner_path, spec_path, ruleset_path, out_dir)
        if not ok or not report or not metrics:
            print(f"ERROR: ruleset {ruleset_id} failed")
            all_ok = False
            break
        rows.append(
            {
                "ruleset_id": ruleset_id,
                "run_id": report.get("run_id"),
                "output_path": str(out_dir),
                "final_value": metrics.get("final_value"),
                "max_drawdown": metrics.get("max_drawdown"),
                "n_orders": metrics.get("n_orders"),
                "n_reduce": metrics.get("n_reduce"),
                "n_zero": metrics.get("n_zero"),
                "n_quarantine_events": metrics.get("n_quarantine_events"),
            }
        )

    summary_csv = out_root / "summary_rulesets.csv"
    summary_md = out_root / "summary_rulesets.md"

    out_root.mkdir(parents=True, exist_ok=True)
    with summary_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "ruleset_id",
                "run_id",
                "output_path",
                "final_value",
                "max_drawdown",
                "n_orders",
                "n_reduce",
                "n_zero",
                "n_quarantine_events",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    with summary_md.open("w", encoding="utf-8") as f:
        f.write("| ruleset_id | final_value | max_drawdown | n_orders | n_reduce | n_zero | n_quarantine_events | output_path | run_id |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
        for row in rows:
            f.write(
                f"| {row['ruleset_id']} | {row['final_value']} | {row['max_drawdown']} | "
                f"{row['n_orders']} | {row['n_reduce']} | {row['n_zero']} | "
                f"{row['n_quarantine_events']} | {row['output_path']} | {row['run_id']} |\n"
            )

    return 0 if all_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
