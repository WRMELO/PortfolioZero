#!/usr/bin/env python3
"""Script de orquestração para construir a pré-lista UNIVERSE_CANDIDATES.

Este script integra ingestão de dados + pipeline UNIVERSE_CANDIDATES,
produzindo a pré-lista de 60-80 tickers candidatos ao universo supervisionado.

Usage:
    # Apenas validar dados existentes
    python scripts/build_universe_candidates.py --validate-only

    # Executar pipeline sem nova ingestão
    python scripts/build_universe_candidates.py

    # Executar ingestão + pipeline
    python scripts/build_universe_candidates.py --with-ingestion

    # Salvar resumo em JSON
    python scripts/build_universe_candidates.py --output-summary-path data/universe/run_summary.json

Example:
    $ python scripts/build_universe_candidates.py --with-ingestion
    
    ============================================================
    CONSTRUÇÃO DA PRÉ-LISTA UNIVERSE_CANDIDATES
    ============================================================
    
    [1/3] Ingestão de dados de mercado...
    ...
    [2/3] Executando pipeline UNIVERSE_CANDIDATES...
    ...
    [3/3] Gerando resumo...
    
    ============================================================
    RESUMO DA PRÉ-LISTA
    ============================================================
    Total de candidatos: 72
    Dentro do intervalo alvo (60-80): ✓ SIM
    
    Por setor:
      Financeiro: 12
      Commodities: 10
      ...
    
    Por volatilidade:
      BAIXA: 15
      MEDIA: 30
      ALTA: 27
    
    Por liquidez:
      BAIXA: 24
      MEDIA: 24
      ALTA: 24
    ============================================================
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Adiciona o diretório do projeto ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "modules"))

import polars as pl

from portfoliozero.core.data.market_data_ingestion import (
    fetch_and_store_universe_market_data,
    validate_raw_market_data,
)
from portfoliozero.core.data.universe_candidates_pipeline import (
    build_universe_candidates,
    get_pipeline_metadata,
    load_universe_candidates,
    validate_universe_candidates,
)


# =============================================================================
# CONSTANTES
# =============================================================================

TARGET_MIN_CANDIDATES = 60
TARGET_MAX_CANDIDATES = 80

EXIT_SUCCESS = 0
EXIT_OUT_OF_RANGE = 1
EXIT_VALIDATION_ERROR = 2
EXIT_INGESTION_ERROR = 3


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================


def setup_logging(verbose: bool = False) -> None:
    """Configura logging para o script."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def summarize_universe_candidates(
    df: pl.DataFrame,
    metadata: Any | None = None,
) -> dict[str, Any]:
    """Produz um resumo estruturado da pré-lista UNIVERSE_CANDIDATES.

    Args:
        df: DataFrame com os candidatos.
        metadata: Metadados do pipeline (opcional).

    Returns:
        Dicionário serializável com estatísticas da pré-lista.
    """
    total = len(df)
    in_target_range = TARGET_MIN_CANDIDATES <= total <= TARGET_MAX_CANDIDATES

    # Contagem por setor
    by_sector: dict[str, int] = {}
    if "setor" in df.columns:
        sector_counts = df.group_by("setor").len().sort("len", descending=True)
        by_sector = dict(
            zip(
                sector_counts["setor"].to_list(),
                sector_counts["len"].to_list(),
            )
        )

    # Contagem por classe de volatilidade
    by_volatility_class: dict[str, int] = {}
    if "volatility_class" in df.columns:
        vol_counts = df.group_by("volatility_class").len()
        by_volatility_class = dict(
            zip(
                vol_counts["volatility_class"].to_list(),
                vol_counts["len"].to_list(),
            )
        )

    # Contagem por classe de liquidez
    by_liquidity_class: dict[str, int] = {}
    if "liquidity_class" in df.columns:
        liq_counts = df.group_by("liquidity_class").len()
        by_liquidity_class = dict(
            zip(
                liq_counts["liquidity_class"].to_list(),
                liq_counts["len"].to_list(),
            )
        )

    # Monta resumo
    summary: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "total_candidates": total,
        "target_range": {"min": TARGET_MIN_CANDIDATES, "max": TARGET_MAX_CANDIDATES},
        "in_target_range": in_target_range,
        "by_sector": by_sector,
        "by_volatility_class": by_volatility_class,
        "by_liquidity_class": by_liquidity_class,
    }

    # Adiciona metadados do pipeline se disponíveis
    if metadata:
        summary["pipeline_metadata"] = {
            "execution_date": metadata.execution_date.isoformat(),
            "input_record_count": metadata.input_record_count,
            "output_record_count": metadata.output_record_count,
            "filters_applied": metadata.filters_applied,
            "warnings": metadata.warnings,
        }

    return summary


