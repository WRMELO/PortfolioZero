#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


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


def read_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def read_parquet(path: Path):
    import pandas as pd  # type: ignore
    return pd.read_parquet(path)


def extract_universe(df) -> Tuple[List[str], str]:
    cols = list(df.columns)
    for c in POSSIBLE_TICKER_COLS:
        if c in cols:
            vals = df[c].astype(str).tolist()
            seen = set()
            out = []
            for v in vals:
                if v not in seen:
                    seen.add(v)
                    out.append(v)
            return out, c
    idx_vals = [str(x) for x in df.index.tolist()]
    seen = set()
    out = []
    for v in idx_vals:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out, "__index__"


@dataclass
class DecisionItem:
    ticker: str
    action: str  # HOLD | EXIT | REDUCE
    reason: str


@dataclass
class DecisionPackageDailyV1:
    version: str
    generated_at_utc: str
    inputs: Dict[str, Any]
    decisions: List[DecisionItem]
    summary: Dict[str, Any]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--risk", required=True)
    ap.add_argument("--supervised-dir", required=True)
    ap.add_argument("--portfolio", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    risk_p = Path(args.risk)
    sup_dir = Path(args.supervised_dir)
    port_p = Path(args.portfolio)
    out_p = Path(args.out)

    if not risk_p.exists():
        print(f"ERROR: risk file not found: {risk_p}")
        return 2
    if not port_p.exists():
        print(f"ERROR: portfolio snapshot not found: {port_p}")
        return 2
    if not sup_dir.exists():
        print(f"ERROR: supervised-dir not found: {sup_dir}")
        return 2

    sup_parquet = newest_parquet(sup_dir)
    if sup_parquet is None:
        print(f"ERROR: no supervised parquet in: {sup_dir}")
        return 2

    risk = read_json(risk_p)
    portfolio = read_json(port_p)
    df = read_parquet(sup_parquet)
    universe, field_used = extract_universe(df)
    universe_set = set(universe)

    decisions: List[DecisionItem] = []
    exits = 0
    holds = 0

    for pos in portfolio.get("positions", []):
        t = str(pos.get("ticker"))
        if t in universe_set:
            decisions.append(DecisionItem(ticker=t, action="HOLD", reason="ticker presente no universo supervisionado"))
            holds += 1
        else:
            decisions.append(DecisionItem(ticker=t, action="EXIT", reason="ticker fora do universo supervisionado (sell-only)"))
            exits += 1

    pkg = DecisionPackageDailyV1(
        version="v1",
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        inputs={
            "risk_package": str(risk_p),
            "portfolio_snapshot": str(port_p),
            "supervised_parquet": str(sup_parquet),
            "universe_ticker_field": field_used
        },
        decisions=decisions,
        summary={
            "positions_total": len(decisions),
            "holds": holds,
            "exits": exits,
            "reduces": 0,
            "note": "v1 sell-only: EXIT quando fora do universo; HOLD quando dentro. REDUCE será adicionado quando houver limites explícitos."
        }
    )

    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(asdict(pkg), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: wrote {out_p} holds={holds} exits={exits}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
