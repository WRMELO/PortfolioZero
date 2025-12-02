"""Testes de integração para o pipeline UNIVERSE_CANDIDATES.

Testes que exercitam o fluxo completo do pipeline com dados sintéticos,
sem fazer chamadas de rede (offline).
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import polars as pl
import pytest

# Adiciona o diretório do projeto ao path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "modules"))
sys.path.insert(0, str(project_root / "scripts"))

from portfoliozero.core.data.universe_candidates_pipeline import (
    build_universe_candidates,
    load_universe_candidates,
    validate_universe_candidates,
    get_pipeline_metadata,
)

# Importa função de sumarização do script
from build_universe_candidates import (
    summarize_universe_candidates,
    TARGET_MIN_CANDIDATES,
    TARGET_MAX_CANDIDATES,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_market_data_large() -> pl.DataFrame:
    """Gera dados de mercado sintéticos com 80+ tickers para passar nos filtros."""
    tickers = []
    sectors = ["Financeiro", "Commodities", "Energia", "Consumo", "Saúde", "Tecnologia", "Indústria", "Utilidades"]
    instrument_types = ["ACAO_ON", "ACAO_PN"]

    # Gera 90 tickers para ter margem
    for i in range(90):
        sector_idx = i % len(sectors)
        ticker = f"TEST{i:03d}{'3' if i % 2 == 0 else '4'}"
        tickers.append({
            "ticker": ticker,
            "setor": sectors[sector_idx],
            "tipo_instrumento": instrument_types[i % 2],
        })

    # Gera 400 dias de dados para cada ticker
    base_date = date(2023, 1, 1)
    records = []

    for ticker_info in tickers:
        base_price = 20 + (hash(ticker_info["ticker"]) % 100)
        base_volume = 10_000_000 + (hash(ticker_info["ticker"]) % 50_000_000)

        for day_offset in range(400):
            current_date = base_date + timedelta(days=day_offset)
            if current_date.weekday() < 5:  # Dias úteis
                price_variation = (hash(str(current_date) + ticker_info["ticker"]) % 1000) / 10000
                records.append({
                    "date": current_date,
                    "ticker": ticker_info["ticker"],
                    "close": base_price * (1 + price_variation),
                    "volume": base_volume * (0.8 + (hash(str(current_date)) % 40) / 100),
                    "tipo_instrumento": ticker_info["tipo_instrumento"],
                    "setor": ticker_info["setor"],
                })

    return pl.DataFrame(records)


@pytest.fixture
def sample_market_data_small() -> pl.DataFrame:
    """Gera dados de mercado sintéticos com poucos tickers (fora do intervalo alvo)."""
    tickers = [
        {"ticker": "PETR4", "setor": "Commodities", "tipo_instrumento": "ACAO_PN"},
        {"ticker": "VALE3", "setor": "Commodities", "tipo_instrumento": "ACAO_ON"},
        {"ticker": "ITUB4", "setor": "Financeiro", "tipo_instrumento": "ACAO_PN"},
    ]

    base_date = date(2023, 1, 1)
    records = []

    for ticker_info in tickers:
        base_price = 30 + (hash(ticker_info["ticker"]) % 50)
        base_volume = 50_000_000

        for day_offset in range(400):
            current_date = base_date + timedelta(days=day_offset)
            if current_date.weekday() < 5:
                records.append({
                    "date": current_date,
                    "ticker": ticker_info["ticker"],
                    "close": base_price * (1 + (day_offset % 10) / 1000),
                    "volume": base_volume,
                    "tipo_instrumento": ticker_info["tipo_instrumento"],
                    "setor": ticker_info["setor"],
                })

    return pl.DataFrame(records)


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Diretório temporário para dados de teste."""
    # Cria estrutura de diretórios
    (tmp_path / "data" / "raw" / "market" / "prices").mkdir(parents=True)
    (tmp_path / "data" / "universe").mkdir(parents=True)
    (tmp_path / "config" / "experiments").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def mock_config_files(temp_data_dir: Path) -> dict[str, Path]:
    """Cria arquivos de configuração de teste."""
    # universe_selection_rules_v1.yaml - com parâmetros relaxados para teste
    selection_rules = {
        "description": "Regras de teste",
        "prelist": {
            "min_avg_volume_21d_brl": 1_000_000,  # Mais relaxado para teste
            "min_price_brl": 1.0,
            "min_history_days": 200,  # Menos exigente
            "min_trading_days_ratio_252d": 0.7,
            "allowed_instruments": ["ACAO_ON", "ACAO_PN", "BDR"],
        },
        "sectors": {
            "min_distinct_sectors": 3,
            "max_weight_per_sector_pct": 0.5,
            "max_names_per_sector": 15,  # Mais relaxado
        },
        "volatility": {
            "lookback_days": 60,
            "thresholds": {
                "low_max_annualized_vol": 0.20,
                "medium_max_annualized_vol": 0.40,
            },
        },
        "universe_size": {
            "target": 30,
            "min": 28,
            "max": 100,  # Mais relaxado para teste
        },
    }

    selection_rules_path = temp_data_dir / "config" / "experiments" / "universe_selection_rules_v1.yaml"
    import yaml
    with open(selection_rules_path, "w") as f:
        yaml.dump(selection_rules, f)

    # universe_pipeline_topology_v1.yaml
    topology = {
        "description": "Topologia de teste",
        "pipeline": {"name": "test_pipeline", "version": "1.0"},
        "paths": {
            "raw": "data/raw/market/",
            "output": "data/universe/",
        },
    }

    topology_path = temp_data_dir / "config" / "experiments" / "universe_pipeline_topology_v1.yaml"
    with open(topology_path, "w") as f:
        yaml.dump(topology, f)

    return {
        "selection_rules": selection_rules_path,
        "topology": topology_path,
    }


