# -*- coding: utf-8 -*-
"""
PortfolioZero — Seletor do Universo Supervisionado

Este módulo implementa a lógica de seleção dos ~30 ativos supervisionados
(UNIVERSE_SUPERVISED) a partir da pré-lista de candidatos (UNIVERSE_CANDIDATES).

Funções principais:
- load_supervised_selection_config(): Carrega regras de seleção do YAML
- select_supervised_universe(): Aplica algoritmo de seleção
- build_universe_supervised(): Orquestra o pipeline completo

Autor: Coding Agent
Data: 02/12/2024
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl
import yaml

# Configuração de logging
logger = logging.getLogger(__name__)

# Caminhos padrão
DEFAULT_CONFIG_PATH = "config/experiments/universe_supervised_selection_rules_v1.yaml"
DEFAULT_CANDIDATES_PATH = "data/universe/UNIVERSE_CANDIDATES.parquet"
DEFAULT_OUTPUT_DIR = "data/universe"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SelectionLogEntry:
    """Registro de decisão de seleção para um ticker."""
    ticker: str
    action: str  # "included" ou "excluded"
    reason: str
    sector: str
    volatility_class: str
    liquidity_class: str
    avg_volume_21d_brl: float
    is_forced_include: bool = False
    is_forced_exclude: bool = False
    priority_score: float = 0.0


@dataclass
class SelectionResult:
    """Resultado da seleção do universo supervisionado."""
    is_valid: bool
    selected_count: int
    target_size: int
    min_size: int
    max_size: int
    selected_df: pl.DataFrame | None = None
    selection_log: list[SelectionLogEntry] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    
    # Estatísticas
    by_sector: dict[str, int] = field(default_factory=dict)
    by_volatility: dict[str, int] = field(default_factory=dict)
    by_liquidity: dict[str, int] = field(default_factory=dict)
    forced_includes_applied: list[str] = field(default_factory=list)
    forced_excludes_applied: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário serializável."""
        result = asdict(self)
        # Remove o DataFrame que não é serializável
        result.pop("selected_df", None)
        # Converte SelectionLogEntry para dict
        result["selection_log"] = [asdict(e) for e in self.selection_log]
        return result


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def _get_project_root() -> Path:
    """Retorna o diretório raiz do projeto."""
    current = Path.cwd()
    
    # Se estamos no diretório do projeto
    if (current / "pyproject.toml").exists():
        return current
    
    # Procura subindo níveis
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    
    return current


def _load_yaml_config(path: Path) -> dict[str, Any]:
    """Carrega arquivo YAML."""
    if not path.exists():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {path}")
    
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _calculate_priority_score(
    row: dict[str, Any],
    tie_breaker_priority: list[str],
) -> float:
    """
    Calcula score de prioridade para desempate.
    
    Quanto maior o score, maior a prioridade de seleção.
    """
    score = 0.0
    
    for i, criterion in enumerate(tie_breaker_priority):
        weight = 1000 ** (len(tie_breaker_priority) - i)  # Pesos decrescentes
        
        if criterion == "higher_liquidity_first":
            liquidity_scores = {"ALTA": 3, "MEDIA": 2, "BAIXA": 1}
            score += weight * liquidity_scores.get(row.get("liquidity_class", "BAIXA"), 0)
        
        elif criterion == "lower_volatility_within_class":
            vol_scores = {"BAIXA": 3, "MEDIA": 2, "ALTA": 1}
            score += weight * vol_scores.get(row.get("volatility_class", "ALTA"), 0)
        
        elif criterion == "higher_avg_volume_21d":
            volume = row.get("avg_volume_21d_brl", 0)
            # Normaliza para escala 0-1 (assumindo max ~100M)
            normalized_vol = min(volume / 100_000_000, 1.0)
            score += weight * normalized_vol
    
    return score


# =============================================================================
# FUNÇÕES PÚBLICAS
# =============================================================================

