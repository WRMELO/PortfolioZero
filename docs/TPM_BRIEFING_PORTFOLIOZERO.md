# PortfolioZero — Briefing Completo para o TPM (Planejador)

> **Documento para:** Technical Project Manager (TPM) / Planejador  
> **Objetivo:** Fornecer todas as informações necessárias para orientar a codificação  
> **Gerado em:** 02/12/2025  
> **Versão:** 1.0

---

## 📋 ÍNDICE

1. [Visão Geral do Projeto](#1-visão-geral-do-projeto)
2. [Perfil do Owner e Restrições de Negócio](#2-perfil-do-owner-e-restrições-de-negócio)
3. [Arquitetura Técnica](#3-arquitetura-técnica)
4. [Stack Tecnológica](#4-stack-tecnológica)
5. [Estrutura do Repositório](#5-estrutura-do-repositório)
6. [Código Existente](#6-código-existente)
7. [Configurações Definidas](#7-configurações-definidas)
8. [Contratos de Interface](#8-contratos-de-interface)
9. [Roadmap e Fases](#9-roadmap-e-fases)
10. [Status Atual e Próximos Passos](#10-status-atual-e-próximos-passos)
11. [Regras de Operação](#11-regras-de-operação)
12. [Decisões Arquiteturais Tomadas](#12-decisões-arquiteturais-tomadas)

---

## 1. Visão Geral do Projeto

### O que é o PortfolioZero?

Um **sistema de alocação de portfólio** que combina:
- **MuZero** (RL baseado em planejamento) para decisões de compra/venda
- **Black-Litterman** para transformar as preferências do agente em pesos de carteira

### Objetivo de Negócio

| Aspecto | Valor |
|---------|-------|
| Capital inicial | R$ 500.000 |
| Meta de retorno | 15-20% CAGR real (acima da inflação) |
| Drawdown máximo | 10-15% |
| Horizonte mínimo | 3 anos (circuito fechado) |
| Operação | Long-only, sem alavancagem |

### Nome do Projeto

"PortfolioZero" é uma referência ao **MuZero** da DeepMind — aprender a tomar decisões por simulação e planejamento, sem conhecer as regras a priori.

---

## 2. Perfil do Owner e Restrições de Negócio

### Owner

- **Idade:** 69 anos
- **Patrimônio total:** R$ 3.000.000
- **Capital alocado:** R$ 500.000 (≈17% do patrimônio)
- **Experiência:** 49 anos profissionais
- **Motivação:** Renda complementar + atividade intelectual na aposentadoria

### Restrições Absolutas (NÃO NEGOCIÁVEIS)

| Restrição | Descrição |
|-----------|-----------|
| **Sem alavancagem** | Exposição máxima = 100% do capital |
| **Long-only** | Nunca opera vendido (short) |
| **Sem derivativos** | Proibido opções, futuros, swaps, termo |
| **Sem FIIs/ETFs** | Apenas ações ON/PN e BDRs |
| **Drawdown limite** | Modo defensivo automático se > 15% |

### Comportamento em Modo Defensivo (Drawdown > 15%)

1. Aumentar posição em caixa
2. Reduzir exposição total ao mercado
3. Priorizar ativos de menor volatilidade
4. Manter até recuperação

---

## 3. Arquitetura Técnica

### Visão de Alto Nível

```
┌─────────────────────────────────────────────────────────────────┐
│                      CAMADA DE SUPERVISÃO                       │
│                   ~30 ativos supervisionados                    │
│                   (radar permanente do sistema)                 │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       CAMADA DE AÇÃO                            │
│                   ~10 ativos na carteira                        │
│                   (capital efetivamente alocado)                │
└─────────────────────────────────────────────────────────────────┘
```

### Fluxo de Decisão

```
DADOS DE MERCADO
      │
      ▼
MODELO DE RISCO CURTO PRAZO (D+1, D+3, D+5)
      │
      ▼
AGENTE MUZERO (aprende política por simulação)
      │
      ▼
BLACK-LITTERMAN (transforma views em pesos)
      │
      ▼
CARTEIRA FINAL (10 ativos, 5%-15% cada)
```

### Componentes Principais

| Componente | Localização | Responsabilidade |
|------------|-------------|------------------|
| **Data Pipeline** | `core/data/` | Ingestão, normalização, métricas |
| **Environment** | `core/env/` | Ambiente de mercado simulado (Gym-like) |
| **MuZero Agent** | `core/rl/muzero/` | Redes neurais + replay buffer + trainer |
| **MCTS Search** | `core/rl/search/` | Monte Carlo Tree Search para planejamento |
| **Black-Litterman** | `core/allocation/` | Otimização de pesos com views |
| **Models** | `core/models/` | Redes de representação, dinâmica, previsão |

---

## 4. Stack Tecnológica

### Ambiente de Execução

| Componente | Versão | Status |
|------------|--------|--------|
| Python | 3.11.14 | ✅ Configurado |
| Ubuntu (container) | 24.04 LTS | ✅ Configurado |
| Docker image | portfoliozero:latest | ✅ 17.2GB |
| Poetry | 2.2.1 | ✅ Configurado |

### Dependências Principais

```toml
# Core
polars = "^1.16.0"      # DataFrames de alta performance
pydantic = "^2.10.3"    # Validação de dados e configs
torch = "^2.5.1"        # Deep Learning (MuZero)
ray = "^2.40.0"         # Computação distribuída
numpy = "^1.26.4"       # Computação numérica
pandas = "^2.2.3"       # Compatibilidade
scipy = "^1.14.1"       # Otimização (Black-Litterman)

# Dev
pytest = "^8.3.4"       # Testes
black = "^24.10.0"      # Formatação
ruff = "^0.8.2"         # Linting
mypy = "^1.13.0"        # Type checking
```

### Convenções de Código

- **Line length:** 100 caracteres
- **Type hints:** Obrigatórios (`disallow_untyped_defs = true`)
- **Imports:** Ordenados por ruff (isort)
- **Docstrings:** Google style

---

## 5. Estrutura do Repositório

```
PortfolioZero/
│
├── config/
│   └── experiments/
│       ├── universe_selection_rules_v1.yaml    # Parâmetros de seleção
│       ├── universe_data_sources_v1.yaml       # Fontes de dados
│       ├── universe_pipeline_topology_v1.yaml  # Topologia do pipeline
│       └── default_muzero_bl.yaml              # Config padrão experimento
│
├── data/
│   ├── raw/market/          # Dados brutos (prices, sectors, indices)
│   ├── interim/             # Dados intermediários
│   ├── processed/           # Dados prontos para uso
│   └── universe/            # UNIVERSE_CANDIDATES.parquet
│
├── docs/
│   ├── PORTFOLIOZERO_PLAN_V1.md              # Plano de negócio (referência)
│   └── universe/
│       ├── UNIVERSE_TRILHO_A_OVERVIEW.md     # Visão geral Trilho A
│       ├── UNIVERSE_SELECTION_CRITERIA_V1.md # Critérios de seleção
│       ├── UNIVERSE_DATA_PIPELINE_V1.md      # Pipeline de dados
│       └── UNIVERSE_DECISION_LOG_TEMPLATE.md # Template de log
│
├── modules/portfoliozero/
│   ├── __init__.py
│   ├── config/
│   │   ├── base.py          # BaseConfig, GlobalConfig
│   │   └── domain.py        # DataConfig, MuZeroConfig, BlackLittermanConfig
│   ├── core/
│   │   ├── data/            # Pipeline de dados (a implementar)
│   │   ├── env/             # Ambiente de mercado (a implementar)
│   │   ├── rl/
│   │   │   ├── muzero/      # Agente MuZero (a implementar)
│   │   │   └── search/      # MCTS (a implementar)
│   │   ├── models/          # Redes neurais (a implementar)
│   │   └── allocation/      # Black-Litterman (a implementar)
│   └── utils/
│       ├── logging.py       # setup_logging()
│       └── random.py        # set_global_seed()
│
├── planning/task_specs/     # JSONs de tasks do TPM
│   ├── TASK_005_*.json
│   ├── TASK_006_*.json
│   └── TASK_007_*.json
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── notebooks/
│   ├── eda/
│   └── prototipos/
│
├── pyproject.toml
├── Dockerfile
└── README.md
```

---

## 6. Código Existente

### 6.1 Classes Pydantic de Configuração

**Localização:** `modules/portfoliozero/config/domain.py`

```python
class DataConfig(DomainConfig):
    universe: list[str]                          # Lista de tickers
    data_frequency: Literal["daily", "intraday"] # Default: "daily"
    lookback_window: int = 252                   # Janela histórica
    data_paths: dict[str, str]                   # Mapeamento de datasets

class MuZeroConfig(DomainConfig):
    discount: float = 0.99                       # Gamma
    num_simulations: int = 50                    # Simulações MCTS
    num_unroll_steps: int = 5                    # Unroll da dinâmica
    td_steps: int = 5                            # Bootstrap horizon
    policy_temperature: float = 1.0              # Temperatura exploração
    learning_rate: float = 3e-4
    batch_size: int = 256
    replay_buffer_size: int = 100_000

class BlackLittermanConfig(DomainConfig):
    tau: float = 0.05                            # Incerteza do prior
    risk_aversion: float = 2.5                   # Aversão ao risco
    view_confidence: float = 0.7                 # Confiança nas views
    max_leverage: float = 1.0                    # Sempre 1.0 (long-only)

class RayConfig(DomainConfig):
    enabled: bool = False
    num_workers: int = 1

class LoggingConfig(DomainConfig):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_to_file: bool = True
    log_dir: str = "logs"
```

### 6.2 Utilitários Implementados

```python
# modules/portfoliozero/utils/logging.py
def setup_logging(config: LoggingConfig) -> None:
    """Configura logging com base em LoggingConfig."""

# modules/portfoliozero/utils/random.py
def set_global_seed(seed: int) -> None:
    """Define seeds para random, numpy, torch, CUDA."""
```

---

## 7. Configurações Definidas

### 7.1 Parâmetros de Seleção do Universo

**Arquivo:** `config/experiments/universe_selection_rules_v1.yaml`

```yaml
prelist:
  min_avg_volume_21d_brl: 5000000    # R$ 5 milhões/dia
  min_price_brl: 5.0                  # R$ 5,00
  min_history_days: 252               # 1 ano
  min_trading_days_ratio_252d: 0.9    # 90% dos dias
  allowed_instruments: [ACAO_ON, ACAO_PN, BDR]

sectors:
  min_distinct_sectors: 6
  max_weight_per_sector_pct: 0.35     # Máx 35% por setor
  max_names_per_sector: 6

volatility:
  lookback_days: 60
  thresholds:
    low_max_annualized_vol: 0.20      # BAIXA ≤ 20%
    medium_max_annualized_vol: 0.40   # MEDIA ≤ 40%, ALTA > 40%
  target_proportions:
    min_medium_pct: 0.30              # Mín 30% MEDIA
    max_high_pct: 0.50                # Máx 50% ALTA

universe_size:
  target: 30
  min: 28
  max: 32

review_policy:
  regular_review_months: 12
```

### 7.2 Topologia do Pipeline

**Arquivo:** `config/experiments/universe_pipeline_topology_v1.yaml`

```yaml
stages:
  - id: ingest_raw
    outputs: data/raw/market/*.parquet
    
  - id: normalize_identifiers
    depends_on: [ingest_raw]
    outputs: data/interim/universe_normalized.parquet
    
  - id: compute_metrics
    depends_on: [normalize_identifiers]
    outputs: data/interim/universe_with_metrics.parquet
    
  - id: apply_prelist_filters
    depends_on: [compute_metrics]
    outputs: data/universe/UNIVERSE_CANDIDATES.parquet

paths:
  raw: data/raw/market/
  interim: data/interim/
  output: data/universe/
```

---

## 8. Contratos de Interface

### 8.1 Pipeline de Candidatos ao Universo

**Localização esperada:** `modules/portfoliozero/core/data/universe_candidates_pipeline.py`

```python
def build_universe_candidates(
    config_paths: dict[str, str] | None = None,
    force_refresh: bool = False,
    output_csv: bool = True,
) -> str:
    """
    Executa pipeline completo para construir UNIVERSE_CANDIDATES.
    
    Returns:
        Caminho do arquivo gerado (data/universe/UNIVERSE_CANDIDATES.parquet)
    """

def load_universe_candidates(
    path: str | None = None,
) -> pl.DataFrame:
    """Carrega UNIVERSE_CANDIDATES em DataFrame Polars."""

def validate_universe_candidates(
    df: pl.DataFrame,
) -> ValidationResult:
    """Valida DataFrame contra schema esperado."""
```

### 8.2 Classes de Suporte Esperadas

```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    record_count: int

@dataclass
class PipelineMetadata:
    execution_date: datetime
    input_record_count: int
    output_record_count: int
    filters_applied: list[str]
    warnings: list[str]
```

---

## 9. Roadmap e Fases

### Visão Geral

```
Fase 0 ──► Fase 1 ──► Fase 2 ──► Fase 3 ──► Fase 4 ──► Fase 5
Regras     Dados      MuZero     B-L        Backtest   Dry Run
   │
   └──────► Trilho A: Seleção dos 30 supervisionados (paralelo)
```

### Detalhamento das Fases

| Fase | Nome | Entregas Principais | Status |
|------|------|---------------------|--------|
| **0** | Regras do jogo | Limites, drawdown, quarentena, documentação | ✅ Concluída |
| **A** | Trilho de universo | Pré-lista 60-80, seleção dos 30 | 🟡 Em andamento |
| **1** | Dados e features | Pipeline de dados, modelo de risco D+1/D+3/D+5 | ⏳ Próxima |
| **2** | MuZero | Environment, agente, MCTS, replay buffer | ⏳ Futura |
| **3** | Black-Litterman | Extração de views, otimização de pesos | ⏳ Futura |
| **4** | Backtests | Simulações históricas, comparação com benchmarks | ⏳ Futura |
| **5** | Dry Run | 6+ meses em tempo real, sem capital | ⏳ Futura |

---

## 10. Status Atual e Próximos Passos

### ✅ Já Implementado

- [x] Infraestrutura (Poetry, Docker, .gitignore)
- [x] Ambiente Docker validado (Python 3.11.14, 142 pacotes)
- [x] Scaffold do pacote core (Pydantic configs)
- [x] Plano V1 de negócio e risco
- [x] Área de arquivamento de JSONs
- [x] Documentação do Trilho A
- [x] Regras detalhadas de seleção do universo
- [x] Especificação do pipeline de dados (sem código)

### 🔴 Próximos Passos Sugeridos (prioridade)

1. **TASK_008:** Implementar `universe_candidates_pipeline.py`
   - Ingestão de dados de mercado
   - Cálculo de métricas (volume, volatilidade)
   - Aplicação de filtros
   - Geração de UNIVERSE_CANDIDATES.parquet

2. **TASK_009:** Definir fonte de dados de mercado
   - Escolher provedor (API, dataset local)
   - Implementar adapter de ingestão

3. **TASK_010:** Construir pré-lista de 60-80 candidatos
   - Executar pipeline com dados reais
   - Validar contra critérios

4. **TASK_011:** Selecionar os 30 supervisionados
   - Aplicar regras de concentração setorial
   - Aplicar balanceamento de volatilidade
   - Gerar UNIVERSE_SUPERVISED.parquet

5. **TASK_012:** Implementar modelo de risco de curto prazo
   - Features de retorno/volatilidade
   - Previsão de distribuição D+1, D+3, D+5

---

## 11. Regras de Operação

### Frequência de Decisão

| Tipo | Frequência | Racional |
|------|------------|----------|
| **Venda (gestão de risco)** | Diária | Proteger capital é prioridade |
| **Compra (realocação)** | Semanal | Reduzir custos, evitar overtrading |

### Quarentena Pós-Venda

- **Duração:** 20 pregões (~1 mês)
- **Regra:** Ativo vendido por risco não pode ser recomprado durante quarentena
- **Objetivo:** Evitar comportamento caótico de entra-e-sai

### Limites de Posição

| Parâmetro | Valor |
|-----------|-------|
| Número de ativos na carteira | ~10 (8-12) |
| Tamanho mínimo de posição | 5% |
| Tamanho máximo de posição | 15% |
| Tamanho médio | ~10% |

### Custos a Considerar

- Custo fixo por ordem (corretagem)
- Custo percentual sobre volume (emolumentos)
- IR aproximado (15% sobre lucro > R$ 20k/mês em vendas)
- Penalização por turnover excessivo na reward function

---

## 12. Decisões Arquiteturais Tomadas

### 12.1 Polars vs Pandas

**Decisão:** Usar **Polars** como biblioteca principal de DataFrames.

**Racional:**
- Performance superior para datasets grandes
- API mais consistente
- Lazy evaluation nativo
- Pandas disponível para compatibilidade quando necessário

### 12.2 Pydantic para Configurações

**Decisão:** Todas as configurações são classes Pydantic.

**Racional:**
- Validação estrita de tipos
- Serialização/deserialização automática
- Documentação embutida nos fields
- `extra="forbid"` evita typos silenciosos

### 12.3 YAML para Parâmetros Numéricos

**Decisão:** Parâmetros ajustáveis em arquivos YAML separados.

**Racional:**
- Fácil de editar sem tocar no código
- Versionável
- Pode ser sobrescrito por experimento

### 12.4 Separação Pipeline/Seleção

**Decisão:** O pipeline de candidatos (60-80) é separado da seleção final (30).

**Racional:**
- Pipeline é determinístico e automatizado
- Seleção final pode ter overrides do Owner
- Facilita debugging e reprocessamento

### 12.5 Arquivo Parquet como Formato Principal

**Decisão:** Usar Parquet para todos os datasets intermediários e finais.

**Racional:**
- Compressão eficiente
- Schema embutido
- Leitura rápida com Polars
- CSV apenas para inspeção manual

---

## 📎 Anexos

### A. Arquivos de Specs Arquivados

- `planning/task_specs/TASK_005_TRILHO_A_UNIVERSE_AND_JSON_ARCHIVE.json`
- `planning/task_specs/TASK_006_UNIVERSE_DECISION_RULES_DETAIL.json`
- `planning/task_specs/TASK_007_UNIVERSE_CANDIDATES_PIPELINE.json`

### B. Documentos de Referência Obrigatórios

1. `docs/PORTFOLIOZERO_PLAN_V1.md` — Plano de negócio (leitura obrigatória)
2. `docs/universe/UNIVERSE_SELECTION_CRITERIA_V1.md` — Critérios de seleção
3. `modules/portfoliozero/core/data/universe_candidates_pipeline_contract.md` — Contrato do pipeline

### C. Comandos Úteis

```bash
# Build da imagem Docker
docker build -t portfoliozero:latest .

# Executar container interativo
docker run -it --rm -v $(pwd):/app portfoliozero:latest bash

# Verificar versão do Python
docker run --rm portfoliozero:latest poetry run python --version

# Executar testes
docker run --rm portfoliozero:latest poetry run pytest

# Jupyter Lab
docker run -p 8888:8888 portfoliozero:latest
```

---

*Este documento deve ser atualizado quando houver mudanças significativas no projeto.*

