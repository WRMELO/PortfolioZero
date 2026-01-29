#!/usr/bin/env python3
import argparse
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd


def to_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.date


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def window_dates(center: date, delta_days: int) -> tuple[date, date]:
    return center - timedelta(days=delta_days), center + timedelta(days=delta_days)


def top_orders_by_proxy(orders: pd.DataFrame, limit: int = 30) -> pd.DataFrame:
    if "qty" in orders.columns and "price" in orders.columns:
        orders["qty"] = pd.to_numeric(orders["qty"], errors="coerce").fillna(0.0)
        orders["price"] = pd.to_numeric(orders["price"], errors="coerce").fillna(0.0)
        orders["notional"] = (orders["qty"].abs() * orders["price"]).astype(float)
        return orders.sort_values("notional", ascending=False).head(limit)
    if "fee_total" in orders.columns:
        orders["fee_total"] = pd.to_numeric(orders["fee_total"], errors="coerce").fillna(0.0)
        return orders.assign(notional_proxy=orders["fee_total"].abs()).sort_values(
            "notional_proxy", ascending=False
        ).head(limit)
    return orders.head(limit)


def detect_negative_positions(orders: pd.DataFrame) -> pd.DataFrame:
    if "qty" not in orders.columns:
        return pd.DataFrame()
    orders = orders.copy()
    orders["qty"] = pd.to_numeric(orders["qty"], errors="coerce").fillna(0.0)
    orders["signed_qty"] = orders["qty"]
    orders.loc[orders["action"] == "SELL", "signed_qty"] *= -1.0
    orders = orders.sort_values(["ticker", "date"])
    orders["cum_qty"] = orders.groupby("ticker")["signed_qty"].cumsum()
    return orders[orders["cum_qty"] < 0].head(5)


def detect_duplicate_settlement(orders: pd.DataFrame) -> pd.DataFrame:
    if "settlement_date" not in orders.columns:
        return pd.DataFrame()
    subset = ["ticker", "qty", "price", "settlement_date", "action"]
    dup = orders[orders.duplicated(subset=subset, keep=False)]
    return dup.head(5)


def detect_price_anomalies(orders: pd.DataFrame, min_price: float, max_price: float) -> pd.DataFrame:
    if "price" not in orders.columns:
        return pd.DataFrame()
    price = pd.to_numeric(orders["price"], errors="coerce").fillna(0.0)
    bad = orders[(price <= min_price) | (price > max_price)]
    return bad.head(5)


def detect_notional_vs_equity(orders: pd.DataFrame, equity_map: dict, multiple: float) -> pd.DataFrame:
    if "qty" not in orders.columns or "price" not in orders.columns:
        return pd.DataFrame()
    orders = orders.copy()
    orders["qty"] = pd.to_numeric(orders["qty"], errors="coerce").fillna(0.0)
    orders["price"] = pd.to_numeric(orders["price"], errors="coerce").fillna(0.0)
    orders["notional"] = (orders["qty"].abs() * orders["price"]).astype(float)
    candidates = []
    for _, row in orders.iterrows():
        if row.get("action") != "BUY":
            continue
        eq = equity_map.get(row["date"])
        if eq and row["notional"] > eq * multiple:
            candidates.append(row)
    return pd.DataFrame(candidates).head(5)


def detect_buy_cashflow_mismatch(orders: pd.DataFrame) -> pd.DataFrame:
    if "cash_delta_date" not in orders.columns:
        return pd.DataFrame()
    bad = orders[(orders["action"] == "BUY") & (orders["cash_delta_date"] != orders["date"])]
    return bad.head(5)


