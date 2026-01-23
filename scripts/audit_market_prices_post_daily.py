from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import polars as pl


def _try_import_tqdm():
    try:
        from tqdm import tqdm  # type: ignore
        return tqdm
    except Exception:
        return None


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def try_git(cmd: List[str]) -> Optional[str]:
    try:
        return subprocess.check_output(cmd, text=True).strip()
    except Exception:
        return None


def grep_provenance(repo_root: Path) -> Tuple[List[str], List[str]]:
    """
    Identifica arquivos que referenciam o path de raw prices/manifest.
    Retorna (notebooks, scripts), com paths relativos.
    """
    patterns = [
        "data/raw/market/prices",
        "manifest_prices.json",
        "update_market_data_daily.py",
    ]

    hits: List[str] = []
    for pat in patterns:
        try:
            out = subprocess.check_output(
                ["grep", "-RIn", pat, "scripts", "modules", "config"],
                cwd=str(repo_root),
                text=True,
                stderr=subprocess.DEVNULL,
            )
            hits.extend([line.split(":", 1)[0] for line in out.splitlines() if line.strip()])
        except Exception:
            # grep pode retornar exit code !=0 quando não encontra, isso é ok
            pass

    # notebooks: varredura simples (pode não existir neste repo)
    nb_hits: List[str] = []
    try:
        out = subprocess.check_output(
            ["grep", "-RIn", "data/raw/market/prices", "."],
            cwd=str(repo_root),
            text=True,
            stderr=subprocess.DEVNULL,
        )
        nb_hits = [line.split(":", 1)[0] for line in out.splitlines() if line.strip() and line.split(":", 1)[0].endswith(".ipynb")]
    except Exception:
        pass

    scripts = sorted({h for h in hits if h.endswith(".py")})
    notebooks = sorted(set(nb_hits))
    return notebooks, scripts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prices-dir", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--report-dir", required=True)

    args = parser.parse_args()

    repo_root = Path.cwd()
    prices_dir = Path(args.prices_dir)
    manifest_path = Path(args.manifest)
    run_dir = Path(args.run_dir)
    report_dir = Path(args.report_dir)

    run_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    # 0) bloqueio: sample sintético não pode existir
    sample = prices_dir / "sample_market_data.parquet"
    if sample.exists():
        errors.append({"code": "SAMPLE_FILE_PRESENT", "file": str(sample)})

    # 1) manifesto deve existir e ser válido
    manifest: Optional[Dict[str, Any]] = None
    if not manifest_path.exists():
        errors.append({"code": "MANIFEST_MISSING", "file": str(manifest_path)})
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(manifest, dict):
                errors.append({"code": "MANIFEST_NOT_DICT", "file": str(manifest_path)})
                manifest = None
        except Exception as e:
            errors.append({"code": "MANIFEST_INVALID_JSON", "file": str(manifest_path), "error": str(e)})
            manifest = None

    entries: Dict[str, Any] = {}
    if manifest is not None:
        raw_entries = manifest.get("entries", {}) or {}
        if isinstance(raw_entries, dict):
            entries = raw_entries
        else:
            errors.append({"code": "MANIFEST_ENTRIES_NOT_DICT", "file": str(manifest_path)})

    # 2) arquivos parquet
    parquets = sorted(prices_dir.glob("*.parquet"))
    if not parquets:
        errors.append({"code": "NO_PARQUETS_FOUND", "dir": str(prices_dir)})

    required_cols = {
        "date",
        "ticker",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "tipo_instrumento",
        "setor",
    }

    tqdm = _try_import_tqdm()
    it = tqdm(parquets, desc="audit_parquets") if tqdm else parquets

    schema_signatures: Dict[str, List[str]] = {}
    files_profile: List[Dict[str, Any]] = []
    tickers_in_files: List[str] = []
    infile_dupes_sample: List[Dict[str, Any]] = []

    overall_min_date: Optional[str] = None
    overall_max_date: Optional[str] = None

    for p in it:
        try:
            # schema rápido
            schema = pl.read_parquet(p, n_rows=0).schema
            # assinatura preservando ordem de colunas
            sig = ",".join([f"{k}:{v}" for k, v in schema.items()])
            schema_signatures.setdefault(sig, []).append(p.name)

            cols = set(schema.keys())
            missing = sorted(list(required_cols - cols))
            if missing:
                errors.append({"code": "MISSING_REQUIRED_COLS", "file": p.name, "missing": missing})
                continue

            # leitura mínima (date + ticker)
            df = pl.read_parquet(p, columns=["ticker", "date"])
            if df.is_empty():
                errors.append({"code": "EMPTY_PARQUET", "file": p.name})
                continue

            n_ticker = int(df.select(pl.col("ticker").n_unique()).item())
            if n_ticker != 1:
                errors.append({"code": "MULTI_TICKER_FILE", "file": p.name, "n_unique_ticker": n_ticker})
                continue

            ticker = str(df.select(pl.col("ticker").first()).item())
            tickers_in_files.append(ticker)

            # unicidade por date dentro do arquivo (equivale a (ticker,date) pois ticker é único)
            n_unique_dates = int(df.select(pl.col("date").n_unique()).item())
            if n_unique_dates != df.height:
                errors.append({"code": "DUPLICATE_DATES_IN_FILE", "file": p.name, "ticker": ticker, "n_unique_dates": n_unique_dates, "rows": int(df.height)})
                infile_dupes_sample.append({"file": p.name, "ticker": ticker, "n_unique_dates": n_unique_dates, "rows": int(df.height)})
                continue

            # ordenação por date
            if not df.get_column("date").is_sorted():
                errors.append({"code": "DATE_NOT_SORTED", "file": p.name, "ticker": ticker})
                continue

            min_date = df.select(pl.col("date").min()).item()
            max_date = df.select(pl.col("date").max()).item()

            min_date_s = str(min_date)
            max_date_s = str(max_date)

            if overall_min_date is None or min_date_s < overall_min_date:
                overall_min_date = min_date_s
            if overall_max_date is None or max_date_s > overall_max_date:
                overall_max_date = max_date_s

            sha = sha256_file(p)

            files_profile.append(
                {
                    "file": p.name,
                    "ticker": ticker,
                    "rows": int(df.height),
                    "min_date": min_date_s,
                    "max_date": max_date_s,
                    "size_bytes": int(p.stat().st_size),
                    "sha256": sha,
                    "schema_signature": sig,
                }
            )

        except Exception as e:
            errors.append({"code": "READ_OR_VALIDATE_FAILED", "file": p.name, "error": str(e)})

    # 3) schema único
    schema_clusters = [
        {"schema_signature": k, "n_files": len(v), "files_sample": v[:10]}
        for k, v in schema_signatures.items()
    ]
    n_schema_clusters = len(schema_signatures)
    if n_schema_clusters != 1:
        errors.append({"code": "MULTIPLE_SCHEMA_CLUSTERS", "n_clusters": n_schema_clusters, "clusters": schema_clusters})

    # 4) manifesto cobre tickers presentes nos arquivos
    files_tickers_set = sorted(set(tickers_in_files))
    manifest_tickers_set = sorted(set(entries.keys()))
    missing_in_manifest = sorted(set(files_tickers_set) - set(manifest_tickers_set))
    manifest_without_file = sorted(set(manifest_tickers_set) - set(files_tickers_set))

    if missing_in_manifest:
        errors.append(
            {
                "code": "MANIFEST_MISSING_TICKERS",
                "n_missing": len(missing_in_manifest),
                "missing_sample": missing_in_manifest[:25],
            }
        )

    # 5) proveniência por grep (não é critério de FAIL, só evidência)
    notebooks_writing_raw_prices, scripts_writing_raw_prices = grep_provenance(repo_root)

    # 6) montagem do report (mantém chaves principais do V1 e amplia sem quebrar leitura humana)
    git_head = try_git(["git", "rev-parse", "HEAD"]) or "UNKNOWN"
    git_branch = try_git(["git", "rev-parse", "--abbrev-ref", "HEAD"]) or "UNKNOWN"
    created_at_utc = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    per_ticker_summary_sample = []
    # amostra determinística: ordena por ticker e limita
    for row in sorted(files_profile, key=lambda x: (x["ticker"], x["file"]))[:30]:
        per_ticker_summary_sample.append(
            {
                "ticker": row["ticker"],
                "file": row["file"],
                "rows": row["rows"],
                "min_date": row["min_date"],
                "max_date": row["max_date"],
            }
        )

    report: Dict[str, Any] = {
        "repo": str(repo_root),
        "head": git_head,
        "head_meta": {
            "created_at_utc": created_at_utc,
            "git_branch": git_branch,
            "task_id": "TASK_D_003",
        },
        "data_inventory": {
            "prices_dir": str(prices_dir),
            "manifest_path": str(manifest_path),
            "n_files": len(parquets),
            "files_sample": [p.name for p in parquets[:30]],
            "n_schema_clusters": n_schema_clusters,
            "schema_clusters": schema_clusters,
            "overall_min_date": overall_min_date,
            "overall_max_date": overall_max_date,
        },
        "coverage_summary": {
            "date_col_candidates_seen": ["date"],
            "per_ticker_summary_sample": per_ticker_summary_sample,
            "n_unique_tickers_in_files": len(files_tickers_set),
            "missing_in_manifest_sample": missing_in_manifest[:25],
            "manifest_without_file_sample": manifest_without_file[:25],
        },
        "duplication_findings": {
            "filename_collisions": [],
            "infile_dupes_sample": infile_dupes_sample[:10],
        },
        "provenance": {
            "notebooks_writing_raw_prices": notebooks_writing_raw_prices[:50],
            "scripts_writing_raw_prices": scripts_writing_raw_prices[:50],
        },
        "recommendations_minimal": [
            "Manter 1 schema unico para todos os parquets de prices (colunas e tipos).",
            "Garantir unicidade por date dentro de cada arquivo (implica (ticker,date) pois ticker deve ser unico por arquivo).",
            "Garantir date ordenado (crescente) dentro de cada arquivo.",
            "Manifesto deve cobrir todos os tickers que existirem em arquivo (tickers_in_files subset de manifest.entries).",
        ],
        "warnings": warnings,
        "errors": errors,
        "status": "PASS" if not errors else "FAIL",
    }

    out_run = run_dir / "REPORT_DATA_AUDIT_MARKET_PRICES_V2.json"
    out_rep = report_dir / "REPORT_DATA_AUDIT_MARKET_PRICES_V2.json"
    out_run.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_rep.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("AUDIT_STATUS=", report["status"])
    print("git_head=", git_head)
    print("n_parquets=", report["data_inventory"]["n_files"])
    print("n_schema_clusters=", report["data_inventory"]["n_schema_clusters"])
    print("n_unique_tickers_in_files=", report["coverage_summary"]["n_unique_tickers_in_files"])
    print("overall_min_date=", report["data_inventory"]["overall_min_date"])
    print("overall_max_date=", report["data_inventory"]["overall_max_date"])
    print("missing_in_manifest_sample=", report["coverage_summary"]["missing_in_manifest_sample"][:10])
    print("manifest_without_file_sample=", report["coverage_summary"]["manifest_without_file_sample"][:10])
    print("report_run_path=", str(out_run))
    print("report_report_path=", str(out_rep))

    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
