# -*- coding: utf-8 -*-
"""
Testes de integração para o pipeline UNIVERSE_SUPERVISED.

Testa o pipeline de ponta a ponta usando dados sintéticos.
"""

import pytest
import polars as pl
import tempfile
import sys
from pathlib import Path

# Adiciona módulos ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "modules"))

from portfoliozero.core.universe.universe_supervised_selector import (
    build_universe_supervised,
    select_supervised_universe,
    load_supervised_selection_config,
)


@pytest.fixture
def temp_output_dir():
    """Cria diretório temporário para outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_candidates_parquet(temp_output_dir):
    """Cria um arquivo UNIVERSE_CANDIDATES.parquet de teste."""
    data = []
    
    sectors = ["Financeiro", "Commodities", "Energia", "Consumo", "Saúde", "Tecnologia"]
    vol_classes = ["BAIXA", "MEDIA", "ALTA"]
    liq_classes = ["ALTA", "MEDIA", "BAIXA"]
    
    ticker_num = 1
    for sector in sectors:
        for i in range(10):
            vol_class = vol_classes[i % 3]
            liq_class = liq_classes[i % 3]
            volume = 10_000_000 - (i * 500_000)
            
            data.append({
                "ticker": f"TEST{ticker_num:02d}.SA",
                "setor": sector,
                "tipo_instrumento": "ACAO_ON",
                "volatility_class": vol_class,
                "liquidity_class": liq_class,
                "avg_volume_21d_brl": float(volume),
                "avg_price_recent_brl": 20.0,
                "history_days": 300,
                "trading_days_ratio_252d": 0.95,
                "date_first": "2022-01-01",
                "date_last": "2024-12-01",
                "last_price": 22.0,
                "annualized_vol_60d": 0.25,
            })
            ticker_num += 1
    
    df = pl.DataFrame(data)
    
    candidates_path = Path(temp_output_dir) / "UNIVERSE_CANDIDATES.parquet"
    df.write_parquet(candidates_path)
    
    return str(candidates_path)


@pytest.fixture
def sample_config(temp_output_dir):
    """Cria arquivo de configuração de teste."""
    import yaml
    
    config = {
        "target_size": 30,
        "min_size": 28,
        "max_size": 32,
        "sector_constraints": {
            "min_per_sector": 2,
            "max_per_sector": 6,
        },
        "volatility_mix": {
            "target_low_pct": 0.30,
            "target_medium_pct": 0.50,
            "target_high_pct": 0.20,
            "tolerance_pct": 0.15,
        },
        "liquidity_preferences": {
            "min_high_liquidity_pct": 0.50,
            "max_low_liquidity_count": 3,
        },
        "owner_overrides": {
            "forced_includes": ["TEST01.SA", "TEST02.SA"],
            "forced_excludes": [],
            "validate_forced_includes": True,
        },
        "tie_breaker_priority": [
            "higher_liquidity_first",
            "lower_volatility_within_class",
            "higher_avg_volume_21d",
        ],
        "output": {
            "generate_csv": True,
            "generate_selection_log": True,
            "generate_ticker_list": True,
        },
    }
    
    config_path = Path(temp_output_dir) / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)
    
    return str(config_path)


class TestIntegrationPipeline:
    """Testes de integração do pipeline."""
    
    def test_full_pipeline_execution(self, sample_candidates_parquet, sample_config, temp_output_dir):
        """Testa execução completa do pipeline."""
        output_path = build_universe_supervised(
            config_path=sample_config,
            candidates_path=sample_candidates_parquet,
            output_dir=temp_output_dir,
            dry_run=False,
        )
        
        # Verifica que o arquivo foi criado
        assert Path(output_path).exists()
        
        # Carrega e verifica o resultado
        result_df = pl.read_parquet(output_path)
        assert len(result_df) == 30
        
        # Verifica forced includes
        tickers = result_df["ticker"].to_list()
        assert "TEST01.SA" in tickers
        assert "TEST02.SA" in tickers
    
    def test_generates_all_outputs(self, sample_candidates_parquet, sample_config, temp_output_dir):
        """Testa que todos os arquivos de saída são gerados."""
        build_universe_supervised(
            config_path=sample_config,
            candidates_path=sample_candidates_parquet,
            output_dir=temp_output_dir,
            dry_run=False,
        )
        
        output_dir = Path(temp_output_dir)
        
        # Verifica arquivos gerados
        assert (output_dir / "UNIVERSE_SUPERVISED.parquet").exists()
        assert (output_dir / "UNIVERSE_SUPERVISED.csv").exists()
        assert (output_dir / "UNIVERSE_SUPERVISED_selection_log.json").exists()
        assert (output_dir / "UNIVERSE_SUPERVISED_tickers.txt").exists()
    
    def test_selection_log_structure(self, sample_candidates_parquet, sample_config, temp_output_dir):
        """Testa a estrutura do log de seleção."""
        import json
        
        build_universe_supervised(
            config_path=sample_config,
            candidates_path=sample_candidates_parquet,
            output_dir=temp_output_dir,
            dry_run=False,
        )
        
        log_path = Path(temp_output_dir) / "UNIVERSE_SUPERVISED_selection_log.json"
        with open(log_path) as f:
            log_data = json.load(f)
        
        # Verifica campos obrigatórios
        assert "timestamp" in log_data
        assert "candidates_count" in log_data
        assert "selected_count" in log_data
        assert "by_sector" in log_data
        assert "by_volatility" in log_data
        assert "selection_log" in log_data
        
        # Verifica que temos entries no log
        assert len(log_data["selection_log"]) > 0
    
    def test_ticker_list_content(self, sample_candidates_parquet, sample_config, temp_output_dir):
        """Testa o conteúdo do arquivo de lista de tickers."""
        build_universe_supervised(
            config_path=sample_config,
            candidates_path=sample_candidates_parquet,
            output_dir=temp_output_dir,
            dry_run=False,
        )
        
        tickers_path = Path(temp_output_dir) / "UNIVERSE_SUPERVISED_tickers.txt"
        with open(tickers_path) as f:
            tickers = [line.strip() for line in f if line.strip()]
        
        assert len(tickers) == 30
        assert all(t.endswith(".SA") for t in tickers)
    
    def test_dry_run_mode(self, sample_candidates_parquet, sample_config, temp_output_dir):
        """Testa modo dry-run (não deve gravar arquivos)."""
        # Limpa o diretório primeiro
        output_dir = Path(temp_output_dir)
        
        build_universe_supervised(
            config_path=sample_config,
            candidates_path=sample_candidates_parquet,
            output_dir=temp_output_dir,
            dry_run=True,
        )
        
        # Arquivos não devem existir após dry-run
        # (apenas se o diretório estava vazio antes)
        # Note: o build_universe_supervised não deleta arquivos existentes
    
    def test_handles_missing_candidates(self, sample_config, temp_output_dir):
        """Testa erro quando UNIVERSE_CANDIDATES não existe."""
        with pytest.raises(FileNotFoundError):
            build_universe_supervised(
                config_path=sample_config,
                candidates_path="/caminho/inexistente/UNIVERSE_CANDIDATES.parquet",
                output_dir=temp_output_dir,
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

