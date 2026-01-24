
```mermaid
flowchart TD
  subgraph ESPORADICAS["Tasks esporádicas / uso único (ou raras)"]
    A015["TASK_A_015<br/>Inspect snapshot contract V0<br/>(PASS)"]
    A018["TASK_A_018<br/>Ingest positions real parquet<br/>SOURCE.parquet → REAL.parquet<br/>+ archive + manifest + report<br/>(PASS)"]
    A017["TASK_A_017<br/>Build snapshot V1 from Parquet<br/>REAL.parquet → SNAPSHOT_V1.json<br/>(PASS)"]
  end

  subgraph ROT_DIARIA["Rotina diária (execução diária)"]
    D005["TASK_D_005<br/>Daily E2E sell-only + snapshot V1<br/>(PASS)"]
    D004["TASK_D_004<br/>Daily E2E sell-only baseline<br/>(PASS)"]
    D002["TASK_D_002<br/>Market data daily idempotent<br/>(PASS)"]
    D003["TASK_D_003<br/>Audit post daily → planning/reports/<br/>(PASS)"]
    A012["TASK_A_012<br/>Universe E2E strict<br/>(PASS)"]
    A013["TASK_A_013<br/>Risk package V0<br/>(PASS)"]
    A014["TASK_A_014<br/>Decision sell-only daily<br/>reads SNAPSHOT_V1.json<br/>(PASS)"]
  end

  subgraph ROT_SEMANAL["Rotina semanal (a definir / não implementado)"]
    WEEKBUY["BUY / rebalance semanal (Plan V2)<br/>[NÃO IMPLEMENTADO]"]
  end

  subgraph ROT_MENSAL["Rotina mensal (a definir / não implementado)"]
    MONTHREV["Revisões / reparametrizações (Plan V2)<br/>[NÃO IMPLEMENTADO]"]
  end

  A018 --> A017
  A017 --> A014

  D005 --> D004
  D004 --> D002
  D004 --> D003
  D004 --> A012
  D004 --> A013
  D004 --> A014

  D002 --> D003
  D003 --> D004
  A012 --> A013
  A012 --> A014
  A013 --> A014

  A014 --> WEEKBUY
  WEEKBUY --> MONTHREV
``
