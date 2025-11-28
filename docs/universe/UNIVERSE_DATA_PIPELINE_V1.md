# Pipeline de Dados — UNIVERSE_CANDIDATES (V1)

Este documento descreve o fluxo de dados para construção da tabela `UNIVERSE_CANDIDATES` (pré-lista de 60–80 ativos) no projeto PortfolioZero.

> **Configurações relacionadas:**
> - [`config/experiments/universe_data_sources_v1.yaml`](../../config/experiments/universe_data_sources_v1.yaml)
> - [`config/experiments/universe_pipeline_topology_v1.yaml`](../../config/experiments/universe_pipeline_topology_v1.yaml)
> - [`config/experiments/universe_selection_rules_v1.yaml`](../../config/experiments/universe_selection_rules_v1.yaml)

---

## Objetivo

Construir a tabela `UNIVERSE_CANDIDATES` a partir de fontes de dados de mercado, respeitando:

- O schema definido em [`data/universe/UNIVERSE_CANDIDATES.schema.md`](../../data/universe/UNIVERSE_CANDIDATES.schema.md)
- Os parâmetros de seleção em [`config/experiments/universe_selection_rules_v1.yaml`](../../config/experiments/universe_selection_rules_v1.yaml)

Esta tabela é a **pré-lista** de 60–80 ativos candidatos, sobre a qual serão aplicadas as regras de seleção para chegar aos ~30 supervisionados.

---

