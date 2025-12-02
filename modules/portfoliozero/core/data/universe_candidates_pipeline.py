"""Pipeline para construção do UNIVERSE_CANDIDATES (pré-lista de 60-80 ativos).

Este módulo implementa o pipeline de dados do Trilho A do PortfolioZero,
responsável por gerar a pré-lista de ativos candidatos ao universo supervisionado.

O pipeline:
1. Lê dados brutos de mercado (preços, volumes) de data/raw/market/
2. Normaliza identificadores e calcula métricas
3. Aplica filtros de pré-lista conforme universe_selection_rules_v1.yaml
4. Gera UNIVERSE_CANDIDATES.parquet em data/universe/

Example:
    >>> from portfoliozero.core.data.universe_candidates_pipeline import (
    ...     build_universe_candidates,
    ...     load_universe_candidates,
    ...     validate_universe_candidates,
    ... )
    >>> path = build_universe_candidates()
    >>> df = load_universe_candidates(path)
    >>> result = validate_universe_candidates(df)
    >>> print(f"Valid: {result.is_valid}, Records: {result.record_count}")
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl
import yaml

logger = logging.getLogger(__name__)

# =============================================================================
# DATACLASSES
# =============================================================================


@dataclass
class ValidationResult:
    """Resultado da validação de dados do pipeline.

    Attributes:
        is_valid: Se o DataFrame passou em todas as validações críticas.
        errors: Lista de erros críticos encontrados.
        warnings: Lista de avisos (não impedem is_valid=True).
        record_count: Número de registros no DataFrame validado.
    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    record_count: int = 0


@dataclass
class PipelineMetadata:
    """Metadados de execução do pipeline.

    Attributes:
        execution_date: Data/hora da execução.
        input_record_count: Número de registros de entrada (antes dos filtros).
        output_record_count: Número de registros de saída (após filtros).
        filters_applied: Lista de filtros aplicados durante o pipeline.
        warnings: Lista de avisos gerados durante a execução.
    """

    execution_date: datetime
    input_record_count: int
    output_record_count: int
    filters_applied: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# =============================================================================
# PATHS PADRÃO
# =============================================================================

DEFAULT_PATHS = {
    "selection_rules": "config/experiments/universe_selection_rules_v1.yaml",
    "pipeline_topology": "config/experiments/universe_pipeline_topology_v1.yaml",
    "raw_market": "data/raw/market/",
    "interim": "data/interim/",
    "output_universe": "data/universe/",
    "output_file": "data/universe/UNIVERSE_CANDIDATES.parquet",
    "output_csv": "data/universe/UNIVERSE_CANDIDATES.csv",
    "metadata_file": "data/universe/UNIVERSE_CANDIDATES_metadata.json",
}

# Colunas obrigatórias no output
REQUIRED_OUTPUT_COLUMNS = [
    "ticker",
    "tipo_instrumento",
    "avg_volume_21d_brl",
    "avg_price_recent_brl",
    "history_days",
    "trading_days_ratio_252d",
    "annualized_vol_60d",
    "volatility_class",
]


# =============================================================================
# FUNÇÕES DE CONFIGURAÇÃO
# =============================================================================


def _get_project_root() -> Path:
    """Retorna o diretório raiz do projeto."""
    # Navega a partir deste arquivo até a raiz
    current = Path(__file__).resolve()
    # modules/portfoliozero/core/data/ -> 4 níveis acima
    for _ in range(5):
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    # Fallback: diretório de trabalho atual
    return Path.cwd()


