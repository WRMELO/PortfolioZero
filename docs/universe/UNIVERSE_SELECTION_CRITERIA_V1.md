# Critérios de Seleção do Universo — Versão 1

Este documento define os critérios detalhados para construção e manutenção do universo de ~30 ativos supervisionados do PortfolioZero.

> **Arquivo de parâmetros:** [`config/experiments/universe_selection_rules_v1.yaml`](../../config/experiments/universe_selection_rules_v1.yaml)  
> **Template de log:** [`UNIVERSE_DECISION_LOG_TEMPLATE.md`](./UNIVERSE_DECISION_LOG_TEMPLATE.md)

---

## 1. Objetivo dos 30 Supervisionados

Definir um conjunto **estável** de aproximadamente 30 ativos (ações e BDRs) que:

- Apresentem **liquidez adequada** para operações do bolso de R$ 500k
- Ofereçam **boa distribuição setorial** para mitigação de risco
- Atendam ao **perfil de risco do Owner** (conservador para drawdown)
- Sejam adequados para a meta de:
  - **Retorno real:** 15–20% a.a. (CAGR acima da inflação)
  - **Drawdown máximo:** 10–15%

### Por que 30 ativos?

| Aspecto | Justificativa |
|---------|---------------|
| Diversificação | 30 ativos permitem diversificação setorial sem diluição excessiva |
| Foco | Permite análise profunda de cada ativo pelo Owner |
| Liquidez | Subconjunto gerenciável dos ativos mais líquidos da B3 |
| Estabilidade | Universo estável facilita backtests e operação |

---

## 2. Critérios Quantitativos Mínimos para a Pré-lista (60–80 ativos)

### 2.1 Instrumentos Permitidos

Apenas os seguintes tipos de instrumentos são elegíveis:

| Tipo | Código | Exemplo |
|------|--------|---------|
| Ação ordinária | `ACAO_ON` | VALE3, ITUB3 |
| Ação preferencial | `ACAO_PN` | PETR4, ITUB4 |
| BDR | `BDR` | AAPL34, MSFT34 |

**Instrumentos proibidos:** FII, ETF, derivativos, operações vendidas, alavancagem.

### 2.2 Filtros Quantitativos

Os valores numéricos estão definidos no arquivo YAML de configuração.

| Parâmetro | Descrição | Valor Default |
|-----------|-----------|---------------|
| `min_avg_volume_21d_brl` | Volume financeiro médio diário mínimo (21 pregões) | R$ 5.000.000 |
| `min_price_brl` | Preço médio mínimo (21 pregões) | R$ 5,00 |
| `min_history_days` | Número mínimo de pregões com histórico | 252 dias |
| `min_trading_days_ratio_252d` | Proporção mínima de dias negociados no ano | 90% |

### 2.3 Exclusões Automáticas

- Ativos com `flag_excluir_owner = true` são excluídos mesmo que passem nos filtros numéricos
- Ativos em recuperação judicial ou com eventos de risco extremo

### 2.4 Resultado da Pré-lista

A pré-lista deve conter entre **60 e 80 ativos** que passaram nos filtros mínimos. Se a lista for menor, revisar os parâmetros de filtro.

---

## 3. Critérios Setoriais e de Concentração

### 3.1 Objetivo

Evitar concentração excessiva em poucos setores, garantindo diversificação mínima.

### 3.2 Parâmetros de Concentração

| Parâmetro | Descrição | Valor Default |
|-----------|-----------|---------------|
| `min_distinct_sectors` | Número mínimo de setores distintos representados | 6 |
| `max_weight_per_sector_pct` | Fração máxima dos 30 que pode pertencer a um setor | 35% |
| `max_names_per_sector` | Teto de ativos por setor | 6 |

### 3.3 Setores Considerados

Os setores seguem a classificação padrão da B3/Bloomberg:

- Financeiro (bancos, seguradoras, meios de pagamento)
- Commodities (mineração, siderurgia, papel e celulose)
- Energia (petróleo, gás, elétrico)
- Consumo (varejo, alimentos, bebidas)
- Saúde (farmacêuticas, hospitais, planos)
- Tecnologia (software, hardware, BDRs de tech)
- Utilidades (saneamento, concessões)
- Indústria (construção, transporte, máquinas)
- Outros

### 3.4 Balanceamento

A seleção final deve equilibrar:

1. **Representatividade setorial** — todos os setores relevantes devem estar presentes
2. **Risco de concentração** — nenhum setor domina o universo
3. **Oportunidades de alpha** — setores com maior potencial de retorno

---

## 4. Volatilidade e Classificação Interna

### 4.1 Cálculo de Volatilidade

Cada ativo da pré-lista deve ter **volatilidade histórica anualizada** calculada:

```
volatilidade_anualizada = desvio_padrão(retornos_diários, janela=60) × √252
```

### 4.2 Classificação em Faixas

| Classe | Volatilidade Anualizada | Descrição |
|--------|------------------------|-----------|
| `BAIXA` | ≤ 20% | Ativos mais estáveis, menor risco |
| `MEDIA` | > 20% e ≤ 40% | Risco moderado, balanço retorno/risco |
| `ALTA` | > 40% | Ativos mais voláteis, maior risco |

### 4.3 Proporções Alvo

Para evitar universo desequilibrado:

