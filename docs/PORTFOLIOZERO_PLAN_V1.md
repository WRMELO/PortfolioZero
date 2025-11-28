# PortfolioZero — Plano V1
## Negócio, Risco e Roadmap

> **Versão:** 1.0  
> **Data:** 26 de Novembro de 2025  
> **Status:** Congelado para referência

---

## Sumário

1. [Contexto e objetivos do projeto](#1-contexto-e-objetivos-do-projeto)
2. [Capital, meta de retorno e horizonte de tempo](#2-capital-meta-de-retorno-e-horizonte-de-tempo)
3. [Perfil de risco e limites de drawdown](#3-perfil-de-risco-e-limites-de-drawdown)
4. [Universo de ativos e restrições de instrumentos](#4-universo-de-ativos-e-restrições-de-instrumentos)
5. [Arquitetura de decisão do PortfolioZero](#5-arquitetura-de-decisão-do-portfoliozero)
6. [Regras operacionais (frequência, quarentena, custos)](#6-regras-operacionais-frequência-quarentena-custos)
7. [Roadmap em fases (Fase 0 até Dry Run)](#7-roadmap-em-fases-fase-0-até-dry-run)
8. [Critérios de avaliação e papel do Owner](#8-critérios-de-avaliação-e-papel-do-owner)
9. [Anexos conceituais](#9-anexos-conceituais)

---

## 1. Contexto e objetivos do projeto

O **PortfolioZero** é um projeto pessoal do Owner, aposentado com 69 anos e cerca de 49 anos de experiência profissional.

O objetivo central é combinar conhecimento de **Stock Picking** e **Data Science/IA** para criar um sistema de decisão de portfólio que funcione como:

- **Fonte de renda** complementar na aposentadoria;
- **Atividade intelectual** estimulante, mantendo o Owner engajado em um projeto de alta complexidade técnica.

O projeto não é uma startup nem um produto comercial. É uma ferramenta pessoal, construída para atender às necessidades específicas do Owner, com total controle sobre as decisões e os riscos assumidos.

### Por que "PortfolioZero"?

O nome faz referência ao **MuZero**, algoritmo de aprendizado por reforço desenvolvido pela DeepMind, que aprende a jogar jogos complexos (Go, xadrez, Atari) sem conhecer as regras previamente — apenas por simulação e planejamento. O PortfolioZero aplica essa filosofia ao problema de alocação de portfólio: aprender, por interação com dados históricos de mercado, quais decisões de compra e venda maximizam o retorno ajustado ao risco.

---

## 2. Capital, meta de retorno e horizonte de tempo

### Capital inicial

- **Bolso financeiro separado:** R$ 500.000 (quinhentos mil reais)
- Este valor representa aproximadamente 17% do patrimônio líquido total do Owner (R$ 3.000.000)
- O bolso é tratado como um **circuito fechado**: durante a fase de construção do modelo, não entram novos recursos nem há retiradas sistemáticas para consumo

### Circuito fechado

O conceito de "circuito fechado" significa que:

- Ganhos são reinvestidos dentro do próprio bolso
- Perdas são absorvidas pelo próprio bolso
- O Owner não fará aportes adicionais nem saques durante o período de construção
- **Duração mínima:** 3 anos

Esse isolamento permite avaliar o desempenho real do sistema sem interferência de fluxos externos.

### Meta de retorno

A meta de desempenho é definida em termos de **retorno composto real** (acima da inflação):

| Cenário | CAGR Real (acima da inflação) | Comentário |
|---------|-------------------------------|------------|
| **Base** | 15% a 20% ao ano | Objetivo principal |
| Conservador | 10% a 15% ao ano | Aceitável se com baixo drawdown |
| Agressivo | > 20% ao ano | Desejável, mas não à custa de risco excessivo |

> **Nota importante:** A ideia de "renda mensal de R$ 15.000" é tratada como uma **consequência potencial** de um capital e retorno bem-sucedidos, não como parâmetro rígido do modelo V1. Se o bolso de R$ 500k crescer para R$ 1.000k com retornos sustentáveis de 15% a.a., a renda mensal poderá ser viabilizada. Mas o foco do modelo é **maximizar retorno ajustado ao risco**, não atingir uma cifra específica de renda.

---

## 3. Perfil de risco e limites de drawdown

### Filosofia de risco

O Owner não deseja conviver com **quedas profundas e prolongadas** no bolso de R$ 500k. O objetivo é construir um sistema que entregue retornos consistentes com volatilidade controlada, não um sistema que maximize retorno a qualquer custo.

### Limites de drawdown

| Faixa de Drawdown | Classificação | Comportamento do Sistema |
|-------------------|---------------|--------------------------|
| 0% a 10% | Zona de conforto | Operação normal |
| 10% a 15% | Zona de atenção | Alerta ativo, preparação para redução |
| > 15% | Zona de risco | **Modo defensivo ativado** |

#### Modo defensivo (drawdown > 15%)

Quando o drawdown do bolso ultrapassar 15%:

1. O sistema aumenta automaticamente a **posição em caixa**
2. Reduz a **exposição total ao mercado**
3. Prioriza ativos de menor volatilidade dentro do universo supervisionado
4. Mantém modo defensivo até que o equity se recupere para uma faixa segura

### Monitoramento de drawdown

O drawdown será monitorado em duas dimensões:

- **Drawdown máximo global:** do maior pico histórico ao pior fundo
- **Drawdown em janelas de tempo:** 30 e 60 dias, para evitar quedas prolongadas não endereçadas

### Alinhamento com o perfil do Owner

Se os backtests mostrarem que o modelo só funciona com drawdowns da ordem de **25% a 30%** por longos períodos, isso será tratado como **desalinhamento com o perfil do Owner** e motivo para:

- Revisão dos hiperparâmetros do modelo
- Revisão da estratégia de alocação
- Ou, em último caso, descontinuação do projeto

---

## 4. Universo de ativos e restrições de instrumentos

### Instrumentos PERMITIDOS na V1

| Tipo | Descrição | Critérios |
|------|-----------|-----------|
| **Ações brasileiras** | ON e PN listadas na B3 | Liquidez mínima, governança adequada |
| **BDRs** | Brazilian Depositary Receipts | Mesmos critérios de liquidez e qualidade |

### Instrumentos PROIBIDOS na V1

| Tipo | Motivo da Exclusão |
|------|-------------------|
| **FIIs** | Fundos imobiliários — dinâmica diferente, não alinhado com o modelo |
| **ETFs** | Fundos de índice — o objetivo é stock picking, não replicação de índice |
| **Derivativos** | Opções, futuros, swaps, termo — complexidade e risco não desejados na V1 |
| **Short selling** | Venda a descoberto — proibido; operação será exclusivamente **long-only** |
| **Alavancagem** | Exposição máxima limitada a 100% do capital do bolso |

### Resumo da postura

O PortfolioZero V1 opera de forma **conservadora em termos de instrumentos**:

- Compra apenas ações e BDRs
- Nunca fica vendido
- Nunca usa alavancagem
- O máximo que pode perder é o capital do bolso (R$ 500k), nunca mais

---

## 5. Arquitetura de decisão do PortfolioZero

A arquitetura de decisão do PortfolioZero é organizada em **duas camadas principais**, alimentadas por um motor de decisão baseado em inteligência artificial.

### 5.1 Camada de Supervisão (Universo)

**Aproximadamente 30 tickers** (ações e BDRs) selecionados a partir de critérios de:

- Liquidez mínima (volume médio diário)
- Governança e qualidade do emissor
- Diversificação setorial mínima
- Exclusão de ativos que o Owner não deseja por experiência ou convicção pessoal

Esses 30 ativos formam o **universo supervisionado**, ou "radar" permanente do sistema. O sistema monitora diariamente esses ativos, mesmo que não estejam na carteira ativa.

### 5.2 Camada de Ação (Carteira Ativa)

**Aproximadamente 10 ativos** em posição ao mesmo tempo (intervalo típico: 8 a 12).

| Parâmetro | Valor |
|-----------|-------|
| Número alvo de ativos | 10 |
| Tamanho médio de posição | ~10% do portfólio |
| Tamanho mínimo de posição | 5% do portfólio |
| Tamanho máximo de posição | 15% do portfólio |

A carteira ativa é escolhida com base em critérios técnicos (sinais de tendência, risco de curto prazo, visão do agente) aplicados sobre o universo de 30 supervisionados.

### 5.3 Motor de decisão (MuZero + Black-Litterman)

```
┌─────────────────────────────────────────────────────────────────┐
│                    DADOS DE MERCADO                             │
│         (preços, volumes, retornos, volatilidade)               │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                 MODELO DE RISCO DE CURTO PRAZO                  │
│     (probabilidade de queda em D+1, D+3, D+5)                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AGENTE MUZERO                              │
│  - Aprende por simulação quais ações tomar                      │
│  - Incorpora sinais de risco como parte do estado               │
│  - Gera "views" sobre preferências entre ativos                 │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BLACK-LITTERMAN                              │
│  - Transforma views do agente em pesos de carteira              │
│  - Combina com portfólio de equilíbrio                          │
│  - Aplica parâmetros de aversão ao risco                        │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CARTEIRA FINAL                                │
│  - 10 ativos com pesos definidos                                │
│  - Long-only, sem alavancagem                                   │
│  - Respeita limites por ativo (5%–15%)                          │
└─────────────────────────────────────────────────────────────────┘
```

#### Agente MuZero

O agente de Reinforcement Learning baseado em MuZero é responsável por:

- **Aprender**, por interação com um ambiente simulado de mercado, quais ações (comprar, manter, vender, reduzir) melhor se encaixam nos objetivos de retorno e risco
- **Incorporar** informações de risco de curto prazo (probabilidade de queda/drawdown em horizontes D+1, D+3, D+5) como sinais de alerta
- **Planejar** usando Monte Carlo Tree Search (MCTS) para simular consequências de diferentes decisões

#### Black-Litterman

O modelo Black-Litterman é usado como camada de alocação para:

- **Transformar** as "views" do agente (preferências relativas entre ativos) em pesos de carteira
- **Combinar** essas views com um portfólio de equilíbrio (inspirado em índices de mercado)
- **Aplicar** parâmetros de aversão ao risco calibrados para o perfil do Owner

---

## 6. Regras operacionais (frequência, quarentena, custos)

### 6.1 Frequência de operação

#### Venda (gestão de risco) — DIÁRIA

- Avaliação **diária** dos ativos em carteira
- Se um ativo entrar em zona de risco relevante de queda (com base no modelo de curto prazo e regras definidas), o sistema pode decidir **reduzir ou zerar** a posição naquele dia
- Isso justifica o uso de sinais de horizonte curto (D+1, D+3, D+5)

**Racional:** Proteger o capital é prioridade. Se um ativo sinaliza alta probabilidade de queda, não faz sentido esperar até o próximo ciclo semanal para agir.

#### Compra (realocação de capital) — SEMANAL

- Processos de compra e realocação ocorrem em **batidas semanais**, em um dia fixo da semana (sugestão: quarta-feira)
- Nesse dia, o sistema:
  1. Revisa o universo de 30 supervisionados
  2. Aplica os critérios técnicos (incluindo quarentena)
  3. Decide quais novos ativos entram na carteira ativa
  4. Define os pesos de alocação

**Racional:** Compras não precisam ser tão urgentes quanto vendas de proteção. Um ritmo semanal reduz custos de transação e evita overtrading.

### 6.2 Quarentena pós-venda

Ativos vendidos por motivo de risco (queda prevista ou drawdown) entram em **período de quarentena**:

| Parâmetro | Valor sugerido |
|-----------|----------------|
| Duração mínima | 20 pregões (~1 mês) |
| Configurável | Sim, via arquivo de configuração |

Durante a quarentena:

- O sistema **não pode recomprar** esse ativo, mesmo que os sinais pareçam atrativos
- Isso evita comportamento de "entra-e-sai caótico"
- Força a realocação para outras oportunidades do universo

### 6.3 Custos e impostos

O modelo de simulação e backtest incorporará:

| Componente | Tratamento |
|------------|------------|
| **Custo fixo por ordem** | Valor fixo por operação (corretagem) |
| **Custo percentual** | Emolumentos e taxas sobre volume negociado |
| **Imposto de renda** | Modelo aproximado (15% sobre lucro líquido acima de R$ 20k/mês em vendas) |

#### Penalização por giro excessivo

O agente será penalizado por **giro excessivo** (turnover):

- Será definido um limite de turnover anual aceitável
- Políticas que entreguem bom retorno bruto, mas com giro e custo excessivos, serão:
  - Penalizadas na função de recompensa
  - Descartadas na seleção final de modelos

**Racional:** Um modelo que gera 25% de retorno bruto mas paga 10% em custos e impostos é pior do que um modelo que gera 18% com custos de 3%.

---

## 7. Roadmap em fases (Fase 0 até Dry Run)

### Visão geral

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  Fase 0  │ → │  Fase 1  │ → │  Fase 2  │ → │  Fase 3  │ → │  Fase 4  │ → │  Fase 5  │
│  Regras  │   │  Dados   │   │  MuZero  │   │   B-L    │   │ Backtest │   │ Dry Run  │
└──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
      │
      └──────────────────────────────────────────────────────────────────┐
                                                                         │
                            ┌─────────────────────────────────┐          │
                            │  Trilho A: Seleção dos 30       │ ←────────┘
                            │  (paralelo às fases técnicas)   │
                            └─────────────────────────────────┘
```

---

### Fase 0 — Regras do jogo e universo de ativos

**Objetivo:** Estabelecer todas as regras de negócio antes de escrever código de modelo.

**Entregas:**

- [x] Limites de posição por ativo (5% mín, 15% máx)
- [x] Número alvo de ativos ativos (~10)
- [x] Regras de quarentena (20 pregões)
- [x] Objetivo de drawdown (10–15%)
- [x] Comportamento em modo de risco reduzido
- [ ] Lista inicial dos 30 supervisionados (em construção)

---

### Trilho Paralelo A — Seleção e manutenção dos 30 supervisionados

**Objetivo:** Construir e manter o universo de ativos supervisionados.

**Etapas:**

1. **Construir pré-lista** a partir de:
   - Índices de referência (IBOV, IBrX-100)
   - Ações com histórico conhecido pelo Owner
   - Sugestões de corretores (para comparação futura)

2. **Aplicar filtros:**
   - Volume médio diário mínimo
   - Preço mínimo por ação (evitar penny stocks)
   - Governança (Novo Mercado preferencial)
   - Diversificação setorial

3. **Reduzir para 30 tickers**, cada um classificado por:
   - Setor
   - Liquidez (alta/média)
   - Volatilidade (alta/média/baixa)
   - Tipo: **Core** (posições estáveis) vs. **Oportunidade** (posições táticas)

4. **Definir periodicidade de revisão:**
   - Sugestão: a cada 6 ou 12 meses
   - Sob controle exclusivo do Owner

---

### Fase 1 — Dados, features e modelo de risco de curto prazo

**Objetivo:** Construir a base de dados e o primeiro modelo preditivo.

**Entregas:**

- Pipeline de dados históricos:
  - Preços ajustados (dividendos, splits)
  - Volumes
  - Índices de referência (IBOV, CDI)
  
- Features calculadas:
  - Retornos (diário, semanal, mensal)
  - Volatilidade (rolling windows)
  - Tendência (médias móveis, momentum)
  - Liquidez relativa

- Modelo de risco de curto prazo:
  - Previsão de distribuição de retornos/drawdowns em D+1, D+3, D+5
  - Foco: **identificar quedas relevantes**, não apenas acerto de direção
  - Métrica principal: capacidade de evitar perdas, não de prever altas

---

### Fase 2 — Ambiente de mercado e agente MuZero

**Objetivo:** Implementar o ambiente de simulação e o agente de RL.

**Entregas:**

- **Ambiente de mercado** (`core/env`):
  - Estado: carteira atual, sinais dos ativos, contexto de mercado
  - Ações: aumentar/reduzir/zerar posições (respeitando restrições)
  - Recompensa: retorno - penalização de risco - custos

- **MuZero** (`core/rl/muzero` + `core/rl/search`):
  - Rede de representação (encoder de estados)
  - Rede de dinâmica (modelo do mundo)
  - Rede de previsão (política e valor)
  - MCTS para planejamento

---

### Fase 3 — Camada de alocação com Black-Litterman

**Objetivo:** Conectar as saídas do agente à alocação final de carteira.

**Entregas:**

- Extração de **views** do agente:
  - Preferências relativas entre ativos
  - Níveis de confiança por view

- Implementação do **Black-Litterman** (`core/allocation`):
  - Portfólio de equilíbrio (market cap ou equal weight)
  - Combinação de views com prior
  - Parâmetros de aversão ao risco

- Geração de **pesos finais** respeitando:
  - Limite de 10 ativos
  - Limites por ativo (5%–15%)
  - Long-only, sem alavancagem

---

### Fase 4 — Backtests históricos integrados

**Objetivo:** Validar o sistema completo em dados históricos.

**Entregas:**

- Simulações em múltiplos períodos:
  - Períodos de alta (bull market)
  - Períodos de baixa (bear market)
  - Crises (2008, 2015, 2020)

- Comparação com benchmarks:
  - IBOV
  - Carteira equal-weight dos 30 supervisionados
  - Carteiras de corretores (se houver histórico)

- Métricas de avaliação:

| Métrica | Objetivo |
|---------|----------|
| Retorno anualizado (CAGR) | > 15% real |
| Volatilidade | < IBOV |
| Drawdown máximo | < 15% |
| Sharpe ratio | > 1.0 |
| Turnover anual | < 200% |
| Estabilidade das decisões | Alta |

---

### Fase 5 — Dry Run em tempo real (6+ meses)

**Objetivo:** Testar o sistema em tempo real, sem capital real.

**Mecânica:**

- Rodar o modelo em **modo dry run** todos os dias
- Registrar decisões e resultados da carteira simulada
- Comparar com:
  - IBOV
  - Carteira dos corretores (real)
  - Carteira manual do Owner (se houver)

**Duração:** Mínimo de 6 meses, podendo estender para 12 meses.

**Saídas:**

- Relatórios semanais de performance
- Dashboard de acompanhamento
- Análise de erros e acertos

**Decisão GO/NO-GO:**

A decisão de colocar capital real no PortfolioZero permanece **exclusivamente nas mãos do Owner**:

- Não será codificada como regra rígida
- Não haverá gatilho automático de ativação
- Baseada na confiança, compreensão do comportamento e métricas observadas

---

## 8. Critérios de avaliação e papel do Owner

### O que o sistema PortfolioZero faz

1. **Gera sinais** de decisão de portfólio (comprar, vender, manter)
2. **Simula resultados** históricos e em dry run
3. **Produz métricas e relatórios** compreensíveis para o Owner

### O que o sistema NÃO faz

1. **Não toma decisões de capital real** automaticamente
2. **Não define** quando é hora de começar a operar com dinheiro de verdade
3. **Não substitui** o julgamento do Owner

### Papel do Owner

A decisão de **GO/NO-GO** é 100% do Owner:

> *"Se, quando e quanto capital real alocar ao PortfolioZero é uma decisão minha, baseada no que eu observar durante o dry run, nas comparações com alternativas, e no meu nível de conforto com o comportamento do sistema."*

O Owner utilizará:

- Comparações com carteiras de corretores
- Comparações com benchmarks (IBOV, CDI)
- Sua própria percepção de conforto com o comportamento do sistema
- Métricas objetivas (retorno, drawdown, estabilidade)

### Critérios sugeridos para GO (não vinculantes)

| Critério | Threshold sugerido |
|----------|-------------------|
| Performance no dry run vs IBOV | > 5% a.a. |
| Drawdown máximo no dry run | < 15% |
| Consistência mensal | > 60% dos meses positivos |
| Compreensão do Owner | "Eu entendo por que o modelo tomou cada decisão" |

**Importante:** Esses critérios são sugestões, não gatilhos automáticos. A decisão final é sempre do Owner.

---

## 9. Anexos conceituais

### A. Glossário

| Termo | Definição |
|-------|-----------|
| **Bolso** | Parcela isolada do patrimônio (R$ 500k) dedicada ao PortfolioZero |
| **Circuito fechado** | Operação sem aportes ou retiradas externas |
| **Drawdown** | Queda percentual do equity em relação ao pico anterior |
| **CAGR** | Compound Annual Growth Rate — taxa de crescimento anual composta |
| **Dry run** | Simulação em tempo real sem capital real |
| **View** | Opinião/expectativa do agente sobre retorno relativo de ativos |
| **Universo supervisionado** | Os 30 ativos monitorados permanentemente |
| **Carteira ativa** | Os ~10 ativos com capital efetivamente alocado |
| **Quarentena** | Período em que um ativo vendido não pode ser recomprado |
| **Turnover** | Giro da carteira — volume de compras+vendas / patrimônio |

### B. Referências técnicas

- **MuZero:** Schrittwieser et al. (2020). "Mastering Atari, Go, Chess and Shogi by Planning with a Learned Model." Nature.
- **Black-Litterman:** Black & Litterman (1992). "Global Portfolio Optimization." Financial Analysts Journal.

### C. Histórico de versões do plano

| Versão | Data | Mudanças |
|--------|------|----------|
| V1.0 | 26/11/2025 | Versão inicial congelada |

---

*Este documento é a referência de negócio e risco para todas as tasks técnicas do PortfolioZero. Qualquer alteração significativa nas premissas aqui descritas deve gerar uma nova versão do plano (V2, V3, etc.).*

