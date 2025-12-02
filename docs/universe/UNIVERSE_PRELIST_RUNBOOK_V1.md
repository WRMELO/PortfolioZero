# UNIVERSE_CANDIDATES — Runbook de Operação V1

> **Versão:** 1.0  
> **Data:** 02/12/2024  
> **Responsável:** Coding Agent  

---

## 1. Visão Geral

Este documento descreve o fluxo operacional para construir e manter a **pré-lista UNIVERSE_CANDIDATES** (60-80 tickers candidatos ao universo supervisionado de ~30 ativos).

### Componentes Envolvidos

| Componente | Arquivo | Descrição |
|------------|---------|-----------|
| Script de Orquestração | `scripts/build_universe_candidates.py` | CLI para executar ingestão + pipeline |
| Módulo de Ingestão | `modules/portfoliozero/core/data/market_data_ingestion.py` | Baixa dados do Yahoo Finance |
| Pipeline | `modules/portfoliozero/core/data/universe_candidates_pipeline.py` | Filtra e classifica candidatos |
| Config de Tickers | `config/experiments/universe_data_sources_v1.yaml` | Lista de ~80 tickers alvo |
| Config de Regras | `config/experiments/universe_selection_rules_v1.yaml` | Parâmetros de filtro |

---

## 2. Comandos Típicos

### 2.1 Primeira Execução (com Ingestão)

```bash
# Baixa dados de mercado + executa pipeline
python scripts/build_universe_candidates.py --with-ingestion
```

**Tempo estimado:** 5-10 minutos (depende da quantidade de tickers e conexão)

### 2.2 Execução Subsequente (sem Ingestão)

```bash
# Usa dados já existentes em data/raw/market/
python scripts/build_universe_candidates.py
```

**Tempo estimado:** 10-30 segundos

### 2.3 Apenas Validar Dados Existentes

```bash
# Valida UNIVERSE_CANDIDATES.parquet sem reprocessar
python scripts/build_universe_candidates.py --validate-only
```

### 2.4 Salvar Resumo em JSON

```bash
# Gera arquivo de resumo para análise posterior
python scripts/build_universe_candidates.py --output-summary-path data/universe/run_summary.json
```

### 2.5 Forçar Re-ingestão Completa

```bash
# Sobrescreve dados existentes
python scripts/fetch_market_data.py --overwrite

# Em seguida, executa pipeline
python scripts/build_universe_candidates.py
```

---

## 3. Interpretação do Resumo

### 3.1 Saída Típica

```
============================================================
RESUMO DA PRÉ-LISTA UNIVERSE_CANDIDATES
============================================================

Total de candidatos: 72
Intervalo alvo: 60 - 80
Dentro do intervalo: ✓ SIM

Distribuição por SETOR:
  Financeiro: 12 (16.7%)
  Commodities: 10 (13.9%)
  Energia: 9 (12.5%)
  Consumo: 11 (15.3%)
  Saúde: 8 (11.1%)
  Tecnologia: 10 (13.9%)
  Indústria: 7 (9.7%)
  Utilidades: 5 (6.9%)

Distribuição por VOLATILIDADE:
  BAIXA: 18 (25.0%)
  MEDIA: 30 (41.7%)
  ALTA: 24 (33.3%)

Distribuição por LIQUIDEZ:
  BAIXA: 24 (33.3%)
  MEDIA: 24 (33.3%)
  ALTA: 24 (33.3%)

Metadados do pipeline:
  Execução: 2024-12-02T15:30:00
  Registros entrada: 50,000
  Registros saída: 72
  Filtros aplicados: 6
============================================================
```

### 3.2 Métricas-Chave

| Métrica | Intervalo Ideal | Ação se Fora |
|---------|-----------------|--------------|
| **Total de candidatos** | 60-80 | Ver seção 4 |
| **Setores distintos** | ≥ 6 | Adicionar tickers de setores sub-representados |
| **Concentração por setor** | ≤ 35% | Pipeline já limita a 6 nomes/setor |
| **Volatilidade ALTA** | ≤ 50% | Ajustar thresholds ou adicionar tickers defensivos |

---

## 4. Tratamento de Saídas Fora do Intervalo

### 4.1 Candidatos < 60 (Poucos)

**Sintoma:**
```
Dentro do intervalo: ✗ NÃO
  ⚠️  Faltam 15 candidatos para atingir o mínimo
```

**Exit code:** `1`

**Causas possíveis:**
1. Dados insuficientes (histórico < 252 dias)
2. Tickers com baixa liquidez/volume
3. Parâmetros de filtro muito restritivos

**Ações recomendadas:**
- [ ] Verificar se a ingestão baixou dados suficientes (≥ 1 ano)
- [ ] Adicionar mais tickers em `universe_data_sources_v1.yaml`
- [ ] Relaxar parâmetros em `universe_selection_rules_v1.yaml`:
  - `min_avg_volume_21d_brl`: reduzir de R$ 5M para R$ 3M
  - `min_history_days`: reduzir de 252 para 200
  - `min_trading_days_ratio_252d`: reduzir de 0.9 para 0.8

