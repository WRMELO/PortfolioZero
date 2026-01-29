#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import pandas as pd


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def to_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.date


def run_gates(run_dir: Path, initial_cash: float, max_final_multiple: float) -> tuple[bool, dict]:
    equity_path = run_dir / "timeseries" / "portfolio_equity.csv"
    orders_path = run_dir / "orders" / "orders.csv"
    positions_path = run_dir / "timeseries" / "positions_eod.csv"
    cash_path = run_dir / "timeseries" / "cash_eod.csv"

    equity = pd.read_csv(equity_path)
    equity["date"] = to_date(equity["date"])
    equity = equity.sort_values("date")
    equity_vals = equity["equity"].astype(float)

    orders = pd.read_csv(orders_path)
    orders["date"] = to_date(orders["date"])

    positions = pd.read_csv(positions_path) if positions_path.exists() else pd.DataFrame()
    if not positions.empty:
        positions["date"] = to_date(positions["date"])
        positions["qty"] = pd.to_numeric(positions["qty"], errors="coerce").fillna(0.0)

    cash = pd.read_csv(cash_path) if cash_path.exists() else pd.DataFrame()
    if not cash.empty:
        cash["date"] = to_date(cash["date"])
        cash["cash"] = pd.to_numeric(cash["cash"], errors="coerce").fillna(0.0)

    gate1_neg_pos = False
    neg_pos_rows = pd.DataFrame()
    if not positions.empty:
        neg_pos_rows = positions[positions["qty"] < 0].head(20)
        gate1_neg_pos = not neg_pos_rows.empty

    gate2_sell_gt_pos = False
    sell_gt_rows = pd.DataFrame()
    if not positions.empty and "qty" in orders.columns:
        orders["qty"] = pd.to_numeric(orders["qty"], errors="coerce").fillna(0.0)
        for _, o in orders.iterrows():
            if o.get("action") != "SELL":
                continue
            pos = positions[(positions["date"] == o["date"]) & (positions["ticker"] == o["ticker"])]
            if not pos.empty and o["qty"] > float(pos["qty"].iloc[0]):
                sell_gt_rows = pd.concat([sell_gt_rows, o.to_frame().T], ignore_index=True)
                if len(sell_gt_rows) >= 20:
                    break
        gate2_sell_gt_pos = not sell_gt_rows.empty

    gate3_cash_neg = False
    cash_neg_rows = pd.DataFrame()
    if not cash.empty:
        cash_neg_rows = cash[cash["cash"] < 0].head(20)
        gate3_cash_neg = not cash_neg_rows.empty

    gate4_buy_over_cash = False
    buy_over_rows = pd.DataFrame()
    if not cash.empty and "qty" in orders.columns and "price" in orders.columns:
        orders["qty"] = pd.to_numeric(orders["qty"], errors="coerce").fillna(0.0)
        orders["price"] = pd.to_numeric(orders["price"], errors="coerce").fillna(0.0)
        orders["fee_total"] = pd.to_numeric(orders.get("fee_total", 0), errors="coerce").fillna(0.0)
        orders["notional"] = (orders["qty"].abs() * orders["price"]).astype(float)
        daily_buy_cost = (
            orders[orders["action"] == "BUY"]
            .groupby("date")[["notional", "fee_total"]]
            .sum()
            .assign(total_cost=lambda d: d["notional"] + d["fee_total"])
        )
        cash_map = dict(zip(cash["date"], cash["cash"]))
        for _, o in orders.iterrows():
            if o.get("action") != "BUY":
                continue
            available = cash_map.get(o["date"])
            if available is None:
                continue
            total_buy_cost = float(daily_buy_cost.loc[o["date"], "total_cost"]) if o["date"] in daily_buy_cost.index else 0.0
            available_before = float(available) + total_buy_cost
            if float(o["notional"] + o["fee_total"]) > available_before:
                buy_over_rows = pd.concat([buy_over_rows, o.to_frame().T], ignore_index=True)
                if len(buy_over_rows) >= 20:
                    break
        gate4_buy_over_cash = not buy_over_rows.empty

    gate5_final_multiple = float(equity_vals.iloc[-1]) > initial_cash * max_final_multiple
    first_excess_date = None
    for d, v in zip(equity["date"], equity_vals):
        if v > initial_cash * max_final_multiple:
            first_excess_date = d
            break

    passed = not any([gate1_neg_pos, gate2_sell_gt_pos, gate3_cash_neg, gate4_buy_over_cash, gate5_final_multiple])
    details = {
        "gate1_negative_positions": gate1_neg_pos,
        "gate2_sell_gt_position": gate2_sell_gt_pos,
        "gate3_cash_negative": gate3_cash_neg,
        "gate4_buy_over_cash": gate4_buy_over_cash,
        "gate5_final_multiple": gate5_final_multiple,
        "first_excess_date": str(first_excess_date) if first_excess_date else "",
        "neg_pos_samples": neg_pos_rows.to_dict(orient="records") if gate1_neg_pos else [],
        "sell_gt_samples": sell_gt_rows.to_dict(orient="records") if gate2_sell_gt_pos else [],
        "cash_neg_samples": cash_neg_rows.to_dict(orient="records") if gate3_cash_neg else [],
        "buy_over_samples": buy_over_rows.to_dict(orient="records") if gate4_buy_over_cash else [],
    }
    return passed, details


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="econ_gates_lv_f1_011",
        description="Gates economicos (cash-only, sem short).",
    )
    ap.add_argument(
        "--sweep-root",
        default="0_desenvolvimentos/lab_experimentos/fase1_vendas/outputs/sweep_5_rulesets_v2",
    )
    ap.add_argument("--initial-cash", type=float, default=500000.0)
    ap.add_argument("--max-final-multiple", type=float, default=100.0)
    args = ap.parse_args()

    sweep_root = Path(args.sweep_root)
    diagnosis_dir = sweep_root / "diagnosis"
    diagnosis_dir.mkdir(parents=True, exist_ok=True)

    ruleset_dirs = sorted([p for p in sweep_root.iterdir() if p.is_dir() and p.name.startswith("SELL_RULESET_")])
    rows = []
    any_fail = False
    for run_dir in ruleset_dirs:
        passed, details = run_gates(run_dir, args.initial_cash, args.max_final_multiple)
        any_fail = any_fail or not passed
        rows.append(
            {
                "ruleset_id": run_dir.name,
                "passed": passed,
                **{k: v for k, v in details.items() if k.startswith("gate")},
                "first_excess_date": details.get("first_excess_date", ""),
            }
        )
        (diagnosis_dir / f"econ_gates_{run_dir.name}.json").write_text(
            json.dumps(details, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )

    summary_path = diagnosis_dir / "diagnosis_summary.csv"
    pd.DataFrame(rows).to_csv(summary_path, index=False)

    return 0 if not any_fail else 2


if __name__ == "__main__":
    raise SystemExit(main())
