# Contrato do Módulo `universe_candidates_pipeline`

Este documento define as funções públicas e convenções de I/O do módulo responsável por construir o arquivo `UNIVERSE_CANDIDATES` a partir das fontes de dados configuradas.

---

## Objetivo

O módulo `universe_candidates_pipeline` é responsável por:

1. Ingerir dados de mercado de fontes configuradas
2. Normalizar e padronizar identificadores
3. Calcular métricas necessárias (volume, volatilidade, etc.)
4. Aplicar filtros mínimos da pré-lista
5. Gerar o arquivo `UNIVERSE_CANDIDATES.parquet`

---

## Localização

```
modules/portfoliozero/core/data/universe_candidates_pipeline.py
```

---

## Funções Públicas Esperadas

### 1. `build_universe_candidates`

Função principal que executa todo o pipeline.

```python
def build_universe_candidates(
    config_paths: dict[str, str] | None = None,
    force_refresh: bool = False,
    output_csv: bool = True,
) -> str:
    """
    Executa o pipeline completo para construir UNIVERSE_CANDIDATES.
    
    Args:
        config_paths: Dicionário com caminhos dos arquivos de configuração.
            Se None, usa os caminhos padrão:
            - selection_rules: config/experiments/universe_selection_rules_v1.yaml
            - data_sources: config/experiments/universe_data_sources_v1.yaml
            - pipeline_topology: config/experiments/universe_pipeline_topology_v1.yaml
        
        force_refresh: Se True, ignora cache e reprocessa todos os dados.
        
        output_csv: Se True, gera também versão CSV além do Parquet.
    
    Returns:
        Caminho do arquivo final gerado (data/universe/UNIVERSE_CANDIDATES.parquet).
    
    Raises:
        PipelineError: Se alguma etapa crítica falhar.
        ValidationError: Se os dados de saída não passarem na validação.
    
    Example:
        >>> path = build_universe_candidates()
        >>> print(f"Arquivo gerado: {path}")
        Arquivo gerado: data/universe/UNIVERSE_CANDIDATES.parquet
    """
    ...
```

### 2. `load_universe_candidates`

Carrega o arquivo UNIVERSE_CANDIDATES em memória.

```python
def load_universe_candidates(
    path: str | None = None,
) -> pl.DataFrame:
    """
    Carrega o arquivo UNIVERSE_CANDIDATES em um DataFrame Polars.
    
    Args:
        path: Caminho do arquivo. Se None, usa o caminho padrão:
            data/universe/UNIVERSE_CANDIDATES.parquet
    
    Returns:
        DataFrame Polars com a pré-lista de candidatos.
    
    Raises:
        FileNotFoundError: Se o arquivo não existir.
        SchemaError: Se o arquivo não seguir o schema esperado.
    
    Example:
        >>> df = load_universe_candidates()
        >>> print(f"Candidatos: {len(df)}")
        Candidatos: 75
    """
    ...
```

### 3. `validate_universe_candidates`

Valida um DataFrame contra o schema esperado.

```python
def validate_universe_candidates(
    df: pl.DataFrame,
) -> ValidationResult:
    """
    Valida um DataFrame contra o schema UNIVERSE_CANDIDATES.
    
    Args:
        df: DataFrame a ser validado.
    
    Returns:
        ValidationResult com status e lista de erros/warnings.
    
    Example:
        >>> result = validate_universe_candidates(df)
        >>> if result.is_valid:
        ...     print("Dados válidos!")
    """
    ...
```

### 4. `get_pipeline_metadata`

Retorna metadados da última execução do pipeline.

```python
def get_pipeline_metadata(
    output_path: str | None = None,
) -> PipelineMetadata:
    """
    Retorna metadados da última execução do pipeline.
    
    Args:
        output_path: Caminho base dos outputs. Se None, usa padrão.
    
    Returns:
        PipelineMetadata com informações sobre a execução:
        - execution_date: Data/hora da execução
        - input_record_count: Número de registros de entrada
        - output_record_count: Número de registros de saída
        - filters_applied: Lista de filtros aplicados
        - warnings: Lista de warnings durante execução
    """
    ...
```

---

## Classes de Suporte

### `PipelineError`

```python
class PipelineError(Exception):
    """Erro durante execução do pipeline."""
    
    def __init__(self, stage: str, message: str):
        self.stage = stage
        self.message = message
        super().__init__(f"[{stage}] {message}")
```

### `ValidationResult`

```python
@dataclass
class ValidationResult:
    """Resultado da validação de dados."""
    
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    record_count: int
```

### `PipelineMetadata`

```python
@dataclass
class PipelineMetadata:
    """Metadados de execução do pipeline."""
    
    execution_date: datetime
    input_record_count: int
    output_record_count: int
    filters_applied: list[str]
    warnings: list[str]
    config_versions: dict[str, str]
```

---

## Convenções de Configuração

### Arquivos de Configuração

| Arquivo | Propósito |
|---------|-----------|
| `universe_selection_rules_v1.yaml` | Thresholds de filtros |
| `universe_data_sources_v1.yaml` | Fontes de dados |
| `universe_pipeline_topology_v1.yaml` | Etapas e caminhos |

### Caminhos Padrão

| Tipo | Caminho |
|------|---------|
| Configs | `config/experiments/` |
| Dados brutos | `data/raw/market/` |
| Dados intermediários | `data/interim/` |
| Saída final | `data/universe/` |
| Logs | `logs/pipeline/` |

### Arquivos de Saída

| Arquivo | Descrição |
|---------|-----------|
| `UNIVERSE_CANDIDATES.parquet` | Pré-lista principal (Parquet) |
| `UNIVERSE_CANDIDATES.csv` | Versão CSV (opcional) |
| `UNIVERSE_CANDIDATES_metadata.json` | Metadados da execução |

---

## Escopo e Limitações

### O que este módulo FAZ

- Ingere dados de fontes configuradas
- Calcula métricas agregadas
- Aplica filtros mínimos de elegibilidade
- Gera pré-lista de 60-80 candidatos

### O que este módulo NÃO FAZ

- Selecionar os 30 supervisionados finais
- Aplicar regras de concentração setorial
- Tomar decisões sobre inclusão/exclusão pelo Owner
- Conectar diretamente com APIs externas (usa adapters)

---

## Dependências Internas

```python
# Imports esperados
from portfoliozero.config import GlobalConfig
from portfoliozero.config.domain import DataConfig
from portfoliozero.utils.logging import setup_logging

import polars as pl
import yaml
from pathlib import Path
from datetime import datetime
```

---

## Testes Esperados

O módulo deve ter cobertura de testes para:

- [ ] `build_universe_candidates` com dados de exemplo
- [ ] `load_universe_candidates` com arquivo existente e inexistente
- [ ] `validate_universe_candidates` com dados válidos e inválidos
- [ ] Cada etapa do pipeline isoladamente
- [ ] Aplicação correta de cada filtro

Localização dos testes:

```
tests/unit/core/data/test_universe_candidates_pipeline.py
tests/integration/core/data/test_universe_pipeline_integration.py
```

---

## Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0 | 26/11/2025 | Versão inicial do contrato |