### 4.2 Candidatos > 80 (Muitos)

**Sintoma:**
```
Dentro do intervalo: ✗ NÃO
  ⚠️  Excedem 10 candidatos acima do máximo
```

**Exit code:** `1`

**Causas possíveis:**
1. Muitos tickers na lista de entrada
2. Parâmetros de filtro muito relaxados

**Ações recomendadas:**
- [ ] Aumentar `min_avg_volume_21d_brl` para R$ 7-10M
- [ ] Aumentar `min_history_days` para 300
- [ ] Reduzir `max_names_per_sector` de 6 para 5
- [ ] Remover tickers menos relevantes de `universe_data_sources_v1.yaml`

---

## 5. Exit Codes

| Código | Significado | Ação |
|--------|-------------|------|
| `0` | Sucesso - candidatos dentro de 60-80 | Nenhuma |
| `1` | Candidatos fora do intervalo alvo | Revisar parâmetros/tickers |
| `2` | Erro de validação | Verificar logs |
| `3` | Erro de ingestão | Verificar conexão/API |

---

## 6. Arquivos Gerados

| Arquivo | Descrição |
|---------|-----------|
| `data/universe/UNIVERSE_CANDIDATES.parquet` | Pré-lista final (Polars/Parquet) |
| `data/universe/UNIVERSE_CANDIDATES.csv` | Versão CSV para inspeção manual |
| `data/universe/UNIVERSE_CANDIDATES_metadata.json` | Metadados do pipeline |
| `data/universe/UNIVERSE_CANDIDATES_run_summary.json` | Resumo da execução (opcional) |

---

## 7. Decisão do Owner

Após executar o pipeline e analisar o resumo:

### ✅ Se dentro do intervalo (60-80):
1. Revisar distribuição setorial — há concentração excessiva?
2. Revisar volatilidade — muitos ativos ALTA podem aumentar risco
3. Se satisfeito, prosseguir para TASK_011 (seleção dos 30 supervisionados)

### ⚠️ Se fora do intervalo:
1. Identificar causa (ver seção 4)
2. Ajustar parâmetros ou lista de tickers
3. Re-executar pipeline
4. Repetir até atingir intervalo alvo

---

## 8. Fluxo Visual

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUXO UNIVERSE_CANDIDATES                 │
└─────────────────────────────────────────────────────────────┘

  universe_data_sources_v1.yaml     universe_selection_rules_v1.yaml
         (80 tickers)                    (filtros e regras)
              │                                 │
              ▼                                 │
    ┌──────────────────┐                        │
    │   INGESTÃO       │                        │
    │ (Yahoo Finance)  │                        │
    └────────┬─────────┘                        │
             │                                  │
             ▼                                  │
    data/raw/market/*.parquet                   │
             │                                  │
             ▼                                  ▼
    ┌─────────────────────────────────────────────┐
    │         PIPELINE UNIVERSE_CANDIDATES         │
    │  1. Leitura de dados brutos                  │
    │  2. Normalização de identificadores          │
    │  3. Cálculo de métricas (vol, liquidez)      │
    │  4. Aplicação de filtros                     │
    │  5. Restrições setoriais                     │
    │  6. Persistência                             │
    └────────────────────┬────────────────────────┘
                         │
                         ▼
         UNIVERSE_CANDIDATES.parquet
              (60-80 tickers)
                         │
                         ▼
    ┌─────────────────────────────────────────────┐
    │              RESUMO / VALIDAÇÃO              │
    │  • Total de candidatos                       │
    │  • Distribuição por setor                    │
    │  • Distribuição por volatilidade             │
    │  • Distribuição por liquidez                 │
    │  • Exit code baseado no intervalo            │
    └─────────────────────────────────────────────┘
                         │
                         ▼
    ┌─────────────────────────────────────────────┐
    │           DECISÃO DO OWNER                   │
    │  ✓ Dentro do intervalo → TASK_011           │
    │  ✗ Fora do intervalo → ajustar e re-executar│
    └─────────────────────────────────────────────┘
```

---

## 9. Troubleshooting

### Erro: "Arquivo de configuração não encontrado"
```bash
# Verifique se os arquivos existem
ls config/experiments/universe_selection_rules_v1.yaml
ls config/experiments/universe_data_sources_v1.yaml
```

### Erro: "Nenhum arquivo Parquet encontrado"
```bash
# Execute ingestão primeiro
python scripts/build_universe_candidates.py --with-ingestion
```

### Erro: "yfinance não está instalado"
```bash
# Instale a dependência
pip install yfinance
# ou
poetry install
```

### Pipeline muito lento
- Verifique se o Docker está consumindo muita memória
- Reduza o período de dados em `date_range.start`
- Execute fora do Docker se possível

---

*Última atualização: 02/12/2024*

