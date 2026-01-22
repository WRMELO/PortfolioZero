#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


POSSIBLE_TICKER_COLS = ("ticker", "symbol", "asset", "code", "papel")


def newest_parquet(root: Path) -> Path | None:
    items: List[Tuple[float, int, Path]] = []
    for p in root.rglob("*.parquet"):
        try:
            st = p.stat()
            items.append((st.st_mtime, st.st_size, p))
        except OSError:
            continue
    if not items:
        return None
    items.sort(key=lambda t: (t[0], t[1]))
    return items[-1][2]


def read_parquet(path: Path):
    try:
        import pandas as pd  # type: ignore
    except Exception as e:
        raise RuntimeError(f"pandas não disponível para ler parquet: {e}")
    return pd.read_parquet(path)


def extract_universe(df) -> Tuple[List[str], str]:
    cols = list(df.columns)
    for c in POSSIBLE_TICKER_COLS:
        if c in cols:
            vals = df[c].astype(str).tolist()
            # únicos preservando ordem
            seen = set()
            out = []
            for v in vals:
                if v not in seen:
                    seen.add(v)
                    out.append(v)
            return out, c
    # fallback: usa índice como “id”
    idx_vals = [str(x) for x in df.index.tolist()]
    seen = set()
    out = []
    for v in idx_vals:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out, "__index__"


@dataclass
class PortfolioConstraints:
    capital_brl: int
    long_only: bool
    target_positions: int
    min_positions: int
    max_positions: int


@dataclass
class RiskPackageV0:
    version: str
    generated_at_utc: str
    source_supervised_parquet: str
    source_row_count: int
    source_columns: List[str]
    ticker_field_used: str
    universe: List[str]
    portfolio_constraints: PortfolioConstraints
    risk_limits: Dict[str, Any]
    notes: List[str]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--supervised-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--capital-brl", type=int, required=True)
    ap.add_argument("--target-positions", type=int, required=True)
    ap.add_argument("--min-positions", type=int, required=True)
    ap.add_argument("--max-positions", type=int, required=True)
    args = ap.parse_args()

    supervised_dir = Path(args.supervised_dir)
    out_path = Path(args.out)

    if not supervised_dir.exists():
        print(f"ERROR: supervised-dir não existe: {supervised_dir}")
        return 2

    pqt = newest_parquet(supervised_dir)
    if pqt is None:
        print(f"ERROR: nenhum parquet encontrado em: {supervised_dir}")
        return 2

    df = read_parquet(pqt)
    universe, field_used = extract_universe(df)

    generated_at = datetime.now(timezone.utc).isoformat()

    pkg = RiskPackageV0(
        version="v0",
        generated_at_utc=generated_at,
        source_supervised_parquet=str(pqt),
        source_row_count=int(len(df)),
        source_columns=[str(c) for c in df.columns],
        ticker_field_used=field_used,
        universe=universe,
        portfolio_constraints=PortfolioConstraints(
            capital_brl=int(args.capital_brl),
            long_only=True,
            target_positions=int(args.target_positions),
            min_positions=int(args.min_positions),
            max_positions=int(args.max_positions),
        ),
        # v0: não inventa thresholds. Campos ficam null e serão preenchidos quando o plano explicitar.
        risk_limits={
            "max_gross_exposure_pct": None,
            "max_position_weight_pct": None,
            "max_sector_weight_pct": None,
            "max_drawdown_hard_stop_pct": None,
            "cooldown_days_after_exit": None
        },
        notes=[
            "Risk Package v0 é declarativo e auditável; não impõe thresholds numéricos sem definição explícita no plano.",
            "Os limits null devem ser preenchidos em versões futuras quando os critérios forem consolidados."
        ],
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(asdict(pkg), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("OK: risk package gerado")
    print(f"OUT: {out_path}")
    print(f"SOURCE: {pqt}")
    print(f"UNIVERSE_COUNT: {len(universe)} (field={field_used})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
