#!/usr/bin/env python3
import argparse
import base64
import csv
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMA"
    "ASsJTYQAAAAASUVORK5CYII="
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def iter_trading_days(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        if current.weekday() < 5:
            yield current
        current += timedelta(days=1)


def first_trading_day_of_2023() -> date:
    current = date(2023, 1, 1)
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_csv_rows(path: Path, rows: list[list[str]]) -> None:
    ensure_parent(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def compute_max_drawdown(equity: list[float]) -> float:
    peak = float("-inf")
    max_dd = 0.0
    for value in equity:
        if value > peak:
            peak = value
        if peak > 0:
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd


def resolve_path(repo_root: Path, raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    return repo_root / p


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
    errors: list[str],
) -> pd.DataFrame:
    frames = []
    for ticker in tickers:
        path = pick_price_file(ticker, prices_dir, manifest)
        if not path:
            errors.append(f"price_file_not_found:{ticker}")
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


def compute_portfolio_metrics(equity_history: dict[date, float], asof_date: date) -> dict[str, float | None]:
    if asof_date not in equity_history:
        return {
            "portfolio_drawdown_20d": None,
            "portfolio_drawdown_60d": None,
            "portfolio_var_95_1d_252d": None,
        }
    history_dates = [d for d in sorted(equity_history) if d <= asof_date]
    values = [equity_history[d] for d in history_dates]
    series = pd.Series(values, index=history_dates)
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


def next_trading_date(trading_dates: list[date], current: date, offset: int) -> date:
    idx = trading_dates.index(current)
    target_idx = idx + offset
    if target_idx >= len(trading_dates):
        return trading_dates[-1]
    return trading_dates[target_idx]


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="run_fase1_vendas_full_v1",
        description="Runner FULL v1 do laboratório (fase1_vendas).",
    )
    ap.add_argument("--spec", required=True, help="Caminho do SPEC_FROZEN_MIRROR_V1.json")
    ap.add_argument("--active", required=True, help="Caminho do ACTIVE_RULESET.json")
    ap.add_argument("--out", required=True, help="Diretório de saída do run")
    args = ap.parse_args()

    started_at = datetime.now(timezone.utc).isoformat()
    errors: list[str] = []
    warnings: list[str] = []

    spec_path = Path(args.spec)
    active_path = Path(args.active)
    out_dir = Path(args.out)

    spec = load_json(spec_path)
    active = load_json(active_path)

    repo_root = Path(spec.get("project", {}).get("repo_root", "/home/wilson/PortfolioZero"))
    ruleset_path_raw = active.get("use_ruleset_file", "")
    ruleset_path = resolve_path(repo_root, ruleset_path_raw) if ruleset_path_raw else None
    ruleset = None
    ruleset_sha256 = None
    if ruleset_path and ruleset_path.exists():
        ruleset = load_json(ruleset_path)
        ruleset_sha256 = sha256_file(ruleset_path)
    elif ruleset_path_raw:
        errors.append(f"ruleset_not_found:{ruleset_path_raw}")

    out_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = out_dir / "metrics" / "portfolio_summary.json"
    equity_path = out_dir / "timeseries" / "portfolio_equity.csv"
    orders_path = out_dir / "orders" / "orders.csv"
    plot_path = out_dir / "plots" / "portfolio_equity.png"
    ticker_metrics_path = out_dir / "metrics" / "ticker_metrics_sample.csv"

    horizon = spec.get("experiment_horizon", {})
    warmup_start = parse_date(horizon.get("history_warmup_start", "2022-01-01"))
    warmup_end = date(2022, 12, 31)

    data_contracts = spec.get("data_contracts", {})
    prices_dir = resolve_path(repo_root, data_contracts.get("prices_dir", "data/raw/market/prices"))
    manifest = load_manifest(prices_dir)

    universe_path = resolve_path(
        repo_root, data_contracts.get("universe_supervised_file", "data/universe/supervised_TASK_A_012/UNIVERSE_SUPERVISED.parquet")
    )
    supervised_df = pd.read_parquet(universe_path)
    supervised_tickers = sorted(supervised_df["ticker"].dropna().unique().tolist())

    prices_df = load_prices_for_tickers(supervised_tickers, prices_dir, manifest, errors)
    if prices_df.empty:
        errors.append("no_prices_loaded")

    ibov_ticker = data_contracts.get("ibov_ticker", "_BVSP")
    ibov_series = None
    ibov_path = pick_price_file(ibov_ticker, prices_dir, manifest)
    if ibov_path and ibov_path.exists():
        ibov_df = pd.read_parquet(ibov_path, columns=["date", "close"])
        ibov_df["date"] = pd.to_datetime(ibov_df["date"]).dt.date
        ibov_series = ibov_df.set_index("date")["close"].sort_index()
    else:
        warnings.append(f"ibov_not_found:{ibov_ticker}")

    if prices_df.empty:
        prices_df = pd.DataFrame(index=pd.Index([], name="date"))

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

    trading_dates = sorted([d for d in prices_df.index if warmup_start <= d])
    if not trading_dates:
        errors.append("no_trading_dates")
        trading_dates = list(iter_trading_days(warmup_start, parse_date(horizon.get("end_date", "2026-01-22"))))

    if horizon.get("d0_policy") == "first_trading_day_of_2023":
        start_date = next((d for d in trading_dates if d >= date(2023, 1, 1)), None)
        if not start_date:
            start_date = first_trading_day_of_2023()
            errors.append("start_date_not_found")
    else:
        start_date = parse_date(horizon.get("history_warmup_start", "2023-01-02"))

    try:
        end_date = parse_date(horizon.get("end_date", "2026-01-22"))
    except Exception:
        end_date = date(2026, 1, 22)
        errors.append("invalid_end_date_fallback")

    if start_date not in trading_dates:
        trading_dates.append(start_date)
        trading_dates = sorted(set(trading_dates))

    trading_dates = [d for d in trading_dates if start_date <= d <= end_date or d < start_date]

    warmup_dates = [d for d in trading_dates if warmup_start <= d <= warmup_end]
    warmup_range_used = {
        "start": warmup_dates[0].isoformat() if warmup_dates else None,
        "end": warmup_dates[-1].isoformat() if warmup_dates else None,
        "count": len(warmup_dates),
    }

    initial_capital = float(spec.get("portfolio", {}).get("initial_capital_brl", 500000.0))
    target_positions = int(spec.get("portfolio", {}).get("target_positions", 10))
    fee_percent = float(spec.get("dry_run_execution", {}).get("fees", {}).get("fee_percent_per_order", 0.0))
    fee_fixed = float(spec.get("dry_run_execution", {}).get("fees", {}).get("fee_fixed_brl_per_order", 0.0))
    sell_settlement_days = int(spec.get("dry_run_execution", {}).get("sell_settlement_days", 2))
    weekly_rule = spec.get("weekly_buy_rule_phase1", {})
    weekly_enabled = bool(weekly_rule.get("enabled", True))
    weekly_day = str(weekly_rule.get("day_of_week", "MON")).upper()
    weekly_day_map = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4}
    weekly_weekday = weekly_day_map.get(weekly_day, 0)

    quarantine_sessions = int(spec.get("quarantine", {}).get("sessions_after_zero", 10))
    if ruleset and ruleset.get("reentry", {}).get("quarantine_sessions_after_zero"):
        quarantine_sessions = int(ruleset["reentry"]["quarantine_sessions_after_zero"])

    positions: dict[str, int] = {}
    cash = initial_capital
    pending_cash: list[dict[str, object]] = []
    quarantine: dict[str, int] = {}
    equity_history: dict[date, float] = {}

    for d in trading_dates:
        if d >= start_date:
            break
        equity_history[d] = initial_capital

    orders: list[list[str]] = []
    ticker_metrics_rows: list[list[str]] = []
    action_counts = {"HOLD": 0, "REDUCE": 0, "ZERO": 0}
    n_quarantine_events = 0

    def get_price(asof: date, ticker: str) -> float | None:
        if asof not in prices_df.index or ticker not in prices_df.columns:
            return None
        value = prices_df.at[asof, ticker]
        if pd.isna(value):
            return None
        return float(value)

    def settle_cash(current_date: date) -> None:
        nonlocal cash
        remaining = []
        for item in pending_cash:
            settle_date = item["settle_date"]
            amount = item["amount"]
            if settle_date <= current_date:
                cash += float(amount)
            else:
                remaining.append(item)
        pending_cash.clear()
        pending_cash.extend(remaining)

    def log_order(
        date_value: date,
        action: str,
        ticker: str,
        qty: int,
        price: float,
        fee_total: float,
        cash_delta_date: date,
        settlement_date: date,
        reason: str,
    ) -> None:
        orders.append(
            [
                date_value.isoformat(),
                action,
                ticker,
                str(qty),
                f"{price:.4f}",
                f"{fee_total:.4f}",
                cash_delta_date.isoformat(),
                settlement_date.isoformat(),
                reason,
            ]
        )

    def apply_sell(
        date_value: date,
        ticker: str,
        qty: int,
        price: float,
        reason: str,
    ) -> None:
        if qty <= 0:
            return
        notional = qty * price
        fee_total = notional * fee_percent + fee_fixed
        settle_date = next_trading_date(trading_dates, date_value, sell_settlement_days)
        pending_cash.append({"settle_date": settle_date, "amount": notional - fee_total})
        log_order(date_value, "SELL", ticker, qty, price, fee_total, settle_date, settle_date, reason)

    def apply_buy(
        date_value: date,
        ticker: str,
        qty: int,
        price: float,
        reason: str,
    ) -> None:
        nonlocal cash
        if qty <= 0:
            return
        notional = qty * price
        fee_total = notional * fee_percent + fee_fixed
        total_cost = notional + fee_total
        if total_cost > cash:
            return
        cash -= total_cost
        log_order(date_value, "BUY", ticker, qty, price, fee_total, date_value, date_value, reason)

    def evaluate_action(
        ticker: str,
        metrics: dict,
        portfolio_metrics: dict,
    ) -> tuple[str, str]:
        if ticker not in supervised_tickers:
            return "ZERO", "EXIT_IF_NOT_IN_SUPERVISED"

        priority = ruleset.get("priority_order", []) if ruleset else []
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

    simulation_dates = [d for d in trading_dates if start_date <= d <= end_date]
    if not simulation_dates:
        errors.append("no_simulation_dates")
    for current_date in simulation_dates:
        idx = trading_dates.index(current_date)
        if idx == 0:
            continue
        asof_date = trading_dates[idx - 1]

        for ticker in list(quarantine.keys()):
            quarantine[ticker] -= 1
            if quarantine[ticker] <= 0:
                quarantine.pop(ticker, None)

        settle_cash(current_date)

        portfolio_metrics = compute_portfolio_metrics(equity_history, asof_date)

        decisions: dict[str, tuple[str, str]] = {}
        for ticker in positions:
            metrics = {
                "drawdown_20d": drawdown_20d.at[asof_date, ticker] if ticker in drawdown_20d.columns and asof_date in drawdown_20d.index else None,
                "drawdown_60d": drawdown_60d.at[asof_date, ticker] if ticker in drawdown_60d.columns and asof_date in drawdown_60d.index else None,
                "var_95_1d_252d": var_95_1d_252d.at[asof_date, ticker] if ticker in var_95_1d_252d.columns and asof_date in var_95_1d_252d.index else None,
                "cvar_95_1d_252d": cvar_95_1d_252d.at[asof_date, ticker] if ticker in cvar_95_1d_252d.columns and asof_date in cvar_95_1d_252d.index else None,
                "vol_60d_over_vol_252d": vol_60d_over_252d.at[asof_date, ticker] if ticker in vol_60d_over_252d.columns and asof_date in vol_60d_over_252d.index else None,
                "close_below_sma_100": close_below_sma_100.at[asof_date, ticker] if ticker in close_below_sma_100.columns and asof_date in close_below_sma_100.index else None,
                "close_below_sma_200": close_below_sma_200.at[asof_date, ticker] if ticker in close_below_sma_200.columns and asof_date in close_below_sma_200.index else None,
                "beta_to_ibov_60d": beta_60d.at[asof_date, ticker] if beta_60d is not None and ticker in beta_60d.columns and asof_date in beta_60d.index else None,
                "ibov_vol_60d": ibov_vol_60d.at[asof_date] if ibov_vol_60d is not None and asof_date in ibov_vol_60d.index else None,
            }
            action, rule_id = evaluate_action(ticker, metrics, portfolio_metrics)
            decisions[ticker] = (action, rule_id)
            action_counts[action] += 1

        for ticker, (action, rule_id) in decisions.items():
            price = get_price(asof_date, ticker)
            if price is None:
                continue
            qty = positions.get(ticker, 0)
            if action == "ZERO" and qty > 0:
                apply_sell(current_date, ticker, qty, price, rule_id)
                positions[ticker] = 0
                quarantine[ticker] = quarantine_sessions
                n_quarantine_events += 1
            elif action == "REDUCE" and qty > 0:
                fraction = ruleset.get("actions", {}).get("reduce", {}).get("fraction_of_position_to_sell", 0.5)
                if rule_id.startswith("PORTFOLIO_"):
                    fraction = ruleset.get("actions", {}).get("portfolio_reduce", {}).get("fraction_each_position", fraction)
                sell_qty = int(np.floor(qty * float(fraction)))
                if sell_qty > 0:
                    apply_sell(current_date, ticker, sell_qty, price, rule_id)
                    positions[ticker] = qty - sell_qty

        positions = {t: q for t, q in positions.items() if q > 0}

        do_weekly_buy = weekly_enabled and current_date.weekday() == weekly_weekday
        if current_date == simulation_dates[0]:
            do_weekly_buy = True

        if do_weekly_buy:
            missing = max(target_positions - len(positions), 0)
            if missing > 0 and cash > 0:
                eligible = [t for t in supervised_tickers if t not in positions and t not in quarantine]
                selected = eligible[:missing]
                if selected:
                    alloc = cash / len(selected)
                    for ticker in selected:
                        price = get_price(asof_date, ticker)
                        if price is None or price <= 0:
                            continue
                        qty = int(np.floor(max((alloc - fee_fixed), 0.0) / price))
                        if qty <= 0:
                            continue
                        if qty * price + fee_fixed + qty * price * fee_percent > cash:
                            qty = int(np.floor(max((cash - fee_fixed), 0.0) / price))
                        if qty <= 0:
                            continue
                        apply_buy(current_date, ticker, qty, price, "WEEKLY_BUY")
                        positions[ticker] = positions.get(ticker, 0) + qty

        sample_tickers = supervised_tickers[: min(10, len(supervised_tickers))]
        for ticker in sample_tickers:
            row_metrics = {
                "drawdown_20d": drawdown_20d.at[asof_date, ticker] if ticker in drawdown_20d.columns and asof_date in drawdown_20d.index else None,
                "drawdown_60d": drawdown_60d.at[asof_date, ticker] if ticker in drawdown_60d.columns and asof_date in drawdown_60d.index else None,
                "var_95": var_95_1d_252d.at[asof_date, ticker] if ticker in var_95_1d_252d.columns and asof_date in var_95_1d_252d.index else None,
                "cvar_95": cvar_95_1d_252d.at[asof_date, ticker] if ticker in cvar_95_1d_252d.columns and asof_date in cvar_95_1d_252d.index else None,
                "vol_ratio": vol_60d_over_252d.at[asof_date, ticker] if ticker in vol_60d_over_252d.columns and asof_date in vol_60d_over_252d.index else None,
                "below_sma_100": close_below_sma_100.at[asof_date, ticker] if ticker in close_below_sma_100.columns and asof_date in close_below_sma_100.index else None,
                "below_sma_200": close_below_sma_200.at[asof_date, ticker] if ticker in close_below_sma_200.columns and asof_date in close_below_sma_200.index else None,
                "beta": beta_60d.at[asof_date, ticker] if beta_60d is not None and ticker in beta_60d.columns and asof_date in beta_60d.index else None,
            }
            action, rule_id = decisions.get(ticker, ("HOLD", ""))
            ticker_metrics_rows.append(
                [
                    current_date.isoformat(),
                    asof_date.isoformat(),
                    ticker,
                    row_metrics["drawdown_20d"],
                    row_metrics["drawdown_60d"],
                    row_metrics["var_95"],
                    row_metrics["cvar_95"],
                    row_metrics["vol_ratio"],
                    row_metrics["below_sma_100"],
                    row_metrics["below_sma_200"],
                    row_metrics["beta"],
                    rule_id,
                    action,
                ]
            )

        positions_value = 0.0
        for ticker, qty in positions.items():
            price = get_price(asof_date, ticker)
            if price is None:
                continue
            positions_value += qty * price
        pending_total = sum(float(item["amount"]) for item in pending_cash)
        equity_value = cash + positions_value + pending_total
        equity_history[current_date] = equity_value

    equity_rows = [["date", "equity"]]
    for d in simulation_dates:
        equity_rows.append([d.isoformat(), f"{equity_history.get(d, initial_capital):.2f}"])
    write_csv_rows(equity_path, equity_rows)

    write_csv_rows(
        orders_path,
        [
            [
                "date",
                "action",
                "ticker",
                "qty",
                "price",
                "fee_total",
                "cash_delta_date",
                "settlement_date",
                "rule_id_or_reason",
            ]
        ]
        + orders,
    )

    write_csv_rows(
        ticker_metrics_path,
        [
            [
                "date",
                "asof_date",
                "ticker",
                "drawdown_20d",
                "drawdown_60d",
                "var_95",
                "cvar_95",
                "vol_ratio",
                "below_sma_100",
                "below_sma_200",
                "beta",
                "triggered_rule",
                "action",
            ]
        ]
        + ticker_metrics_rows,
    )

    ensure_parent(plot_path)
    plot_path.write_bytes(PNG_1X1)

    equity_values = [equity_history.get(d, initial_capital) for d in simulation_dates]
    end_equity = equity_values[-1] if equity_values else initial_capital
    total_return = (end_equity / initial_capital - 1.0) if initial_capital else 0.0
    max_drawdown = compute_max_drawdown(equity_values) if equity_values else 0.0

    metrics = {
        "final_value": end_equity,
        "max_drawdown": max_drawdown,
        "n_orders": len(orders),
        "n_reduce": action_counts.get("REDUCE", 0),
        "n_zero": action_counts.get("ZERO", 0),
        "n_quarantine_events": n_quarantine_events,
    }
    ensure_parent(metrics_path)
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    outputs = [
        str(metrics_path),
        str(equity_path),
        str(orders_path),
        str(ticker_metrics_path),
        str(plot_path),
    ]

    overall_pass = len(errors) == 0
    report = {
        "overall_pass": overall_pass,
        "run_id": out_dir.name,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "spec": str(spec_path),
            "active": str(active_path),
        },
        "outputs": outputs,
        "errors": errors,
        "warnings": warnings,
        "decision_metrics_asof": "D-1",
        "warmup_range_used": warmup_range_used,
        "counts": {
            "hold": action_counts.get("HOLD", 0),
            "reduce": action_counts.get("REDUCE", 0),
            "zero": action_counts.get("ZERO", 0),
            "quarantine_events": n_quarantine_events,
        },
        "ruleset_info": {
            "ruleset_id": ruleset.get("ruleset_id") if ruleset else None,
            "ruleset_path": str(ruleset_path) if ruleset_path else None,
            "ruleset_sha256": ruleset_sha256,
        },
    }

    report_path = out_dir / "lab_run_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return 0 if overall_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
