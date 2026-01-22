#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def infer_ticker_column(df: pl.DataFrame) -> str:
    candidates = [c for c in df.columns if c.lower() in ("ticker", "symbol", "asset", "ativo")]
    if candidates:
        return candidates[0]
    # fallback: string column with high cardinality
    str_cols = [c for c, dt in zip(df.columns, df.dtypes) if dt == pl.Utf8]
    if not str_cols:
        raise ValueError("Não encontrei coluna de ticker (nenhuma coluna string).")
    return str_cols[0]


@dataclass
class DecisionPackage:
    contract: str
    generated_at_utc: str
    source_candidates_path: str
    source_supervised_dir: str
    supervised_file: str
    universe_size: int
    universe: list[str]
    actions: list[dict[str, Any]]
    notes: list[str]


def main() -> int:
    ap = argparse.ArgumentParser(description="Gera Decision Package v1 (offline, determinístico) a partir do UNIVERSE_SUPERVISED.")
    ap.add_argument("--supervised-dir", required=True, help="Diretório gerado pelo build_universe_supervised.py (ex: data/universe/supervised_TASK_A_010)")
    ap.add_argument("--candidates-path-file", required=True, help="Arquivo texto contendo path do candidates parquet (ex: planning/runs/TASK_A_010/candidates_path.txt)")
    ap.add_argument("--out", required=True, help="Arquivo JSON de saída (ex: data/decisions/decision_TASK_A_011.json)")
    args = ap.parse_args()

    supervised_dir = Path(args.supervised_dir)
    cand_path_file = Path(args.candidates_path_file)
    out_path = Path(args.out)

    if not supervised_dir.exists():
        raise SystemExit(f"supervised-dir não existe: {supervised_dir}")

    if not cand_path_file.exists():
        raise SystemExit(f"candidates-path-file não existe: {cand_path_file}")

    candidates_path = Path(cand_path_file.read_text(encoding="utf-8").strip())
    if not candidates_path.exists():
        raise SystemExit(f"candidates parquet não encontrado: {candidates_path}")

    # Encontrar parquet principal do supervised (determinístico: pega o maior parquet do dir)
    supervised_parquets = list(supervised_dir.rglob("*.parquet"))
    if not supervised_parquets:
        raise SystemExit(f"nenhum parquet encontrado em supervised-dir: {supervised_dir}")

    supervised_parquets.sort(key=lambda p: (p.stat().st_size, p.stat().st_mtime), reverse=True)
    supervised_file = supervised_parquets[0]

    df = pl.read_parquet(supervised_file)
    ticker_col = infer_ticker_column(df)
    universe = sorted(df.select(pl.col(ticker_col)).unique().to_series().to_list())

    # Decisão v1: HOLD para todos, score determinístico pelo ranking alfabético
    actions = []
    for i, t in enumerate(universe, start=1):
        actions.append(
            {
                "ticker": t,
                "action": "HOLD",
                "score": float(len(universe) - i + 1),
                "rationale": "decision_package_v1: baseline HOLD (no strategy yet)"
            }
        )

    pkg = DecisionPackage(
        contract="decision_package_v1",
        generated_at_utc=utc_now(),
        source_candidates_path=str(candidates_path),
        source_supervised_dir=str(supervised_dir),
        supervised_file=str(supervised_file),
        universe_size=len(universe),
        universe=universe,
        actions=actions,
        notes=[
            "offline_deterministic",
            "no_trading_strategy_applied",
            "actions_are_baseline_hold"
        ],
    )

    write_text(out_path, json.dumps(pkg.__dict__, indent=2, ensure_ascii=False) + "\n")
    print("OK: wrote", out_path)
    print("universe_size =", len(universe))
    print("supervised_file =", supervised_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