def probable_cause(flags: dict) -> tuple[str, float]:
    ordered = [
        ("PRICE_SCALE", flags.get("price_anomaly", 0)),
        ("DUP_SETTLEMENT", flags.get("duplicate_settlement", 0)),
        ("NEGATIVE_POS", flags.get("negative_positions", 0)),
        ("NOTIONAL_GT_EQUITY", flags.get("notional_vs_equity", 0)),
        ("BUY_CASHFLOW_MISMATCH", flags.get("buy_cashflow", 0)),
    ]
    ordered = [item for item in ordered if item[1] > 0]
    if not ordered:
        return ("UNKNOWN", 0.2)
    top = max(ordered, key=lambda x: x[1])
    confidence = 0.7 if top[1] >= 5 else 0.5
    return (top[0], confidence)


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="root_cause_lv_f1_010",
        description="Root cause por ruleset com evidencias.",
    )
    ap.add_argument(
        "--diag-root",
        default="0_desenvolvimentos/lab_experimentos/fase1_vendas/outputs/sweep_5_rulesets/diagnosis",
    )
    ap.add_argument(
        "--sweep-root",
        default="0_desenvolvimentos/lab_experimentos/fase1_vendas/outputs/sweep_5_rulesets",
    )
    ap.add_argument("--initial-cash", type=float, default=500000.0)
    ap.add_argument("--final-multiple", type=float, default=100.0)
    ap.add_argument("--min-price", type=float, default=0.0001)
    ap.add_argument("--max-price", type=float, default=1000000.0)
    ap.add_argument("--max-notional-multiple", type=float, default=1.10)
    ap.add_argument(
        "--rulesets",
        nargs="+",
        default=["SELL_RULESET_01", "SELL_RULESET_03", "SELL_RULESET_04", "SELL_RULESET_05"],
    )
    ap.add_argument("--control", default="SELL_RULESET_02")
    args = ap.parse_args()

    diag_root = Path(args.diag_root)
    sweep_root = Path(args.sweep_root)
    diag_root.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    to_process = list(args.rulesets) + [args.control]

    for ruleset_id in to_process:
        run_dir = sweep_root / ruleset_id
        report_path = run_dir / "lab_run_report.json"
        if not report_path.exists():
            continue

        equity_path = run_dir / "timeseries" / "portfolio_equity.csv"
        orders_path = run_dir / "orders" / "orders.csv"
        equity = pd.read_csv(equity_path)
        orders = pd.read_csv(orders_path)
        equity["date"] = to_date(equity["date"])
        orders["date"] = to_date(orders["date"])

        equity = equity.sort_values("date")
        equity_values = equity["equity"].astype(float).tolist()
        equity_dates = equity["date"].tolist()

        threshold = args.initial_cash * args.final_multiple
        first_explosion_date = None
        for d, v in zip(equity_dates, equity_values):
            if v > threshold:
                first_explosion_date = d
                break

        jumps_rel = [
            (equity_values[i] / equity_values[i - 1] if equity_values[i - 1] else float("inf"))
            for i in range(1, len(equity_values))
        ]
        max_jump_idx = int(max(range(len(jumps_rel)), key=lambda i: jumps_rel[i])) if jumps_rel else -1
        max_jump_date = equity_dates[max_jump_idx + 1] if max_jump_idx >= 0 else None

        if max_jump_date:
            d0, d1 = window_dates(max_jump_date, 5)
            snippet_orders = orders[(orders["date"] >= d0) & (orders["date"] <= d1)]
            snippet_equity = equity[(equity["date"] >= max_jump_date - timedelta(days=10)) & (equity["date"] <= max_jump_date + timedelta(days=10))]
            snippet_orders.to_csv(diag_root / f"snippets_{ruleset_id}_orders_around_event.csv", index=False)
            snippet_equity.to_csv(diag_root / f"snippets_{ruleset_id}_equity_around_event.csv", index=False)

        top_orders = top_orders_by_proxy(orders, 30)

        equity_map = dict(zip(equity_dates, equity_values))
        checks = {
            "buy_cashflow": detect_buy_cashflow_mismatch(orders),
            "duplicate_settlement": detect_duplicate_settlement(orders),
            "negative_positions": detect_negative_positions(orders),
            "price_anomaly": detect_price_anomalies(orders, args.min_price, args.max_price),
            "notional_vs_equity": detect_notional_vs_equity(orders, equity_map, args.max_notional_multiple),
        }

        flags = {k: len(v) for k, v in checks.items()}
        cause, confidence = probable_cause(flags)

        md_path = diag_root / f"root_cause_{ruleset_id}.md"
        lines = [
            f"Root Cause — {ruleset_id}",
            "",
            f"first_explosion_date: {first_explosion_date}",
            f"max_jump_date: {max_jump_date}",
            "",
            f"probable_cause: {cause}",
            f"confidence: {confidence}",
            "",
            "Top 30 orders (proxy por notional):",
            top_orders.head(10).to_csv(index=False),
            "",
            "Checagens A–E (5 exemplos):",
        ]
        for key, df in checks.items():
            lines.append(f"{key}: {len(df)}")
            if not df.empty:
                lines.append(df.head(5).to_csv(index=False))
        md_path.write_text("\n".join(lines), encoding="utf-8")

        summary_rows.append(
            {
                "ruleset_id": ruleset_id,
                "first_explosion_date": str(first_explosion_date) if first_explosion_date else "",
                "max_jump_date": str(max_jump_date) if max_jump_date else "",
                "probable_cause": cause,
                "confidence": confidence,
                "root_cause_md": str(md_path),
            }
        )

        # print summary (10 lines) per ruleset
        print(f"[{ruleset_id}] first_explosion_date={first_explosion_date} max_jump_date={max_jump_date}")
        print(f"[{ruleset_id}] probable_cause={cause} confidence={confidence}")
        for key, df in checks.items():
            print(f"[{ruleset_id}] {key} samples={len(df)}")
        print(f"[{ruleset_id}] top_orders_sample_rows={min(5, len(top_orders))}")

    summary_out = diag_root / "root_cause_summary.csv"
    pd.DataFrame(summary_rows).to_csv(summary_out, index=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