# =============================================================================
# TESTES - SUMARIZAÇÃO
# =============================================================================


def test_summarize_universe_candidates_basic() -> None:
    """Testa função de sumarização com DataFrame básico."""
    df = pl.DataFrame({
        "ticker": ["A", "B", "C", "D", "E"],
        "setor": ["Financeiro", "Financeiro", "Commodities", "Energia", "Tecnologia"],
        "volatility_class": ["BAIXA", "MEDIA", "ALTA", "BAIXA", "MEDIA"],
        "liquidity_class": ["ALTA", "ALTA", "MEDIA", "BAIXA", "BAIXA"],
    })

    summary = summarize_universe_candidates(df)

    # Verifica estrutura
    assert "total_candidates" in summary
    assert "in_target_range" in summary
    assert "by_sector" in summary
    assert "by_volatility_class" in summary
    assert "by_liquidity_class" in summary

    # Verifica valores
    assert summary["total_candidates"] == 5
    assert summary["in_target_range"] is False  # 5 < 60

    # Verifica contagens por setor
    assert summary["by_sector"]["Financeiro"] == 2
    assert summary["by_sector"]["Commodities"] == 1

    # Verifica contagens por volatilidade
    assert summary["by_volatility_class"]["BAIXA"] == 2
    assert summary["by_volatility_class"]["MEDIA"] == 2
    assert summary["by_volatility_class"]["ALTA"] == 1


def test_summarize_universe_candidates_in_range() -> None:
    """Testa que in_target_range é True quando dentro do intervalo."""
    # Cria DataFrame com 70 tickers (dentro do intervalo 60-80)
    df = pl.DataFrame({
        "ticker": [f"T{i:03d}" for i in range(70)],
        "setor": ["Financeiro"] * 70,
        "volatility_class": ["MEDIA"] * 70,
        "liquidity_class": ["ALTA"] * 70,
    })

    summary = summarize_universe_candidates(df)

    assert summary["total_candidates"] == 70
    assert summary["in_target_range"] is True


def test_summarize_universe_candidates_out_of_range_low() -> None:
    """Testa que in_target_range é False quando abaixo do mínimo."""
    df = pl.DataFrame({
        "ticker": [f"T{i:03d}" for i in range(30)],
        "setor": ["Financeiro"] * 30,
        "volatility_class": ["MEDIA"] * 30,
        "liquidity_class": ["ALTA"] * 30,
    })

    summary = summarize_universe_candidates(df)

    assert summary["total_candidates"] == 30
    assert summary["in_target_range"] is False


