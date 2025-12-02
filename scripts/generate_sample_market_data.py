"""Script para gerar dados sintéticos de mercado para testes.

Este script cria arquivos Parquet com dados fictícios de preços e volumes
para testar o pipeline UNIVERSE_CANDIDATES.

Uso:
    python scripts/generate_sample_market_data.py
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl


def generate_sample_data(output_dir: Path, num_tickers: int = 100, num_days: int = 400) -> None:
    """Gera dados sintéticos de mercado.

    Args:
        output_dir: Diretório de saída para os arquivos Parquet.
        num_tickers: Número de tickers a gerar.
        num_days: Número de dias de histórico.
    """
    random.seed(42)
    np.random.seed(42)

    # Lista de tickers fictícios
    prefixes = ["PETR", "VALE", "ITUB", "BBDC", "ABEV", "WEGE", "MGLU", "RENT", "LREN", "JBSS"]
    suffixes = ["3", "4", "11"]
    sectors = ["Commodities", "Financeiro", "Consumo", "Indústria", "Saúde", "Tecnologia", "Energia", "Utilidades"]
    instrument_types = ["ACAO_ON", "ACAO_PN", "BDR"]

    # Gera lista de tickers únicos
    tickers = []
    for prefix in prefixes:
        for suffix in suffixes:
            tickers.append(f"{prefix}{suffix}")
            if len(tickers) >= num_tickers:
                break
        if len(tickers) >= num_tickers:
            break

    # Se precisar de mais tickers
    while len(tickers) < num_tickers:
        ticker = f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=4))}{random.choice(suffixes)}"
        if ticker not in tickers:
            tickers.append(ticker)

    # Gera datas (últimos N dias úteis aproximadamente)
    end_date = datetime(2024, 11, 29)
    dates = []
    current = end_date
    while len(dates) < num_days:
        if current.weekday() < 5:  # Dias úteis
            dates.append(current.date())
        current -= timedelta(days=1)
    dates = sorted(dates)

    # Gera dados para cada ticker
    all_data = []

    for ticker in tickers:
        # Características do ativo
        base_price = random.uniform(5, 200)
        base_volume = random.uniform(1_000_000, 50_000_000)
        volatility = random.uniform(0.01, 0.04)  # Volatilidade diária
        sector = random.choice(sectors)
        instrument_type = random.choice(instrument_types)

        # Alguns ativos terão histórico menor (para testar filtros)
        ticker_days = num_days if random.random() > 0.2 else random.randint(100, 250)

        prices = [base_price]
        for _ in range(ticker_days - 1):
            # Random walk com drift
            daily_return = np.random.normal(0.0002, volatility)
            prices.append(prices[-1] * (1 + daily_return))

        # Alguns dias sem negociação (para testar trading_days_ratio)
        skip_days = set()
        if random.random() > 0.7:
            skip_days = set(random.sample(range(len(prices)), min(30, len(prices) // 5)))

        for i, (date, price) in enumerate(zip(dates[-ticker_days:], prices)):
            if i in skip_days:
                continue

            # Volume varia aleatoriamente
            volume = base_volume * random.uniform(0.5, 1.5)

            # Alguns ativos de baixa liquidez
            if random.random() > 0.8:
                volume = volume * 0.1

            all_data.append({
                "date": date,
                "ticker": ticker,
                "close": round(price, 2),
                "volume": round(volume, 0),
                "tipo_instrumento": instrument_type,
                "setor": sector,
            })

    # Cria DataFrame
    df = pl.DataFrame(all_data)

    # Salva em Parquet
    output_file = output_dir / "sample_market_data.parquet"
    df.write_parquet(output_file)

    print(f"Dados gerados com sucesso!")
    print(f"  Arquivo: {output_file}")
    print(f"  Tickers: {len(tickers)}")
    print(f"  Registros: {len(df)}")
    print(f"  Período: {dates[0]} a {dates[-1]}")
    print(f"\nAmostra dos dados:")
    print(df.head(10))


def main() -> None:
    """Ponto de entrada principal."""
    # Encontra diretório raiz do projeto
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    output_dir = project_root / "data" / "raw" / "market" / "prices"
    output_dir.mkdir(parents=True, exist_ok=True)

    generate_sample_data(output_dir, num_tickers=100, num_days=400)


if __name__ == "__main__":
    main()

