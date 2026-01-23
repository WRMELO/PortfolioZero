#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import polars as pl


ALIASES = {
    "ticker": {"ticker", "symbol", "asset", "code", "papel"},
    "quantity": {"quantity", "qty", "shares", "qtd", "quantidade"},
    "avg_price": {"avg_price", "average_price", "avg", "price_avg", "preco_medio", "pm"},
}


def _try_tqdm():
    try:
        from tqdm import tqdm  # type: ignore
        return tqdm
    except Exception:
        return None


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def norm_col(s: str) -> str:
    return s.strip().lower().replace(" ", "_")


def pick_col(cols_norm: Set[str], wanted: str) -> Optional[str]:
    for c in ALIASES.get(wanted, {wanted}):
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


def copy_with_progress(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    total = src.stat().st_size
    tqdm = _try_tqdm()
    chunk = 1024 * 1024

    with src.open("rb") as fsrc, dst.open("wb") as fdst:
        if tqdm:
            with tqdm(total=total, unit="B", unit_scale=True, desc=f"copy:{src.name}") as pbar:
                while True:
                    b = fsrc.read(chunk)
                    if not b:
                        break
                    fdst.write(b)
                    pbar.update(len(b))
        else:
            while True:
                b = fsrc.read(chunk)
                if not b:
                    break
                fdst.write(b)


def canonicalize_positions_parquet(in_p: Path) -> Tuple[pl.DataFrame, Dict[str, Any]]:
    df = pl.read_parquet(in_p)

    cols_orig = df.columns
    cols_norm = [norm_col(c) for c in cols_orig]
    mapping = dict(zip(cols_orig, cols_norm))
    df = df.rename(mapping)

    cols_set = set(df.columns)
    ct = pick_col(cols_set, "ticker")
    cq = pick_col(cols_set, "quantity")
    ca = pick_col(cols_set, "avg_price")

    missing = [k for k, c in [("ticker", ct), ("quantity", cq), ("avg_price", ca)] if c is None]
    if missing:
        raise ValueError(f"Parquet sem colunas necessarias (ou aliases): {missing}. colunas_norm={sorted(list(cols_set))}")

    sub = df.select([pl.col(ct).cast(pl.Utf8), pl.col(cq), pl.col(ca)]).rename(
        {ct: "ticker", cq: "quantity", ca: "avg_price"}
    )

    def ensure_float(colname: str) -> pl.Expr:
        # converte numéricos; se já for numérico, cast->Utf8 e parse também funciona
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

    bad = sub.filter(
        (pl.col("ticker").is_null())
        | (pl.col("ticker") == "")
        | (pl.col("quantity").is_null())
        | (pl.col("avg_price").is_null())
        | (pl.col("quantity") <= 0)
        | (pl.col("avg_price") < 0)
    )
    if bad.height > 0:
        raise ValueError(f"Linhas invalidas (sample<=10): {bad.head(10).to_dicts()} (n_bad={bad.height})")

    dup = sub.group_by("ticker").agg(pl.len().alias("n")).filter(pl.col("n") > 1)
    if dup.height > 0:
        raise ValueError(f"Tickers duplicados (sample<=20): {dup.head(20).to_dicts()} (n_dup={dup.height})")

    # canonical: ordena por ticker, fixa dtypes
    out = (
        sub.select(
            [
                pl.col("ticker").cast(pl.Utf8),
                pl.col("quantity").cast(pl.Float64),
                pl.col("avg_price").cast(pl.Float64),
            ]
        )
        .sort("ticker")
    )

    meta = {
        "columns_seen_norm": sorted(list(cols_set)),
        "columns_used_norm": {"ticker": ct, "quantity": cq, "avg_price": ca},
        "rows": int(out.height),
        "tickers": int(out.select(pl.col("ticker").n_unique()).item()),
        "schema": {k: str(v) for k, v in out.schema.items()},
    }
    return out, meta


def load_manifest(manifest_p: Path) -> Dict[str, Any]:
    if not manifest_p.exists():
        return {"version": "v1", "generated_at_utc": None, "current": None, "history": []}
    try:
        d = json.loads(manifest_p.read_text(encoding="utf-8"))
        if not isinstance(d, dict):
            return {"version": "v1", "generated_at_utc": None, "current": None, "history": []}
        d.setdefault("version", "v1")
        d.setdefault("history", [])
        return d
    except Exception:
        return {"version": "v1", "generated_at_utc": None, "current": None, "history": []}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-parquet", required=True)
    ap.add_argument("--out-current", required=True)
    ap.add_argument("--archive-dir", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--report-dir", required=True)
    args = ap.parse_args()

    in_p = Path(args.in_parquet)
    out_current = Path(args.out_current)
    archive_dir = Path(args.archive_dir)
    manifest_p = Path(args.manifest)
    run_dir = Path(args.run_dir)
    report_dir = Path(args.report_dir)

    run_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any] = {
        "task_id": "TASK_A_018",
        "generated_at_utc": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "inputs": {
            "in_parquet": str(in_p),
            "out_current": str(out_current),
            "archive_dir": str(archive_dir),
            "manifest": str(manifest_p),
        },
        "status": "FAIL",
        "errors": [],
        "warnings": [],
        "result": None,
    }

    if not in_p.exists():
        report["errors"].append({"code": "INPUT_NOT_FOUND", "path": str(in_p)})
        out_rep = report_dir / "REPORT_PORTFOLIO_POSITIONS_INGEST_V1.json"
        out_rep.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"ERROR: input not found: {in_p}")
        return 2

    # canonicaliza -> escreve tmp -> compara hash com current -> promove/archiva
    try:
        canonical_df, meta = canonicalize_positions_parquet(in_p)
    except Exception as e:
        report["errors"].append({"code": "CANONICALIZE_FAILED", "error": str(e)})
        out_rep = report_dir / "REPORT_PORTFOLIO_POSITIONS_INGEST_V1.json"
        out_rep.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"ERROR: canonicalize failed: {e}")
        return 2

    tmp_p = out_current.parent / (out_current.stem + ".__tmp__.parquet")
    tmp_p.parent.mkdir(parents=True, exist_ok=True)
    canonical_df.write_parquet(tmp_p)

    sha_new = sha256_file(tmp_p)
    sha_cur = sha256_file(out_current) if out_current.exists() else None

    ingested_at_utc = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_p = archive_dir / f"{stamp}_PORTFOLIO_POSITIONS_REAL_{sha_new[:10]}.parquet"

    manifest = load_manifest(manifest_p)

    if sha_cur is not None and sha_new == sha_cur:
        # idempotente: mantém current; atualiza manifest só com nota (sem duplicar history)
        tmp_p.unlink(missing_ok=True)
        report["status"] = "PASS"
        report["result"] = {
            "idempotent": True,
            "current_sha256": sha_cur,
            "new_sha256": sha_new,
            "rows": meta["rows"],
            "tickers": meta["tickers"],
            "note": "conteudo identico ao current; nenhuma promocao realizada",
        }
        manifest["generated_at_utc"] = ingested_at_utc
        if manifest.get("current") is not None:
            manifest["current"]["last_seen_at_utc"] = ingested_at_utc
        manifest_p.parent.mkdir(parents=True, exist_ok=True)
        manifest_p.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        # promove: arquiva e substitui current
        copy_with_progress(tmp_p, archive_p)
        tmp_p.replace(out_current)

        entry = {
            "ingested_at_utc": ingested_at_utc,
            "source_in_parquet": str(in_p),
            "current_path": str(out_current),
            "archive_path": str(archive_p),
            "sha256": sha_new,
            "rows": meta["rows"],
            "tickers": meta["tickers"],
            "schema": meta["schema"],
            "columns_used_norm": meta["columns_used_norm"],
        }

        manifest["generated_at_utc"] = ingested_at_utc
        manifest["current"] = entry
        hist = manifest.get("history", [])
        if not isinstance(hist, list):
            hist = []
        hist.append(entry)
        manifest["history"] = hist

        manifest_p.parent.mkdir(parents=True, exist_ok=True)
        manifest_p.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        report["status"] = "PASS"
        report["result"] = {
            "idempotent": False,
            "previous_current_sha256": sha_cur,
            "new_current_sha256": sha_new,
            "rows": meta["rows"],
            "tickers": meta["tickers"],
            "archive_path": str(archive_p),
        }

    out_rep = report_dir / "REPORT_PORTFOLIO_POSITIONS_INGEST_V1.json"
    out_rep.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: ingest positions ->", out_current)
    print("sha256_current=", sha256_file(out_current))
    print("report=", out_rep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