def test_summarize_universe_candidates_out_of_range_high() -> None:
    """Testa que in_target_range é False quando acima do máximo."""
    df = pl.DataFrame({
        "ticker": [f"T{i:03d}" for i in range(100)],
        "setor": ["Financeiro"] * 100,
        "volatility_class": ["MEDIA"] * 100,
        "liquidity_class": ["ALTA"] * 100,
    })

    summary = summarize_universe_candidates(df)

    assert summary["total_candidates"] == 100
    assert summary["in_target_range"] is False


def test_summarize_universe_candidates_serializable() -> None:
    """Testa que o resumo é serializável para JSON."""
    df = pl.DataFrame({
        "ticker": ["A", "B", "C"],
        "setor": ["Financeiro", "Commodities", "Energia"],
        "volatility_class": ["BAIXA", "MEDIA", "ALTA"],
        "liquidity_class": ["ALTA", "MEDIA", "BAIXA"],
    })

    summary = summarize_universe_candidates(df)

    # Deve ser possível serializar para JSON
    json_str = json.dumps(summary)
    assert json_str is not None

    # Deve ser possível deserializar
    loaded = json.loads(json_str)
    assert loaded["total_candidates"] == 3


# =============================================================================
# TESTES - PIPELINE COM DADOS SINTÉTICOS
# =============================================================================


def test_pipeline_with_large_dataset(
    sample_market_data_large: pl.DataFrame,
    temp_data_dir: Path,
    mock_config_files: dict[str, Path],
) -> None:
    """Testa pipeline completo com dataset grande (caminho feliz)."""
    # Salva dados sintéticos
    data_path = temp_data_dir / "data" / "raw" / "market" / "prices" / "synthetic.parquet"
    sample_market_data_large.write_parquet(data_path)

    # Executa pipeline com configs customizadas
    config_paths = {
        "selection_rules": str(mock_config_files["selection_rules"]),
        "pipeline_topology": str(mock_config_files["topology"]),
        "raw_market": str(temp_data_dir / "data" / "raw" / "market"),
        "output_file": str(temp_data_dir / "data" / "universe" / "UNIVERSE_CANDIDATES.parquet"),
        "output_csv": str(temp_data_dir / "data" / "universe" / "UNIVERSE_CANDIDATES.csv"),
        "metadata_file": str(temp_data_dir / "data" / "universe" / "UNIVERSE_CANDIDATES_metadata.json"),
    }

    # Executa pipeline
    output_path = build_universe_candidates(config_paths=config_paths, force_refresh=True)

    # Verifica que arquivo foi criado
    assert Path(output_path).exists()

    # Carrega e valida resultado
    df = load_universe_candidates(output_path)
    assert len(df) > 0

    validation = validate_universe_candidates(df)
    assert validation.is_valid

    # Gera resumo
    summary = summarize_universe_candidates(df)
    assert summary["total_candidates"] > 0
    assert "by_sector" in summary
    assert len(summary["by_sector"]) > 0


def test_pipeline_with_small_dataset_produces_few_candidates(
    sample_market_data_small: pl.DataFrame,
    temp_data_dir: Path,
    mock_config_files: dict[str, Path],
) -> None:
    """Testa pipeline com dataset pequeno (produz poucos candidatos)."""
    # Salva dados sintéticos
    data_path = temp_data_dir / "data" / "raw" / "market" / "prices" / "synthetic.parquet"
    sample_market_data_small.write_parquet(data_path)

    config_paths = {
        "selection_rules": str(mock_config_files["selection_rules"]),
        "pipeline_topology": str(mock_config_files["topology"]),
        "raw_market": str(temp_data_dir / "data" / "raw" / "market"),
        "output_file": str(temp_data_dir / "data" / "universe" / "UNIVERSE_CANDIDATES.parquet"),
        "output_csv": str(temp_data_dir / "data" / "universe" / "UNIVERSE_CANDIDATES.csv"),
        "metadata_file": str(temp_data_dir / "data" / "universe" / "UNIVERSE_CANDIDATES_metadata.json"),
    }

    # Executa pipeline
    output_path = build_universe_candidates(config_paths=config_paths, force_refresh=True)

    # Carrega resultado
    df = load_universe_candidates(output_path)

    # Gera resumo
    summary = summarize_universe_candidates(df)

    # Com poucos tickers, deve estar fora do intervalo
    assert summary["total_candidates"] < TARGET_MIN_CANDIDATES
    assert summary["in_target_range"] is False


