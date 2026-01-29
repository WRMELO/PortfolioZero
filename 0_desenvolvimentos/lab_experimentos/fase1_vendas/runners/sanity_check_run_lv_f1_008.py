#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(repo_root: Path, raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    return repo_root / p


def load_manifest(prices_dir: Path) -> dict:
    manifest_path = prices_dir / "manifest_prices.json"
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8")).get("entries", {})


def pick_price_file(ticker: str, prices_dir: Path, manifest: dict) -> Path | None:
    if ticker in manifest:
        return Path(manifest[ticker]["file"])
    candidate = prices_dir / f"{ticker.replace('.', '_')}.parquet"
    if candidate.exists():
        return candidate
    return None


def load_prices_for_tickers(
    tickers: list[str],
    prices_dir: Path,
    manifest: dict,
) -> pd.DataFrame:
    frames = []
    for ticker in tickers:
        path = pick_price_file(ticker, prices_dir, manifest)
        if not path:
            continue
        df = pd.read_parquet(path, columns=["date", "close", "ticker"])
        df["date"] = pd.to_datetime(df["date"]).dt.date
        frames.append(df[["date", "ticker", "close"]])
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    prices_df = combined.pivot(index="date", columns="ticker", values="close").sort_index()
    return prices_df


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="sanity_check_run_lv_f1_008",
        description="Sanity checks contabeis do run vencedor.",
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
    ap.add_argument(
        "--equity-explosion-multiplier",
        type=float,
        default=1e12,
        help="Multiplicador para detectar explosao de equity.",
    )
    args = ap.parse_args()

    run_root = Path(args.run_root)
    audit_root = Path(args.audit_root)
    audit_root.mkdir(parents=True, exist_ok=True)

    report_path = run_root / "lab_run_report.json"
    report = load_json(report_path)
    spec_path = report.get("inputs", {}).get("spec") or "0_desenvolvimentos/lab_experimentos/fase1_vendas/configs/SPEC_FROZEN_MIRROR_V1.json"
    spec = load_json(Path(spec_path))
    repo_root = Path(spec.get("project", {}).get("repo_root", "/home/wilson/PortfolioZero"))
    initial_cash = float(spec.get("portfolio", {}).get("initial_capital_brl", 500000.0))

    equity_path = run_root / "timeseries" / "portfolio_equity.csv"
    orders_path = run_root / "orders" / "orders.csv"
    equity_df = pd.read_csv(equity_path)
    equity_df["date"] = pd.to_datetime(equity_df["date"]).dt.date
    orders_df = pd.read_csv(orders_path)
    orders_df["date"] = pd.to_datetime(orders_df["date"]).dt.date

    # equity stats
    equity_values = equity_df["equity"].astype(float)
    equity_stats = {
        "min": float(equity_values.min()),
        "max": float(equity_values.max()),
        "median": float(equity_values.median()),
    }
    equity_exploded = equity_stats["max"] > args.equity_explosion_multiplier * initial_cash

    # prices sanity
    data_contracts = spec.get("data_contracts", {})
    prices_dir = resolve_path(repo_root, data_contracts.get("prices_dir", "data/raw/market/prices"))
    manifest = load_manifest(prices_dir)
    tickers = sorted(orders_df["ticker"].dropna().unique().tolist())
    prices_df = load_prices_for_tickers(tickers, prices_dir, manifest)
    price_alerts = []
    if not prices_df.empty:
        for ticker in tickers:
            if ticker not in prices_df.columns:
                continue
            series = prices_df[ticker].dropna()
            if series.empty:
                continue
            pmin = float(series.min())
            pmax = float(series.max())
            if pmax > 1e6 or pmin <= 0:
                price_alerts.append({"ticker": ticker, "min": pmin, "max": pmax})

    # notional sanity
    orders_df["qty"] = pd.to_numeric(orders_df["qty"], errors="coerce").fillna(0.0)
    orders_df["price"] = pd.to_numeric(orders_df["price"], errors="coerce").fillna(0.0)
    orders_df["notional"] = (orders_df["qty"].abs() * orders_df["price"]).astype(float)
    top_trades = orders_df.sort_values("notional", ascending=False).head(20)
    top_trades_path = audit_root / "tables" / "top_trades_by_notional.csv"
    top_trades_path.parent.mkdir(parents=True, exist_ok=True)
    top_trades.to_csv(top_trades_path, index=False)

    # notional vs equity (same day)
    equity_map = dict(zip(equity_df["date"], equity_df["equity"]))
    leverage_flags = []
    for _, row in orders_df.iterrows():
        eq = equity_map.get(row["date"])
        if eq is None or eq == 0:
            continue
        if row["notional"] > 10.0 * float(eq):
            leverage_flags.append(
                {
                    "date": str(row["date"]),
                    "ticker": row["ticker"],
                    "action": row["action"],
                    "notional": row["notional"],
                    "equity": float(eq),
                }
            )

    # cashflow (if fee_total exists)
    cashflow_df = None
    if "fee_total" in orders_df.columns:
        orders_df["fee_total"] = pd.to_numeric(orders_df["fee_total"], errors="coerce").fillna(0.0)
        orders_df["cashflow_signed"] = 0.0
        buy_mask = orders_df["action"] == "BUY"
        sell_mask = orders_df["action"] == "SELL"
        orders_df.loc[buy_mask, "cashflow_signed"] = -(orders_df.loc[buy_mask, "notional"] + orders_df.loc[buy_mask, "fee_total"])
        orders_df.loc[sell_mask, "cashflow_signed"] = orders_df.loc[sell_mask, "notional"] - orders_df.loc[sell_mask, "fee_total"]
        cashflow_df = orders_df.sort_values("cashflow_signed", ascending=False).head(20)
        cashflow_path = audit_root / "tables" / "top_trades_by_cashflow.csv"
        cashflow_df.to_csv(cashflow_path, index=False)

    # turnover
    total_buy = float(orders_df.loc[orders_df["action"] == "BUY", "notional"].sum())
    total_sell = float(orders_df.loc[orders_df["action"] == "SELL", "notional"].sum())
    avg_equity = float(equity_values.mean())
    turnover_ratio = (total_buy + total_sell) / avg_equity if avg_equity else float("nan")

    sanity = {
        "equity_stats": equity_stats,
        "equity_exploded": equity_exploded,
        "equity_explosion_threshold": args.equity_explosion_multiplier * initial_cash,
        "price_alerts": price_alerts,
        "leverage_flags": leverage_flags,
        "turnover": {
            "total_notional_buy": total_buy,
            "total_notional_sell": total_sell,
            "avg_equity": avg_equity,
            "turnover_ratio": turnover_ratio,
        },
    }

    report_path = audit_root / "tables" / "sanity_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(sanity, ensure_ascii=False, indent=2), encoding="utf-8")

    notes_path = audit_root / "md" / "SANITY_NOTES.md"
    notes_path.parent.mkdir(parents=True, exist_ok=True)
    notes = [
        "# Sanity Notes",
        f"- equity_min: {equity_stats['min']}",
        f"- equity_max: {equity_stats['max']}",
        f"- equity_median: {equity_stats['median']}",
        f"- equity_exploded: {equity_exploded}",
        f"- price_alerts: {len(price_alerts)}",
        f"- leverage_flags: {len(leverage_flags)}",
        f"- turnover_ratio: {turnover_ratio}",
    ]
    notes_path.write_text("\n".join(notes), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
