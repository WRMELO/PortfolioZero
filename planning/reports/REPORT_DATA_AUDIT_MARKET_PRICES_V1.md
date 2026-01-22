## Relatorio de Auditoria - Market Prices (V1)

Escopo: inventario e auditoria de `data/raw/market/prices`, origem dos dados e recomendacoes minimas para rotina diaria idempotente (sem duplicacao).

### Contexto documental (PLAN V2)
O PLAN_V2 explicita o "Market Data Package" como artefato base com dados brutos e derivados minimos validados:
```38:44:docs/PORTFOLIOZERO — PLAN_V2 (consolidado).md
## 3) Os 4 produtos (artefatos) do sistema

Tudo no V2 gira em torno de quatro pacotes gerados por pipeline:

1. Market Data Package  
    Dados brutos e derivados mínimos validados (ex.: parquet padronizado, cobertura, datas).
```

### 1) Inventario do diretorio
- Total de arquivos: 122 parquets, padrao majoritario `TICKER_SA.parquet`.
- Um arquivo fora do padrao: `sample_market_data.parquet` (dados sinteticos).
- Tamanho dos parquets por ticker: ~20-26 KB; `sample_market_data.parquet` ~256 KB.

### 2) Schemas encontrados
Foram detectados 2 clusters de schema:
- **Schema A (121 arquivos)**: `date, ticker, open, high, low, close, adj_close, volume, tipo_instrumento, setor`.
- **Schema B (1 arquivo)**: `date, ticker, close, volume, tipo_instrumento, setor` (apenas `sample_market_data.parquet`).

Evidencia de escrita no formato por ticker e path de saida:
```329:355:modules/portfoliozero/core/data/market_data_ingestion.py
    output_config = config.get("output", {})
    base_path = output_config.get("path", "data/raw/market/")
    partitioning = output_config.get("partitioning", "per_ticker")
    output_format = output_config.get("format", "parquet")

    # Cria diretório de saída
    output_dir = root / base_path / "prices"
    output_dir.mkdir(parents=True, exist_ok=True)
...
    if output_format == "parquet":
        df.write_parquet(file_path)
```

### 3) Cobertura temporal (amostra)
- Amostra de 30 arquivos (5 maiores + 25 alfabeticos) mostra:
  - Coluna de data sempre `date`.
  - Intervalo tipico: `2022-01-03` ate `2025-12-01`, com ~980 linhas por ticker.
  - Excecao: `AURE3_SA.parquet` com 922 linhas e inicio em `2022-03-28`.
- `sample_market_data.parquet` cobre `2023-05-22` a `2024-11-29` com 34.032 linhas.

### 4) Duplicidades
- **Entre arquivos**: nenhuma colisao de nomes por normalizacao (case/sufixo).
- **Dentro do arquivo**:
  - Parquets por ticker: sem duplicidade de `date`, e datas monotonicas.
  - `sample_market_data.parquet`: `date` aparece duplicada por conter multiplos tickers (nao ha duplicata por chave `(ticker, date)`).

Leitura recursiva do raw market no pipeline (risco de misturar arquivos):
```181:224:modules/portfoliozero/core/data/universe_candidates_pipeline.py
def _read_raw_market_data(raw_market_path: Path) -> pl.DataFrame:
    if not raw_market_path.exists():
        raise RuntimeError(
            f"Diretório de dados brutos não encontrado: {raw_market_path}\n"
            "Execute primeiro a ingestão de dados para popular data/raw/market/"
        )
...
    parquet_files = list(raw_market_path.glob("**/*.parquet"))
...
    dfs = []
    for pf in parquet_files:
        try:
            df = pl.read_parquet(pf)
            dfs.append(df)
```

### 5) Origem / Proveniencia dos dados
**Scripts e modulos que escrevem em `data/raw/market/prices`:**
- `modules/portfoliozero/core/data/market_data_ingestion.py` (funcao `_persist_ticker_data`).
- `scripts/fetch_market_data.py` (CLI para ingestao com `--overwrite`, `--dry-run`, `--validate-only`).
- `scripts/generate_sample_market_data.py` (gera `sample_market_data.parquet`).

Evidencia de sobrescrita condicional (sem dedup/merge):
```407:415:modules/portfoliozero/core/data/market_data_ingestion.py
        if file_path.exists() and not overwrite:
            logger.info(f"  Arquivo já existe, pulando: {file_path}")
            files_generated.append(str(file_path))
            continue
```

Evidencia do arquivo sintetico:
```111:133:scripts/generate_sample_market_data.py
    # Salva em Parquet
    output_file = output_dir / "sample_market_data.parquet"
    df.write_parquet(output_file)
...
    output_dir = project_root / "data" / "raw" / "market" / "prices"
    output_dir.mkdir(parents=True, exist_ok=True)
```

Configuracao do path base em YAML:
```230:235:config/experiments/universe_data_sources_v1.yaml
output:
  path: data/raw/market/
  partitioning: per_ticker  # Opções: per_ticker, per_ticker_year, single_file
  format: parquet
```

Notebooks:
- `notebooks/build_universe_candidates.ipynb` importa ingestao e executa `build_universe_candidates`, mas nao escreve raw diretamente.
- `notebooks/select_universe_supervised.ipynb` apenas le `data/universe/UNIVERSE_CANDIDATES.parquet`.

### 6) Riscos atuais de duplicacao
- Se houver **mais de um arquivo por ticker** (ex.: `per_ticker_year`), o pipeline concatena tudo sem dedup.
- `sample_market_data.parquet` no mesmo diretorio pode contaminar ingestao real.
- Nao existe manifest/controle de "ultima data ingerida" por ticker.

### 7) Recomendacao minima para rotina diaria idempotente
Sem implementar agora, o desenho minimo sugerido:
- **Chave de idempotencia**: `(ticker, date)` como chave primaria.
- **Dedup**: remover duplicados por `(ticker, date)` antes da persistencia final.
- **Estrategia de escrita**:
  - por ticker: merge incremental + overwrite completo do arquivo por ticker, ou
  - append apenas de datas novas com validacao de cobertura.
- **Manifesto**:
  - manter `data/raw/market/manifest.json` com: ticker, min_date, max_date, row_count, hash do arquivo, updated_at.
  - bloquear ingestao se tentar reprocessar sem alteracao de janela.
- **Higienizacao**:
  - manter `sample_market_data.parquet` fora do path de producao ou com exclusao explicita na leitura.

### 8) Conclusao
O estado atual atende a um baseline de dados por ticker, mas a rotina diaria ainda nao e idempotente por falta de dedup/manifesto. O risco principal esta na concatenacao cega de parquets e na presenca de `sample_market_data.parquet` no mesmo diretorio de producao.
