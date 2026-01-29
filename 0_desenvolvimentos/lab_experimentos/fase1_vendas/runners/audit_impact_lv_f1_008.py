#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="audit_impact_lv_f1_008",
        description="Enriquece orders_enriched com impacto (qty/price/notional/cashflow).",
    )
    ap.add_argument(
        "--run-root",
        default="0_desenvolvimentos/lab_experimentos/fase1_vendas/outputs/run_winner_final",
        help="Diretorio do run vencedor.",
    )
    ap.add_argument(
        "--audit-root",
        default="0_desenvolvimentos/lab_experimentos/fase1_vendas/outputs/run_winner_final/audit",
        help="Diretorio do audit.",
    )
    args = ap.parse_args()

    run_root = Path(args.run_root)
    audit_root = Path(args.audit_root)

    orders_path = run_root / "orders" / "orders.csv"
    enriched_path = audit_root / "tables" / "orders_enriched.csv"
    if not orders_path.exists() or not enriched_path.exists():
        raise SystemExit("orders.csv ou orders_enriched.csv nao encontrado.")

    orders = pd.read_csv(orders_path)
    enriched = pd.read_csv(enriched_path)

    for df in (orders, enriched):
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["ticker"] = df["ticker"].astype(str)
        df["action"] = df["action"].astype(str)

    orders["group_idx"] = orders.groupby(["date", "ticker", "action"]).cumcount()
    enriched["group_idx"] = enriched.groupby(["date", "ticker", "action"]).cumcount()

    merged = enriched.merge(
        orders,
        on=["date", "ticker", "action", "group_idx"],
        how="left",
        suffixes=("", "_order"),
    )

    # prefer columns from orders.csv
    qty = merged.get("qty")
    price = merged.get("price")
    fee_total = merged.get("fee_total")
    if qty is None and "quantity" in merged.columns:
        qty = merged["quantity"]
    if qty is None:
        qty = 0
    if price is None:
        price = 0
    if fee_total is None:
        fee_total = 0

    merged["qty"] = pd.to_numeric(qty, errors="coerce").fillna(0).astype(int)
    merged["price"] = pd.to_numeric(price, errors="coerce").fillna(0.0)
    merged["fee_total"] = pd.to_numeric(fee_total, errors="coerce").fillna(0.0)
    merged["notional"] = (merged["qty"].abs() * merged["price"]).astype(float)
    merged["side"] = merged["action"].where(merged["action"].isin(["BUY", "SELL"]), "")
    if "settlement_date" in merged.columns:
        merged["settlement_date"] = merged["settlement_date"].astype(str)
    if "cash_delta_date" in merged.columns:
        merged["cash_delta_date"] = merged["cash_delta_date"].astype(str)

    # cashflow signed: negative for BUY on D, positive for SELL on D+2
    merged["cashflow_signed"] = 0.0
    buy_mask = merged["action"] == "BUY"
    sell_mask = merged["action"] == "SELL"
    merged.loc[buy_mask, "cashflow_signed"] = -(merged.loc[buy_mask, "notional"] + merged.loc[buy_mask, "fee_total"])
    merged.loc[sell_mask, "cashflow_signed"] = merged.loc[sell_mask, "notional"] - merged.loc[sell_mask, "fee_total"]

    out_path = audit_root / "tables" / "orders_enriched_with_impact.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged.drop(columns=["group_idx"], errors="ignore").to_csv(out_path, index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
