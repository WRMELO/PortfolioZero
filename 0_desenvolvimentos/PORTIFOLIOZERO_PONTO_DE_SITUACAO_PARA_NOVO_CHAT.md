# PORTIFOLIOZERO — Ponto de Situação (briefing completo para iniciar novo chat)

Data de referência: 2026-01-28  
Timezone: America/Sao_Paulo  
SSOT do repositório: `/home/wilson/PortfolioZero` (PORTIFOLIOZERO)  

Este documento descreve, de forma objetiva e verificável, a posição atual do projeto, os contratos de dados/artefatos existentes, o que está “congelado”, o que está pendente e qual é o encaminhamento natural do trabalho. Ele foi escrito para permitir iniciar um novo chat sem depender de contexto anterior.

---

## 1) Premissas do Owner (contexto de operação)

1. Operação **pessoal** (sem integração com corretora): as ordens serão executadas manualmente em **apps de bancos**.  
2. Rotina prevista: **toda manhã em dia útil**, usando como referência o **fechamento do último pregão disponível**.  
3. Filosofia: **preservação de capital** e preferência por estratégias com **menor perda / menor drawdown**, mesmo que com retorno menor.  
4. Evolução em estágios: primeiro um sistema operacional e auditável em **Dry-Run**, depois (após validação) evolução para maior sofisticação (ML/RL/MuZero).

> Observação: a decisão de “GO/NO-GO” para capital real permanece exclusivamente do Owner (o sistema não toma essa decisão automaticamente).  

---

## 2) Regra operacional (Dry-Run) — o que está formalizado

O acordo operacional definitivo do Dry-Run define:

- **Preço oficial** para decisões: sempre **Close** do último pregão disponível (D-1 útil).  
- **Estado de decisão (manhã de D)**: posições (quantidades) + caixa disponível em D. Compras não podem usar “caixa futuro”.  
- **Liquidação no dry-run**:
  - Venda: baixa imediata na quantidade; crédito em caixa em **D+2** calculado por `qtd_vendida × Close(D-1)` menos custo por ordem.
  - Compra: executada em D com o caixa disponível em D; volume comprado derivado de `caixa_disponível / Close(D-1)` menos custo por ordem.  
- **Fonte base de preços** no modo operacional: **Yahoo Finance**; antes de risco/decisão deve haver atualização + auditoria do pacote de preços (quando o modo diário estiver ativo).  
- Horizontes **D+1/D+3/D+5**: só poderão existir como **horizontes de previsão** (quando houver ML); não são “informação realizada” para decisão.

---

## 3) Artefatos do sistema (contratos e caminhos)

O PLAN_V2 consolidado descreve o sistema como produção de pacotes auditáveis (artefatos) e execução por TASK specs.

### 3.1. Market Data Package (preços)
- Diretório de preços raw: `data/raw/market/prices/`  
- Manifesto: `data/raw/market/prices/manifest_prices.json`  
- Observação de governança: existe um arquivo explicitamente “proibido” no raw (anti-sintético) citado no manifesto do estado atual: `data/raw/market/prices/sample_market_data.parquet` (deve ser removido/impedido no fluxo E2E).

### 3.2. Universe Package
- Candidates (canon): `data/universe/UNIVERSE_CANDIDATES.parquet`  
- Supervised (canon por diretório): `data/universe/supervised_TASK_A_012/` (o parquet mais recente dentro do diretório é a fonte operacional)  
- Existe também o supervised “raiz” e cópias por TASK (ver seção 4).

### 3.3. Risk Package
- Atual (v0): `data/risk/RISK_PACKAGE_V0.json`  
- Característica essencial: **campos de limites ficam `null` por design** até definição explícita (não há thresholds numéricos impostos pelo v0).

### 3.4. Decision Package (daily)
- Atual (SELL-ONLY v1): `data/decisions/DECISION_PACKAGE_DAILY_V1.json`  
- Regra de decisão atual:
  - Se ticker do portfolio está no universo supervisionado → `HOLD`
  - Se ticker está fora do universo supervisionado → `EXIT`
  - `REDUCE` está reservado para quando existirem regras/limites explícitos.

### 3.5. Posições (fonte governada)
- Fonte de entrada (input): `data/portfolio/incoming/PORTFOLIO_POSITIONS_SOURCE.parquet`  
- Saída “current” (consumo interno): `data/portfolio/PORTFOLIO_POSITIONS_REAL.parquet`  
- Archive: `data/portfolio/positions_archive/`  
- Manifest: `data/portfolio/manifest_positions_real.json`  
- Report: `planning/reports/REPORT_PORTFOLIO_POSITIONS_INGEST_V1.json`

