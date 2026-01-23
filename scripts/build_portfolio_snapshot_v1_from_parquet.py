#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import polars as pl


REQUIRED_CANONICAL = ("ticker", "quantity", "avg_price")

ALIASES = {
    "ticker": {"ticker", "symbol", "asset", "code", "papel"},
    "quantity": {"quantity", "qty", "shares", "qtd", "quantidade"},
    "avg_price": {"avg_price", "average_price", "avg", "price_avg", "preco_medio", "pm"},
}


def norm_col(s: str) -> str:
    return s.strip().lower().replace(" ", "_")


def pick_col(cols_norm: Set[str], wanted: str) -> Optional[str]:
    candidates = ALIASES.get(wanted, {wanted})
    for c in candidates:
        if c in cols_norm:
            return c
    return None


def to_float_strict(x: Any) -> float:
    s = str(x).strip()
    if s == "":
        raise ValueError("empty numeric")
    # suporta 1.234,56 e 1234.56
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    return float(s)


@dataclass
class PositionItem:
    ticker: str
    quantity: float
    avg_price: float


def read_positions_parquet(path: Path) -> Tuple[List[PositionItem], Dict[str, Any]]:
    df = pl.read_parquet(path)

    cols_orig = df.columns
    cols_norm = [norm_col(c) for c in cols_orig]
    mapping = dict(zip(cols_orig, cols_norm))

    # renomeia para nomes normalizados (sem perder o original)
    df = df.rename(mapping)
    cols_set = set(df.columns)

    ct = pick_col(cols_set, "ticker")
    cq = pick_col(cols_set, "quantity")
    ca = pick_col(cols_set, "avg_price")

    missing = [k for k, c in [("ticker", ct), ("quantity", cq), ("avg_price", ca)] if c is None]
    if missing:
        raise ValueError(f"Parquet sem colunas necessarias (ou aliases): {missing}. Colunas_norm={sorted(list(cols_set))}")

    # seleciona e valida
    sub = df.select([pl.col(ct).cast(pl.Utf8), pl.col(cq), pl.col(ca)]).rename(
        {ct: "ticker", cq: "quantity", ca: "avg_price"}
    )

    # converte numericos de forma robusta (suporta string pt-br)
    # Se já for numérico, mantém. Se for string, converte.
    def ensure_float(colname: str) -> pl.Expr:
        return (
            pl.when(pl.col(colname).is_null())
            .then(pl.lit(None))
            .otherwise(pl.col(colname))
            .cast(pl.Utf8)
            .map_elements(to_float_strict, return_dtype=pl.Float64)
        )

    sub = sub.with_columns(
        [
            pl.col("ticker").cast(pl.Utf8).str.strip_chars(),
            ensure_float("quantity").alias("quantity"),
            ensure_float("avg_price").alias("avg_price"),
        ]
    )

    # valida linha a linha (falha dura)
    bad = sub.filter(
        (pl.col("ticker").is_null())
        | (pl.col("ticker") == "")
        | (pl.col("quantity").is_null())
        | (pl.col("avg_price").is_null())
        | (pl.col("quantity") <= 0)
        | (pl.col("avg_price") < 0)
    )
    if bad.height > 0:
        sample = bad.head(10).to_dicts()
        raise ValueError(f"Linhas invalidas no Parquet (sample até 10): {sample} (n_bad={bad.height})")

    # valida duplicidade de ticker (falha dura; não agrego sem ordem explícita sua)
    dup = (
        sub.group_by("ticker")
        .agg(pl.len().alias("n"))
        .filter(pl.col("n") > 1)
    )
    if dup.height > 0:
        sample = dup.head(20).to_dicts()
        raise ValueError(f"Tickers duplicados no Parquet (sample até 20): {sample} (n_dup={dup.height})")

    positions: List[PositionItem] = []
    for row in sub.to_dicts():
        positions.append(
            PositionItem(
                ticker=str(row["ticker"]),
                quantity=float(row["quantity"]),
                avg_price=float(row["avg_price"]),
            )
        )

    meta = {
        "parquet_path": str(path),
        "columns_seen_norm": sorted(list(cols_set)),
        "columns_used_norm": {"ticker": ct, "quantity": cq, "avg_price": ca},
        "positions_read": len(positions),
    }
    return positions, meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-parquet", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--capital-brl", required=True, type=float)
    ap.add_argument("--cash-brl", required=True, type=float)
    ap.add_argument("--notes", required=True)
    args = ap.parse_args()

    in_p = Path(args.in_parquet)
    out_p = Path(args.out)

    if not in_p.exists():
        print(f"ERROR: input Parquet not found: {in_p}")
        return 2

    try:
        positions, _meta = read_positions_parquet(in_p)
    except Exception as e:
        print(f"ERROR: failed to parse positions Parquet: {e}")
        return 2

    # Importante: manter EXATAMENTE as chaves top-level do V0 (sem extras),
    # para não criar ambiguidade de contrato.
    snapshot: Dict[str, Any] = {
        "version": "v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "capital_brl": float(args.capital_brl),
        "cash_brl": float(args.cash_brl),
        "notes": str(args.notes),
        "positions": [asdict(p) for p in positions],
    }

    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: wrote {out_p} positions={len(positions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
