# PORTIFOLIOZERO — Fluxo atual (24.01.26)

Legenda:
- Verde = já valendo (PASS / em uso)
- Amarelo = precisamos desenvolver
- Vermelho = não mexemos (não implementado)

```mermaid
flowchart TD
  %% =========================
  %% OCASIONAL / ESPORÁDICO
  %% =========================
  subgraph OCASIONAL["Ocasional / esporádico (execução rara)"]
    A015["A_015 — Contrato do Snapshot V0<br/>Valida chaves/estrutura do JSON de carteira (V0)"]
    A018["A_018 — Ingestão Posições Reais<br/>SOURCE.parquet → REAL.parquet<br/>+ archive + manifest + report"]
    A017["A_017 — Monta Snapshot V1<br/>REAL.parquet → SNAPSHOT_V1.json (carteira consumível)"]
  end

  %% =========================
  %% ROTINA DIÁRIA (SELL-ONLY)
  %% =========================
  subgraph DIARIO["Rotina diária (sell-only em produção)"]
    D002["D_002 — Atualiza Preços (Daily)<br/>Baixa/atualiza market prices parquet (idempotente)"]
    D003["D_003 — Auditoria Pós-Daily<br/>Checa integridade/schemas e escreve report em planning/reports/"]
    A012["A_012 — Gera Universo Supervisionado<br/>Constrói universe candidates + supervised parquet (strict)"]
    A013["A_013 — Pacote de Risco V0<br/>Gera RISK_PACKAGE_V0.json (limites ainda null)"]
    A014["A_014 — Decisão Diária Sell-Only<br/>HOLD se no universo; EXIT se fora (usa SNAPSHOT_V1.json)"]
    D004["D_004 — Orquestra Daily Baseline<br/>Roda D_002→D_003→A_012→A_013→A_014 e verifica outputs"]
    D005["D_005 — Daily com Snapshot V1 (E2E)<br/>Garantia de paths corretos + usa supervised_TASK_A_012 + snapshot V1"]
  end

  %% =========================
  %% FUTURO (PLAN V2)
  %% =========================
  subgraph BACKLOG["Backlog (precisa desenvolver)"]
    REDUCE_RULES["Futuro — Regras de REDUCE<br/>Definir limites explícitos para reduzir posição (além de HOLD/EXIT)"]
    SOURCE_PROC["Futuro — Procedimento do SOURCE.parquet<br/>Definir rotina de geração do input de posições (manual/API/export)"]
  end

  subgraph SEMANAL["Rotina semanal (não mexemos)"]
    WEEKBUY["Futuro — BUY/Rebalance semanal<br/>Comprar/realocar (Plan V2)"]
  end

  subgraph MENSAL["Rotina mensal (não mexemos)"]
    MONTHREV["Futuro — Revisões mensais<br/>Reparametrizar universo/risco/modelos (Plan V2)"]
  end

  %% =========================
  %% ENCADEAMENTOS
  %% =========================
  SOURCE_PROC --> A018
  A018 --> A017
  A017 --> A014

  D002 --> D003
  D003 --> A012
  A012 --> A013
  A012 --> A014
  A013 --> A014

  D004 --> D002
  D004 --> D003
  D004 --> A012
  D004 --> A013
  D004 --> A014

  D005 --> D004

  A014 --> REDUCE_RULES
  REDUCE_RULES --> WEEKBUY
  WEEKBUY --> MONTHREV

  %% =========================
  %% CORES
  %% =========================
  classDef done fill:#2ecc71,stroke:#145a32,color:#000,stroke-width:1px;
  classDef todo fill:#f1c40f,stroke:#7d6608,color:#000,stroke-width:1px;
  classDef notstarted fill:#e74c3c,stroke:#641e16,color:#000,stroke-width:1px;

  %% Verde (já valendo)
  class A015,A018,A017,D002,D003,A012,A013,A014,D004,D005 done;

  %% Amarelo (precisa desenvolver)
  class REDUCE_RULES,SOURCE_PROC todo;

  %% Vermelho (não mexemos)
  class WEEKBUY,MONTHREV notstarted;
