#!/usr/bin/env python3
"""
PortfolioZero — Rotina diária idempotente de atualização de preços (Yahoo Finance via yfinance)

Objetivo:
- Atualizar dados em data/raw/market/prices/ (1 parquet por ticker) sem duplicação
- Adotar refresh window (default 60 dias) para capturar revisões do provider
- Garantir chave (ticker, date) e, por arquivo, unicidade de date
- Manter manifesto estável (só muda quando o conteúdo muda)

Saídas:
- Parquets por ticker: data/raw/market/prices/{TICKER_SAFE}.parquet
- Manifesto: data/raw/market/prices/manifest_prices.json (default; configurável)

Regras:
- Merge incremental por ticker, mantendo histórico anterior ao start_date_fetch
- Dedup por date (por ticker), mantendo a linha mais recente (prioriza janela baixada)
- Não reescrever arquivo/manifesto se o conteúdo não mudou (hash de conteúdo)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Dependências esperadas no repo/venv:
# - PyYAML (yaml)
# - polars
# - yfinance
# - pandas (dependência comum do yfinance)
try:
    import yaml  # type: ignore
except Exception as e:
    raise SystemExit(
        "ERRO: PyYAML não está disponível. Instale no .venv (pip install pyyaml) "
        "ou verifique o ambiente do repo."
    ) from e

try:
    import polars as pl  # type: ignore
except Exception as e:
    raise SystemExit(
        "ERRO: polars não está disponível. Instale no .venv (pip install polars) "
        "ou verifique o ambiente do repo."
    ) from e

try:
    import yfinance as yf  # type: ignore
except Exception as e:
    raise SystemExit(
        "ERRO: yfinance não está disponível. Instale no .venv (pip install yfinance) "
        "ou verifique o ambiente do repo."
    ) from e


CANONICAL_COLS = [
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
]


@dataclass(frozen=True)
class ManifestEntry:
    ticker: str
    file: str
    min_date: str
    max_date: str
    row_count: int
    content_hash: str
    updated_at_utc: str
    schema_cols: List[str]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_ticker_filename(ticker: str) -> str:
    # Ex.: ITUB4.SA -> ITUB4_SA.parquet ; ^BVSP -> _BVSP.parquet (se algum dia usado)
    safe = ticker.replace(".", "_").replace("^", "_").replace("=", "_").replace("-", "_")
    return f"{safe}.parquet"


def _infer_tipo_instrumento(ticker: str) -> str:
    # Heurística simples, suficiente para V1:
    # - BDRs geralmente terminam com 31/32/33/34/35 (ex.: AAPL34.SA)
    # - Ações BR: demais *.SA
    if ticker.endswith(".SA"):
        base = ticker.split(".")[0]
        if base.endswith(("31", "32", "33", "34", "35")):
            return "BDR"
        return "ACAO"
    if ticker.startswith("^"):
        return "INDICE"
    return "OUTRO"


def _infer_setor(ticker: str, tipo_instrumento: str, sector_mapping: Dict[str, str]) -> str:
    if ticker in sector_mapping:
        return sector_mapping[ticker]
    if tipo_instrumento == "BDR":
        return "Internacional"
    if tipo_instrumento == "INDICE":
        return "Indice"
    return "Nao_mapeado"


def _resolve_config_dates(cfg: Dict[str, Any]) -> Tuple[str, str]:
    dr = cfg.get("date_range", {}) or {}
    start = dr.get("start", "2022-01-01")
    end = dr.get("end", "today")
    if isinstance(end, str) and end.lower() == "today":
        end = date.today().isoformat()
    if not isinstance(start, str) or not isinstance(end, str):
        raise ValueError("Config inválida: date_range.start/end devem ser strings.")
    return start, end


def _parse_iso_date(s: str) -> date:
    return date.fromisoformat(s)


def _empty_prices_df() -> pl.DataFrame:
    return pl.DataFrame(
        schema=[
            ("date", pl.Date),
            ("ticker", pl.Utf8),
            ("open", pl.Float64),
            ("high", pl.Float64),
            ("low", pl.Float64),
            ("close", pl.Float64),
            ("adj_close", pl.Float64),
            ("volume", pl.Int64),
        ]
    )


def _normalize_yahoo_columns(df: "Any") -> "Any":
    # yfinance pode retornar MultiIndex mesmo para um ticker
    try:
        import pandas as pd  # type: ignore
    except Exception:
        pd = None  # type: ignore

    if pd is not None and isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    rename_map_ci = {
        "date": "date",
        "datetime": "date",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "adj close": "adj_close",
        "adj_close": "adj_close",
        "adjclose": "adj_close",
        "volume": "volume",
    }
    rename_map = {}
    for col in df.columns:
        key = str(col).strip()
        lower = key.lower()
        if lower in rename_map_ci:
            rename_map[key] = rename_map_ci[lower]

    if rename_map:
        df = df.rename(columns=rename_map)

    return df


def _download_yahoo_1d(ticker: str, start_iso: str, end_iso_inclusive: str, verbose: bool) -> pl.DataFrame:
    """
    yfinance download: parâmetro end é exclusivo. Para incluir end_iso_inclusive,
    pedimos end = end + 1 dia.
    """
    start_d = _parse_iso_date(start_iso)
    end_d_inclusive = _parse_iso_date(end_iso_inclusive)
    end_exclusive = end_d_inclusive + timedelta(days=1)

    if verbose:
        print(f"[FETCH] {ticker} start={start_d.isoformat()} end_inclusive={end_d_inclusive.isoformat()}")

    df = yf.download(
        ticker,
        start=start_d.isoformat(),
        end=end_exclusive.isoformat(),
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=True,
    )

    if df is None or getattr(df, "empty", True):
        return _empty_prices_df()

    # yfinance retorna índice DateTimeIndex
    df = df.reset_index()
    df = _normalize_yahoo_columns(df)

    # normaliza nomes (para casos sem MultiIndex)
    # Possíveis colunas: Date, Open, High, Low, Close, Adj Close, Volume
    rename_map = {
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Volume": "volume",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # garante colunas mínimas (algumas séries podem vir sem adj_close)
    if "adj_close" not in df.columns and "close" in df.columns:
        df["adj_close"] = df["close"]

    if "date" not in df.columns:
        raise ValueError(f"Coluna 'date' ausente após normalização: {list(df.columns)}")

    # adiciona ticker
    df["ticker"] = ticker

    # converte para polars
    pl_df = pl.from_pandas(df)

    # converte date para Date
    pl_df = pl_df.with_columns(
        pl.col("date").cast(pl.Datetime).dt.date().alias("date")
    )

    # mantém apenas colunas base; outras colunas desconhecidas são descartadas
    cols_present = set(pl_df.columns)

    # preenche ausentes com null
    def col_or_null(name: str, dtype: pl.DataType) -> pl.Expr:
        if name in cols_present:
            return pl.col(name).cast(dtype)
        return pl.lit(None, dtype=dtype).alias(name)

    pl_df = pl_df.select(
        [
            pl.col("date").cast(pl.Date),
            pl.col("ticker").cast(pl.Utf8),
            col_or_null("open", pl.Float64),
            col_or_null("high", pl.Float64),
            col_or_null("low", pl.Float64),
            col_or_null("close", pl.Float64),
            col_or_null("adj_close", pl.Float64),
            col_or_null("volume", pl.Int64),
        ]
    )

    # remove linhas sem close (ou close não finito)
    pl_df = pl_df.filter(
        pl.col("close").is_not_null() & pl.col("close").is_finite()
    )

    return pl_df


def _content_hash(df: pl.DataFrame) -> str:
    """
    Hash estável do conteúdo (por ticker), baseado em:
    date (days since epoch i32) + OHLC + adj_close + volume (float64/int64)
    Observação: tipo_instrumento/setor/ticker são constantes e não entram no hash.
    """
    if df.is_empty():
        return hashlib.sha256(b"").hexdigest()

    # garante ordenação
    dfx = df.sort("date")

    mat = dfx.select(
        [
            pl.col("date").cast(pl.Date).cast(pl.Int32),
            pl.col("open").cast(pl.Float64),
            pl.col("high").cast(pl.Float64),
            pl.col("low").cast(pl.Float64),
            pl.col("close").cast(pl.Float64),
            pl.col("adj_close").cast(pl.Float64),
            pl.col("volume").cast(pl.Int64),
        ]
    ).to_numpy()

    return hashlib.sha256(mat.tobytes()).hexdigest()


def _load_manifest(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "version": "1.0",
            "created_at_utc": _utc_now_iso(),
            "updated_at_utc": _utc_now_iso(),
            "entries": {},
        }
    return json.loads(path.read_text(encoding="utf-8"))


def _write_manifest_if_changed(path: Path, manifest_obj: Dict[str, Any], previous_text: Optional[str]) -> bool:
    new_text = json.dumps(manifest_obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if previous_text is not None and new_text == previous_text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_text, encoding="utf-8")
    return True


def _read_existing_prices(path: Path) -> pl.DataFrame:
    if not path.exists():
        return pl.DataFrame(schema=[("date", pl.Date)])
    df = pl.read_parquet(path)
    # normaliza tipos de date
    if "date" in df.columns:
        df = df.with_columns(pl.col("date").cast(pl.Date))
    return df


def _merge_idempotent(existing: pl.DataFrame, incoming: pl.DataFrame, start_fetch: date) -> pl.DataFrame:
    """
    Mantém histórico anterior a start_fetch e substitui/reconstrói janela start_fetch..fim
    a partir do incoming. Dedup por date, mantendo a última ocorrência (prioriza incoming).
    """
    if incoming.is_empty():
        return existing
    if existing.is_empty():
        base = pl.DataFrame(schema=[("date", pl.Date)])
    else:
        base = existing.filter(pl.col("date") < pl.lit(start_fetch))

    merged = pl.concat([base, incoming], how="vertical", rechunk=True)

    # garante unicidade por date, preferindo linhas "mais novas" (incoming vem por último)
    merged = merged.unique(subset=["date"], keep="last").sort("date")

    return merged


def _progress_iter(items: List[str]):
    # tqdm é opcional
    try:
        from tqdm import tqdm  # type: ignore

        return tqdm(items, total=len(items))
    except Exception:
        return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--config",
        default="config/experiments/universe_data_sources_v1.yaml",
        help="Caminho do YAML de configuração (default: config/experiments/universe_data_sources_v1.yaml)",
    )
    ap.add_argument(
        "--refresh-days",
        type=int,
        default=60,
        help="Janela de refresh (dias corridos) para recapturar revisões (default: 60)",
    )
    ap.add_argument(
        "--prices-dir",
        default="data/raw/market/prices",
        help="Diretório de saída dos parquets (default: data/raw/market/prices)",
    )
    ap.add_argument(
        "--manifest",
        default="data/raw/market/prices/manifest_prices.json",
        help="Arquivo de manifesto de preços (default: data/raw/market/prices/manifest_prices.json)",
    )
    ap.add_argument("--dry-run", action="store_true", help="Não escreve nada; apenas simula")
    ap.add_argument("-v", "--verbose", action="store_true", help="Logs mais detalhados")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        print(f"ERRO: config não encontrado: {cfg_path}")
        return 2

    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

    provider = cfg.get("provider")
    if provider != "yahoo_finance":
        print(f"ERRO: provider inesperado no config: {provider!r} (esperado: 'yahoo_finance')")
        return 2

    start_cfg, end_cfg = _resolve_config_dates(cfg)
    end_date = min(_parse_iso_date(end_cfg), date.today()).isoformat()

    universe: List[str] = cfg.get("universe", []) or []
    if not universe:
        print("ERRO: config não contém lista 'universe' (ou está vazia).")
        return 2

    sector_mapping: Dict[str, str] = cfg.get("sector_mapping", {}) or {}

    prices_dir = Path(args.prices_dir)
    prices_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = Path(args.manifest)
    prev_manifest_text: Optional[str] = None
    if manifest_path.exists():
        prev_manifest_text = manifest_path.read_text(encoding="utf-8")

    manifest_obj = _load_manifest(manifest_path)
    entries: Dict[str, Any] = manifest_obj.get("entries", {}) or {}
    manifest_changed = False

    # estatísticas
    n_total = 0
    n_changed = 0
    n_unchanged = 0
    n_errors = 0
    errors: List[str] = []

    # garante que sample sintético não esteja no diretório (produção)
    sample_path = prices_dir / "sample_market_data.parquet"
    if sample_path.exists():
        print(f"ERRO: arquivo sintético ainda existe em produção: {sample_path}")
        print("Remova antes de rodar (rm -f data/raw/market/prices/sample_market_data.parquet).")
        return 2

    for ticker in _progress_iter(universe):
        n_total += 1
        try:
            out_file = prices_dir / _safe_ticker_filename(ticker)
            tipo = _infer_tipo_instrumento(ticker)
            setor = _infer_setor(ticker, tipo, sector_mapping)

            existing = _read_existing_prices(out_file)
            max_date_existing: Optional[date] = None
            if not existing.is_empty() and "date" in existing.columns:
                max_date_existing = existing.select(pl.col("date").max()).item()

            if max_date_existing is None:
                start_fetch = _parse_iso_date(start_cfg)
            else:
                start_fetch = max(_parse_iso_date(start_cfg), max_date_existing - timedelta(days=args.refresh_days))

            incoming = _download_yahoo_1d(ticker, start_fetch.isoformat(), end_date, args.verbose)

            # enriquece com colunas canônicas
            incoming = incoming.with_columns(
                pl.lit(tipo).cast(pl.Utf8).alias("tipo_instrumento"),
                pl.lit(setor).cast(pl.Utf8).alias("setor"),
            )

            if incoming.is_empty() and existing.is_empty():
                # nada para escrever; mantém entrada vazia (não cria arquivo)
                if args.verbose:
                    print(f"[SKIP] {ticker}: sem dados (incoming vazio e sem existente)")
                n_unchanged += 1
                continue

            merged = _merge_idempotent(existing, incoming, start_fetch)

            # garante colunas canônicas (ordem e presença)
            cols_present = set(merged.columns)
            for c in CANONICAL_COLS:
                if c not in cols_present:
                    merged = merged.with_columns(pl.lit(None).alias(c))
            merged = merged.select(CANONICAL_COLS)

            # validações mínimas por ticker
            if merged.select(pl.col("date").n_unique()).item() != merged.height:
                raise RuntimeError("duplicidade detectada por date após merge/dedup (não deveria acontecer).")
            if not merged.get_column("date").is_sorted():
                raise RuntimeError("coluna date não está ordenada após sort (não deveria acontecer).")

            new_hash = _content_hash(merged)

            prev_entry = entries.get(ticker)
            prev_hash = None
            if isinstance(prev_entry, dict):
                prev_hash = prev_entry.get("content_hash")

            if prev_hash == new_hash and out_file.exists():
                # conteúdo igual: não reescreve e não muda updated_at
                n_unchanged += 1
                continue

            # escrever parquet (ou simular)
            if not args.dry_run:
                merged.write_parquet(out_file)
            n_changed += 1

            # atualizar manifesto (somente quando conteúdo mudou)
            min_d = merged.select(pl.col("date").min()).item()
            max_d = merged.select(pl.col("date").max()).item()
            entry = ManifestEntry(
                ticker=ticker,
                file=str(out_file.as_posix()),
                min_date=min_d.isoformat() if min_d else "",
                max_date=max_d.isoformat() if max_d else "",
                row_count=int(merged.height),
                content_hash=new_hash,
                updated_at_utc=_utc_now_iso(),
                schema_cols=CANONICAL_COLS,
            )
            entries[ticker] = {
                "ticker": entry.ticker,
                "file": entry.file,
                "min_date": entry.min_date,
                "max_date": entry.max_date,
                "row_count": entry.row_count,
                "content_hash": entry.content_hash,
                "updated_at_utc": entry.updated_at_utc,
                "schema_cols": entry.schema_cols,
            }
            manifest_changed = True

        except Exception as e:
            n_errors += 1
            msg = f"{ticker}: {type(e).__name__}: {e}"
            errors.append(msg)
            if args.verbose:
                print(f"[ERROR] {msg}")

    manifest_obj["entries"] = entries
    if manifest_changed:
        manifest_obj["updated_at_utc"] = _utc_now_iso()
        manifest_obj["provider"] = "yahoo_finance_via_yfinance"
        manifest_obj["refresh_days"] = int(args.refresh_days)
        manifest_obj["prices_dir"] = str(prices_dir.as_posix())
        manifest_obj["config_path"] = str(cfg_path.as_posix())

    # escreve manifesto apenas se mudou (e não em dry-run)
    wrote_manifest = False
    if manifest_changed and not args.dry_run:
        wrote_manifest = _write_manifest_if_changed(manifest_path, manifest_obj, prev_manifest_text)

    # resumo final
    summary = {
        "provider": "yahoo_finance_via_yfinance",
        "refresh_days": int(args.refresh_days),
        "config": str(cfg_path),
        "prices_dir": str(prices_dir),
        "manifest": str(manifest_path),
        "dry_run": bool(args.dry_run),
        "n_total": n_total,
        "n_changed": n_changed,
        "n_unchanged": n_unchanged,
        "n_errors": n_errors,
        "manifest_written": bool(wrote_manifest),
        "updated_at_utc": _utc_now_iso(),
        "errors": errors[:50],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    return 0 if n_errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
