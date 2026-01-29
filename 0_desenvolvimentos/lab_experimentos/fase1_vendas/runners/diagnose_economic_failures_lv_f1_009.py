#!/usr/bin/env python3
import argparse
import csv
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def to_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.date


def window_dates(center: date, delta_days: int = 3) -> tuple[date, date]:
    return center - timedelta(days=delta_days), center + timedelta(days=delta_days)


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="diagnose_economic_failures_lv_f1_009",
        description="Diagnostico de falhas economicas nos 5 rulesets.",
    )
    ap.add_argument(
        "--sweep-root",
        default="0_desenvolvimentos/lab_experimentos/fase1_vendas/outputs/sweep_5_rulesets",
    )
    ap.add_argument(
        "--summary-csv",
        default="0_desenvolvimentos/lab_experimentos/fase1_vendas/outputs/sweep_5_rulesets/summary_rulesets.csv",
    )
    ap.add_argument("--initial-cash", type=float, default=500000.0)
    ap.add_argument("--max-final-multiple", type=float, default=100.0)
    ap.add_argument("--max-equity-multiple-any-day", type=float, default=200.0)
    ap.add_argument("--max-daily-jump-multiple", type=float, default=5.0)
    ap.add_argument("--max-price-reasonable", type=float, default=1000000.0)
    ap.add_argument("--min-price-reasonable", type=float, default=0.0001)
    ap.add_argument("--max-notional-to-equity-multiple", type=float, default=1.10)
    args = ap.parse_args()

    sweep_root = Path(args.sweep_root)
    summary_path = Path(args.summary_csv)
    summary = pd.read_csv(summary_path)

    diagnosis_dir = sweep_root / "diagnosis"
    diagnosis_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    any_fail = False
    report_lines = []
    report_lines.append("DIAGNOSTICO ECONOMICO — RULESETS (fase1_vendas)")
    report_lines.append("")

    for _, row in summary.iterrows():
        ruleset_id = row["ruleset_id"]
        run_path = Path(row.get("output_path", sweep_root / ruleset_id))
        if not run_path.is_absolute():
            run_path = sweep_root / ruleset_id

        equity_path = run_path / "timeseries" / "portfolio_equity.csv"
        orders_path = run_path / "orders" / "orders.csv"
        if not equity_path.exists() or not orders_path.exists():
            rows.append(
                {
                    "ruleset_id": ruleset_id,
                    "run_path": str(run_path),
                    "status": "MISSING_FILES",
                }
            )
            any_fail = True
            continue

        equity = pd.read_csv(equity_path)
        equity["date"] = to_date(equity["date"])
        equity = equity.sort_values("date")
        equity_values = equity["equity"].astype(float).tolist()
        equity_dates = equity["date"].tolist()

        equity_min = float(min(equity_values))
        equity_max = float(max(equity_values))
        equity_final = float(equity_values[-1])

        jumps_abs = [abs(equity_values[i] - equity_values[i - 1]) for i in range(1, len(equity_values))]
        jumps_rel = [
            (equity_values[i] / equity_values[i - 1] if equity_values[i - 1] else float("inf"))
            for i in range(1, len(equity_values))
        ]
        max_jump_idx = int(max(range(len(jumps_rel)), key=lambda i: jumps_rel[i])) if jumps_rel else -1
        max_jump_rel = float(jumps_rel[max_jump_idx]) if jumps_rel else 0.0
        max_jump_date = equity_dates[max_jump_idx + 1] if max_jump_idx >= 0 else None

        explosion_threshold_day = args.initial_cash * args.max_equity_multiple_any_day
        explosion_date = None
        for d, v in zip(equity_dates, equity_values):
            if v > explosion_threshold_day:
                explosion_date = d
                break

        orders = pd.read_csv(orders_path)
        orders["date"] = to_date(orders["date"])
        price_fail = False
        if "price" in orders.columns:
            price = pd.to_numeric(orders["price"], errors="coerce")
            price_fail = bool(((price <= args.min_price_reasonable) | (price > args.max_price_reasonable)).any())

        notional_fail = False
        if "qty" in orders.columns and "price" in orders.columns:
            orders["qty"] = pd.to_numeric(orders["qty"], errors="coerce").fillna(0.0)
            orders["price"] = pd.to_numeric(orders["price"], errors="coerce").fillna(0.0)
            orders["notional"] = (orders["qty"].abs() * orders["price"]).astype(float)
            equity_map = dict(zip(equity_dates, equity_values))
            for _, o in orders.iterrows():
                if o.get("action") != "BUY":
                    continue
                eq = equity_map.get(o["date"])
                if eq and o["notional"] > eq * args.max_notional_to_equity_multiple:
                    notional_fail = True
                    break

        duplicate_fail = False
        duplicate_count = 0
        if "settlement_date" in orders.columns and "ticker" in orders.columns and "qty" in orders.columns and "price" in orders.columns:
            dup_cols = ["ticker", "qty", "price", "settlement_date"]
            duplicate_count = int(orders.duplicated(subset=dup_cols).sum())
            duplicate_fail = duplicate_count > 0

        fail_final = equity_final > args.initial_cash * args.max_final_multiple
        fail_any_day = equity_max > explosion_threshold_day
        fail_jump = max_jump_rel > args.max_daily_jump_multiple

        any_fail = any_fail or any([fail_final, fail_any_day, fail_jump, price_fail, notional_fail, duplicate_fail])

        event_date = explosion_date or max_jump_date
        if event_date:
            start, end = window_dates(event_date)
            event_orders = orders[(orders["date"] >= start) & (orders["date"] <= end)].copy()
            event_path = diagnosis_dir / f"events_{ruleset_id}.csv"
            event_orders.to_csv(event_path, index=False)
        else:
            event_path = ""

        rows.append(
            {
                "ruleset_id": ruleset_id,
                "run_path": str(run_path),
                "equity_min": equity_min,
                "equity_max": equity_max,
                "equity_final": equity_final,
                "max_jump_rel": max_jump_rel,
                "max_jump_date": str(max_jump_date) if max_jump_date else "",
                "explosion_date": str(explosion_date) if explosion_date else "",
                "fail_final": fail_final,
                "fail_any_day": fail_any_day,
                "fail_jump": fail_jump,
                "price_fail": price_fail,
                "notional_fail": notional_fail,
                "duplicate_fail": duplicate_fail,
                "duplicate_count": duplicate_count,
                "event_orders_path": str(event_path) if event_date else "",
            }
        )

        report_lines.append(f"Ruleset {ruleset_id}: final={equity_final} max={equity_max} jump={max_jump_rel} fail_any={fail_any_day}")

    summary_out = diagnosis_dir / "diagnosis_summary.csv"
    pd.DataFrame(rows).to_csv(summary_out, index=False)

    report_path = diagnosis_dir / "DIAGNOSIS_REPORT.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    return 2 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
