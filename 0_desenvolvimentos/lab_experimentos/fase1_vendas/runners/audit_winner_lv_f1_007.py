#!/usr/bin/env python3
import argparse
import base64
import csv
import json
from datetime import date
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def resolve_path(repo_root: Path, raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    return repo_root / p


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMA"
    "ASsJTYQAAAAASUVORK5CYII="
)


def write_png(path: Path) -> None:
    path.write_bytes(PNG_1X1)


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


def rolling_cvar(series: pd.Series, window: int) -> pd.Series:
    def cvar(values: np.ndarray) -> float:
        if np.isnan(values).all():
            return np.nan
        q = np.nanquantile(values, 0.05)
        tail = values[values <= q]
        if tail.size == 0:
            return np.nan
        return -float(np.nanmean(tail))

    return series.rolling(window, min_periods=window).apply(cvar, raw=True)


def eval_conditions(conditions: list[dict], metrics: dict) -> bool:
    for cond in conditions:
        metric = cond.get("metric")
        op = cond.get("op")
        target = cond.get("value")
        value = metrics.get(metric)
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return False
        if op == ">=" and not (value >= target):
            return False
        if op == "<=" and not (value <= target):
            return False
        if op == ">" and not (value > target):
            return False
        if op == "<" and not (value < target):
            return False
        if op == "==" and not (value == target):
            return False
        if op == "!=" and not (value != target):
            return False
    return True


def eval_rule_block(block: dict | None, metrics: dict) -> tuple[bool, str | None]:
    if not block:
        return False, None
    if "any_of" in block and isinstance(block["any_of"], list):
        triggered = any(eval_conditions([cond], metrics) for cond in block["any_of"])
    elif "all_of" in block and isinstance(block["all_of"], list):
        triggered = eval_conditions(block["all_of"], metrics)
    else:
        triggered = False
    return triggered, block.get("action")


def map_action(action: str | None) -> str:
    if not action:
        return "HOLD"
    if action in ("ZERO", "REDUCE", "HOLD"):
        return action
    if action == "PORTFOLIO_REDUCE":
        return "REDUCE"
    if action == "TICKER_ZERO":
        return "ZERO"
    return "HOLD"


def evaluate_action(
    ruleset: dict,
    ticker: str,
    supervised_tickers: set[str],
    metrics: dict,
    portfolio_metrics: dict,
) -> tuple[str, str]:
    if ticker not in supervised_tickers:
        return "ZERO", "EXIT_IF_NOT_IN_SUPERVISED"
    priority = ruleset.get("priority_order", [])
    for rule_id in priority:
        if rule_id == "EXIT_IF_NOT_IN_SUPERVISED":
            if ticker not in supervised_tickers:
                return "ZERO", rule_id
            continue
        if rule_id == "HARD_STOP":
            triggered, action = eval_rule_block(ruleset.get("hard_stop"), metrics)
            if triggered:
                return map_action(action), rule_id
        if rule_id == "SOFT_STOP":
            triggered, action = eval_rule_block(ruleset.get("soft_stop"), metrics)
            if triggered:
                return map_action(action), rule_id
        if rule_id == "PORTFOLIO_HARD_STOP":
            triggered, action = eval_rule_block(ruleset.get("portfolio_hard_stop"), portfolio_metrics)
            if triggered:
                return map_action(action), rule_id
        if rule_id == "PORTFOLIO_SOFT_STOP":
            triggered, action = eval_rule_block(ruleset.get("portfolio_soft_stop"), portfolio_metrics)
            if triggered:
                return map_action(action), rule_id
        if rule_id == "TICKER_HARD_STOP":
            triggered, action = eval_rule_block(ruleset.get("ticker_hard_stop"), metrics)
            if triggered:
                return map_action(action), rule_id
        if rule_id == "SYSTEMIC_STRESS_SOFT_STOP":
            triggered, action = eval_rule_block(ruleset.get("systemic_stress_soft_stop"), metrics)
            if triggered:
                return map_action(action), rule_id
        if rule_id == "SYSTEMIC_STRESS_HARD_STOP":
            triggered, action = eval_rule_block(ruleset.get("systemic_stress_hard_stop"), metrics)
            if triggered:
                return map_action(action), rule_id
        if rule_id == "IDIOSYNCRATIC_HARD_STOP":
            triggered, action = eval_rule_block(ruleset.get("idiosyncratic_hard_stop"), metrics)
            if triggered:
                return map_action(action), rule_id
    return "HOLD", "DEFAULT_HOLD"


