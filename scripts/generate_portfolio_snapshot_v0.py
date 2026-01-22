#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict


@dataclass
class Position:
    ticker: str
    quantity: int
    avg_price: float


@dataclass
class PortfolioSnapshotV0:
    version: str
    generated_at_utc: str
    capital_brl: int
    cash_brl: float
    positions: List[Position]
    notes: List[str]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--capital-brl", type=int, required=True)
    ap.add_argument("--positions", type=int, required=True)
    args = ap.parse_args()

    out_path = Path(args.out)
    n = int(args.positions)
    capital = int(args.capital_brl)

    # v0: carteira fictícia e neutra (sem preço real), apenas para destravar o pipeline
    pos = []
    for i in range(n):
        pos.append(Position(ticker=f"TICKER_{i+1:02d}", quantity=100, avg_price=10.0))

    snap = PortfolioSnapshotV0(
        version="v0",
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        capital_brl=capital,
        cash_brl=float(capital) * 0.0,
        positions=pos,
        notes=[
            "Snapshot v0 sintético para destravar Decision Package sem integração real com corretora/extrato.",
            "Será substituído por snapshot real quando a integração for implementada."
        ],
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(asdict(snap), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: wrote {out_path} positions={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
