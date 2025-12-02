#!/usr/bin/env python3
"""Script CLI para ingestão de dados de mercado.

Este script orquestra a ingestão de dados de mercado usando o módulo
market_data_ingestion, baixando dados OHLCV para o universo de tickers
definido na configuração.

Usage:
    python scripts/fetch_market_data.py
    python scripts/fetch_market_data.py --config config/experiments/universe_data_sources_v1.yaml
    python scripts/fetch_market_data.py --overwrite
    python scripts/fetch_market_data.py --dry-run

Example:
    $ python scripts/fetch_market_data.py --overwrite
    
    ============================================================
    Iniciando ingestão de dados de mercado
      Provider: yahoo_finance
      Tickers: 80
      Período: 2022-01-01 a 2024-12-02
    ============================================================
    [1/80] Processando ITUB4.SA...
      ✓ Salvo: data/raw/market/prices/ITUB4_SA.parquet (720 registros)
    ...
    ============================================================
    Ingestão concluída
      Tempo total: 45.3s
      Arquivos gerados: 78
      Registros totais: 56,160
      Falhas: 2
    ============================================================
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Adiciona o diretório do projeto ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "modules"))

from portfoliozero.core.data.market_data_ingestion import (
    fetch_and_store_universe_market_data,
    load_data_source_config,
    validate_raw_market_data,
)


def setup_logging(verbose: bool = False) -> None:
    """Configura logging para o script."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def parse_args() -> argparse.Namespace:
    """Parse argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        description="Ingestão de dados de mercado para o PortfolioZero",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python scripts/fetch_market_data.py
  python scripts/fetch_market_data.py --config custom_config.yaml
  python scripts/fetch_market_data.py --overwrite
  python scripts/fetch_market_data.py --dry-run
  python scripts/fetch_market_data.py --validate-only
        """,
    )

    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Caminho do arquivo YAML de configuração (default: config/experiments/universe_data_sources_v1.yaml)",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescreve arquivos existentes",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas mostra o que seria baixado, sem executar",
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Apenas valida os dados existentes em data/raw/market/",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Modo verbose com mais detalhes de log",
    )

    return parser.parse_args()


def print_config_summary(config: dict) -> None:
    """Imprime resumo da configuração."""
    print("\n" + "=" * 60)
    print("CONFIGURAÇÃO DE INGESTÃO")
    print("=" * 60)
    print(f"  Provider: {config.get('provider', 'yahoo_finance')}")
    print(f"  Tickers: {len(config.get('universe', []))}")

    date_range = config.get("date_range", {})
    print(f"  Período: {date_range.get('start', 'N/A')} a {date_range.get('end', 'today')}")

    output = config.get("output", {})
    print(f"  Output: {output.get('path', 'data/raw/market/')}")
    print(f"  Formato: {output.get('format', 'parquet')}")
    print("=" * 60 + "\n")


def print_validation_summary(validation: dict) -> None:
    """Imprime resumo da validação."""
    print("\n" + "=" * 60)
    print("VALIDAÇÃO DE DADOS")
    print("=" * 60)
    print(f"  Válido: {'✓' if validation['valid'] else '✗'}")
    print(f"  Arquivos: {validation.get('files', 0)}")
    print(f"  Registros totais: {validation.get('total_records', 0):,}")
    print(f"  Tickers: {len(validation.get('tickers', []))}")

    errors = validation.get("errors", [])
    if errors:
        print(f"  Erros: {len(errors)}")
        for err in errors[:5]:  # Mostra apenas os 5 primeiros
            print(f"    - {err}")
        if len(errors) > 5:
            print(f"    ... e mais {len(errors) - 5} erros")
    print("=" * 60 + "\n")


def main() -> int:
    """Ponto de entrada principal."""
    args = parse_args()
    setup_logging(args.verbose)

    logger = logging.getLogger(__name__)

    try:
        # Modo: apenas validação
        if args.validate_only:
            print("\n🔍 Validando dados existentes...")
            validation = validate_raw_market_data()
            print_validation_summary(validation)
            return 0 if validation["valid"] else 1

        # Carrega configuração
        config = load_data_source_config(args.config)
        print_config_summary(config)

        # Modo: dry run
        if args.dry_run:
            print("🔍 [DRY RUN] Nenhum arquivo será criado\n")
            universe = config.get("universe", [])
            for i, ticker in enumerate(universe, 1):
                print(f"  [{i}/{len(universe)}] Seria baixado: {ticker}")
            print(f"\nTotal: {len(universe)} tickers")
            return 0

        # Executa ingestão
        print("🚀 Iniciando ingestão...\n")
        files = fetch_and_store_universe_market_data(
            config_path=args.config,
            overwrite=args.overwrite,
        )

        # Resumo final
        print("\n" + "=" * 60)
        print("RESUMO FINAL")
        print("=" * 60)
        print(f"  Arquivos gerados: {len(files)}")

        # Valida resultado
        validation = validate_raw_market_data()
        print(f"  Registros totais: {validation.get('total_records', 0):,}")
        print(f"  Tickers únicos: {len(validation.get('tickers', []))}")
        print("=" * 60)

        if files:
            print("\n✅ Ingestão concluída com sucesso!")
            print("   Próximo passo: execute build_universe_candidates()")
        else:
            print("\n⚠️  Nenhum arquivo foi gerado.")

        return 0

    except FileNotFoundError as e:
        logger.error(f"Arquivo não encontrado: {e}")
        return 1
    except ValueError as e:
        logger.error(f"Erro de configuração: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Ingestão interrompida pelo usuário.")
        return 130
    except Exception as e:
        logger.exception(f"Erro inesperado: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