def print_summary(summary: dict[str, Any]) -> None:
    """Imprime o resumo de forma legível."""
    print("\n" + "=" * 60)
    print("RESUMO DA PRÉ-LISTA UNIVERSE_CANDIDATES")
    print("=" * 60)

    total = summary["total_candidates"]
    in_range = summary["in_target_range"]
    target = summary["target_range"]

    print(f"\nTotal de candidatos: {total}")
    print(f"Intervalo alvo: {target['min']} - {target['max']}")

    if in_range:
        print("Dentro do intervalo: ✓ SIM")
    else:
        print("Dentro do intervalo: ✗ NÃO")
        if total < target["min"]:
            print(f"  ⚠️  Faltam {target['min'] - total} candidatos para atingir o mínimo")
        else:
            print(f"  ⚠️  Excedem {total - target['max']} candidatos acima do máximo")

    # Por setor
    by_sector = summary.get("by_sector", {})
    if by_sector:
        print("\nDistribuição por SETOR:")
        for sector, count in sorted(by_sector.items(), key=lambda x: -x[1]):
            pct = (count / total * 100) if total > 0 else 0
            print(f"  {sector}: {count} ({pct:.1f}%)")

    # Por volatilidade
    by_vol = summary.get("by_volatility_class", {})
    if by_vol:
        print("\nDistribuição por VOLATILIDADE:")
        for vol_class in ["BAIXA", "MEDIA", "ALTA"]:
            count = by_vol.get(vol_class, 0)
            pct = (count / total * 100) if total > 0 else 0
            print(f"  {vol_class}: {count} ({pct:.1f}%)")

    # Por liquidez
    by_liq = summary.get("by_liquidity_class", {})
    if by_liq:
        print("\nDistribuição por LIQUIDEZ:")
        for liq_class in ["BAIXA", "MEDIA", "ALTA"]:
            count = by_liq.get(liq_class, 0)
            pct = (count / total * 100) if total > 0 else 0
            print(f"  {liq_class}: {count} ({pct:.1f}%)")

    # Metadados do pipeline
    meta = summary.get("pipeline_metadata")
    if meta:
        print("\nMetadados do pipeline:")
        print(f"  Execução: {meta['execution_date']}")
        print(f"  Registros entrada: {meta['input_record_count']:,}")
        print(f"  Registros saída: {meta['output_record_count']:,}")
        print(f"  Filtros aplicados: {len(meta['filters_applied'])}")
        if meta["warnings"]:
            print(f"  Warnings: {len(meta['warnings'])}")
            for w in meta["warnings"]:
                print(f"    - {w}")

    print("=" * 60 + "\n")