| Restrição | Valor Default |
|-----------|---------------|
| Mínimo de ativos `MEDIA` | 30% do universo |
| Máximo de ativos `ALTA` | 50% do universo |

### 4.4 Racional

- Universo 100% `BAIXA`: provavelmente não atinge 15-20% de retorno
- Universo 100% `ALTA`: provavelmente excede 15% de drawdown
- Mix balanceado: melhor chance de atingir metas de risco-retorno

---

## 5. Overrides do Owner (Inclusão e Exclusão Explícitas)

### 5.1 Tipos de Override

O Owner pode forçar:

| Tipo | Flag | Descrição |
|------|------|-----------|
| Exclusão | `flag_excluir_owner = true` | Ativo excluído independente de métricas |
| Inclusão | `flag_incluir_owner = true` | Ativo incluído se não violar regras críticas |

### 5.2 Regras de Override

#### Exclusão

- **Prevalece** sobre critérios numéricos
- Motivo deve ser registrado em log (campo `motivo_exclusao`)
- Exemplos: experiência negativa, convicção pessoal, risco reputacional

#### Inclusão Forçada

- Ativo **deve** ainda atender à liquidez mínima (`respect_min_liquidity_for_forced_inclusion = true`)
- Inclusão é registrada em log
- Se a inclusão quebrar regras de concentração/volatilidade:
  - Sistema emite alerta
  - Owner deve aceitar conscientemente
  - Decisão é documentada

### 5.3 Registro de Overrides

Todos os overrides são registrados com:
- Data
- Ticker
- Tipo (inclusão/exclusão)
- Motivo
- Impacto nas métricas do universo

---

## 6. Processo de Redução da Pré-lista para ~30 Supervisionados

### 6.1 Fluxo de Seleção

```
┌─────────────────────────────────────────────────────────────────┐
│  ETAPA 1: Filtros Quantitativos                                 │
│  • Aplicar min_avg_volume, min_price, min_history               │
│  • Resultado: pré-lista de 60–80 candidatos                     │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  ETAPA 2: Cálculo de Rótulos                                    │
│  • Setor                                                        │
│  • Volatilidade (BAIXA/MEDIA/ALTA)                              │
│  • Liquidez relativa (ranking)                                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  ETAPA 3: Overrides do Owner                                    │
│  • Aplicar exclusões forçadas                                   │
│  • Aplicar inclusões forçadas (com validação)                   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  ETAPA 4: Balanceamento e Redução                               │
│  • Aplicar limites de concentração setorial                     │
│  • Aplicar limites de proporção de volatilidade                 │
│  • Priorizar por liquidez dentro de cada grupo                  │
│  • Reduzir ao alvo de 28–32 ativos (target: 30)                 │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  ETAPA 5: Validação e Log                                       │
│  • Verificar se metas foram atingidas                           │
│  • Registrar divergências com justificativa                     │
│  • Gerar universo final supervisionado                          │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Critérios de Priorização

Dentro de cada grupo (setor/volatilidade), a priorização é por:

1. **Liquidez** (maior volume → maior prioridade)
2. **Participação em índices** (IBOV > IBrX-50 > outros)
3. **Qualidade percebida** (governança, histórico)

### 6.3 Tratamento de Divergências

Se o processo não conseguir atingir alguma meta:

| Situação | Ação |
|----------|------|
| < 28 ativos após filtros | Relaxar filtros de liquidez ou volatilidade |
| > 32 ativos após redução | Aplicar corte adicional por liquidez |
| < 6 setores | Aceitar ou buscar ativos de setores sub-representados |
| Concentração > 35% em setor | Cortar ativos do setor em excesso |

Todas as divergências devem ser **registradas em log** com justificativa.

---

## 7. Política de Revisão do Universo

### 7.1 Princípio de Estabilidade

O universo de 30 supervisionados deve ser **relativamente estável** para:
- Manter consistência de backtests
- Evitar custos de transação desnecessários
- Permitir acompanhamento profundo pelo Owner

### 7.2 Tipos de Revisão

| Tipo | Frequência | Gatilho |
|------|------------|---------|
| **Ordinária** | A cada 12 meses | Calendário fixo (ex: janeiro) |
| **Extraordinária** | Ad hoc | Evento relevante |

### 7.3 Eventos que Justificam Revisão Extraordinária

- Fusão ou aquisição de empresa do universo
- Recuperação judicial ou evento de crédito grave
- Deslistagem ou mudança de tipo de ativo
- Perda significativa de liquidez
- Solicitação explícita do Owner

### 7.4 Registro de Revisões

Cada revisão (ordinária ou extraordinária) deve ser documentada usando o template:

[`UNIVERSE_DECISION_LOG_TEMPLATE.md`](./UNIVERSE_DECISION_LOG_TEMPLATE.md)

O registro inclui:
- Data e versão
- Entradas e saídas
- Justificativas
- Impacto nas métricas do universo

---

## 8. Referência de Parâmetros

Todos os parâmetros numéricos e flags estão centralizados em:

```
config/experiments/universe_selection_rules_v1.yaml
```

Para alterar qualquer valor, edite o arquivo YAML. O documento markdown serve como **referência conceitual**; os **valores operacionais** estão no YAML.

---

## Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0 | 26/11/2025 | Versão inicial dos critérios |
| 1.1 | 26/11/2025 | Detalhamento completo (TASK_006) |