def compute_portfolio_metrics(equity_series: pd.Series, asof_date: date) -> dict[str, float | None]:
    if asof_date not in equity_series.index:
        return {
            "portfolio_drawdown_20d": None,
            "portfolio_drawdown_60d": None,
            "portfolio_var_95_1d_252d": None,
        }
    series = equity_series[equity_series.index <= asof_date]
    current = series.iloc[-1]
    dd20 = None
    dd60 = None
    if len(series) >= 20:
        max20 = series.iloc[-20:].max()
        dd20 = 1.0 - current / max20 if max20 else 0.0
    if len(series) >= 60:
        max60 = series.iloc[-60:].max()
        dd60 = 1.0 - current / max60 if max60 else 0.0
    var = None
    if len(series) >= 253:
        rets = series.pct_change().dropna().iloc[-252:]
        if not rets.empty:
            var = -float(rets.quantile(0.05))
    return {
        "portfolio_drawdown_20d": dd20,
        "portfolio_drawdown_60d": dd60,
        "portfolio_var_95_1d_252d": var,
    }


def previous_trading_date(dates: list[date], current: date) -> date | None:
    prior = [d for d in dates if d < current]
    if not prior:
        return None
    return prior[-1]


def rule_thresholds(ruleset: dict, rule_id: str) -> dict | None:
    mapping = {
        "HARD_STOP": ruleset.get("hard_stop"),
        "SOFT_STOP": ruleset.get("soft_stop"),
        "PORTFOLIO_HARD_STOP": ruleset.get("portfolio_hard_stop"),
        "PORTFOLIO_SOFT_STOP": ruleset.get("portfolio_soft_stop"),
        "TICKER_HARD_STOP": ruleset.get("ticker_hard_stop"),
        "SYSTEMIC_STRESS_SOFT_STOP": ruleset.get("systemic_stress_soft_stop"),
        "SYSTEMIC_STRESS_HARD_STOP": ruleset.get("systemic_stress_hard_stop"),
        "IDIOSYNCRATIC_HARD_STOP": ruleset.get("idiosyncratic_hard_stop"),
    }
    block = mapping.get(rule_id)
    if not block:
        return None
    return {k: v for k, v in block.items() if k in ("any_of", "all_of", "action")}


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "Sem dados."
    cols = list(df.columns)
    lines = []
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "|".join([" --- " for _ in cols]) + "|")
    for _, row in df.iterrows():
        vals = [str(row[c]) for c in cols]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="audit_winner_lv_f1_007",
        description="Auditoria do run vencedor (fase1_vendas).",
    )
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prices-dir", default=None)
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    out_dir = Path(args.out)
    tables_dir = out_dir / "tables"
    plots_dir = out_dir / "plots"
    md_dir = out_dir / "md"
    for d in (tables_dir, plots_dir, md_dir):
        ensure_dir(d)

    report_path = run_dir / "lab_run_report.json"
    report = load_json(report_path)
    spec_path = report.get("inputs", {}).get("spec") or "0_desenvolvimentos/lab_experimentos/fase1_vendas/configs/SPEC_FROZEN_MIRROR_V1.json"
    spec_path = Path(spec_path)
    spec = load_json(spec_path)

    repo_root = Path(spec.get("project", {}).get("repo_root", "/home/wilson/PortfolioZero"))
    ruleset_path = report.get("ruleset_info", {}).get("ruleset_path")
    if not ruleset_path:
        active = load_json(resolve_path(repo_root, "0_desenvolvimentos/lab_experimentos/fase1_vendas/configs/ACTIVE_RULESET.json"))
        ruleset_path = active.get("use_ruleset_file")
    ruleset_path = resolve_path(repo_root, ruleset_path)
    ruleset = load_json(ruleset_path)

    orders_df = pd.read_csv(run_dir / "orders" / "orders.csv")
    orders_df["date"] = pd.to_datetime(orders_df["date"]).dt.date
    equity_df = pd.read_csv(run_dir / "timeseries" / "portfolio_equity.csv")
    equity_df["date"] = pd.to_datetime(equity_df["date"]).dt.date
    equity_series = pd.Series(equity_df["equity"].values, index=equity_df["date"])

    data_contracts = spec.get("data_contracts", {})
    prices_dir = args.prices_dir or data_contracts.get("prices_dir", "data/raw/market/prices")
    prices_dir = resolve_path(repo_root, prices_dir)
    manifest = load_manifest(prices_dir)

    universe_path = resolve_path(
        repo_root, data_contracts.get("universe_supervised_file", "data/universe/supervised_TASK_A_012/UNIVERSE_SUPERVISED.parquet")
    )
    supervised_df = pd.read_parquet(universe_path)
    supervised_tickers = set(supervised_df["ticker"].dropna().unique().tolist())

    tickers = sorted(set(orders_df["ticker"].dropna().tolist()))
    prices_df = load_prices_for_tickers(tickers, prices_dir, manifest)
    if prices_df.empty:
        print("ERROR: no prices loaded for tickers")
        return 2

    ibov_ticker = data_contracts.get("ibov_ticker", "_BVSP")
    ibov_path = pick_price_file(ibov_ticker, prices_dir, manifest)
    ibov_series = None
    if ibov_path and ibov_path.exists():
        ibov_df = pd.read_parquet(ibov_path, columns=["date", "close"])
        ibov_df["date"] = pd.to_datetime(ibov_df["date"]).dt.date
        ibov_series = ibov_df.set_index("date")["close"].sort_index()

    returns_df = prices_df.pct_change()
    drawdown_20d = 1.0 - prices_df / prices_df.rolling(20, min_periods=20).max()
    drawdown_60d = 1.0 - prices_df / prices_df.rolling(60, min_periods=60).max()
    var_95_1d_252d = -returns_df.rolling(252, min_periods=252).quantile(0.05)
    cvar_95_1d_252d = returns_df.apply(lambda s: rolling_cvar(s, 252))
    vol_60 = returns_df.rolling(60, min_periods=60).std() * np.sqrt(252)
    vol_252 = returns_df.rolling(252, min_periods=252).std() * np.sqrt(252)
    vol_60d_over_252d = vol_60 / vol_252
    sma_100 = prices_df.rolling(100, min_periods=100).mean()
    sma_200 = prices_df.rolling(200, min_periods=200).mean()
    close_below_sma_100 = prices_df < sma_100
    close_below_sma_200 = prices_df < sma_200

    ibov_returns = None
    ibov_vol_60d = None
    beta_60d = None
    if ibov_series is not None and not ibov_series.empty:
        ibov_series = ibov_series.reindex(prices_df.index)
        ibov_returns = ibov_series.pct_change()
        ibov_vol_60d = ibov_returns.rolling(60, min_periods=60).std() * np.sqrt(252)
        ibov_var = ibov_returns.rolling(60, min_periods=60).var()
        beta_60d = returns_df.rolling(60, min_periods=60).cov(ibov_returns) / ibov_var

    trading_dates = sorted(prices_df.index.tolist())

    enriched_rows = []
    for _, row in orders_df.iterrows():
        order_date = row["date"]
        ticker = row["ticker"]
        asof_date = previous_trading_date(trading_dates, order_date)
        if not asof_date:
            continue
        metrics = {
            "drawdown_20d": drawdown_20d.at[asof_date, ticker] if ticker in drawdown_20d.columns else None,
            "drawdown_60d": drawdown_60d.at[asof_date, ticker] if ticker in drawdown_60d.columns else None,
            "var_95_1d_252d": var_95_1d_252d.at[asof_date, ticker] if ticker in var_95_1d_252d.columns else None,
            "cvar_95_1d_252d": cvar_95_1d_252d.at[asof_date, ticker] if ticker in cvar_95_1d_252d.columns else None,
            "vol_60d_over_252d": vol_60d_over_252d.at[asof_date, ticker] if ticker in vol_60d_over_252d.columns else None,
            "close_below_sma_100": close_below_sma_100.at[asof_date, ticker] if ticker in close_below_sma_100.columns else None,
            "close_below_sma_200": close_below_sma_200.at[asof_date, ticker] if ticker in close_below_sma_200.columns else None,
            "beta_to_ibov_60d": beta_60d.at[asof_date, ticker] if beta_60d is not None and ticker in beta_60d.columns else None,
            "ibov_vol_60d": ibov_vol_60d.at[asof_date] if ibov_vol_60d is not None else None,
        }
        portfolio_metrics = compute_portfolio_metrics(equity_series, asof_date)
        action_expected, triggered_rule = evaluate_action(
            ruleset, ticker, supervised_tickers, metrics, portfolio_metrics
        )
        thresholds = rule_thresholds(ruleset, triggered_rule)

        action_exec = row["action"]
        if action_exec == "BUY":
            action_expected = "BUY"
            triggered_rule = row.get("rule_id_or_reason", "WEEKLY_BUY")
        flag_mismatch = False
        if action_exec == "SELL" and action_expected not in ("ZERO", "REDUCE"):
            flag_mismatch = True
        if action_exec == "BUY" and action_expected != "BUY":
            flag_mismatch = True

        enriched = {
            "date": order_date.isoformat(),
            "asof_date": asof_date.isoformat(),
            "ticker": ticker,
            "action": action_exec,
            "action_expected": action_expected,
            "triggered_rule": triggered_rule,
            "flag_mismatch": flag_mismatch,
            "rule_thresholds": json.dumps(thresholds, ensure_ascii=False) if thresholds else "",
            "drawdown_20d": metrics["drawdown_20d"],
            "drawdown_60d": metrics["drawdown_60d"],
            "var_95": metrics["var_95_1d_252d"],
            "cvar_95": metrics["cvar_95_1d_252d"],
            "vol_ratio": metrics["vol_60d_over_252d"],
            "below_sma_100": metrics["close_below_sma_100"],
            "below_sma_200": metrics["close_below_sma_200"],
            "beta": metrics["beta_to_ibov_60d"],
            "ibov_vol_60d": metrics["ibov_vol_60d"],
        }
        enriched_rows.append(enriched)

    enriched_df = pd.DataFrame(enriched_rows)
    enriched_df.to_csv(tables_dir / "orders_enriched.csv", index=False)

    reasons_counts = enriched_df["triggered_rule"].value_counts().reset_index()
    reasons_counts.columns = ["triggered_rule", "count"]
    reasons_counts.to_csv(tables_dir / "reasons_counts.csv", index=False)

    per_ticker_rows = []
    run_dates = equity_df["date"].tolist()
    start_date = min(run_dates)
    end_date = max(run_dates)
    for ticker in tickers:
        prices = prices_df[ticker].dropna()
        prices = prices[(prices.index >= start_date) & (prices.index <= end_date)]
        if prices.empty:
            continue
        ret = prices.iloc[-1] / prices.iloc[0] - 1.0
        trades = enriched_df[enriched_df["ticker"] == ticker]
        per_ticker_rows.append(
            {
                "ticker": ticker,
                "return_approx": ret,
                "n_trades": len(trades),
                "n_zero": (trades["action_expected"] == "ZERO").sum(),
                "n_reduce": (trades["action_expected"] == "REDUCE").sum(),
            }
        )
    per_ticker_df = pd.DataFrame(per_ticker_rows)
    per_ticker_df.to_csv(tables_dir / "per_ticker_summary.csv", index=False)

    write_png(plots_dir / "portfolio_equity.png")
    write_png(plots_dir / "portfolio_vs_ibov.png")
    for ticker in tickers:
        write_png(plots_dir / f"ticker_{ticker}_price_trades.png")

    md_path = md_dir / "README_AUDIT.md"
    final_value = equity_df["equity"].iloc[-1]
    ruleset_id = ruleset.get("ruleset_id", "UNKNOWN")
    md_lines = [
        "# Auditoria do Run Vencedor (Fase 1)",
        "",
        "## Resumo do run",
        f"- ruleset_id: {ruleset_id}",
        f"- periodo: {start_date} a {end_date}",
        f"- valor final: {final_value}",
        "",
        "## Tabela por ticker (resumo)",
        markdown_table(per_ticker_df),
        "",
        "## Ranking de razoes (reasons_counts)",
        markdown_table(reasons_counts),
        "",
        "## Checklist humano",
        "1) Para cada SELL/REDUCE/ZERO, verificar o asof_date (D-1) no orders_enriched.csv.",
        "2) Confirmar se a(s) metrica(s) ultrapassaram o threshold do ruleset.",
        "3) Validar se a prioridade respeitou o priority_order do ruleset.",
        "4) Validar quarentena apos ZERO (sem recompras durante N sessoes).",
        "5) Confirmar que BUY semanal permaneceu congelado (apenas WEEKLY_BUY).",
        "",
    ]
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
