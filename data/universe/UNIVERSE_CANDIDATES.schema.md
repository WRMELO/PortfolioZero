# Schema para Arquivo de Candidatos ao Universo Supervisionado

Este documento descreve o schema esperado para arquivos tabulares (CSV/Parquet) que contêm a pré-lista de ativos candidatos ao universo de 30 supervisionados.

---

## Formato do Arquivo

| Aspecto | Especificação |
|---------|---------------|
| Formatos aceitos | CSV, Parquet |
| Encoding (CSV) | UTF-8 |
| Separador (CSV) | `,` (vírgula) |
| Primeira linha | Header com nomes das colunas |

---

## Colunas do Schema

### Colunas Obrigatórias

| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `ticker` | string | Ticker do ativo na B3 | `PETR4`, `VALE3`, `AAPL34` |
| `tipo_instrumento` | string | Tipo do instrumento | `ACAO_ON`, `ACAO_PN`, `BDR` |

### Colunas Recomendadas

| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `setor` | string | Setor econômico | `Financeiro`, `Commodities` |
| `subsetor` | string | Detalhamento do setor | `Bancos`, `Mineração` |
| `volume_medio_21d` | float | Volume financeiro médio diário (21 pregões) em R$ | `150000000.0` |
| `preco_medio_21d` | float | Preço médio em 21 pregões em R$ | `35.50` |
| `volatilidade_21d` | float | Volatilidade histórica (21 pregões) | `0.025` |

### Colunas de Classificação

| Coluna | Tipo | Descrição | Valores Possíveis |
|--------|------|-----------|-------------------|
| `flag_ibov` | bool | Participa do IBOV | `true`, `false` |
| `flag_ibrx50` | bool | Participa do IBrX-50 | `true`, `false` |
| `flag_ibrx100` | bool | Participa do IBrX-100 | `true`, `false` |
| `liquidez_classe` | string | Classe de liquidez | `ALTA`, `MEDIA`, `BAIXA` |
| `volatilidade_classe` | string | Classe de volatilidade | `ALTA`, `MEDIA`, `BAIXA` |
| `categoria` | string | Categoria estratégica | `CORE`, `OPORTUNIDADE` |

### Colunas de Controle

| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `flag_excluir_owner` | bool | Owner excluiu explicitamente | `true`, `false` |
| `motivo_exclusao` | string | Razão da exclusão pelo Owner | `Experiência negativa` |
| `flag_supervisionado` | bool | Faz parte dos 30 finais | `true`, `false` |
| `data_inclusao` | date | Data de inclusão no universo | `2025-11-26` |

---

## Exemplo de Arquivo

### CSV

```csv
ticker,tipo_instrumento,setor,volume_medio_21d,preco_medio_21d,volatilidade_21d,flag_ibov,flag_supervisionado
PETR4,ACAO_PN,Energia,450000000.0,38.50,0.028,true,true
VALE3,ACAO_ON,Commodities,620000000.0,68.20,0.032,true,true
ITUB4,ACAO_PN,Financeiro,380000000.0,32.10,0.018,true,true
AAPL34,BDR,Tecnologia,85000000.0,52.30,0.022,false,true
OIBR3,ACAO_ON,Telecom,12000000.0,1.25,0.085,false,false
```

### Parquet

Para arquivos Parquet, o schema deve ser equivalente, com tipos de dados:
- `string` → `utf8`
- `float` → `float64`
- `bool` → `bool`
- `date` → `date32`

---

## Validações Sugeridas

O módulo de seleção de universo deve validar:

1. **Obrigatórios presentes:** `ticker` e `tipo_instrumento` devem existir
2. **Tipos válidos:** `tipo_instrumento` ∈ {`ACAO_ON`, `ACAO_PN`, `BDR`}
3. **Sem duplicatas:** `ticker` deve ser único
4. **Valores numéricos:** `volume_medio_21d`, `preco_medio_21d`, `volatilidade_21d` ≥ 0

---

## Versionamento do Universo

Cada versão do universo deve ser salva com nome que indique a data:

```
universe_candidates_2025_11_26.csv
universe_supervised_v1_2025_11_26.csv
```

Isso permite rastrear a evolução do universo ao longo do tempo.

---

## Arquivos Relacionados

| Arquivo | Descrição |
|---------|-----------|
| `universe_candidates_YYYY_MM_DD.csv` | Pré-lista de 60–80 candidatos |
| `universe_supervised_vX_YYYY_MM_DD.csv` | Lista final de ~30 supervisionados |
| `universe_changelog.md` | Registro de alterações no universo |

---

## Histórico de Versões do Schema

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0 | 26/11/2025 | Versão inicial do schema |

