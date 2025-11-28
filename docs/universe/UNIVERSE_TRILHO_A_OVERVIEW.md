# Trilho A — Universo de 30 Ativos Supervisionados

Este documento descreve o objetivo e o escopo do **Trilho A** no projeto PortfolioZero.

---

## Objetivo

O Trilho A tem como objetivo definir e manter um universo de aproximadamente **30 ativos supervisionados** (ações e BDRs) que serão o "radar" permanente do sistema PortfolioZero.

Esses ativos formam a **Camada de Supervisão** descrita no [Plano V1](../PORTFOLIOZERO_PLAN_V1.md) e alimentam a **Camada de Ação**, que mantém cerca de 10 ativos ativos com capital efetivamente alocado.

```
┌─────────────────────────────────────────────────────────────┐
│           CAMADA DE SUPERVISÃO (Trilho A)                   │
│                   ~30 ativos supervisionados                │
│                                                             │
│   O sistema monitora diariamente, mesmo sem capital        │
│   alocado. São o "radar" permanente do PortfolioZero.      │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              CAMADA DE AÇÃO                                 │
│                   ~10 ativos ativos                         │
│                                                             │
│   Capital efetivamente alocado. Selecionados do radar      │
│   com base em sinais do agente + critérios de risco.       │
└─────────────────────────────────────────────────────────────┘
```

---

## Restrições de Instrumentos (conforme Plano V1)

### ✅ Permitidos

| Tipo | Descrição |
|------|-----------|
| Ações brasileiras ON/PN | Listadas na B3, com liquidez e governança adequadas |
| BDRs elegíveis | Mesmos critérios de liquidez e qualidade |

### ❌ Proibidos na V1

| Tipo | Motivo |
|------|--------|
| FIIs | Dinâmica diferente, não alinhado com o modelo |
| ETFs | O objetivo é stock picking, não replicação de índice |
| Derivativos | Opções, futuros, swaps — complexidade e risco não desejados |
| Short selling | Operação será exclusivamente long-only |
| Alavancagem | Exposição máxima = 100% do capital |

---

## Conexão com Risco e Retorno

O universo de 30 supervisionados deve suportar:

| Meta | Valor |
|------|-------|
| Retorno real (CAGR) | 15–20% ao ano |
| Drawdown máximo | 10–15% |

Para atingir essas metas, o universo precisa ter:

1. **Liquidez suficiente** para entrar e sair sem grande impacto no preço
2. **Diversidade setorial mínima** para evitar concentração de risco
3. **Qualidade mínima dos emissores** (governança, histórico, solidez)

---

## Estrutura do Trilho A

### Documentos Relacionados

| Arquivo | Descrição |
|---------|-----------|
| `UNIVERSE_TRILHO_A_OVERVIEW.md` | Este documento (visão geral) |
| `UNIVERSE_SELECTION_CRITERIA_V1.md` | Critérios de seleção detalhados |
| `../../data/universe/UNIVERSE_CANDIDATES.schema.md` | Schema para arquivos de candidatos |

### Fluxo de Trabalho

```
1. PRÉ-LISTA (60–80 ativos)
   │
   │  Fontes: IBOV, IBrX-50, IBrX-100
   │  Filtros: liquidez, preço, governança
   │
   ▼
2. REDUÇÃO (→ 30 supervisionados)
   │
   │  Critérios: diversificação, qualidade, preferências Owner
   │
   ▼
3. CLASSIFICAÇÃO
   │
   │  Rótulos: setor, liquidez, volatilidade, core/oportunidade
   │
   ▼
4. REVISÃO PERIÓDICA
   │
   │  Frequência: 6–12 meses
   │  Registro de mudanças com datas
```

---

## Próximos Passos no Trilho A

- [ ] Definir critérios objetivos de filtro inicial (pré-lista de 60–80 ativos)
- [ ] Definir critérios de redução e classificação para chegar nos ~30 supervisionados
- [ ] Construir a primeira versão da pré-lista de candidatos
- [ ] Aplicar filtros e gerar a lista final de 30 supervisionados
- [ ] Registrar versões sucessivas do universo e suas datas de vigência

---

## Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0 | 26/11/2025 | Versão inicial do documento |

