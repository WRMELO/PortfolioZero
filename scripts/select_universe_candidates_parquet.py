#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable, List, Tuple

def _extract_cols_from_schema_md(text: str) -> List[str]:
    """
    Extrai nomes de colunas de um schema.md.
    Tentativas, em ordem:
      (1) Tabela markdown com colunas (primeira coluna = nome)
      (2) Itens com backticks: `col_name`
    Retorna lista única (ordenada) de nomes.
    """
    cols = set()

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # (1) tentar achar linhas de tabela
    table_lines = [ln for ln in lines if ln.startswith("|") and ln.count("|") >= 2]
    if table_lines:
        # remove separadores tipo |---|---|
        def is_sep(ln: str) -> bool:
            core = ln.strip("|").strip()
            return core and all(ch in "-: " for ch in core)

        for ln in table_lines:
            if is_sep(ln):
                continue
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if not cells:
                continue
            name = cells[0].strip()
            if not name:
                continue
            # pular header comum
            if name.lower() in {"col", "cols", "column", "columns", "field", "name"}:
                continue
            cols.add(name)

    # (2) fallback: backticks
    if not cols:
        for m in re.finditer(r"`([^`]+)`", text):
            token = m.group(1).strip()
            if token and " " not in token:
                cols.add(token)

    return sorted(cols)

def _parquet_columns_and_num_rows(p: Path) -> Tuple[List[str], int]:
    # Preferir pyarrow (schema rápido) se existir
    try:
        import pyarrow.parquet as pq  # type: ignore
        pf = pq.ParquetFile(str(p))
        cols = pf.schema.names
        nrows = pf.metadata.num_rows if pf.metadata is not None else -1
        return list(cols), int(nrows)
    except Exception:
        pass

    # Fallback pandas
    import pandas as pd  # type: ignore
    df = pd.read_parquet(p)
    return list(df.columns), int(len(df))

def _is_candidate_parquet(p: Path, required_cols: List[str]) -> Tuple[bool, str]:
    try:
        cols, nrows = _parquet_columns_and_num_rows(p)
    except Exception as e:
        return False, f"READ_FAIL: {e}"

    missing = [c for c in required_cols if c not in cols]
    if missing:
        return False, f"MISSING_COLS({len(missing)}): {missing[:12]}"
    if nrows == 0:
        return False, "ZERO_ROWS"
    return True, f"OK cols={len(cols)} rows={nrows}"

def newest_ok_candidate(universe_dir: Path, required_cols: List[str]) -> Tuple[Path | None, List[Tuple[Path, str]]]:
    """
    Varre .parquet em universe_dir (recursivo) e retorna o mais novo que passa no schema.
    Também retorna diagnósticos de cada parquet lido.
    """
    diags: List[Tuple[Path, str]] = []
    candidates: List[Tuple[float, Path]] = []
    for p in universe_dir.rglob("*.parquet"):
        ok, msg = _is_candidate_parquet(p, required_cols)
        diags.append((p, msg))
        if ok:
            try:
                candidates.append((p.stat().st_mtime, p))
            except OSError:
                pass
    if not candidates:
        return None, diags
    candidates.sort(key=lambda t: t[0])
    return candidates[-1][1], diags

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe-dir", required=True)
    ap.add_argument("--schema-md", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    universe_dir = Path(args.universe_dir)
    schema_md = Path(args.schema_md)
    out_path = Path(args.out)

    if not schema_md.exists():
        print(f"ERROR: schema-md não encontrado: {schema_md}")
        return 2
    if not universe_dir.exists():
        print(f"ERROR: universe-dir não encontrado: {universe_dir}")
        return 2

    schema_text = schema_md.read_text(encoding="utf-8", errors="replace")
    required_cols = _extract_cols_from_schema_md(schema_text)
    if not required_cols:
        print("ERROR: não consegui extrair colunas do schema.md")
        return 2

    chosen, diags = newest_ok_candidate(universe_dir, required_cols)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"SCHEMA_MD: {schema_md}")
    print(f"REQUIRED_COLS_COUNT: {len(required_cols)}")
    print(f"UNIVERSE_DIR: {universe_dir}")
    print("PARQUET_DIAGNOSTICS (top 40):")
    for p, msg in diags[:40]:
        print(f"- {p}: {msg}")

    if chosen is None:
        out_path.write_text("", encoding="utf-8")
        print("ERROR: nenhum parquet em data/universe passou na validação de candidates (schema).")
        return 2

    out_path.write_text(str(chosen), encoding="utf-8")
    print(f"CHOSEN_CANDIDATES_PARQUET: {chosen}")
    print(f"WROTE: {out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