## Visão Geral do Fluxo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FONTES DE DADOS EXTERNAS                            │
│  • API de corretora / provedor de dados                                     │
│  • Datasets locais (CSV/Parquet)                                            │
│  • Composição de índices (IBOV, IBrX)                                       │
│  • Classificação setorial                                                   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ETAPA 1: INGESTÃO DE DADOS BRUTOS                                          │
│  • Baixar/ler dados de preços e volumes históricos                          │
│  • Baixar/ler lista de ativos elegíveis (ações + BDRs)                      │
│  • Baixar/ler classificação setorial                                        │
│  • Baixar/ler composição de índices                                         │
│  → Saída: data/raw/market/*.parquet                                         │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ETAPA 2: NORMALIZAÇÃO E PADRONIZAÇÃO                                       │
│  • Padronizar tickers (remover espaços, uppercase)                          │
│  • Mapear tipos de instrumento (ACAO_ON, ACAO_PN, BDR)                       │
│  • Unificar chaves de junção entre tabelas                                  │
│  • Tratar dados ausentes                                                    │
│  → Saída: data/interim/universe_normalized.parquet                          │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ETAPA 3: CÁLCULO DE MÉTRICAS                                               │
│  • volume_medio_21d: média de volume financeiro nos últimos 21 pregões      │
│  • preco_medio_21d: média de preço de fechamento nos últimos 21 pregões     │
│  • volatilidade_21d: desvio-padrão dos retornos (anualizado)                │
│  • flag_ibov, flag_ibrx50, flag_ibrx100: participação em índices            │
│  • dias_negociados_252d: contagem de pregões com negociação                 │
│  → Saída: data/interim/universe_with_metrics.parquet                        │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ETAPA 4: APLICAÇÃO DE FILTROS DA PRÉ-LISTA                                 │
│  • min_avg_volume_21d_brl ≥ R$ 5.000.000                                    │
│  • min_price_brl ≥ R$ 5,00                                                  │
│  • min_history_days ≥ 252                                                   │
│  • min_trading_days_ratio_252d ≥ 90%                                        │
│  • tipo_instrumento ∈ {ACAO_ON, ACAO_PN, BDR}                               │
│  • Aplicar exclusões do Owner (flag_excluir_owner = true)                   │
│  → Saída: data/universe/UNIVERSE_CANDIDATES.parquet                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Entradas Esperadas

As fontes de dados são especificadas em `config/experiments/universe_data_sources_v1.yaml`.

### 1. Dados de Mercado (Preços e Volumes)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `ticker` | string | Código do ativo na B3 |
| `trade_date` | date | Data do pregão |
| `close_price_brl` | float | Preço de fechamento ajustado (R$) |
| `volume_brl` | float | Volume financeiro do dia (R$) |

**Requisitos:**
- Mínimo de 252 pregões de histórico
- Dados ajustados por proventos (dividendos, splits)

### 2. Lista de Ativos Elegíveis

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `ticker` | string | Código do ativo |
| `tipo_instrumento` | string | ACAO_ON, ACAO_PN ou BDR |
| `situacao_listagem` | string | Ativo, Suspenso, etc. |

**Requisitos:**
- Apenas ativos em situação "Ativo" são considerados
- FIIs, ETFs e derivativos são automaticamente excluídos

### 3. Classificação Setorial

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `ticker` | string | Código do ativo |
| `setor` | string | Setor econômico |
| `subsetor` | string | Subsetor (opcional) |

### 4. Composição de Índices (Opcional)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `ticker` | string | Código do ativo |
| `indice` | string | Nome do índice (IBOV, IBrX-50, etc.) |
| `flag_membro` | bool | Se o ativo é membro do índice |

---

## Saídas do Pipeline

### Arquivo Principal

```
data/universe/UNIVERSE_CANDIDATES.parquet
```

Este arquivo contém a pré-lista de 60–80 ativos que passaram nos filtros mínimos.

### Colunas do Arquivo de Saída

Conforme definido em `UNIVERSE_CANDIDATES.schema.md`:

| Coluna | Tipo | Obrigatória |
|--------|------|-------------|
| `ticker` | string | ✅ |
| `tipo_instrumento` | string | ✅ |
| `setor` | string | ✅ |
| `subsetor` | string | |
| `volume_medio_21d` | float | ✅ |
| `preco_medio_21d` | float | ✅ |
| `volatilidade_21d` | float | ✅ |
| `flag_ibov` | bool | |
| `flag_ibrx50` | bool | |
| `flag_ibrx100` | bool | |
| `liquidez_classe` | string | |
| `volatilidade_classe` | string | |
| `flag_excluir_owner` | bool | |
| `flag_supervisionado` | bool | |

### Arquivo Opcional (CSV)

```
data/universe/UNIVERSE_CANDIDATES.csv
```

Para inspeção manual e compatibilidade com ferramentas externas.

---

## Cálculo das Métricas

### Volume Médio 21d

```python
volume_medio_21d = df.filter(
    pl.col("trade_date") >= data_referencia - 21_pregoes
).group_by("ticker").agg(
    pl.col("volume_brl").mean().alias("volume_medio_21d")
)
```

### Preço Médio 21d

```python
preco_medio_21d = df.filter(
    pl.col("trade_date") >= data_referencia - 21_pregoes
).group_by("ticker").agg(
    pl.col("close_price_brl").mean().alias("preco_medio_21d")
)
```

### Volatilidade Anualizada

```python
# Retornos diários
retornos = df.with_columns(
    (pl.col("close_price_brl") / pl.col("close_price_brl").shift(1) - 1)
    .alias("retorno_diario")
)

# Volatilidade anualizada (60 dias)
volatilidade_21d = retornos.filter(
    pl.col("trade_date") >= data_referencia - 60_pregoes
).group_by("ticker").agg(
    (pl.col("retorno_diario").std() * (252 ** 0.5)).alias("volatilidade_21d")
)
```

### Classificação de Volatilidade

Conforme `universe_selection_rules_v1.yaml`:

| Classe | Condição |
|--------|----------|
| BAIXA | volatilidade ≤ 20% |
| MEDIA | 20% < volatilidade ≤ 40% |
| ALTA | volatilidade > 40% |

---

## Relação com o Trilho A

```
┌─────────────────────────────────────────────────────────────────┐
│  UNIVERSE_CANDIDATES (60-80 ativos)                             │
│  • Gerado por este pipeline                                     │
│  • Contém todos os ativos que passaram nos filtros mínimos      │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              │  Regras de seleção
                              │  (UNIVERSE_SELECTION_CRITERIA_V1.md)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  UNIVERSE_SUPERVISED (~30 ativos)                               │
│  • Gerado em task futura (TASK_008+)                            │
│  • Contém os ativos selecionados para supervisão                │
└─────────────────────────────────────────────────────────────────┘
```

Este pipeline **não seleciona** os 30 supervisionados. Ele apenas gera a pré-lista consistente e filtrada que será usada como entrada para a seleção.

---

## Implementação Futura

### Localização do Módulo

```
modules/portfoliozero/core/data/universe_candidates_pipeline.py
```

### Contrato de Interface

Definido em:
```
modules/portfoliozero/core/data/universe_candidates_pipeline_contract.md
```

### Stack Tecnológica

| Componente | Tecnologia |
|------------|------------|
| Linguagem | Python 3.11 |
| Manipulação de dados | Polars |
| Validação de schemas | Pydantic |
| Formato de saída | Parquet (primário), CSV (opcional) |

---

## Dependências de Configuração

O pipeline depende dos seguintes arquivos de configuração:

| Arquivo | Propósito |
|---------|-----------|
| `universe_selection_rules_v1.yaml` | Thresholds de filtros |
| `universe_data_sources_v1.yaml` | Fontes de dados |
| `universe_pipeline_topology_v1.yaml` | Etapas e caminhos |

---

## Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0 | 26/11/2025 | Versão inicial do documento |

