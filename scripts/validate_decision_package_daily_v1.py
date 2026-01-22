#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_TOP = ["version", "generated_at_utc", "inputs", "decisions", "summary"]
ALLOWED_ACTIONS = {"HOLD", "EXIT", "REDUCE"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    args = ap.parse_args()

    p = Path(args.in_path)
    if not p.exists():
        print(f"ERROR: arquivo não existe: {p}")
        return 2

    data = json.loads(p.read_text(encoding="utf-8"))
    for k in REQUIRED_TOP:
        if k not in data:
            print(f"ERROR: missing field: {k}")
            return 2

    dec = data.get("decisions", [])
    if not isinstance(dec, list) or len(dec) == 0:
        print("ERROR: decisions vazio")
        return 2

    for i, item in enumerate(dec[:2000]):
        if "ticker" not in item or "action" not in item or "reason" not in item:
            print(f"ERROR: decision item inválido no índice {i}")
            return 2
        if item["action"] not in ALLOWED_ACTIONS:
            print(f"ERROR: action inválida no índice {i}: {item['action']}")
            return 2

    print("OK: decision package daily v1 válido")
    print(f"DECISIONS_COUNT: {len(dec)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