def _load_yaml_config(path: str | Path) -> dict[str, Any]:
    """Carrega um arquivo YAML de configuração.

    Args:
        path: Caminho do arquivo YAML.

    Returns:
        Dicionário com o conteúdo do arquivo.

    Raises:
        FileNotFoundError: Se o arquivo não existir.
        yaml.YAMLError: Se o arquivo não for YAML válido.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {path}")

    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_selection_rules(config_paths: dict[str, str] | None = None) -> dict[str, Any]:
    """Carrega as regras de seleção do universo.

    Args:
        config_paths: Dicionário com caminhos personalizados.

    Returns:
        Dicionário com as regras de seleção.
    """
    root = _get_project_root()
    path = config_paths.get("selection_rules") if config_paths else None
    path = path or DEFAULT_PATHS["selection_rules"]
    return _load_yaml_config(root / path)


def _load_pipeline_topology(config_paths: dict[str, str] | None = None) -> dict[str, Any]:
    """Carrega a topologia do pipeline.

    Args:
        config_paths: Dicionário com caminhos personalizados.

    Returns:
        Dicionário com a topologia.
    """
    root = _get_project_root()
    path = config_paths.get("pipeline_topology") if config_paths else None
    path = path or DEFAULT_PATHS["pipeline_topology"]
    return _load_yaml_config(root / path)


# =============================================================================
# FUNÇÕES DE LEITURA DE DADOS
# =============================================================================


def _read_raw_market_data(raw_market_path: Path) -> pl.DataFrame:
    """Lê todos os arquivos Parquet de dados de mercado.

    Args:
        raw_market_path: Diretório contendo os arquivos Parquet.

    Returns:
        DataFrame consolidado com todos os dados de mercado.

    Raises:
        RuntimeError: Se não houver arquivos ou colunas mínimas ausentes.
    """
    if not raw_market_path.exists():
        raise RuntimeError(
            f"Diretório de dados brutos não encontrado: {raw_market_path}\n"
            "Execute primeiro a ingestão de dados para popular data/raw/market/"
        )

    # Procura arquivos Parquet recursivamente
    parquet_files = list(raw_market_path.glob("**/*.parquet"))

    if not parquet_files:
        raise RuntimeError(
            f"Nenhum arquivo Parquet encontrado em: {raw_market_path}\n"
            "Popule data/raw/market/ com dados de preços/volumes antes de executar o pipeline."
        )

    logger.info(f"Encontrados {len(parquet_files)} arquivos Parquet em {raw_market_path}")

    # Lê e concatena todos os arquivos
    dfs = []
    for pf in parquet_files:
        try:
            df = pl.read_parquet(pf)
            dfs.append(df)
            logger.debug(f"Lido: {pf.name} ({len(df)} registros)")
        except Exception as e:
            logger.warning(f"Erro ao ler {pf}: {e}")

    if not dfs:
        raise RuntimeError("Nenhum arquivo Parquet pôde ser lido com sucesso.")

    # Concatena todos os DataFrames
    combined = pl.concat(dfs, how="diagonal")

    # Verifica colunas mínimas
    required_cols = {"date", "ticker", "close", "volume"}
    # Normaliza nomes de colunas para lowercase
    combined = combined.rename({col: col.lower() for col in combined.columns})
    found_cols = set(combined.columns)

    missing = required_cols - found_cols
    if missing:
        raise RuntimeError(
            f"Colunas mínimas ausentes nos dados brutos.\n"
            f"Esperadas: {required_cols}\n"
            f"Encontradas: {found_cols}\n"
            f"Faltando: {missing}"
        )

    logger.info(f"Dados brutos carregados: {len(combined)} registros, {len(combined.columns)} colunas")
    return combined


# =============================================================================
# FUNÇÕES DE CÁLCULO DE MÉTRICAS
# =============================================================================


def _normalize_identifiers(df: pl.DataFrame) -> pl.DataFrame:
    """Normaliza identificadores (ticker em maiúsculas, datas consistentes).

    Args:
        df: DataFrame com dados brutos.

    Returns:
        DataFrame com identificadores normalizados.
    """
    df = df.with_columns([
        pl.col("ticker").str.to_uppercase().str.strip_chars().alias("ticker"),
        pl.col("date").cast(pl.Date).alias("date"),
    ])

    # Remove duplicatas (mesmo ticker/data)
    df = df.unique(subset=["ticker", "date"], keep="last")

    return df.sort(["ticker", "date"])


def _compute_metrics_per_ticker(df: pl.DataFrame, rules: dict[str, Any]) -> pl.DataFrame:
    """Calcula métricas agregadas por ticker.

    Args:
        df: DataFrame com dados de mercado normalizados.
        rules: Regras de seleção do YAML.

    Returns:
        DataFrame com uma linha por ticker e métricas calculadas.
    """
    vol_lookback = rules.get("volatility", {}).get("lookback_days", 60)

    # Calcula retornos diários
    df = df.sort(["ticker", "date"]).with_columns([
        (pl.col("close") / pl.col("close").shift(1).over("ticker") - 1).alias("daily_return")
    ])

    # Agregações por ticker
    metrics = df.group_by("ticker").agg([
        # Datas
        pl.col("date").min().alias("date_first"),
        pl.col("date").max().alias("date_last"),
        pl.col("date").count().alias("history_days"),

        # Volume médio 21 dias (últimos registros)
        pl.col("volume").tail(21).mean().alias("avg_volume_21d_brl"),

        # Preço médio recente (últimos 21 dias)
        pl.col("close").tail(21).mean().alias("avg_price_recent_brl"),

        # Último preço
        pl.col("close").last().alias("last_price"),

        # Volatilidade anualizada (últimos N dias)
        (pl.col("daily_return").tail(vol_lookback).std() * (252 ** 0.5)).alias("annualized_vol_60d"),

        # Tipo de instrumento (se disponível)
        pl.col("tipo_instrumento").first().alias("tipo_instrumento") if "tipo_instrumento" in df.columns else pl.lit("ACAO_ON").alias("tipo_instrumento"),

        # Setor (se disponível)
        pl.col("setor").first().alias("setor") if "setor" in df.columns else pl.lit("Outros").alias("setor"),
    ])

    # Calcula proporção de dias negociados nos últimos 252 pregões
    # (assumindo que cada registro = 1 dia negociado)
    # Se o histórico for menor que 252, usa o que tem
    metrics = metrics.with_columns([
        (pl.col("history_days") / 252.0).clip(0, 1).alias("trading_days_ratio_252d")
    ])

    return metrics


def _classify_volatility(df: pl.DataFrame, rules: dict[str, Any]) -> pl.DataFrame:
    """Classifica ativos por faixa de volatilidade.

    Args:
        df: DataFrame com métricas por ticker.
        rules: Regras de seleção do YAML.

    Returns:
        DataFrame com coluna volatility_class adicionada.
    """
    thresholds = rules.get("volatility", {}).get("thresholds", {})
    low_max = thresholds.get("low_max_annualized_vol", 0.20)
    medium_max = thresholds.get("medium_max_annualized_vol", 0.40)

    df = df.with_columns([
        pl.when(pl.col("annualized_vol_60d") <= low_max)
        .then(pl.lit("BAIXA"))
        .when(pl.col("annualized_vol_60d") <= medium_max)
        .then(pl.lit("MEDIA"))
        .otherwise(pl.lit("ALTA"))
        .alias("volatility_class")
    ])

    return df


def _classify_liquidity(df: pl.DataFrame) -> pl.DataFrame:
    """Classifica ativos por faixa de liquidez (tercis).

    Args:
        df: DataFrame com métricas por ticker.

    Returns:
        DataFrame com coluna liquidity_class adicionada.
    """
    # Calcula percentis de volume
    p33 = df.select(pl.col("avg_volume_21d_brl").quantile(0.33)).item()
    p66 = df.select(pl.col("avg_volume_21d_brl").quantile(0.66)).item()

    df = df.with_columns([
        pl.when(pl.col("avg_volume_21d_brl") >= p66)
        .then(pl.lit("ALTA"))
        .when(pl.col("avg_volume_21d_brl") >= p33)
        .then(pl.lit("MEDIA"))
        .otherwise(pl.lit("BAIXA"))
        .alias("liquidity_class")
    ])

    return df


# =============================================================================
# FUNÇÕES DE FILTRO
# =============================================================================


def _apply_prelist_filters(
    df: pl.DataFrame,
    rules: dict[str, Any],
    metadata: PipelineMetadata,
) -> pl.DataFrame:
    """Aplica filtros de pré-lista conforme regras do YAML.

    Args:
        df: DataFrame com métricas por ticker.
        rules: Regras de seleção do YAML.
        metadata: Objeto para registrar filtros aplicados.

    Returns:
        DataFrame filtrado.
    """
    prelist = rules.get("prelist", {})
    initial_count = len(df)

    # Filtro: histórico mínimo
    min_history = prelist.get("min_history_days", 252)
    df = df.filter(pl.col("history_days") >= min_history)
    metadata.filters_applied.append(f"min_history_days >= {min_history}")
    logger.info(f"Após filtro histórico mínimo: {len(df)} ativos (removidos: {initial_count - len(df)})")

    # Filtro: proporção de dias negociados
    min_trading_ratio = prelist.get("min_trading_days_ratio_252d", 0.9)
    before = len(df)
    df = df.filter(pl.col("trading_days_ratio_252d") >= min_trading_ratio)
    metadata.filters_applied.append(f"trading_days_ratio >= {min_trading_ratio}")
    logger.info(f"Após filtro trading ratio: {len(df)} ativos (removidos: {before - len(df)})")

    # Filtro: volume mínimo
    min_volume = prelist.get("min_avg_volume_21d_brl", 5_000_000)
    before = len(df)
    df = df.filter(pl.col("avg_volume_21d_brl") >= min_volume)
    metadata.filters_applied.append(f"avg_volume_21d >= R$ {min_volume:,.0f}")
    logger.info(f"Após filtro volume: {len(df)} ativos (removidos: {before - len(df)})")

    # Filtro: preço mínimo
    min_price = prelist.get("min_price_brl", 5.0)
    before = len(df)
    df = df.filter(pl.col("avg_price_recent_brl") >= min_price)
    metadata.filters_applied.append(f"avg_price >= R$ {min_price:.2f}")
    logger.info(f"Após filtro preço: {len(df)} ativos (removidos: {before - len(df)})")

    # Filtro: instrumentos permitidos
    allowed = prelist.get("allowed_instruments", ["ACAO_ON", "ACAO_PN", "BDR"])
    before = len(df)
    df = df.filter(pl.col("tipo_instrumento").is_in(allowed))
    metadata.filters_applied.append(f"tipo_instrumento in {allowed}")
    logger.info(f"Após filtro instrumentos: {len(df)} ativos (removidos: {before - len(df)})")

    return df


def _apply_sector_constraints(
    df: pl.DataFrame,
    rules: dict[str, Any],
    metadata: PipelineMetadata,
) -> pl.DataFrame:
    """Aplica restrições setoriais (máximo de ativos por setor).

    Args:
        df: DataFrame com métricas por ticker.
        rules: Regras de seleção do YAML.
        metadata: Objeto para registrar filtros aplicados.

    Returns:
        DataFrame com restrições setoriais aplicadas.
    """
    sectors = rules.get("sectors", {})
    max_per_sector = sectors.get("max_names_per_sector", 6)

    # Ordena por volume dentro de cada setor e mantém os top N
    df = df.sort("avg_volume_21d_brl", descending=True)

    # Adiciona rank por setor
    df = df.with_columns([
        pl.col("ticker").cum_count().over("setor").alias("rank_in_sector")
    ])

    before = len(df)
    df = df.filter(pl.col("rank_in_sector") < max_per_sector)
    df = df.drop("rank_in_sector")

    metadata.filters_applied.append(f"max_names_per_sector < {max_per_sector}")
    logger.info(f"Após limite por setor: {len(df)} ativos (removidos: {before - len(df)})")

    return df


# =============================================================================
# FUNÇÕES PÚBLICAS
# =============================================================================


def build_universe_candidates(
    config_paths: dict[str, str] | None = None,
    force_refresh: bool = False,
    output_csv: bool = True,
) -> str:
    """Executa o pipeline completo para construir UNIVERSE_CANDIDATES.

    Args:
        config_paths: Dicionário com caminhos dos arquivos de configuração.
            Se None, usa os caminhos padrão:
            - selection_rules: config/experiments/universe_selection_rules_v1.yaml
            - pipeline_topology: config/experiments/universe_pipeline_topology_v1.yaml
            - raw_market: data/raw/market/
            - output_file: data/universe/UNIVERSE_CANDIDATES.parquet

        force_refresh: Se True, ignora cache e reprocessa todos os dados.

        output_csv: Se True, gera também versão CSV além do Parquet.

    Returns:
        Caminho do arquivo final gerado (data/universe/UNIVERSE_CANDIDATES.parquet).

    Raises:
        RuntimeError: Se não houver dados brutos ou se ocorrer erro crítico.
        FileNotFoundError: Se arquivos de configuração não existirem.
    """
    root = _get_project_root()
    logger.info("=" * 60)
    logger.info("Iniciando pipeline UNIVERSE_CANDIDATES")
    logger.info(f"Project root: {root}")
    logger.info("=" * 60)

    # Inicializa metadados
    metadata = PipelineMetadata(
        execution_date=datetime.now(),
        input_record_count=0,
        output_record_count=0,
    )

    # Carrega configurações
    rules = _load_selection_rules(config_paths)
    topology = _load_pipeline_topology(config_paths)
    logger.info("Configurações carregadas com sucesso")

    # Define caminhos
    paths = config_paths or {}
    raw_path = root / paths.get("raw_market", DEFAULT_PATHS["raw_market"])
    output_file = root / paths.get("output_file", DEFAULT_PATHS["output_file"])
    output_csv_path = root / paths.get("output_csv", DEFAULT_PATHS["output_csv"])
    metadata_file = root / paths.get("metadata_file", DEFAULT_PATHS["metadata_file"])

    # Verifica se já existe e force_refresh=False
    if output_file.exists() and not force_refresh:
        logger.info(f"Arquivo existente encontrado: {output_file}")
        logger.info("Use force_refresh=True para reprocessar")
        return str(output_file)

    # Garante que diretórios de saída existem
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # ETAPA 1: Leitura de dados brutos
    logger.info("-" * 40)
    logger.info("ETAPA 1: Leitura de dados brutos")
    df_raw = _read_raw_market_data(raw_path)
    metadata.input_record_count = len(df_raw)

    # ETAPA 2: Normalização
    logger.info("-" * 40)
    logger.info("ETAPA 2: Normalização de identificadores")
    df_normalized = _normalize_identifiers(df_raw)
    logger.info(f"Dados normalizados: {len(df_normalized)} registros")

    # ETAPA 3: Cálculo de métricas
    logger.info("-" * 40)
    logger.info("ETAPA 3: Cálculo de métricas por ticker")
    df_metrics = _compute_metrics_per_ticker(df_normalized, rules)
    df_metrics = _classify_volatility(df_metrics, rules)
    df_metrics = _classify_liquidity(df_metrics)
    logger.info(f"Métricas calculadas para {len(df_metrics)} tickers únicos")

    # ETAPA 4: Aplicação de filtros
    logger.info("-" * 40)
    logger.info("ETAPA 4: Aplicação de filtros da pré-lista")
    df_filtered = _apply_prelist_filters(df_metrics, rules, metadata)

    # ETAPA 5: Restrições setoriais
    logger.info("-" * 40)
    logger.info("ETAPA 5: Aplicação de restrições setoriais")
    df_final = _apply_sector_constraints(df_filtered, rules, metadata)

    # Validação de tamanho do universo
    universe_size = rules.get("universe_size", {})
    target_min = universe_size.get("min", 28)
    target_max = universe_size.get("max", 80)

    if len(df_final) < target_min:
        msg = f"Universo muito pequeno: {len(df_final)} < {target_min} (mínimo esperado)"
        logger.warning(msg)
        metadata.warnings.append(msg)
    elif len(df_final) > target_max:
        msg = f"Universo muito grande: {len(df_final)} > {target_max} (máximo esperado)"
        logger.warning(msg)
        metadata.warnings.append(msg)

    metadata.output_record_count = len(df_final)

    # Seleciona e ordena colunas de saída
    output_columns = [
        "ticker",
        "tipo_instrumento",
        "setor",
        "date_first",
        "date_last",
        "history_days",
        "trading_days_ratio_252d",
        "avg_volume_21d_brl",
        "avg_price_recent_brl",
        "last_price",
        "annualized_vol_60d",
        "volatility_class",
        "liquidity_class",
    ]
    # Mantém apenas colunas existentes
    output_columns = [c for c in output_columns if c in df_final.columns]
    df_final = df_final.select(output_columns).sort("avg_volume_21d_brl", descending=True)

    # ETAPA 6: Persistência
    logger.info("-" * 40)
    logger.info("ETAPA 6: Persistência dos resultados")

    # Salva Parquet
    df_final.write_parquet(output_file)
    logger.info(f"Salvo: {output_file}")

    # Salva CSV (opcional)
    if output_csv:
        df_final.write_csv(output_csv_path)
        logger.info(f"Salvo: {output_csv_path}")

    # Salva metadados
    metadata_dict = {
        "execution_date": metadata.execution_date.isoformat(),
        "input_record_count": metadata.input_record_count,
        "output_record_count": metadata.output_record_count,
        "filters_applied": metadata.filters_applied,
        "warnings": metadata.warnings,
    }
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata_dict, f, indent=2, ensure_ascii=False)
    logger.info(f"Salvo: {metadata_file}")

    # Resumo final
    logger.info("=" * 60)
    logger.info("Pipeline UNIVERSE_CANDIDATES concluído")
    logger.info(f"  Registros de entrada: {metadata.input_record_count:,}")
    logger.info(f"  Registros de saída:   {metadata.output_record_count:,}")
    logger.info(f"  Filtros aplicados:    {len(metadata.filters_applied)}")
    logger.info(f"  Warnings:             {len(metadata.warnings)}")
    logger.info("=" * 60)

    return str(output_file)


def load_universe_candidates(path: str | None = None) -> pl.DataFrame:
    """Carrega o arquivo UNIVERSE_CANDIDATES em um DataFrame Polars.

    Args:
        path: Caminho do arquivo. Se None, usa o caminho padrão:
            data/universe/UNIVERSE_CANDIDATES.parquet

    Returns:
        DataFrame Polars com a pré-lista de candidatos.

    Raises:
        FileNotFoundError: Se o arquivo não existir.
    """
    if path is None:
        root = _get_project_root()
        path = str(root / DEFAULT_PATHS["output_file"])

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo UNIVERSE_CANDIDATES não encontrado: {path}\n"
            "Execute build_universe_candidates() primeiro."
        )

    df = pl.read_parquet(path)
    logger.info(f"Carregado UNIVERSE_CANDIDATES: {len(df)} registros de {path}")
    return df


def validate_universe_candidates(df: pl.DataFrame) -> ValidationResult:
    """Valida um DataFrame contra o schema UNIVERSE_CANDIDATES.

    Args:
        df: DataFrame a ser validado.

    Returns:
        ValidationResult com status e lista de erros/warnings.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Verifica se DataFrame está vazio
    if len(df) == 0:
        errors.append("DataFrame está vazio")
        return ValidationResult(
            is_valid=False,
            errors=errors,
            warnings=warnings,
            record_count=0,
        )

    # Verifica colunas obrigatórias
    missing_cols = set(REQUIRED_OUTPUT_COLUMNS) - set(df.columns)
    if missing_cols:
        errors.append(f"Colunas obrigatórias ausentes: {missing_cols}")

    # Verifica tipos de dados
    if "ticker" in df.columns:
        null_tickers = df.filter(pl.col("ticker").is_null()).height
        if null_tickers > 0:
            errors.append(f"Encontrados {null_tickers} tickers nulos")

    # Verifica valores negativos onde não deveriam existir
    numeric_cols = ["avg_volume_21d_brl", "avg_price_recent_brl", "history_days"]
    for col in numeric_cols:
        if col in df.columns:
            negative = df.filter(pl.col(col) < 0).height
            if negative > 0:
                errors.append(f"Encontrados {negative} valores negativos em {col}")

    # Warnings: tamanho do universo
    if len(df) < 60:
        warnings.append(f"Universo pequeno: {len(df)} ativos (esperado 60-80)")
    elif len(df) > 80:
        warnings.append(f"Universo grande: {len(df)} ativos (esperado 60-80)")

    # Warnings: concentração setorial
    if "setor" in df.columns:
        sector_counts = df.group_by("setor").len()
        max_sector = sector_counts.select(pl.col("len").max()).item()
        if max_sector and max_sector > 10:
            warnings.append(f"Alta concentração setorial: {max_sector} ativos no maior setor")

    is_valid = len(errors) == 0
    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        record_count=len(df),
    )


def get_pipeline_metadata(output_path: str | None = None) -> PipelineMetadata | None:
    """Retorna metadados da última execução do pipeline.

    Args:
        output_path: Caminho base dos outputs. Se None, usa padrão.

    Returns:
        PipelineMetadata com informações sobre a execução, ou None se não existir.
    """
    if output_path is None:
        root = _get_project_root()
        metadata_file = root / DEFAULT_PATHS["metadata_file"]
    else:
        metadata_file = Path(output_path).parent / "UNIVERSE_CANDIDATES_metadata.json"

    if not metadata_file.exists():
        return None

    with open(metadata_file, encoding="utf-8") as f:
        data = json.load(f)

    return PipelineMetadata(
        execution_date=datetime.fromisoformat(data["execution_date"]),
        input_record_count=data["input_record_count"],
        output_record_count=data["output_record_count"],
        filters_applied=data.get("filters_applied", []),
        warnings=data.get("warnings", []),
    )

