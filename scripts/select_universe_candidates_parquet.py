#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import List, Tuple, Optional


COL_KEYS = ("coluna", "campo", "column", "field", "name")
TYPE_KEYS = ("tipo", "type", "dtype", "datatype", "data type")


def _strip_md(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("`") and s.endswith("`") and len(s) >= 2:
        s = s[1:-1].strip()
    return s


def _is_separator_row(cells: List[str]) -> bool:
    joined = "".join(cells).strip().replace("|", "")
    if not joined:
        return True
    return all(ch in "-: " for ch in joined)


def _parse_markdown_tables(text: str) -> List[List[List[str]]]:
    lines = [ln.rstrip("\n") for ln in text.splitlines()]
    tables: List[List[List[str]]] = []
    current: List[List[str]] = []

    def flush():
        nonlocal current
        if current:
            tables.append(current)
            current = []

    for ln in lines:
        st = ln.strip()
        if st.startswith("|") and st.count("|") >= 2:
            cells = [c.strip() for c in st.strip("|").split("|")]
            current.append(cells)
        else:
            flush()

    flush()
    return tables


def _parquet_columns_and_num_rows(p: Path) -> Tuple[List[str], int]:
    try:
        import pyarrow.parquet as pq  # type: ignore
        pf = pq.ParquetFile(str(p))
        cols = pf.schema.names
        nrows = pf.metadata.num_rows if pf.metadata is not None else -1
        return list(cols), int(nrows)
    except Exception:
        pass

    import pandas as pd  # type: ignore
    df = pd.read_parquet(p)
    return list(df.columns), int(len(df))


def _extract_table_schema_candidates(table: List[List[str]]) -> Optional[dict]:
    """
    Retorna dict com:
      - header
      - col_idx (onde está o nome da coluna)
      - has_type
      - columns (lista extraída)
    ou None se a tabela não parece ser tabela de schema de colunas.
    """
    if len(table) < 2:
        return None

    header = table[0]
    header_n = [_strip_md(c).lower() for c in header]

    col_idx = None
    for key in COL_KEYS:
        if key in header_n:
            col_idx = header_n.index(key)
            break
    if col_idx is None:
        return None

    has_type = any(k in header_n for k in TYPE_KEYS)

    start_row = 1
    if len(table) > 1 and _is_separator_row(table[1]):
        start_row = 2

    cols: List[str] = []
    for row in table[start_row:]:
        if not row or _is_separator_row(row):
            continue
        if col_idx >= len(row):
            continue
        name = _strip_md(row[col_idx])
        if not name:
            continue
        if name.lower() in COL_KEYS:
            continue
        cols.append(name)

    # remove duplicados preservando ordem
    seen = set()
    out = []
    for c in cols:
        if c not in seen:
            seen.add(c)
            out.append(c)

    if not out:
        return None

    return {
        "header": header,
        "col_idx": col_idx,
        "has_type": has_type,
        "columns": out,
    }


def _choose_best_schema_table(schema_text: str, reference_cols: List[str]) -> Tuple[List[str], str]:
    """
    Escolhe a tabela cujo conjunto de colunas tem maior overlap com reference_cols.
    Tie-breakers: maior overlap_ratio, maior overlap_count, maior num_cols, tem 'tipo'.
    """
    tables = _parse_markdown_tables(schema_text)
    ref = set(reference_cols)

    candidates = []
    for i, t in enumerate(tables):
        info = _extract_table_schema_candidates(t)
        if not info:
            continue
        cols = info["columns"]
        colset = set(cols)
        overlap = len(colset.intersection(ref))
        overlap_ratio = overlap / max(1, len(colset))
        num_cols = len(cols)
        has_type = 1 if info["has_type"] else 0
        candidates.append((overlap_ratio, overlap, num_cols, has_type, i, info))

    if not candidates:
        # fallback: backticks filtrados por identificador simples
        tokens = []
        for m in re.finditer(r"`([^`]+)`", schema_text):
            token = _strip_md(m.group(1))
            if token and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token):
                tokens.append(token)
        seen = set()
        out = []
        for t in tokens:
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out, "FALLBACK_BACKTICKS"

    candidates.sort(reverse=True)
    best = candidates[0]
    overlap_ratio, overlap, num_cols, has_type, idx, info = best

    reason = (
        f"USED_TABLE_INDEX={idx} "
        f"OVERLAP_RATIO={overlap_ratio:.3f} OVERLAP_COUNT={overlap} "
        f"NUM_COLS={num_cols} HAS_TYPE={bool(has_type)} "
        f"HEADER={info['header']}"
    )
    return info["columns"], reason


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

    # referência: colunas do UNIVERSE_CANDIDATES.parquet existente, se houver
    ref_cols: List[str] = []
    ref_path = universe_dir / "UNIVERSE_CANDIDATES.parquet"
    if ref_path.exists():
        try:
            ref_cols, _ = _parquet_columns_and_num_rows(ref_path)
        except Exception:
            ref_cols = []

    # fallback: union de colunas do primeiro parquet legível
    if not ref_cols:
        for p in universe_dir.rglob("*.parquet"):
            try:
                ref_cols, _ = _parquet_columns_and_num_rows(p)
                if ref_cols:
                    break
            except Exception:
                continue

    if not ref_cols:
        print("ERROR: não consegui obter colunas de referência de nenhum parquet em data/universe/")
        return 2

    required_cols, reason = _choose_best_schema_table(schema_text, ref_cols)
    if not required_cols:
        print("ERROR: não consegui extrair colunas do schema.md (nenhuma tabela/backticks).")
        return 2

    chosen, diags = newest_ok_candidate(universe_dir, required_cols)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"SCHEMA_MD: {schema_md}")
    print(f"EXTRACTION_REASON: {reason}")
    print(f"REFERENCE_COLS_COUNT: {len(ref_cols)}")
    print(f"REQUIRED_COLS_COUNT: {len(required_cols)}")
    print(f"REQUIRED_COLS_SAMPLE: {required_cols[:12]}")
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
