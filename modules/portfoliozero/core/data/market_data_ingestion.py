"""Módulo de ingestão de dados de mercado para o Trilho A do PortfolioZero.

Este módulo implementa o adaptador de ingestão de dados de mercado,
utilizando Yahoo Finance (yfinance) como provider padrão v1.

Fluxo:
    config YAML → ingestão → data/raw/market/ → universe_candidates_pipeline

Example:
    >>> from portfoliozero.core.data.market_data_ingestion import (
    ...     fetch_and_store_universe_market_data,
    ...     load_data_source_config,
    ... )
    >>> config = load_data_source_config()
    >>> files = fetch_and_store_universe_market_data()
    >>> print(f"Arquivos gerados: {len(files)}")
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl
import yaml

# Import yfinance no nível do módulo para permitir mocking em testes
try:
    import yfinance as yf
except ImportError:
    yf = None  # type: ignore

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTES
# =============================================================================

DEFAULT_CONFIG_PATH = "config/experiments/universe_data_sources_v1.yaml"

REQUIRED_OUTPUT_COLUMNS = ["date", "ticker", "close", "volume"]

OPTIONAL_OUTPUT_COLUMNS = [
    "open",
    "high",
    "low",
    "adj_close",
    "tipo_instrumento",
    "setor",
]


# =============================================================================
# DATACLASSES
# =============================================================================


@dataclass
class IngestionResult:
    """Resultado da ingestão de dados para um ticker.

    Attributes:
        ticker: Código do ticker.
        success: Se a ingestão foi bem-sucedida.
        records: Número de registros obtidos.
        file_path: Caminho do arquivo gerado (se sucesso).
        error: Mensagem de erro (se falha).
        date_range: Tupla (data_inicio, data_fim) dos dados obtidos.
    """

    ticker: str
    success: bool
    records: int = 0
    file_path: str | None = None
    error: str | None = None
    date_range: tuple[str, str] | None = None


@dataclass
class IngestionSummary:
    """Resumo da ingestão de todos os tickers.

    Attributes:
        total_tickers: Número total de tickers processados.
        successful: Número de tickers com sucesso.
        failed: Número de tickers com falha.
        total_records: Total de registros obtidos.
        files_generated: Lista de arquivos gerados.
        failed_tickers: Lista de tickers que falharam.
        execution_time_seconds: Tempo total de execução.
    """

    total_tickers: int
    successful: int
    failed: int
    total_records: int
    files_generated: list[str] = field(default_factory=list)
    failed_tickers: list[str] = field(default_factory=list)
    execution_time_seconds: float = 0.0


# =============================================================================
# FUNÇÕES DE CONFIGURAÇÃO
# =============================================================================


def _get_project_root() -> Path:
    """Retorna o diretório raiz do projeto."""
    current = Path(__file__).resolve()
    for _ in range(5):
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    return Path.cwd()


def load_data_source_config(path: str | None = None) -> dict[str, Any]:
    """Carrega e valida o YAML de configuração de fontes de dados.

    Args:
        path: Caminho do arquivo YAML. Se None, usa o caminho padrão:
            config/experiments/universe_data_sources_v1.yaml

    Returns:
        Dicionário com a configuração carregada.

    Raises:
        FileNotFoundError: Se o arquivo não existir.
        ValueError: Se campos obrigatórios estiverem ausentes.
    """
    root = _get_project_root()
    config_path = Path(path) if path else root / DEFAULT_CONFIG_PATH

    if not config_path.exists():
        raise FileNotFoundError(
            f"Arquivo de configuração não encontrado: {config_path}\n"
            f"Crie o arquivo com os campos: provider, universe, date_range, frequency, output"
        )

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Valida campos obrigatórios
    required_fields = ["provider", "universe", "date_range", "output"]
    missing = [f for f in required_fields if f not in config]
    if missing:
        raise ValueError(
            f"Campos obrigatórios ausentes no YAML: {missing}\n"
            f"Arquivo: {config_path}"
        )

    # Valida date_range
    if "start" not in config["date_range"]:
        raise ValueError("Campo 'date_range.start' é obrigatório")

    logger.info(f"Configuração carregada: {config_path}")
    logger.info(f"  Provider: {config['provider']}")
    logger.info(f"  Tickers: {len(config['universe'])}")

    return config


def _resolve_date_range(config: dict[str, Any]) -> tuple[str, str]:
    """Resolve o período de datas da configuração.

    Args:
        config: Dicionário de configuração.

    Returns:
        Tupla (start_date, end_date) como strings YYYY-MM-DD.
    """
    date_range = config.get("date_range", {})
    start = date_range.get("start", "2022-01-01")
    end = date_range.get("end", "today")

    if end == "today":
        end = datetime.now().strftime("%Y-%m-%d")

    return start, end


# =============================================================================
# FUNÇÕES DE INGESTÃO - YAHOO FINANCE
# =============================================================================


def _fetch_yahoo_finance(
    ticker: str,
    start_date: str,
    end_date: str,
    config: dict[str, Any],
) -> pl.DataFrame | None:
    """Busca dados de um ticker via Yahoo Finance.

    Args:
        ticker: Código do ticker (ex: PETR4.SA).
        start_date: Data inicial (YYYY-MM-DD).
        end_date: Data final (YYYY-MM-DD).
        config: Dicionário de configuração.

    Returns:
        DataFrame Polars com os dados, ou None se falhar.
    """
    if yf is None:
        raise ImportError(
            "yfinance não está instalado. Execute: pip install yfinance"
        )

    try:
        # Baixa dados do Yahoo Finance
        stock = yf.Ticker(ticker)
        df_pandas = stock.history(start=start_date, end=end_date, auto_adjust=False)

        if df_pandas.empty:
            logger.warning(f"Sem dados para {ticker} no período {start_date} a {end_date}")
            return None

        # Reseta índice para ter 'Date' como coluna
        df_pandas = df_pandas.reset_index()

        # Converte para Polars
        df = pl.from_pandas(df_pandas)

        # Renomeia colunas para snake_case
        column_mapping = {
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
            "Dividends": "dividends",
            "Stock Splits": "stock_splits",
        }

        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename({old_name: new_name})

        # Adiciona coluna ticker
        df = df.with_columns(pl.lit(ticker).alias("ticker"))

        # Adiciona tipo de instrumento e setor (se disponível na config)
        sector_mapping = config.get("sector_mapping", {})
        instrument_mapping = config.get("instrument_type_mapping", {})

        setor = sector_mapping.get(ticker, "Outros")
        tipo = instrument_mapping.get(ticker, "ACAO_ON")

        df = df.with_columns([
            pl.lit(setor).alias("setor"),
            pl.lit(tipo).alias("tipo_instrumento"),
        ])

        # Normaliza data para Date (remove timezone se houver)
        if "date" in df.columns:
            # Converte para string e depois para Date para remover timezone
            df = df.with_columns(
                pl.col("date").cast(pl.Date).alias("date")
            )

        # Seleciona apenas colunas relevantes
        output_cols = [
            "date", "ticker", "open", "high", "low", "close", "volume",
            "tipo_instrumento", "setor"
        ]
        if "adj_close" in df.columns:
            output_cols.insert(6, "adj_close")

        existing_cols = [c for c in output_cols if c in df.columns]
        df = df.select(existing_cols)

        return df

    except Exception as e:
        logger.error(f"Erro ao buscar {ticker}: {e}")
        return None


# =============================================================================
# FUNÇÕES DE INGESTÃO - GENÉRICA
# =============================================================================


def fetch_market_data_for_ticker(
    ticker: str,
    config: dict[str, Any],
) -> pl.DataFrame | None:
    """Busca dados de mercado para um único ticker.

    Args:
        ticker: Código do ticker.
        config: Dicionário de configuração.

    Returns:
        DataFrame Polars com o schema mínimo exigido, ou None se falhar.
    """
    provider = config.get("provider", "yahoo_finance")
    start_date, end_date = _resolve_date_range(config)

    if provider == "yahoo_finance":
        return _fetch_yahoo_finance(ticker, start_date, end_date, config)
    else:
        raise ValueError(f"Provider não suportado: {provider}")


def _persist_ticker_data(
    df: pl.DataFrame,
    ticker: str,
    config: dict[str, Any],
    root: Path,
) -> str:
    """Persiste os dados de um ticker em Parquet.

    Args:
        df: DataFrame com os dados.
        ticker: Código do ticker.
        config: Dicionário de configuração.
        root: Diretório raiz do projeto.

    Returns:
        Caminho do arquivo gerado.
    """
    output_config = config.get("output", {})
    base_path = output_config.get("path", "data/raw/market/")
    partitioning = output_config.get("partitioning", "per_ticker")
    output_format = output_config.get("format", "parquet")

    # Cria diretório de saída
    output_dir = root / base_path / "prices"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define nome do arquivo
    ticker_clean = ticker.replace(".", "_").replace("^", "")

    if partitioning == "per_ticker":
        filename = f"{ticker_clean}.{output_format}"
    elif partitioning == "per_ticker_year":
        # Agrupa por ano (usa o primeiro registro)
        year = df.select(pl.col("date").min()).item().year
        filename = f"{ticker_clean}_{year}.{output_format}"
    else:
        filename = f"{ticker_clean}.{output_format}"

    file_path = output_dir / filename

    # Persiste
    if output_format == "parquet":
        df.write_parquet(file_path)
    else:
        df.write_csv(file_path)

    return str(file_path)


def fetch_and_store_universe_market_data(
    config_path: str | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> list[str]:
    """Fluxo de alto nível para ingestão de dados do universo completo.

    Args:
        config_path: Caminho do YAML de configuração. Se None, usa padrão.
        overwrite: Se True, sobrescreve arquivos existentes.
        dry_run: Se True, apenas lista o que seria baixado sem executar.

    Returns:
        Lista de caminhos dos arquivos gerados/atualizados.
    """
    root = _get_project_root()
    config = load_data_source_config(config_path)

    universe = config.get("universe", [])
    start_date, end_date = _resolve_date_range(config)

    logger.info("=" * 60)
    logger.info("Iniciando ingestão de dados de mercado")
    logger.info(f"  Provider: {config.get('provider', 'yahoo_finance')}")
    logger.info(f"  Tickers: {len(universe)}")
    logger.info(f"  Período: {start_date} a {end_date}")
    logger.info("=" * 60)

    if dry_run:
        logger.info("[DRY RUN] Nenhum arquivo será criado")
        for ticker in universe:
            logger.info(f"  [DRY RUN] Seria baixado: {ticker}")
        return []

    # Rate limiting
    rate_limit = config.get("rate_limit", {})
    delay = rate_limit.get("delay_between_tickers_seconds", 0.5)

    files_generated: list[str] = []
    failed_tickers: list[str] = []
    total_records = 0
    start_time = time.time()

    for i, ticker in enumerate(universe, 1):
        logger.info(f"[{i}/{len(universe)}] Processando {ticker}...")

        # Verifica se arquivo já existe
        output_config = config.get("output", {})
        base_path = output_config.get("path", "data/raw/market/")
        ticker_clean = ticker.replace(".", "_").replace("^", "")
        file_path = root / base_path / "prices" / f"{ticker_clean}.parquet"

        if file_path.exists() and not overwrite:
            logger.info(f"  Arquivo já existe, pulando: {file_path}")
            files_generated.append(str(file_path))
            continue

        # Busca dados
        df = fetch_market_data_for_ticker(ticker, config)

        if df is None or len(df) == 0:
            logger.warning(f"  Sem dados para {ticker}")
            failed_tickers.append(ticker)
            continue

        # Persiste
        try:
            path = _persist_ticker_data(df, ticker, config, root)
            files_generated.append(path)
            total_records += len(df)
            logger.info(f"  ✓ Salvo: {path} ({len(df)} registros)")
        except Exception as e:
            logger.error(f"  Erro ao salvar {ticker}: {e}")
            failed_tickers.append(ticker)

        # Rate limiting
        if delay > 0 and i < len(universe):
            time.sleep(delay)

    elapsed = time.time() - start_time

    # Resumo
    logger.info("=" * 60)
    logger.info("Ingestão concluída")
    logger.info(f"  Tempo total: {elapsed:.1f}s")
    logger.info(f"  Arquivos gerados: {len(files_generated)}")
    logger.info(f"  Registros totais: {total_records:,}")
    logger.info(f"  Falhas: {len(failed_tickers)}")
    if failed_tickers:
        logger.warning(f"  Tickers com falha: {failed_tickers}")
    logger.info("=" * 60)

    return files_generated


def get_ingestion_summary(
    config_path: str | None = None,
    overwrite: bool = False,
) -> IngestionSummary:
    """Executa ingestão e retorna resumo estruturado.

    Args:
        config_path: Caminho do YAML de configuração.
        overwrite: Se True, sobrescreve arquivos existentes.

    Returns:
        IngestionSummary com estatísticas da ingestão.
    """
    root = _get_project_root()
    config = load_data_source_config(config_path)

    universe = config.get("universe", [])
    rate_limit = config.get("rate_limit", {})
    delay = rate_limit.get("delay_between_tickers_seconds", 0.5)

    files_generated: list[str] = []
    failed_tickers: list[str] = []
    total_records = 0
    start_time = time.time()

    for i, ticker in enumerate(universe, 1):
        logger.info(f"[{i}/{len(universe)}] Processando {ticker}...")

        # Busca dados
        df = fetch_market_data_for_ticker(ticker, config)

        if df is None or len(df) == 0:
            failed_tickers.append(ticker)
            continue

        # Persiste
        try:
            path = _persist_ticker_data(df, ticker, config, root)
            files_generated.append(path)
            total_records += len(df)
        except Exception:
            failed_tickers.append(ticker)

        # Rate limiting
        if delay > 0 and i < len(universe):
            time.sleep(delay)

    elapsed = time.time() - start_time

    return IngestionSummary(
        total_tickers=len(universe),
        successful=len(files_generated),
        failed=len(failed_tickers),
        total_records=total_records,
        files_generated=files_generated,
        failed_tickers=failed_tickers,
        execution_time_seconds=elapsed,
    )


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================


def validate_raw_market_data(data_path: str | None = None) -> dict[str, Any]:
    """Valida os dados brutos em data/raw/market/.

    Args:
        data_path: Caminho do diretório de dados. Se None, usa padrão.

    Returns:
        Dicionário com estatísticas de validação.
    """
    root = _get_project_root()
    path = Path(data_path) if data_path else root / "data/raw/market/prices"

    if not path.exists():
        return {
            "valid": False,
            "error": f"Diretório não encontrado: {path}",
            "files": 0,
            "total_records": 0,
        }

    parquet_files = list(path.glob("*.parquet"))

    if not parquet_files:
        return {
            "valid": False,
            "error": "Nenhum arquivo Parquet encontrado",
            "files": 0,
            "total_records": 0,
        }

    total_records = 0
    tickers: list[str] = []
    errors: list[str] = []

    for pf in parquet_files:
        try:
            df = pl.read_parquet(pf)
            total_records += len(df)

            # Verifica colunas obrigatórias
            missing = set(REQUIRED_OUTPUT_COLUMNS) - set(df.columns)
            if missing:
                errors.append(f"{pf.name}: colunas ausentes {missing}")

            # Extrai tickers únicos
            if "ticker" in df.columns:
                tickers.extend(df.select("ticker").unique().to_series().to_list())

        except Exception as e:
            errors.append(f"{pf.name}: erro ao ler - {e}")

    return {
        "valid": len(errors) == 0,
        "files": len(parquet_files),
        "total_records": total_records,
        "tickers": list(set(tickers)),
        "errors": errors,
    }