# =============================================================================
# TESTES - VALIDAÇÃO
# =============================================================================


def test_validate_universe_candidates_with_valid_data() -> None:
    """Testa validação com dados válidos."""
    df = pl.DataFrame({
        "ticker": ["PETR4", "VALE3", "ITUB4"],
        "tipo_instrumento": ["ACAO_PN", "ACAO_ON", "ACAO_PN"],
        "avg_volume_21d_brl": [50_000_000.0, 40_000_000.0, 60_000_000.0],
        "avg_price_recent_brl": [35.0, 70.0, 30.0],
        "history_days": [300, 300, 300],
        "trading_days_ratio_252d": [0.95, 0.93, 0.96],
        "annualized_vol_60d": [0.25, 0.30, 0.20],
        "volatility_class": ["MEDIA", "MEDIA", "BAIXA"],
    })

    result = validate_universe_candidates(df)

    # Deve ser válido (sem erros críticos)
    # Pode ter warnings sobre tamanho do universo
    assert result.record_count == 3


def test_validate_universe_candidates_with_empty_df() -> None:
    """Testa validação com DataFrame vazio."""
    df = pl.DataFrame()

    result = validate_universe_candidates(df)

    assert result.is_valid is False
    assert result.record_count == 0


# =============================================================================
# TESTES - METADADOS
# =============================================================================


def test_pipeline_produces_metadata(
    sample_market_data_large: pl.DataFrame,
    temp_data_dir: Path,
    mock_config_files: dict[str, Path],
) -> None:
    """Testa que o pipeline produz metadados."""
    # Salva dados sintéticos
    data_path = temp_data_dir / "data" / "raw" / "market" / "prices" / "synthetic.parquet"
    sample_market_data_large.write_parquet(data_path)

    config_paths = {
        "selection_rules": str(mock_config_files["selection_rules"]),
        "pipeline_topology": str(mock_config_files["topology"]),
        "raw_market": str(temp_data_dir / "data" / "raw" / "market"),
        "output_file": str(temp_data_dir / "data" / "universe" / "UNIVERSE_CANDIDATES.parquet"),
        "output_csv": str(temp_data_dir / "data" / "universe" / "UNIVERSE_CANDIDATES.csv"),
        "metadata_file": str(temp_data_dir / "data" / "universe" / "UNIVERSE_CANDIDATES_metadata.json"),
    }

    # Executa pipeline
    output_path = build_universe_candidates(config_paths=config_paths, force_refresh=True)

    # Carrega metadados
    metadata = get_pipeline_metadata(output_path)

    assert metadata is not None
    assert metadata.input_record_count > 0
    assert metadata.output_record_count >= 0
    assert len(metadata.filters_applied) > 0


def test_summarize_with_metadata(
    sample_market_data_large: pl.DataFrame,
    temp_data_dir: Path,
    mock_config_files: dict[str, Path],
) -> None:
    """Testa sumarização com metadados do pipeline."""
    # Salva dados sintéticos
    data_path = temp_data_dir / "data" / "raw" / "market" / "prices" / "synthetic.parquet"
    sample_market_data_large.write_parquet(data_path)

    config_paths = {
        "selection_rules": str(mock_config_files["selection_rules"]),
        "pipeline_topology": str(mock_config_files["topology"]),
        "raw_market": str(temp_data_dir / "data" / "raw" / "market"),
        "output_file": str(temp_data_dir / "data" / "universe" / "UNIVERSE_CANDIDATES.parquet"),
        "output_csv": str(temp_data_dir / "data" / "universe" / "UNIVERSE_CANDIDATES.csv"),
        "metadata_file": str(temp_data_dir / "data" / "universe" / "UNIVERSE_CANDIDATES_metadata.json"),
    }

    # Executa pipeline
    output_path = build_universe_candidates(config_paths=config_paths, force_refresh=True)

    # Carrega resultado e metadados
    df = load_universe_candidates(output_path)
    metadata = get_pipeline_metadata(output_path)

    # Gera resumo com metadados
    summary = summarize_universe_candidates(df, metadata)

    # Verifica que metadados estão incluídos
    assert "pipeline_metadata" in summary
    assert "execution_date" in summary["pipeline_metadata"]
    assert "input_record_count" in summary["pipeline_metadata"]
    assert "filters_applied" in summary["pipeline_metadata"]

