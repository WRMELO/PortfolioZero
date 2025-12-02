# Runbook — UNIVERSE_SUPERVISED (V1)

## Visão Geral

Este runbook descreve como executar a seleção dos **30 ativos supervisionados** (`UNIVERSE_SUPERVISED`) a partir da pré-lista de candidatos (`UNIVERSE_CANDIDATES`).

---

## Pré-requisitos

1. **UNIVERSE_CANDIDATES** deve existir em `data/universe/UNIVERSE_CANDIDATES.parquet`
2. Ambiente Python com dependências instaladas (`polars`, `pyyaml`)
3. Arquivos de configuração presentes em `config/experiments/`

---

## Execução Básica

### 1. Execução Padrão

```bash
python scripts/build_universe_supervised.py
```

**O que faz:**
- Carrega `UNIVERSE_CANDIDATES.parquet` (68 candidatos)
- Aplica regras de seleção configuradas
- Gera `UNIVERSE_SUPERVISED.parquet` (30 ativos)
- Gera arquivos auxiliares (CSV, log, lista de tickers)

### 2. Modo Verbose

```bash
python scripts/build_universe_supervised.py -v
```

### 3. Modo Dry-Run (não grava arquivos)

```bash
python scripts/build_universe_supervised.py --dry-run
```

### 4. Mostrar Lista Completa

```bash
python scripts/build_universe_supervised.py --list
```

---

## Arquivos de Configuração

### Regras de Seleção

**Arquivo:** `config/experiments/universe_supervised_selection_rules_v1.yaml`

| Parâmetro | Valor Padrão | Descrição |
|-----------|--------------|-----------|
| `target_size` | 30 | Número alvo de ativos |
| `min_size` | 28 | Mínimo aceitável |
| `max_size` | 32 | Máximo aceitável |
| `sector_constraints.max_per_sector` | 6 | Máximo por setor |
| `volatility_mix.target_low_pct` | 0.30 | % alvo volatilidade BAIXA |
| `volatility_mix.target_medium_pct` | 0.50 | % alvo volatilidade MEDIA |
| `volatility_mix.target_high_pct` | 0.20 | % alvo volatilidade ALTA |
| `liquidity_preferences.max_low_liquidity_count` | 3 | Máx. ativos baixa liquidez |

### Forced Includes/Excludes

Para forçar inclusão ou exclusão de tickers específicos, edite o YAML:

```yaml
owner_overrides:
  forced_includes:
    - PETR4.SA   # Obrigatório
    - VALE3.SA   # Obrigatório
    - ITUB4.SA   # Obrigatório
  forced_excludes:
    - MGLU3.SA   # Excluir por risco específico
```

---

## Arquivos Gerados

| Arquivo | Descrição |
|---------|-----------|
| `data/universe/UNIVERSE_SUPERVISED.parquet` | Lista final (30 ativos) |
| `data/universe/UNIVERSE_SUPERVISED.csv` | Versão CSV para inspeção |
| `data/universe/UNIVERSE_SUPERVISED_selection_log.json` | Log de decisões |
| `data/universe/UNIVERSE_SUPERVISED_tickers.txt` | Lista simples de tickers |

---

## Interpretando o Resultado

### Resumo da Seleção

```
============================================================
RESUMO DA SELEÇÃO — UNIVERSE_SUPERVISED
============================================================

Total selecionado: 30
Tamanho alvo: 30 (mín: 28, máx: 32)
Válido: ✓ SIM

Distribuição por SETOR:
  Financeiro: 5 (16.7%)
  Commodities: 5 (16.7%)
  Energia: 5 (16.7%)
  ...

Distribuição por VOLATILIDADE:
  BAIXA: 9 (30.0%)
  MEDIA: 15 (50.0%)
  ALTA: 6 (20.0%)

Distribuição por LIQUIDEZ:
  ALTA: 18 (60.0%)
  MEDIA: 10 (33.3%)
  BAIXA: 2 (6.7%)
============================================================
```

### Warnings Comuns

| Warning | Significado | Ação |
|---------|-------------|------|
| `Volatilidade X fora da tolerância` | Mix não atingiu o alvo | Ajustar YAML ou candidatos |
| `Universo menor que o mínimo` | Poucos candidatos passaram | Relaxar filtros no YAML |
| `Limite de setor atingido` | Setor saturado | Normal, prioriza liquidez |

---

## Ajustando Regras

### Incluir Mais Ativos de um Setor

```yaml
sector_constraints:
  max_per_sector: 8  # Aumentar de 6 para 8
```

### Permitir Mais Ativos de Baixa Liquidez

```yaml
liquidity_preferences:
  max_low_liquidity_count: 5  # Aumentar de 3 para 5
```

### Alterar Mix de Volatilidade

```yaml
volatility_mix:
  target_low_pct: 0.25   # Reduzir defensivos
  target_medium_pct: 0.55  # Mais core
  target_high_pct: 0.20
  tolerance_pct: 0.15  # Tolerância de ±15%
```

### Adicionar Forced Includes

```yaml
owner_overrides:
  forced_includes:
    - PETR4.SA
    - VALE3.SA
    - ITUB4.SA
    - BBDC4.SA
    - WEGE3.SA
    - ABEV3.SA  # Adicionar
```

---

## Ciclo de Ajuste

```
┌─────────────────────────────────────────────────────────┐
│  1. Executar seleção: scripts/build_universe_supervised.py │
│  2. Analisar resumo e warnings                             │
│  3. Se não satisfeito, ajustar YAML                        │
│  4. Re-executar e verificar                                │
│  5. Se OK → Aprovar universo final                         │
└─────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Erro: UNIVERSE_CANDIDATES não encontrado

```
FileNotFoundError: UNIVERSE_CANDIDATES não encontrado
```

**Solução:** Execute primeiro:
```bash
python scripts/build_universe_candidates.py --with-ingestion
```

### Erro: Forced include não encontrado

```
Forced includes não encontrados em UNIVERSE_CANDIDATES: {'TICKER.SA'}
```

**Solução:** Verifique se o ticker existe em UNIVERSE_CANDIDATES ou remova do `forced_includes`.

### Resultado com menos de 28 ativos

Pode ocorrer se:
- Filtros muito restritivos em UNIVERSE_CANDIDATES
- Poucos candidatos por setor

**Solução:** Relaxar filtros no `universe_selection_rules_v1.yaml` ou adicionar mais tickers na configuração de dados.

---

## Logs Detalhados

O arquivo `UNIVERSE_SUPERVISED_selection_log.json` contém:

```json
{
  "timestamp": "2024-12-02T...",
  "candidates_count": 68,
  "selected_count": 30,
  "is_valid": true,
  "by_sector": {"Financeiro": 5, ...},
  "by_volatility": {"BAIXA": 9, "MEDIA": 15, "ALTA": 6},
  "selection_log": [
    {
      "ticker": "PETR4.SA",
      "action": "included",
      "reason": "forced_include pelo Owner",
      "sector": "Commodities",
      "volatility_class": "BAIXA",
      "liquidity_class": "ALTA"
    },
    ...
  ]
}
```

---

## Próximos Passos

Após aprovar o `UNIVERSE_SUPERVISED`:

1. **Modelos Supervisionados:** Usar os 30 ativos para treinar modelos de previsão
2. **Ambiente RL:** Configurar ambiente MuZero com esses ativos
3. **Black-Litterman:** Usar como universo base para otimização de portfólio

---

*Documento gerado em 02/12/2024*