def save_summary(summary: dict[str, Any], path: str) -> None:
    """Salva o resumo em arquivo JSON."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"📄 Resumo salvo em: {output_path}")


# =============================================================================
# FUNÇÕES PRINCIPAIS
# =============================================================================


def run_validation_only() -> int:
    """Executa apenas validação de dados existentes.

    Returns:
        Código de saída (0 = sucesso, != 0 = erro).
    """
    print("\n" + "=" * 60)
    print("VALIDAÇÃO DE UNIVERSE_CANDIDATES EXISTENTE")
    print("=" * 60)

    logger = logging.getLogger(__name__)

    try:
        # Carrega dados existentes
        df = load_universe_candidates()
        logger.info(f"Carregados {len(df)} candidatos")

        # Valida
        validation = validate_universe_candidates(df)
        if not validation.is_valid:
            logger.error("Validação falhou:")
            for err in validation.errors:
                logger.error(f"  - {err}")
            return EXIT_VALIDATION_ERROR

        # Carrega metadados
        metadata = get_pipeline_metadata()

        # Gera resumo
        summary = summarize_universe_candidates(df, metadata)
        print_summary(summary)

        # Retorna código de saída baseado no intervalo
        if summary["in_target_range"]:
            return EXIT_SUCCESS
        else:
            logger.warning("Número de candidatos fora do intervalo alvo!")
            return EXIT_OUT_OF_RANGE

    except FileNotFoundError as e:
        logger.error(f"Arquivo não encontrado: {e}")
        logger.error("Execute o pipeline primeiro: python scripts/build_universe_candidates.py")
        return EXIT_VALIDATION_ERROR


def run_full_pipeline(
    with_ingestion: bool = False,
    output_summary_path: str | None = None,
) -> int:
    """Executa o pipeline completo (opcionalmente com ingestão).

    Args:
        with_ingestion: Se True, executa ingestão antes do pipeline.
        output_summary_path: Caminho para salvar resumo em JSON.

    Returns:
        Código de saída (0 = sucesso, != 0 = erro).
    """
    print("\n" + "=" * 60)
    print("CONSTRUÇÃO DA PRÉ-LISTA UNIVERSE_CANDIDATES")
    print("=" * 60)

    logger = logging.getLogger(__name__)
    total_steps = 3 if with_ingestion else 2
    current_step = 0

    # Etapa 1: Ingestão (opcional)
    if with_ingestion:
        current_step += 1
        print(f"\n[{current_step}/{total_steps}] Ingestão de dados de mercado...")

        try:
            files = fetch_and_store_universe_market_data(overwrite=False)
            logger.info(f"Ingestão concluída: {len(files)} arquivos")
        except Exception as e:
            logger.error(f"Erro na ingestão: {e}")
            return EXIT_INGESTION_ERROR

        # Valida dados brutos
        validation = validate_raw_market_data()
        if not validation["valid"]:
            logger.error("Dados brutos inválidos após ingestão")
            for err in validation.get("errors", []):
                logger.error(f"  - {err}")
            return EXIT_INGESTION_ERROR

    # Etapa 2: Pipeline UNIVERSE_CANDIDATES
    current_step += 1
    print(f"\n[{current_step}/{total_steps}] Executando pipeline UNIVERSE_CANDIDATES...")

    try:
        output_path = build_universe_candidates(force_refresh=True)
        logger.info(f"Pipeline concluído: {output_path}")
    except RuntimeError as e:
        logger.error(f"Erro no pipeline: {e}")
        return EXIT_VALIDATION_ERROR
    except FileNotFoundError as e:
        logger.error(f"Arquivo de configuração não encontrado: {e}")
        return EXIT_VALIDATION_ERROR

    # Etapa 3: Resumo
    current_step += 1
    print(f"\n[{current_step}/{total_steps}] Gerando resumo...")

    # Carrega resultado
    df = load_universe_candidates(output_path)
    validation = validate_universe_candidates(df)

    if not validation.is_valid:
        logger.error("Validação do resultado falhou:")
        for err in validation.errors:
            logger.error(f"  - {err}")
        return EXIT_VALIDATION_ERROR

    # Carrega metadados
    metadata = get_pipeline_metadata(output_path)

    # Gera resumo
    summary = summarize_universe_candidates(df, metadata)
    print_summary(summary)

    # Salva resumo se solicitado
    if output_summary_path:
        save_summary(summary, output_summary_path)

    # Retorna código de saída baseado no intervalo
    if summary["in_target_range"]:
        print("✅ Pré-lista construída com sucesso!")
        return EXIT_SUCCESS
    else:
        logger.warning("⚠️  Número de candidatos fora do intervalo alvo!")
        logger.warning("   Revise os parâmetros em universe_selection_rules_v1.yaml")
        logger.warning("   ou adicione/remova tickers em universe_data_sources_v1.yaml")
        return EXIT_OUT_OF_RANGE


# =============================================================================
# CLI
# =============================================================================


def parse_args() -> argparse.Namespace:
    """Parse argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        description="Constrói a pré-lista UNIVERSE_CANDIDATES para o Trilho A",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Apenas validar dados existentes
  python scripts/build_universe_candidates.py --validate-only

  # Executar pipeline (sem nova ingestão)
  python scripts/build_universe_candidates.py

  # Executar ingestão + pipeline
  python scripts/build_universe_candidates.py --with-ingestion

  # Salvar resumo em JSON
  python scripts/build_universe_candidates.py --output-summary-path data/universe/run_summary.json

Exit codes:
  0 = Sucesso (candidatos dentro do intervalo 60-80)
  1 = Candidatos fora do intervalo alvo
  2 = Erro de validação
  3 = Erro de ingestão
        """,
    )

    parser.add_argument(
        "--with-ingestion",
        action="store_true",
        help="Executa ingestão de dados antes do pipeline",
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Apenas valida UNIVERSE_CANDIDATES existente (não executa pipeline)",
    )

    parser.add_argument(
        "--output-summary-path",
        type=str,
        default=None,
        help="Caminho para salvar resumo em JSON (ex.: data/universe/run_summary.json)",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Modo verbose com mais detalhes de log",
    )

    return parser.parse_args()


def main() -> int:
    """Ponto de entrada principal."""
    args = parse_args()
    setup_logging(args.verbose)

    try:
        if args.validate_only:
            return run_validation_only()
        else:
            return run_full_pipeline(
                with_ingestion=args.with_ingestion,
                output_summary_path=args.output_summary_path,
            )

    except KeyboardInterrupt:
        print("\n\n⚠️  Execução interrompida pelo usuário.")
        return 130
    except Exception as e:
        logging.getLogger(__name__).exception(f"Erro inesperado: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