---

## 4) Universo — números verificados e estrutura correta

### 4.1. Números verificados por inventário de parquets
O inventário `PARQUET_INVENTARIO_E_MANIFESTOS.json` registra:

- `data/universe/UNIVERSE_CANDIDATES.parquet` com **68 linhas**.  
- `data/universe/UNIVERSE_SUPERVISED.parquet` com **30 linhas**.  
- Cópias versionadas do supervised também com **30 linhas**:
  - `data/universe/supervised_TASK_A_010/UNIVERSE_SUPERVISED.parquet`
  - `data/universe/supervised_TASK_A_012/UNIVERSE_SUPERVISED.parquet` (mais recente pelo mtime no inventário)

### 4.2. Relação correta entre conjuntos (aninhamento)
A relação correta, compatível com o desenho do sistema, é:

- **Operando (10)** ⊆ **Supervised (30)** ⊆ **Candidates (68)**

Decomposição operacional útil:

- 10 operando (carteira alvo)  
- 20 supervisionados “disponíveis” (30 − 10), para rotação/substituição  
- 38 candidates fora do supervised (68 − 30), para observação / possível promoção futura  

> Importante: isso elimina a interpretação errada de “68 + 30 = 98” como se fossem conjuntos independentes.

### 4.3. Conteúdo de instrumentos (BDR/ETF) — o que é fato hoje
- Os parquets de universe possuem coluna `tipo_instrumento` no schema (tanto candidates quanto supervised).  
- O inventário do grupo de preços (`data/raw/market/prices/*.parquet`) lista diversos tickers com padrão de BDR (ex.: `AAPL34_SA.parquet`) como “row_anomalies”; isso indica que há **dados de preços** para BDRs no repositório, independentemente de estarem ou não no universo operável atual.

> Decisão de governança já estabelecida em chat: “o que estiver no universo é o que vale”. Portanto, a discussão “BDR vs ETF” não é opinativa: deve ser lida do universe vigente (`tipo_instrumento`) e congelada por evidência.

---

## 5) Estado do pipeline — o que está estável (PASS) e o que isso significa

O “Manifesto do Estado Atual” registra como estáveis e com validação PASS:

- **TASK_A_013 — Risk Package v0**: gera `data/risk/RISK_PACKAGE_V0.json` (thresholds `null` por design).  
- **TASK_A_018 — Ingestão oficial de posições**: consome `data/portfolio/incoming/PORTFOLIO_POSITIONS_SOURCE.parquet` e produz o parquet current + archive/manifest/report.  
- **TASK_A_017 — Build Portfolio Snapshot v1**: produz `data/portfolio/PORTFOLIO_SNAPSHOT_V1.json` a partir de `PORTFOLIO_POSITIONS_REAL.parquet` (sem fallback).  
- **TASK_A_014 — Daily Decision SELL-ONLY v1**: consome risk + universe supervised + snapshot e produz `DECISION_PACKAGE_DAILY_V1.json`.  
- **TASK_D_004 — Daily E2E SELL-ONLY v1**: orquestra o fluxo diário (prices → audit → universe → risk → decision) e inclui correção para remover `sample_market_data.parquet` antes do daily.  
- **TASK_D_005 — Daily E2E SELL-ONLY com Snapshot V1**: refina allowlist e corrige o caminho do supervised para `data/universe/supervised_TASK_A_012`.

Em resumo: o projeto já tem um “motor mínimo operacional” para **venda (sell-only)** e para **governança de posições** (ingestão + snapshot) com trilha auditável.

---

## 6) O que está deliberadamente pendente (e não deve ser “inventado”)

Os seguintes itens permanecem pendentes por decisão explícita (devem ser decididos via bateria de testes históricos, e não por chute):

1) Thresholds numéricos do Risk Package (campos hoje `null`) e regra explícita para “remover null” no risk package.  
2) Política de **REDUCE** (gatilhos, quantidade de redução, reversão, modo defensivo).  
3) Rotina semanal de **BUY/rebalance** do PLAN_V2 (ainda não implementada como contrato operacional).  
4) Política de **custos por ordem**: o acordo exige “custo fixo conservador por ordem”, mas o valor numérico ainda deve ser congelado via política versionada (e pode ser testado em cenários).

