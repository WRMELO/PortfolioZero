"""Testes unitários para o pipeline UNIVERSE_CANDIDATES.

Testes com dados sintéticos em memória para validar a lógica de filtros.
"""

from __future__ import annotations

from datetime import date, datetime

import polars as pl
import pytest

from portfoliozero.core.data.universe_candidates_pipeline import (
    PipelineMetadata,
    ValidationResult,
    _apply_prelist_filters,
    _classify_liquidity,
    _classify_volatility,
    _compute_metrics_per_ticker,
    _normalize_identifiers,
    validate_universe_candidates,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_raw_data() -> pl.DataFrame:
    """Cria dados brutos de exemplo para testes."""
    from datetime import timedelta
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(300)]

    records = []
    for d in dates:
        # PETR4 - Alta liquidez, baixa volatilidade
        records.append({
            "date": d,
            "ticker": "PETR4",
            "close": 35.0 + (hash(str(d)) % 100) / 100,
            "volume": 50_000_000.0,
            "tipo_instrumento": "ACAO_PN",
            "setor": "Commodities",
        })
        # VALE3 - Alta liquidez, média volatilidade
        records.append({
            "date": d,
            "ticker": "VALE3",
            "close": 70.0 + (hash(str(d)) % 200) / 50,
            "volume": 40_000_000.0,
            "tipo_instrumento": "ACAO_ON",
            "setor": "Commodities",
        })
        # MGLU3 - Baixa liquidez (deve ser filtrado)
        records.append({
            "date": d,
            "ticker": "MGLU3",
            "close": 2.0 + (hash(str(d)) % 50) / 100,
            "volume": 1_000_000.0,
            "tipo_instrumento": "ACAO_ON",
            "setor": "Consumo",
        })
        # ITUB4 - Alta liquidez, setor Financeiro
        records.append({
            "date": d,
            "ticker": "ITUB4",
            "close": 30.0 + (hash(str(d)) % 80) / 100,
            "volume": 60_000_000.0,
            "tipo_instrumento": "ACAO_PN",
            "setor": "Financeiro",
        })

    return pl.DataFrame(records)


@pytest.fixture
def sample_rules() -> dict:
    """Regras de seleção de exemplo."""
    return {
        "prelist": {
            "min_avg_volume_21d_brl": 5_000_000,
            "min_price_brl": 5.0,
            "min_history_days": 252,
            "min_trading_days_ratio_252d": 0.9,
            "allowed_instruments": ["ACAO_ON", "ACAO_PN", "BDR"],
        },
        "sectors": {
            "min_distinct_sectors": 6,
            "max_weight_per_sector_pct": 0.35,
            "max_names_per_sector": 6,
        },
        "volatility": {
            "lookback_days": 60,
            "thresholds": {
                "low_max_annualized_vol": 0.20,
                "medium_max_annualized_vol": 0.40,
            },
            "target_proportions": {
                "min_medium_pct": 0.30,
                "max_high_pct": 0.50,
            },
        },
        "universe_size": {
            "target": 30,
            "min": 28,
            "max": 80,
        },
    }


@pytest.fixture
def sample_metrics_df() -> pl.DataFrame:
    """DataFrame com métricas calculadas para testes."""
    return pl.DataFrame({
        "ticker": ["PETR4", "VALE3", "MGLU3", "ITUB4", "WEGE3"],
        "tipo_instrumento": ["ACAO_PN", "ACAO_ON", "ACAO_ON", "ACAO_PN", "ACAO_ON"],
        "setor": ["Commodities", "Commodities", "Consumo", "Financeiro", "Indústria"],
        "date_first": [date(2024, 1, 1)] * 5,
        "date_last": [date(2024, 11, 1)] * 5,
        "history_days": [300, 300, 200, 300, 300],  # MGLU3 tem histórico menor
        "avg_volume_21d_brl": [50_000_000.0, 40_000_000.0, 1_000_000.0, 60_000_000.0, 20_000_000.0],
        "avg_price_recent_brl": [35.0, 70.0, 2.0, 30.0, 45.0],  # MGLU3 preço baixo
        "last_price": [35.0, 70.0, 2.0, 30.0, 45.0],
        "annualized_vol_60d": [0.15, 0.25, 0.50, 0.18, 0.30],
        "trading_days_ratio_252d": [0.95, 0.93, 0.80, 0.96, 0.92],  # MGLU3 ratio baixo
    })


# =============================================================================
# TESTES - DATACLASSES
# =============================================================================


def test_validation_result_creation() -> None:
    """Testa criação de ValidationResult."""
    result = ValidationResult(
        is_valid=True,
        errors=[],
        warnings=["test warning"],
        record_count=10,
    )
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert len(result.warnings) == 1
    assert result.record_count == 10


def test_pipeline_metadata_creation() -> None:
    """Testa criação de PipelineMetadata."""
    now = datetime.now()
    metadata = PipelineMetadata(
        execution_date=now,
        input_record_count=100,
        output_record_count=30,
        filters_applied=["filter1", "filter2"],
        warnings=["warning1"],
    )
    assert metadata.execution_date == now
    assert metadata.input_record_count == 100
    assert metadata.output_record_count == 30
    assert len(metadata.filters_applied) == 2


# =============================================================================
# TESTES - NORMALIZAÇÃO
# =============================================================================


