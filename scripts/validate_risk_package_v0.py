#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_TOP = [
    "version",
    "generated_at_utc",
    "source_supervised_parquet",
    "universe",
    "portfolio_constraints",
    "risk_limits",
]


REQUIRED_CONSTRAINTS = [
    "capital_brl",
    "long_only",
    "target_positions",
    "min_positions",
    "max_positions",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    args = ap.parse_args()

    p = Path(args.in_path)
    if not p.exists():
        print(f"ERROR: arquivo não existe: {p}")
        return 2

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR: json inválido: {e}")
        return 2

    for k in REQUIRED_TOP:
        if k not in data:
            print(f"ERROR: missing top field: {k}")
            return 2

    pc = data.get("portfolio_constraints", {})
    for k in REQUIRED_CONSTRAINTS:
        if k not in pc:
            print(f"ERROR: missing portfolio_constraints field: {k}")
            return 2

    universe = data.get("universe", [])
    if not isinstance(universe, list) or len(universe) == 0:
        print("ERROR: universe vazio ou inválido")
        return 2

    # validações simples de coerência
    if pc["min_positions"] > pc["target_positions"] or pc["target_positions"] > pc["max_positions"]:
        print("ERROR: incoerência em min/target/max positions")
        return 2

    if pc["long_only"] is not True:
        print("ERROR: long_only deve ser true no v0")
        return 2

    print("OK: risk package v0 válido")
    print(f"UNIVERSE_COUNT: {len(universe)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