def load_supervised_selection_config(path: str | None = None) -> dict[str, Any]:
    """
    Carrega e valida configuração de seleção do universo supervisionado.
    
    Args:
        path: Caminho para o arquivo YAML. Se None, usa o padrão.
        
    Returns:
        Dicionário com a configuração validada.
        
    Raises:
        FileNotFoundError: Se o arquivo não existir.
        ValueError: Se a configuração for inválida.
    """
    root = _get_project_root()
    config_path = Path(path) if path else root / DEFAULT_CONFIG_PATH
    
    logger.info(f"Carregando configuração de seleção: {config_path}")
    config = _load_yaml_config(config_path)
    
    # Validações básicas
    required_keys = ["target_size", "sector_constraints", "volatility_mix", "owner_overrides"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Configuração inválida: campo '{key}' ausente")
    
    # Valida mix de volatilidade
    vol_mix = config.get("volatility_mix", {})
    total_pct = (
        vol_mix.get("target_low_pct", 0) +
        vol_mix.get("target_medium_pct", 0) +
        vol_mix.get("target_high_pct", 0)
    )
    tolerance = vol_mix.get("tolerance_pct", 0.1)
    if abs(total_pct - 1.0) > tolerance:
        raise ValueError(
            f"Configuração inválida: soma de target_*_pct = {total_pct:.2f} "
            f"(esperado 1.0 ± {tolerance})"
        )
    
    logger.info(f"  Tamanho alvo: {config.get('target_size', 30)}")
    logger.info(f"  Forced includes: {len(config.get('owner_overrides', {}).get('forced_includes', []))}")
    
    return config


def select_supervised_universe(
    candidates_df: pl.DataFrame,
    config: dict[str, Any],
) -> SelectionResult:
    """
    Seleciona os ativos supervisionados a partir dos candidatos.
    
    Implementa algoritmo multi-critério que:
    1. Aplica forced_includes e forced_excludes
    2. Respeita limites por setor
    3. Busca aproximar mix de volatilidade alvo
    4. Prioriza liquidez ALTA/MEDIA
    5. Usa critérios de desempate configurados
    
    Args:
        candidates_df: DataFrame com UNIVERSE_CANDIDATES
        config: Configuração de seleção
        
    Returns:
        SelectionResult com o universo selecionado e metadados
    """
    logger.info("=" * 60)
    logger.info("Iniciando seleção do UNIVERSE_SUPERVISED")
    logger.info(f"  Candidatos disponíveis: {len(candidates_df)}")
    logger.info("=" * 60)
    
    # Extrai parâmetros da configuração
    target_size = config.get("target_size", 30)
    min_size = config.get("min_size", 28)
    max_size = config.get("max_size", 32)
    
    sector_constraints = config.get("sector_constraints", {})
    min_per_sector = sector_constraints.get("min_per_sector", 2)
    max_per_sector = sector_constraints.get("max_per_sector", 6)
    
    vol_mix = config.get("volatility_mix", {})
    target_low_pct = vol_mix.get("target_low_pct", 0.30)
    target_medium_pct = vol_mix.get("target_medium_pct", 0.50)
    target_high_pct = vol_mix.get("target_high_pct", 0.20)
    
    liq_prefs = config.get("liquidity_preferences", {})
    max_low_liq_count = liq_prefs.get("max_low_liquidity_count", 3)
    
    owner_overrides = config.get("owner_overrides", {})
    forced_includes = set(owner_overrides.get("forced_includes", []))
    forced_excludes = set(owner_overrides.get("forced_excludes", []))
    
    tie_breaker = config.get("tie_breaker_priority", [
        "higher_liquidity_first",
        "lower_volatility_within_class",
        "higher_avg_volume_21d"
    ])
    
    # Inicializa resultado
    result = SelectionResult(
        is_valid=True,
        selected_count=0,
        target_size=target_size,
        min_size=min_size,
        max_size=max_size,
    )
    
    # Converte para lista de dicts para facilitar manipulação
    candidates = candidates_df.to_dicts()
    
    # Verifica forced_includes
    available_tickers = {c["ticker"] for c in candidates}
    missing_forced = forced_includes - available_tickers
    if missing_forced:
        msg = f"Forced includes não encontrados em UNIVERSE_CANDIDATES: {missing_forced}"
        if owner_overrides.get("validate_forced_includes", True):
            result.errors.append(msg)
            logger.error(msg)
        else:
            result.warnings.append(msg)
            logger.warning(msg)
    
    # Remove forced_excludes dos candidatos
    if forced_excludes:
        excluded_count = len([c for c in candidates if c["ticker"] in forced_excludes])
        candidates = [c for c in candidates if c["ticker"] not in forced_excludes]
        logger.info(f"  Removidos {excluded_count} forced_excludes")
        result.forced_excludes_applied = list(forced_excludes & available_tickers)
    
    # Calcula priority score para todos os candidatos
    for c in candidates:
        c["priority_score"] = _calculate_priority_score(c, tie_breaker)
    
    # Ordena por priority_score (maior primeiro)
    candidates.sort(key=lambda x: x["priority_score"], reverse=True)
    
    # Estruturas de controle
    selected: list[dict[str, Any]] = []
    selection_log: list[SelectionLogEntry] = []
    sector_counts: dict[str, int] = {}
    vol_counts: dict[str, int] = {"BAIXA": 0, "MEDIA": 0, "ALTA": 0}
    liq_counts: dict[str, int] = {"BAIXA": 0, "MEDIA": 0, "ALTA": 0}
    
    # PASSO 1: Inclui forced_includes primeiro
    logger.info("-" * 40)
    logger.info("PASSO 1: Processando forced_includes")
    
    for ticker in forced_includes:
        candidate = next((c for c in candidates if c["ticker"] == ticker), None)
        if candidate is None:
            continue
        
        sector = candidate.get("setor", "Outros")
        vol_class = candidate.get("volatility_class", "MEDIA")
        liq_class = candidate.get("liquidity_class", "MEDIA")
        
        selected.append(candidate)
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
        vol_counts[vol_class] = vol_counts.get(vol_class, 0) + 1
        liq_counts[liq_class] = liq_counts.get(liq_class, 0) + 1
        
        result.forced_includes_applied.append(ticker)
        
        selection_log.append(SelectionLogEntry(
            ticker=ticker,
            action="included",
            reason="forced_include pelo Owner",
            sector=sector,
            volatility_class=vol_class,
            liquidity_class=liq_class,
            avg_volume_21d_brl=candidate.get("avg_volume_21d_brl", 0),
            is_forced_include=True,
            priority_score=candidate.get("priority_score", 0),
        ))
        
        logger.info(f"  ✓ {ticker} (forced_include)")
    
    logger.info(f"  Selecionados após forced_includes: {len(selected)}")
    
    # PASSO 2: Preenche o restante das vagas
    logger.info("-" * 40)
    logger.info("PASSO 2: Preenchendo vagas restantes")
    
    selected_tickers = {s["ticker"] for s in selected}
    remaining_candidates = [c for c in candidates if c["ticker"] not in selected_tickers]
    
    # Calcula metas de volatilidade
    target_low = int(round(target_size * target_low_pct))
    target_medium = int(round(target_size * target_medium_pct))
    target_high = target_size - target_low - target_medium
    
    logger.info(f"  Metas de volatilidade: BAIXA={target_low}, MEDIA={target_medium}, ALTA={target_high}")
    
    # Função para verificar se candidato pode ser adicionado
    def can_add_candidate(c: dict[str, Any]) -> tuple[bool, str]:
        sector = c.get("setor", "Outros")
        vol_class = c.get("volatility_class", "MEDIA")
        liq_class = c.get("liquidity_class", "MEDIA")
        
        # Verifica limite de setor
        if sector_counts.get(sector, 0) >= max_per_sector:
            return False, f"setor {sector} já tem {max_per_sector} ativos"
        
        # Verifica limite de baixa liquidez
        if liq_class == "BAIXA" and liq_counts.get("BAIXA", 0) >= max_low_liq_count:
            return False, f"limite de {max_low_liq_count} ativos de baixa liquidez atingido"
        
        return True, "ok"
    
    # Função para calcular score de necessidade (prioriza classes sub-representadas)
    def get_need_score(c: dict[str, Any]) -> float:
        vol_class = c.get("volatility_class", "MEDIA")
        current = vol_counts.get(vol_class, 0)
        
        if vol_class == "BAIXA":
            target = target_low
        elif vol_class == "MEDIA":
            target = target_medium
        else:
            target = target_high
        
        # Quanto mais longe do target, maior a necessidade
        if current < target:
            return (target - current) / max(target, 1)
        return 0
    
    # Itera sobre candidatos restantes
    for c in remaining_candidates:
        if len(selected) >= target_size:
            break
        
        can_add, reason = can_add_candidate(c)
        if not can_add:
            selection_log.append(SelectionLogEntry(
                ticker=c["ticker"],
                action="excluded",
                reason=reason,
                sector=c.get("setor", "Outros"),
                volatility_class=c.get("volatility_class", "MEDIA"),
                liquidity_class=c.get("liquidity_class", "MEDIA"),
                avg_volume_21d_brl=c.get("avg_volume_21d_brl", 0),
                priority_score=c.get("priority_score", 0),
            ))
            continue
        
        # Adiciona candidato
        sector = c.get("setor", "Outros")
        vol_class = c.get("volatility_class", "MEDIA")
        liq_class = c.get("liquidity_class", "MEDIA")
        
        selected.append(c)
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
        vol_counts[vol_class] = vol_counts.get(vol_class, 0) + 1
        liq_counts[liq_class] = liq_counts.get(liq_class, 0) + 1
        
        selection_log.append(SelectionLogEntry(
            ticker=c["ticker"],
            action="included",
            reason="selecionado por critérios",
            sector=sector,
            volatility_class=vol_class,
            liquidity_class=liq_class,
            avg_volume_21d_brl=c.get("avg_volume_21d_brl", 0),
            priority_score=c.get("priority_score", 0),
        ))
    
    # Registra candidatos não selecionados
    selected_tickers = {s["ticker"] for s in selected}
    for c in remaining_candidates:
        if c["ticker"] not in selected_tickers:
            existing_entry = next(
                (e for e in selection_log if e.ticker == c["ticker"]), None
            )
            if not existing_entry:
                selection_log.append(SelectionLogEntry(
                    ticker=c["ticker"],
                    action="excluded",
                    reason="não selecionado (limite atingido)",
                    sector=c.get("setor", "Outros"),
                    volatility_class=c.get("volatility_class", "MEDIA"),
                    liquidity_class=c.get("liquidity_class", "MEDIA"),
                    avg_volume_21d_brl=c.get("avg_volume_21d_brl", 0),
                    priority_score=c.get("priority_score", 0),
                ))
    
    # PASSO 3: Validação e montagem do resultado
    logger.info("-" * 40)
    logger.info("PASSO 3: Validação do resultado")
    
    result.selected_count = len(selected)
    result.selection_log = selection_log
    result.by_sector = sector_counts
    result.by_volatility = vol_counts
    result.by_liquidity = liq_counts
    
    # Verifica tamanho
    if len(selected) < min_size:
        result.warnings.append(
            f"Universo menor que o mínimo: {len(selected)} < {min_size}"
        )
        result.is_valid = False
    elif len(selected) > max_size:
        result.warnings.append(
            f"Universo maior que o máximo: {len(selected)} > {max_size}"
        )
        result.is_valid = False
    
    # Verifica distribuição de volatilidade
    low_pct = vol_counts.get("BAIXA", 0) / max(len(selected), 1)
    medium_pct = vol_counts.get("MEDIA", 0) / max(len(selected), 1)
    high_pct = vol_counts.get("ALTA", 0) / max(len(selected), 1)
    tolerance = vol_mix.get("tolerance_pct", 0.10)
    
    if abs(low_pct - target_low_pct) > tolerance:
        result.warnings.append(
            f"Volatilidade BAIXA fora da tolerância: {low_pct:.1%} (alvo: {target_low_pct:.1%})"
        )
    if abs(medium_pct - target_medium_pct) > tolerance:
        result.warnings.append(
            f"Volatilidade MEDIA fora da tolerância: {medium_pct:.1%} (alvo: {target_medium_pct:.1%})"
        )
    if abs(high_pct - target_high_pct) > tolerance:
        result.warnings.append(
            f"Volatilidade ALTA fora da tolerância: {high_pct:.1%} (alvo: {target_high_pct:.1%})"
        )
    
    # Converte selecionados para DataFrame
    if selected:
        result.selected_df = pl.DataFrame(selected)
        # Remove coluna auxiliar
        if "priority_score" in result.selected_df.columns:
            result.selected_df = result.selected_df.drop("priority_score")
    
    # Logs finais
    logger.info(f"  Total selecionado: {len(selected)}")
    logger.info(f"  Por setor: {sector_counts}")
    logger.info(f"  Por volatilidade: {vol_counts}")
    logger.info(f"  Por liquidez: {liq_counts}")
    
    if result.warnings:
        for w in result.warnings:
            logger.warning(f"  ⚠️ {w}")
    
    logger.info("=" * 60)
    
    return result


def build_universe_supervised(
    config_path: str | None = None,
    candidates_path: str | None = None,
    output_dir: str | None = None,
    dry_run: bool = False,
) -> str:
    """
    Função de alto nível que executa o pipeline completo de seleção.
    
    1. Carrega configuração
    2. Carrega UNIVERSE_CANDIDATES
    3. Executa seleção
    4. Persiste resultados
    
    Args:
        config_path: Caminho para YAML de configuração
        candidates_path: Caminho para UNIVERSE_CANDIDATES.parquet
        output_dir: Diretório de saída
        dry_run: Se True, não grava arquivos
        
    Returns:
        Caminho do arquivo UNIVERSE_SUPERVISED.parquet gerado
        
    Raises:
        FileNotFoundError: Se arquivos de entrada não existirem
        ValueError: Se configuração for inválida
        RuntimeError: Se seleção falhar
    """
    root = _get_project_root()
    
    # Resolve caminhos
    candidates_file = Path(candidates_path) if candidates_path else root / DEFAULT_CANDIDATES_PATH
    output_path = Path(output_dir) if output_dir else root / DEFAULT_OUTPUT_DIR
    
    logger.info("=" * 60)
    logger.info("Pipeline UNIVERSE_SUPERVISED")
    logger.info(f"  Project root: {root}")
    logger.info("=" * 60)
    
    # Verifica se UNIVERSE_CANDIDATES existe
    if not candidates_file.exists():
        raise FileNotFoundError(
            f"UNIVERSE_CANDIDATES não encontrado: {candidates_file}\n"
            "Execute primeiro: python scripts/build_universe_candidates.py"
        )
    
    # Carrega configuração
    config = load_supervised_selection_config(config_path)
    
    # Carrega candidatos
    logger.info(f"Carregando candidatos de: {candidates_file}")
    candidates_df = pl.read_parquet(candidates_file)
    logger.info(f"  Candidatos carregados: {len(candidates_df)}")
    
    # Executa seleção
    result = select_supervised_universe(candidates_df, config)
    
    # Verifica resultado
    if result.errors:
        raise RuntimeError(f"Erros na seleção: {result.errors}")
    
    if result.selected_df is None or len(result.selected_df) == 0:
        raise RuntimeError("Seleção não produziu resultados")
    
    if dry_run:
        logger.info("Modo dry_run: arquivos não serão gravados")
        return str(output_path / "UNIVERSE_SUPERVISED.parquet")
    
    # Persiste resultados
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Parquet principal
    parquet_path = output_path / "UNIVERSE_SUPERVISED.parquet"
    result.selected_df.write_parquet(parquet_path)
    logger.info(f"Salvo: {parquet_path}")
    
    # CSV opcional
    output_config = config.get("output", {})
    if output_config.get("generate_csv", True):
        csv_path = output_path / "UNIVERSE_SUPERVISED.csv"
        result.selected_df.write_csv(csv_path)
        logger.info(f"Salvo: {csv_path}")
    
    # Log de seleção
    if output_config.get("generate_selection_log", True):
        log_path = output_path / "UNIVERSE_SUPERVISED_selection_log.json"
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "candidates_count": len(candidates_df),
            "selected_count": result.selected_count,
            "is_valid": result.is_valid,
            "by_sector": result.by_sector,
            "by_volatility": result.by_volatility,
            "by_liquidity": result.by_liquidity,
            "forced_includes_applied": result.forced_includes_applied,
            "forced_excludes_applied": result.forced_excludes_applied,
            "warnings": result.warnings,
            "selection_log": [asdict(e) for e in result.selection_log],
        }
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Salvo: {log_path}")
    
    # Lista de tickers
    if output_config.get("generate_ticker_list", True):
        tickers_path = output_path / "UNIVERSE_SUPERVISED_tickers.txt"
        tickers = result.selected_df["ticker"].to_list()
        with open(tickers_path, "w", encoding="utf-8") as f:
            f.write("\n".join(tickers))
        logger.info(f"Salvo: {tickers_path}")
    
    logger.info("=" * 60)
    logger.info("Pipeline UNIVERSE_SUPERVISED concluído")
    logger.info(f"  Ativos selecionados: {result.selected_count}")
    logger.info(f"  Válido: {'✓' if result.is_valid else '✗'}")
    logger.info("=" * 60)
    
    return str(parquet_path)

