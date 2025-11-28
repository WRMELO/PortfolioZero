# Critérios de Seleção do Universo — Versão 1

Esta versão define os critérios iniciais para construção do universo de ~30 ativos supervisionados.

---

## Visão Geral do Processo

```
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 1: Construir pré-lista de candidatos (60–80 ativos) │
│                                                             │
│  • Fonte: índices da B3 (IBOV, IBrX-50, IBrX-100)          │
│  • Filtros quantitativos básicos                            │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 2: Reduzir para ~30 supervisionados                  │
│                                                             │
│  • Critérios qualitativos e quantitativos                   │
│  • Preferências do Owner                                    │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 3: Classificar os 30 selecionados                    │
│                                                             │
│  • Rótulos: setor, liquidez, volatilidade, categoria        │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Pré-lista de Candidatos (60–80 ativos)

### 1.1 Fontes de Dados

| Fonte | Descrição | Prioridade |
|-------|-----------|------------|
| IBOV | Índice Bovespa — ~80 ativos mais negociados | Alta |
| IBrX-50 | 50 ativos mais líquidos | Alta |
| IBrX-100 | 100 ativos mais líquidos | Média |
| Sugestões de corretores | Para comparação futura | Baixa |

A pré-lista será construída a partir da **união** desses índices, sem duplicatas.

### 1.2 Filtros Mínimos (Quantitativos)

| Critério | Parâmetro | Racional |
|----------|-----------|----------|
| **Liquidez mínima** | Volume médio diário > R$ X milhões (a definir) | Garantir entrada/saída sem impacto |
| **Preço mínimo** | Preço > R$ Y (a definir, ex: R$ 5) | Evitar penny stocks extremos |
| **Exclusão por risco extremo** | Ativos em recuperação judicial | Risco binário inaceitável |
| **Tipo de ativo** | Apenas ações ON/PN e BDRs | Conforme restrições do Plano V1 |

> **Nota:** Os valores numéricos exatos (R$ X, R$ Y) serão definidos na etapa técnica de implementação, com base em análise dos dados disponíveis.

### 1.3 Resultado da Etapa 1

Uma lista de 60–80 ativos candidatos, cada um com:
- Ticker
- Tipo (ACAO_ON, ACAO_PN, BDR)
- Volume médio
- Preço médio
- Participação em índices

---

## 2. Redução para ~30 Supervisionados

### 2.1 Critérios de Redução

A redução de 60–80 para ~30 combina critérios **quantitativos** e **qualitativos**:

#### Critérios Quantitativos

| Critério | Objetivo |
|----------|----------|
| Diversificação setorial | Máximo de X ativos por setor (ex: 5–6) |
| Liquidez relativa | Priorizar os mais líquidos dentro de cada setor |
| Volatilidade | Balancear entre ativos de alta e baixa volatilidade |

#### Critérios Qualitativos

| Critério | Descrição |
|----------|-----------|
| Governança | Preferência por Novo Mercado, histórico limpo |
| Qualidade do emissor | Histórico de resultados, solidez financeira |
| Preferências do Owner | Exclusão de nomes específicos por convicção/experiência |

### 2.2 Processo de Decisão

1. **Ordenar** candidatos por liquidez (decrescente)
2. **Agrupar** por setor
3. **Selecionar** os N mais líquidos de cada setor (respeitando teto por setor)
4. **Aplicar** exclusões do Owner
5. **Ajustar** para atingir ~30 ativos totais

### 2.3 Resultado da Etapa 2

Lista final de ~30 ativos supervisionados.

---

## 3. Classificação dos 30 Supervisionados

Cada ativo selecionado recebe rótulos auxiliares para uso pelo sistema:

### 3.1 Rótulos Obrigatórios

| Rótulo | Tipo | Valores Possíveis |
|--------|------|-------------------|
| `setor` | string | Financeiro, Commodities, Consumo, Energia, etc. |
| `liquidez_classe` | enum | ALTA, MEDIA, BAIXA |
| `volatilidade_classe` | enum | ALTA, MEDIA, BAIXA |
| `categoria` | enum | CORE, OPORTUNIDADE |

### 3.2 Definição das Classes

#### Liquidez

| Classe | Critério (sugestão) |
|--------|---------------------|
| ALTA | Top 33% por volume médio |
| MEDIA | 33%–66% |
| BAIXA | Bottom 33% |

#### Volatilidade

| Classe | Critério (sugestão) |
|--------|---------------------|
| ALTA | Volatilidade 21d > X% |
| MEDIA | Entre Y% e X% |
| BAIXA | < Y% |

#### Categoria Estratégica

| Categoria | Descrição |
|-----------|-----------|
| CORE | Posições de longo prazo, empresas sólidas, menor giro |
| OPORTUNIDADE | Posições táticas, maior volatilidade, potencial de alpha |

---

## 4. Revisão Periódica

### 4.1 Frequência

O universo de 30 supervisionados **não deve mudar com muita frequência**, para manter:
- Estabilidade de backtests
- Consistência operacional
- Redução de custos de transação

| Tipo de Revisão | Frequência | Gatilho |
|-----------------|------------|---------|
| Ordinária | A cada 6–12 meses | Calendário fixo |
| Extraordinária | Ad hoc | Evento relevante (fusão, recuperação judicial, etc.) |

### 4.2 Registro de Alterações

Toda alteração no universo deve ser registrada com:
- Data de vigência
- Ativos incluídos
- Ativos excluídos
- Motivação

Exemplo de registro:

```
| Data       | Incluídos   | Excluídos   | Motivação                        |
|------------|-------------|-------------|----------------------------------|
| 01/06/2026 | BBAS3, SUZB3| OIBR3, COGN3| Revisão semestral; OIBR3 ilíquido|
```

---

## 5. Parâmetros a Definir (Etapa Técnica)

Os seguintes parâmetros numéricos serão definidos quando houver acesso aos dados:

| Parâmetro | Descrição | Valor (a definir) |
|-----------|-----------|-------------------|
| `MIN_VOLUME_DIARIO` | Volume mínimo em R$ | ? |
| `MIN_PRECO` | Preço mínimo por ação | ? |
| `MAX_ATIVOS_POR_SETOR` | Limite de concentração setorial | ? |
| `THRESHOLD_VOL_ALTA` | Volatilidade para classe ALTA | ? |
| `THRESHOLD_VOL_BAIXA` | Volatilidade para classe BAIXA | ? |

---

## Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0 | 26/11/2025 | Versão inicial dos critérios |