---

## 7) Linha de trabalho proposta pelo Owner (experimentos)

O Owner definiu um processo de desenvolvimento em 2 fases:

### Fase 1 — escolher o melhor critério de vendas
- Não usar ML com horizontes D+1/D+3/D+5.
- Não usar RL/MuZero.
- Compra semanal simples, fixa e imutável, apenas para manter o sistema rodando (não é o objeto de otimização nesta fase).
- Métrica: melhor valor final na última data do histórico disponível.

### Fase 2 — otimizar compras mantendo a venda vencedora congelada
- O critério de venda escolhido na fase 1 vira “invariante” (não muda).
- A otimização passa a ser o mecanismo de compra semanal.

Nesta etapa de laboratório, foi decidido que **não haverá atualização por Yahoo Finance**: os testes usarão somente o histórico já existente em parquet (range de datas observado no inventário: 2022-01-03 a 2026-01-22 para o grupo de preços).

---

## 8) Orientação de governança do trabalho (para novo chat)

Esta é a regra operacional entre Owner e Planejador para evitar erros:

- Não criar novos “protocolos”.  
- Não inferir fatos quando existir artefato verificável no repo.  
- Só afirmar como “verdade do projeto” o que vier com evidência: caminho do arquivo + conteúdo/schema/linhas + (se aplicável) referência do manifesto/plan/task.  
- Quando não houver evidência, registrar explicitamente como: **[NÃO VERIFICADO]** ou **[INFORMAÇÃO AUSENTE]** e não concluir.

---

## 9) As duas últimas ações relevantes (estado recente)

1) Confirmação por inventário de que o universo vigente é **Candidates = 68** e **Supervised = 30**, com supervised mais recente no diretório `supervised_TASK_A_012` (base para a decomposição 10/20/38).  
2) Consolidação do entendimento de que “operando (10) está contido no supervised (30)”, isto é, a carteira alvo é sempre subconjunto do universo supervisionado (e qualquer posição fora do supervised tende a saída pela regra sell-only atual).

---

## 10) Próximos passos (encaminhamento natural)

A sequência lógica para avançar, sem “contaminar” o que já foi feito:

1) Criar um diretório **novo** sob a raiz do repo para laboratório (experimentos), concentrando specs, runners e outputs, sem alterar o pipeline já estável.  
2) Definir formalmente o D0 (data de partida) e o “warmup” mínimo necessário para o critério de venda escolhido (para não iniciar sem histórico suficiente).  
3) Definir e congelar a regra de compra semanal “imutável” da Fase 1 (mesmo que simples), apenas para permitir simulações coerentes.  
4) Especificar a bateria de experimentos de venda (Fase 1): conjunto de critérios candidatos + métricas (valor final, maxDD, turnover, taxa de trades, etc.) e logs.  
5) Rodar os experimentos no histórico existente e selecionar o critério vencedor.  
6) Somente então iniciar a Fase 2 (melhoria de compras) mantendo a venda vencedora congelada.

---

## 11) Prompt pronto para abrir um novo chat (copiar e colar)

“Estou retomando o projeto PORTIFOLIOZERO no repo `/home/wilson/PortfolioZero`. Preciso trabalhar apenas com fatos verificáveis em artefatos do repo. Não crie novos protocolos; não inferir.  
Premissas: operação pessoal, sem corretora; rotina manhã em dias úteis; preço oficial Close(D-1); venda baixa quantidade em D e caixa entra em D+2; compra usa caixa disponível em D; Yahoo Finance é a fonte-alvo (mas nesta fase de laboratório só usar histórico já existente).  
Artefatos estáveis: prices raw + audit; universe; risk v0 (thresholds null); ingest de posições (A_018); snapshot v1 (A_017); decisão sell-only (A_014); E2E diário (D_004/D_005).  
Universo verificado: candidates=68 e supervised=30; operando(10) ⊆ supervised(30) ⊆ candidates(68) ⇒ decomposição 10/20/38.  
Objetivo agora: desenhar e executar experimentos em 2 fases: Fase 1 escolher critério de venda (sem ML/RL) com compra semanal fixa; Fase 2 otimizar compras mantendo a venda vencedora congelada.  
Comece propondo o desenho dos experimentos da Fase 1, mas cite sempre os arquivos do repo que sustentam cada afirmação.”

---

Fim.
