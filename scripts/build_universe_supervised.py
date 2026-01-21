#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PortfolioZero — Script de Seleção do Universo Supervisionado

Este script orquestra a seleção dos ~30 ativos supervisionados
(UNIVERSE_SUPERVISED) a partir da pré-lista de candidatos (UNIVERSE_CANDIDATES).

Uso:
    # Execução padrão
    python scripts/build_universe_supervised.py
    
    # Modo dry-run (não grava arquivos)
    python scripts/build_universe_supervised.py --dry-run
    
    # Com caminho customizado para configuração
    python scripts/build_universe_supervised.py --config path/to/config.yaml
    
    # Verbose mode
    python scripts/build_universe_supervised.py -v

Autor: Coding Agent
Data: 02/12/2024
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Adiciona o diretório de módulos ao path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "modules"))

from portfoliozero.core.universe.universe_supervised_selector import (
    build_universe_supervised,
    load_supervised_selection_config,
    SelectionResult,
)
from portfoliozero.core.data.universe_candidates_pipeline import (
    load_universe_candidates,
)


def setup_logging(verbose: bool = False) -> None:
    """Configura logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s - %(message)s",
    )


def print_summary(result: SelectionResult) -> None:
    """Imprime resumo da seleção."""
    print("\n" + "=" * 60)
    print("RESUMO DA SELEÇÃO — UNIVERSE_SUPERVISED")
    print("=" * 60)
    
    print(f"\nTotal selecionado: {result.selected_count}")
    print(f"Tamanho alvo: {result.target_size} (mín: {result.min_size}, máx: {result.max_size})")
    print(f"Válido: {'✓ SIM' if result.is_valid else '✗ NÃO'}")
    
    # Por setor
    print("\nDistribuição por SETOR:")
    total = result.selected_count or 1
    for sector, count in sorted(result.by_sector.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        print(f"  {sector}: {count} ({pct:.1f}%)")
    
    # Por volatilidade
    print("\nDistribuição por VOLATILIDADE:")
    for vol_class in ["BAIXA", "MEDIA", "ALTA"]:
        count = result.by_volatility.get(vol_class, 0)
        pct = count / total * 100
        print(f"  {vol_class}: {count} ({pct:.1f}%)")
    
    # Por liquidez
    print("\nDistribuição por LIQUIDEZ:")
    for liq_class in ["ALTA", "MEDIA", "BAIXA"]:
        count = result.by_liquidity.get(liq_class, 0)
        pct = count / total * 100
        print(f"  {liq_class}: {count} ({pct:.1f}%)")
    
    # Forced includes
    if result.forced_includes_applied:
        print(f"\nForced includes aplicados: {len(result.forced_includes_applied)}")
        for ticker in result.forced_includes_applied:
            print(f"  ✓ {ticker}")
    
    # Warnings
    if result.warnings:
        print("\n⚠️ Warnings:")
        for w in result.warnings:
            print(f"  - {w}")
    
    print("\n" + "=" * 60)


def print_selected_list(result: SelectionResult) -> None:
    """Imprime lista de ativos selecionados."""
    if result.selected_df is None:
        return
    
    print("\n" + "=" * 60)
    print("LISTA DOS 30 ATIVOS SUPERVISIONADOS")
    print("=" * 60)
    
    df = result.selected_df.sort("setor", "avg_volume_21d_brl", descending=[False, True])
    
    print(f"\n{'#':>2} {'Ticker':<12} {'Setor':<12} {'Volume':>12} {'Vol.':>8} {'Liq.':>8}")
    print("-" * 60)
    
    for i, row in enumerate(df.iter_rows(named=True), 1):
        vol_m = row.get("avg_volume_21d_brl", 0) / 1_000_000
        print(
            f"{i:2}. {row.get('ticker', 'N/A'):<12} "
            f"{row.get('setor', 'N/A'):<12} "
            f"R$ {vol_m:>8.1f}M "
            f"{row.get('volatility_class', 'N/A'):>8} "
            f"{row.get('liquidity_class', 'N/A'):>8}"
        )


def main() -> int:
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Seleciona UNIVERSE_SUPERVISED (~30 ativos) a partir de UNIVERSE_CANDIDATES"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Caminho para arquivo de configuração YAML"
    )
    parser.add_argument(
        "--candidates",
        type=str,
        default=None,
        help="Caminho para UNIVERSE_CANDIDATES.parquet"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Diretório de saída"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Executa sem gravar arquivos"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Mostra lista completa dos ativos selecionados"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Modo verbose (mais detalhes)"
    )
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    
    logger = logging.getLogger(__name__)
    
    try:
        # Carrega configuração para obter o result
        config = load_supervised_selection_config(args.config)
        
        # Carrega candidatos
        candidates_df = load_universe_candidates(args.candidates)
        
        # Importa a função de seleção
        from portfoliozero.core.universe.universe_supervised_selector import (
            select_supervised_universe,
        )
        
        # Executa seleção
        result = select_supervised_universe(candidates_df, config)
        
        # Imprime resumo
        print_summary(result)
        
        if args.list:
            print_selected_list(result)
        
        # Se não for dry-run, executa pipeline completo
        if not args.dry_run:
            output_path = build_universe_supervised(
                config_path=args.config,
                candidates_path=args.candidates,
                output_dir=args.output_dir,
                dry_run=False,
            )
            print(f"\n✅ Arquivos gerados em: {Path(output_path).parent}")
        else:
            print("\n[dry-run] Arquivos não foram gravados")
        
        # Exit code
        if result.is_valid:
            return 0
        elif result.selected_count < result.min_size:
            logger.warning("Universo menor que o esperado")
            return 1
        elif result.selected_count > result.max_size:
            logger.warning("Universo maior que o esperado")
            return 1
        else:
            return 0
        
    except FileNotFoundError as e:
        logger.error(f"Arquivo não encontrado: {e}")
        return 2
    except ValueError as e:
        logger.error(f"Erro de configuração: {e}")
        return 3
    except Exception as e:
        logger.exception(f"Erro inesperado: {e}")
        return 4


if __name__ == "__main__":
    sys.exit(main())