def test_normalize_identifiers(sample_raw_data: pl.DataFrame) -> None:
    """Testa normalização de identificadores."""
    # Adiciona ticker em minúsculas para testar
    df = sample_raw_data.with_columns([
        pl.col("ticker").str.to_lowercase().alias("ticker")
    ])

    normalized = _normalize_identifiers(df)

    # Verifica que todos os tickers estão em maiúsculas
    tickers = normalized.select("ticker").unique().to_series().to_list()
    for ticker in tickers:
        assert ticker == ticker.upper()


# =============================================================================
# TESTES - MÉTRICAS
# =============================================================================


def test_compute_metrics_per_ticker(sample_raw_data: pl.DataFrame, sample_rules: dict) -> None:
    """Testa cálculo de métricas por ticker."""
    normalized = _normalize_identifiers(sample_raw_data)
    metrics = _compute_metrics_per_ticker(normalized, sample_rules)

    # Verifica número de tickers únicos
    assert len(metrics) == 4

    # Verifica colunas obrigatórias
    expected_cols = ["ticker", "history_days", "avg_volume_21d_brl", "avg_price_recent_brl"]
    for col in expected_cols:
        assert col in metrics.columns


def test_classify_volatility(sample_metrics_df: pl.DataFrame, sample_rules: dict) -> None:
    """Testa classificação de volatilidade."""
    df = _classify_volatility(sample_metrics_df, sample_rules)

    assert "volatility_class" in df.columns

    # PETR4 tem vol 0.15 -> BAIXA
    petr = df.filter(pl.col("ticker") == "PETR4").select("volatility_class").item()
    assert petr == "BAIXA"

    # VALE3 tem vol 0.25 -> MEDIA
    vale = df.filter(pl.col("ticker") == "VALE3").select("volatility_class").item()
    assert vale == "MEDIA"

    # MGLU3 tem vol 0.50 -> ALTA
    mglu = df.filter(pl.col("ticker") == "MGLU3").select("volatility_class").item()
    assert mglu == "ALTA"


def test_classify_liquidity(sample_metrics_df: pl.DataFrame) -> None:
    """Testa classificação de liquidez."""
    df = _classify_liquidity(sample_metrics_df)

    assert "liquidity_class" in df.columns

    # ITUB4 tem maior volume -> ALTA
    itub = df.filter(pl.col("ticker") == "ITUB4").select("liquidity_class").item()
    assert itub == "ALTA"


# =============================================================================
# TESTES - FILTROS
# =============================================================================


def test_apply_prelist_filters(sample_metrics_df: pl.DataFrame, sample_rules: dict) -> None:
    """Testa aplicação de filtros da pré-lista."""
    metadata = PipelineMetadata(
        execution_date=datetime.now(),
        input_record_count=len(sample_metrics_df),
        output_record_count=0,
    )

    df = _apply_prelist_filters(sample_metrics_df, sample_rules, metadata)

    # MGLU3 deve ser filtrado (histórico < 252, volume < 5M, preço < 5)
    tickers = df.select("ticker").to_series().to_list()
    assert "MGLU3" not in tickers

    # PETR4, VALE3, ITUB4, WEGE3 devem passar
    assert "PETR4" in tickers
    assert "VALE3" in tickers
    assert "ITUB4" in tickers
    assert "WEGE3" in tickers


# =============================================================================
# TESTES - VALIDAÇÃO
# =============================================================================


def test_validate_universe_candidates_valid(sample_metrics_df: pl.DataFrame, sample_rules: dict) -> None:
    """Testa validação com dados válidos."""
    # Adiciona colunas faltantes para passar validação
    df = _classify_volatility(sample_metrics_df, sample_rules)

    result = validate_universe_candidates(df)

    # Pode ter warnings sobre tamanho do universo, mas não deve ter erros críticos
    assert result.record_count == len(df)


def test_validate_universe_candidates_empty() -> None:
    """Testa validação com DataFrame vazio."""
    df = pl.DataFrame()
    result = validate_universe_candidates(df)

    assert result.is_valid is False
    assert "vazio" in result.errors[0].lower()


def test_validate_universe_candidates_missing_columns() -> None:
    """Testa validação com colunas faltantes."""
    df = pl.DataFrame({
        "ticker": ["PETR4", "VALE3"],
        "close": [35.0, 70.0],
    })

    result = validate_universe_candidates(df)

    assert result.is_valid is False
    assert any("ausentes" in e.lower() for e in result.errors)


# =============================================================================
# TESTES DE INTEGRAÇÃO
# =============================================================================


def test_full_metrics_pipeline(sample_raw_data: pl.DataFrame, sample_rules: dict) -> None:
    """Testa fluxo completo de cálculo de métricas."""
    # Normaliza
    df = _normalize_identifiers(sample_raw_data)

    # Calcula métricas
    df = _compute_metrics_per_ticker(df, sample_rules)

    # Classifica
    df = _classify_volatility(df, sample_rules)
    df = _classify_liquidity(df)

    # Aplica filtros
    metadata = PipelineMetadata(
        execution_date=datetime.now(),
        input_record_count=len(df),
        output_record_count=0,
    )
    df = _apply_prelist_filters(df, sample_rules, metadata)

    # Verifica resultado
    assert len(df) > 0
    assert "volatility_class" in df.columns
    assert "liquidity_class" in df.columns
    assert len(metadata.filters_applied) > 0

