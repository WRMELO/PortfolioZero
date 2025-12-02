"""Testes unitários para o módulo de ingestão de dados de mercado.

Testes com mocks do provider (yfinance) para validar o fluxo de ingestão
e o schema do Parquet gerado.
"""

from __future__ import annotations

import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import polars as pl
import pytest

from portfoliozero.core.data.market_data_ingestion import (
    IngestionResult,
    IngestionSummary,
    REQUIRED_OUTPUT_COLUMNS,
    _resolve_date_range,
    fetch_market_data_for_ticker,
    load_data_source_config,
    validate_raw_market_data,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_config() -> dict[str, Any]:
    """Configuração de exemplo para testes."""
    return {
        "provider": "yahoo_finance",
        "universe": ["PETR4.SA", "VALE3.SA", "ITUB4.SA"],
        "date_range": {
            "start": "2024-01-01",
            "end": "2024-06-30",
        },
        "frequency": "1d",
        "fields": ["open", "high", "low", "close", "adj_close", "volume"],
        "output": {
            "path": "data/raw/market/",
            "partitioning": "per_ticker",
            "format": "parquet",
        },
        "sector_mapping": {
            "PETR4.SA": "Commodities",
            "VALE3.SA": "Commodities",
            "ITUB4.SA": "Financeiro",
        },
        "instrument_type_mapping": {
            "PETR4.SA": "ACAO_PN",
            "VALE3.SA": "ACAO_ON",
            "ITUB4.SA": "ACAO_PN",
        },
        "rate_limit": {
            "delay_between_tickers_seconds": 0.0,
        },
    }


@pytest.fixture
def mock_yfinance_data() -> pd.DataFrame:
    """Dados mockados do yfinance."""
    dates = pd.date_range(start="2024-01-01", end="2024-06-30", freq="B")
    n = len(dates)

    return pd.DataFrame({
        "Date": dates,
        "Open": [35.0 + i * 0.1 for i in range(n)],
        "High": [36.0 + i * 0.1 for i in range(n)],
        "Low": [34.0 + i * 0.1 for i in range(n)],
        "Close": [35.5 + i * 0.1 for i in range(n)],
        "Adj Close": [35.5 + i * 0.1 for i in range(n)],
        "Volume": [1000000 + i * 1000 for i in range(n)],
        "Dividends": [0.0] * n,
        "Stock Splits": [0.0] * n,
    }).set_index("Date")


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Diretório temporário para dados de teste."""
    data_dir = tmp_path / "data" / "raw" / "market" / "prices"
    data_dir.mkdir(parents=True)
    return data_dir


# =============================================================================
# TESTES - DATACLASSES
# =============================================================================


def test_ingestion_result_creation() -> None:
    """Testa criação de IngestionResult."""
    result = IngestionResult(
        ticker="PETR4.SA",
        success=True,
        records=100,
        file_path="/path/to/file.parquet",
    )
    assert result.success is True
    assert result.records == 100
    assert result.ticker == "PETR4.SA"


def test_ingestion_result_failure() -> None:
    """Testa IngestionResult com falha."""
    result = IngestionResult(
        ticker="INVALID.SA",
        success=False,
        error="Ticker não encontrado",
    )
    assert result.success is False
    assert result.error == "Ticker não encontrado"
    assert result.records == 0


def test_ingestion_summary_creation() -> None:
    """Testa criação de IngestionSummary."""
    summary = IngestionSummary(
        total_tickers=10,
        successful=8,
        failed=2,
        total_records=1000,
        files_generated=["file1.parquet", "file2.parquet"],
        failed_tickers=["FAIL1.SA", "FAIL2.SA"],
        execution_time_seconds=10.5,
    )
    assert summary.total_tickers == 10
    assert summary.successful == 8
    assert summary.failed == 2
    assert len(summary.files_generated) == 2
    assert len(summary.failed_tickers) == 2


# =============================================================================
# TESTES - CONFIGURAÇÃO
# =============================================================================


def test_resolve_date_range_with_dates(sample_config: dict) -> None:
    """Testa resolução de date_range com datas fixas."""
    start, end = _resolve_date_range(sample_config)
    assert start == "2024-01-01"
    assert end == "2024-06-30"


def test_resolve_date_range_with_today() -> None:
    """Testa resolução de date_range com 'today'."""
    config = {
        "date_range": {
            "start": "2024-01-01",
            "end": "today",
        }
    }
    start, end = _resolve_date_range(config)
    assert start == "2024-01-01"
    assert end == datetime.now().strftime("%Y-%m-%d")


def test_load_config_file_not_found() -> None:
    """Testa erro quando arquivo de config não existe."""
    with pytest.raises(FileNotFoundError) as exc_info:
        load_data_source_config("/path/inexistente/config.yaml")
    
    assert "não encontrado" in str(exc_info.value).lower()


# =============================================================================
# TESTES - INGESTÃO COM MOCK
# =============================================================================


def test_fetch_market_data_for_ticker_with_mock(
    sample_config: dict,
    mock_yfinance_data: pd.DataFrame,
) -> None:
    """Testa fetch de dados com yfinance mockado."""
    with patch("portfoliozero.core.data.market_data_ingestion.yf") as mock_yf:
        # Configura mock
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_yfinance_data.copy()
        mock_yf.Ticker.return_value = mock_ticker

        # Executa
        df = fetch_market_data_for_ticker("PETR4.SA", sample_config)

        # Verifica
        assert df is not None
        assert len(df) > 0

        # Verifica colunas obrigatórias
        for col in REQUIRED_OUTPUT_COLUMNS:
            assert col in df.columns, f"Coluna obrigatória ausente: {col}"

        # Verifica valores
        assert df.select("ticker").unique().to_series().to_list() == ["PETR4.SA"]


def test_fetch_market_data_empty_response(sample_config: dict) -> None:
    """Testa comportamento quando yfinance retorna dados vazios."""
    with patch("portfoliozero.core.data.market_data_ingestion.yf") as mock_yf:
        # Configura mock para retornar DataFrame vazio
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_ticker

        # Executa
        df = fetch_market_data_for_ticker("INVALID.SA", sample_config)

        # Verifica
        assert df is None


def test_fetch_market_data_with_sector_mapping(
    sample_config: dict,
    mock_yfinance_data: pd.DataFrame,
) -> None:
    """Testa que setor e tipo_instrumento são mapeados corretamente."""
    with patch("portfoliozero.core.data.market_data_ingestion.yf") as mock_yf:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_yfinance_data.copy()
        mock_yf.Ticker.return_value = mock_ticker

        df = fetch_market_data_for_ticker("PETR4.SA", sample_config)

        assert df is not None
        assert "setor" in df.columns
        assert "tipo_instrumento" in df.columns
        
        # Verifica valores do mapeamento
        setor = df.select("setor").unique().to_series().to_list()[0]
        tipo = df.select("tipo_instrumento").unique().to_series().to_list()[0]
        
        assert setor == "Commodities"
        assert tipo == "ACAO_PN"


# =============================================================================
# TESTES - VALIDAÇÃO
# =============================================================================


def test_validate_raw_market_data_no_directory() -> None:
    """Testa validação quando diretório não existe."""
    result = validate_raw_market_data("/path/inexistente")
    
    assert result["valid"] is False
    assert "não encontrado" in result.get("error", "").lower()


def test_validate_raw_market_data_empty_directory(temp_data_dir: Path) -> None:
    """Testa validação quando diretório está vazio."""
    result = validate_raw_market_data(str(temp_data_dir))
    
    assert result["valid"] is False
    assert result["files"] == 0


def test_validate_raw_market_data_with_valid_parquet(temp_data_dir: Path) -> None:
    """Testa validação com arquivo Parquet válido."""
    # Cria arquivo de teste
    df = pl.DataFrame({
        "date": [date(2024, 1, 1), date(2024, 1, 2)],
        "ticker": ["PETR4.SA", "PETR4.SA"],
        "close": [35.0, 35.5],
        "volume": [1000000, 1100000],
    })
    df.write_parquet(temp_data_dir / "PETR4_SA.parquet")

    result = validate_raw_market_data(str(temp_data_dir))

    assert result["valid"] is True
    assert result["files"] == 1
    assert result["total_records"] == 2
    assert "PETR4.SA" in result["tickers"]


def test_validate_raw_market_data_missing_columns(temp_data_dir: Path) -> None:
    """Testa validação detecta colunas ausentes."""
    # Cria arquivo sem coluna 'volume'
    df = pl.DataFrame({
        "date": [date(2024, 1, 1)],
        "ticker": ["PETR4.SA"],
        "close": [35.0],
        # Faltando 'volume'
    })
    df.write_parquet(temp_data_dir / "PETR4_SA.parquet")

    result = validate_raw_market_data(str(temp_data_dir))

    assert result["valid"] is False
    assert len(result["errors"]) > 0
    assert any("volume" in err.lower() for err in result["errors"])


# =============================================================================
# TESTES - SCHEMA DO OUTPUT
# =============================================================================


def test_output_schema_has_required_columns(
    sample_config: dict,
    mock_yfinance_data: pd.DataFrame,
) -> None:
    """Testa que o output tem todas as colunas obrigatórias."""
    with patch("portfoliozero.core.data.market_data_ingestion.yf") as mock_yf:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_yfinance_data.copy()
        mock_yf.Ticker.return_value = mock_ticker

        df = fetch_market_data_for_ticker("PETR4.SA", sample_config)

        assert df is not None
        
        # Colunas obrigatórias para universe_candidates_pipeline
        required = ["date", "ticker", "close", "volume"]
        for col in required:
            assert col in df.columns, f"Coluna obrigatória ausente: {col}"


def test_output_date_is_date_type(
    sample_config: dict,
    mock_yfinance_data: pd.DataFrame,
) -> None:
    """Testa que a coluna date é do tipo Date."""
    with patch("portfoliozero.core.data.market_data_ingestion.yf") as mock_yf:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_yfinance_data.copy()
        mock_yf.Ticker.return_value = mock_ticker

        df = fetch_market_data_for_ticker("PETR4.SA", sample_config)

        assert df is not None
        assert df.schema["date"] == pl.Date


def test_output_numeric_columns_are_numeric(
    sample_config: dict,
    mock_yfinance_data: pd.DataFrame,
) -> None:
    """Testa que colunas numéricas são do tipo correto."""
    with patch("portfoliozero.core.data.market_data_ingestion.yf") as mock_yf:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_yfinance_data.copy()
        mock_yf.Ticker.return_value = mock_ticker

        df = fetch_market_data_for_ticker("PETR4.SA", sample_config)

        assert df is not None
        
        # Verifica tipos numéricos
        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            if col in df.columns:
                dtype = df.schema[col]
                assert dtype in [pl.Float64, pl.Int64, pl.Float32, pl.Int32], \
                    f"Coluna {col} deveria ser numérica, mas é {dtype}"


# =============================================================================
# TESTES - INTEGRAÇÃO
# =============================================================================


def test_integration_ingest_and_validate(
    sample_config: dict,
    mock_yfinance_data: pd.DataFrame,
    temp_data_dir: Path,
) -> None:
    """Teste de integração: ingestão + validação."""
    with patch("portfoliozero.core.data.market_data_ingestion.yf") as mock_yf:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_yfinance_data.copy()
        mock_yf.Ticker.return_value = mock_ticker

        # Executa ingestão para um ticker
        df = fetch_market_data_for_ticker("PETR4.SA", sample_config)
        
        assert df is not None
        
        # Salva no diretório temporário
        df.write_parquet(temp_data_dir / "PETR4_SA.parquet")

        # Valida
        result = validate_raw_market_data(str(temp_data_dir))

        assert result["valid"] is True
        assert result["total_records"] == len(df)


def test_unsupported_provider_raises_error(sample_config: dict) -> None:
    """Testa que provider não suportado levanta erro."""
    config = sample_config.copy()
    config["provider"] = "unsupported_provider"

    with pytest.raises(ValueError) as exc_info:
        fetch_market_data_for_ticker("PETR4.SA", config)
    
    assert "não suportado" in str(exc_info.value).lower()

