#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Tuple, List

def _parquet_num_rows(p: Path) -> int:
    try:
        import pyarrow.parquet as pq  # type: ignore
        pf = pq.ParquetFile(str(p))
        return int(pf.metadata.num_rows) if pf.metadata is not None else -1
    except Exception:
        pass
    import pandas as pd  # type: ignore
    df = pd.read_parquet(p)
    return int(len(df))

def newest_parquet(root: Path) -> Path | None:
    items: List[Tuple[float, int, Path]] = []
    for p in root.rglob("*.parquet"):
        try:
            st = p.stat()
            items.append((st.st_mtime, st.st_size, p))
        except OSError:
            pass
    if not items:
        return None
    items.sort(key=lambda t: (t[0], t[1]))
    return items[-1][2]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--supervised-dir", required=True)
    ap.add_argument("--min", type=int, required=True)
    ap.add_argument("--max", type=int, required=True)
    args = ap.parse_args()

    root = Path(args.supervised_dir)
    if not root.exists():
        print(f"ERROR: supervised-dir não existe: {root}")
        return 2

    latest = newest_parquet(root)
    if latest is None:
        print(f"ERROR: nenhum .parquet encontrado em {root}")
        return 2

    n = _parquet_num_rows(latest)
    print(f"SUPERVISED_DIR: {root}")
    print(f"LATEST_PARQUET: {latest}")
    print(f"ROWS: {n}")

    if n < args.min or n > args.max:
        print(f"ERROR: rows fora do intervalo [{args.min}, {args.max}]")
        return 2

    print("OK: supervised output dentro do intervalo.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
