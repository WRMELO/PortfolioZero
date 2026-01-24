Data de referência: 2026-01-23
Repo (SSOT): `/home/wilson/PortfolioZero`
Branch: `main`
Ambiente: Ubuntu 25.10 | Python 3.12.12 | `.venv` no repo | `agno==2.4.1`

---

## 1) Forma de trabalhar

### 1.1 Ciclo operacional (fixo)

1. Eu (Estrategista) escrevo:
   - TASK (JSON) em `planning/task_specs/`
   - scripts `.py` em `scripts/` (quando necessário)

2. Você copia/cola no Cursor (Agente/Editor) e o Cursor aplica no repo.

3. Você executa no terminal, dentro do `.venv`, via runner:

   ```bash
   cd /home/wilson/PortfolioZero
   python scripts/agno_runner.py --task planning/task_specs/<TASK>.json
   ```

4. Se der FAIL: você cola `planning/runs/<TASK>/report.json` + artifact do step que falhou; eu corrijo e repetimos.

### 1.2 Critério de estabilidade

* Uma TASK “base” só é considerada estável quando passa repetidamente sem mudanças de código.

* Para A_012, o critério foi PASS 3 vezes seguidas (sem alterações entre runs).

### 1.3 Política de gates (prática)

* Evitar gate “repo clean” para TASKs que geram outputs.

* Preferir allowlist focada em prefixos diretos (sem glob):

  * `planning/task_specs/`
  * `planning/runs/`
  * `planning/reports/`
  * `data/`
  * `scripts/`

Observação: o `agno_runner` aceita allowlist por prefixos de diretório (com `/`) ou caminhos exatos; não aceitar `**` foi relevante em correções recentes.

---

## 2) Papéis e responsabilidades

### 2.1 Atores

* Owner: Wilson
  Decide direção, valida entregáveis, executa os comandos no ambiente.

* Estrategista: ChatGPT (GPT-5.2 Thinking)
  Autor de TASKs e contratos; decide sequência técnica; corrige quando há falhas.

* Agente/Editor: Cursor
  Aplica alterações no repo (JSON e Python), executa ajustes no código conforme instrução.

### 2.2 Regra prática

* TASK e scripts são “autoria do Estrategista”, “aplicação pelo Cursor”, “execução/validação pelo Owner”.

---

## 3) Infra e runtime

### 3.1 Runner (ponto único de execução)

* Script: `scripts/agno_runner.py`

* Entrada padrão:

  ```bash
  python scripts/agno_runner.py --task planning/task_specs/<TASK>.json
  ```

* Saída padrão:

  * imprime PASS/FAIL por step
  * grava `planning/runs/<TASK>/report.json`
  * grava artifacts por step em `planning/runs/<TASK>/<STEP>.txt`

### 3.2 Estrutura de diretórios relevante

* TASK specs: `planning/task_specs/`
* Runs/artefatos: `planning/runs/`
* Reports consolidados: `planning/reports/`
* Dados: `data/`

  * mercado (prices): `data/raw/market/prices/`
  * universo: `data/universe/`
  * risco: `data/risk/`
  * carteira: `data/portfolio/`
  * decisões: `data/decisions/`

---

## 4) O que está implementado e congelado (baseline operacional)

### 4.1 TASK_D_002 — Market Data Daily Idempotent v1 (estável)

Spec:

* `planning/task_specs/TASK_D_002_MARKET_DATA_DAILY_IDEMPOTENT_V1.json`

Objetivo:

* Atualização diária idempotente de market prices (parquet), com política de refresh de janela (padrão atual).

Status:

* OVERALL: PASS (confirmado).

### 4.2 TASK_D_003 — Audit Market Prices Post Daily (estável)

Spec:

* `planning/task_specs/TASK_D_003_AUDIT_MARKET_PRICES_POST_DAILY_V1.json`

Objetivo:

* Auditoria pós-daily dos parquets de prices e escrita de report em `planning/reports/`.

Status:

* OVERALL: PASS (confirmado).

### 4.3 TASK_A_012 — Universe E2E Strict v1 (congelada)

Spec:

* `planning/task_specs/TASK_A_012_UNIVERSE_E2E_STRICT_V1.json`

Objetivo:

* Pipeline estrito de universo: sample → candidates validado → supervised.
* Evita fallback silencioso por seleção errada de parquet/schema.

Artefatos principais:

* Candidates parquet (esperado): `data/universe/UNIVERSE_CANDIDATES.parquet`
* Supervised output (gerado pela task): `data/universe/supervised_TASK_A_012/` (contém parquet)
* Runs: `planning/runs/TASK_A_012/`

Validação:

* PASS 3 vezes seguidas (estabilidade comprovada).

### 4.4 TASK_A_013 — Risk Package v0 (congelada)

Spec:

* `planning/task_specs/TASK_A_013_RISK_PACKAGE_V0.json`

Saída:

* `data/risk/RISK_PACKAGE_V0.json`

Características do v0:

* Declarativo e auditável.
* Não impõe thresholds numéricos (campos de limites ficam `null` por design, até definição explícita).

Validação:

* PASS.

### 4.5 TASK_A_018 — Ingestão oficial de posições reais (estável)

Spec:

* `planning/task_specs/TASK_A_018_INGEST_PORTFOLIO_POSITIONS_REAL_PARQUET_V1.json`

Objetivo:

* Ingestão oficial do arquivo-fonte de posições (Parquet) com:

  * canonicalização de colunas e tipos
  * idempotência por hash
  * versionamento (archive)
  * manifest de histórico
  * report de ingestão

Convenção de entrada (fonte):

* `data/portfolio/incoming/PORTFOLIO_POSITIONS_SOURCE.parquet`

Saídas e governança:

* Current: `data/portfolio/PORTFOLIO_POSITIONS_REAL.parquet`
* Archive: `data/portfolio/positions_archive/`
* Manifest: `data/portfolio/manifest_positions_real.json`
* Report: `planning/reports/REPORT_PORTFOLIO_POSITIONS_INGEST_V1.json`

Ajuste operacional feito pelo Owner (para viabilizar a primeira execução):

* Criado input esperado:

  * `data/portfolio/incoming/PORTFOLIO_POSITIONS_SOURCE.parquet` (cópia do parquet atual para servir de input)
* Criada estrutura exigida:

  * `data/portfolio/positions_archive/`

Status:

* OVERALL: PASS (confirmado).

### 4.6 TASK_A_017 — Build Portfolio Snapshot v1 from Parquet (estável, sem fallback)

Spec:

* `planning/task_specs/TASK_A_017_BUILD_PORTFOLIO_SNAPSHOT_V1_FROM_PARQUET.json`

Objetivo:

* Gerar `data/portfolio/PORTFOLIO_SNAPSHOT_V1.json` a partir de `data/portfolio/PORTFOLIO_POSITIONS_REAL.parquet`,
  mantendo contrato mínimo compatível com o consumidor SELL-ONLY.

Condição (governança):

* O Parquet `data/portfolio/PORTFOLIO_POSITIONS_REAL.parquet` deve existir e ser produzido pela TASK_A_018.
* Foi removido o step de fallback que gerava Parquet automaticamente.

Status:

* OVERALL: PASS (confirmado, após remoção do fallback).

### 4.7 TASK_A_014 — Daily Decision SELL-ONLY v1 (congelada)

Spec:

* `planning/task_specs/TASK_A_014_DAILY_DECISION_SELL_ONLY_V1.json`

Entradas:

* Risk package: `data/risk/RISK_PACKAGE_V0.json`
* Universo supervisionado: `data/universe/supervised_TASK_A_012/`
* Snapshot v1 (atual): `data/portfolio/PORTFOLIO_SNAPSHOT_V1.json`

Saída:

* `data/decisions/DECISION_PACKAGE_DAILY_V1.json`

Regra atual (v1 sell-only):

* Se ticker do portfolio está no universo supervisionado → `HOLD`
* Se ticker está fora do universo supervisionado → `EXIT`
* `REDUCE` reservado para quando houver regras/limites explícitos

Status:

* OVERALL: PASS (confirmado).

### 4.8 TASK_D_004 — Daily E2E SELL-ONLY v1 (estável)

Spec:

* `planning/task_specs/TASK_D_004_DAILY_E2E_SELL_ONLY_V1.json`

Objetivo:

* Orquestrar o daily E2E:

  * D_002 (daily prices) → D_003 (audit) → A_012 (universe) → A_013 (risk) → A_014 (decision)

Falha raiz corrigida:

* `data/raw/market/prices/sample_market_data.parquet` existia (gerado por A_012), quebrando D_002 e D_003.
* Correção aplicada:

  * Remoção explícita do `sample_market_data.parquet` antes de rodar D_002 (e verificação final).

Status:

* OVERALL: PASS (confirmado).

### 4.9 TASK_D_005 — Daily E2E SELL-ONLY com Snapshot V1 (estável)

Spec:

* `planning/task_specs/TASK_D_005_DAILY_E2E_SELL_ONLY_SNAPSHOT_V1.json`

Objetivo:

* Rodar o E2E diário garantindo uso de snapshot V1 e caminhos consistentes com A_014.

Correções aplicadas:

* Allowlist:

  * removido `**` e padronizado para:

    * `planning/task_specs/`, `planning/runs/`, `planning/reports/`, `data/`, `scripts/`
* Supervised dir:

  * corrigido de `data/supervised` para `data/universe/supervised_TASK_A_012`

Status:

* OVERALL: PASS (confirmado).

---

## 5) Contratos de dados atuais (o que existe de fato)

### 5.1 Market Prices (raw parquet + manifesto)

* diretório: `data/raw/market/prices/`
* manifesto: `data/raw/market/prices/manifest_prices.json`
* arquivo proibido no raw (anti-sintético): `data/raw/market/prices/sample_market_data.parquet`

### 5.2 Universe (candidates/supervised)

* Candidates:

  * arquivo: `data/universe/UNIVERSE_CANDIDATES.parquet`
  * schema referência: `data/universe/UNIVERSE_CANDIDATES.schema.md`

* Supervised:

  * diretório: `data/universe/supervised_TASK_A_012/`
  * parquet mais recente dentro desse diretório é tomado como fonte.

### 5.3 Risk Package

* arquivo: `data/risk/RISK_PACKAGE_V0.json`
* contém: universo (lista), restrições de portfólio (capital, posições), limites ainda indefinidos (null).

### 5.4 Portfolio Positions (fonte governada)

* Fonte operacional (entrada):

  * `data/portfolio/incoming/PORTFOLIO_POSITIONS_SOURCE.parquet`

* Current (consumo interno):

  * `data/portfolio/PORTFOLIO_POSITIONS_REAL.parquet`

* Versionamento e rastreabilidade:

  * `data/portfolio/positions_archive/`
  * `data/portfolio/manifest_positions_real.json`
  * `planning/reports/REPORT_PORTFOLIO_POSITIONS_INGEST_V1.json`

### 5.5 Portfolio Snapshot

* snapshot sintético (ainda existe, para referência): `data/portfolio/PORTFOLIO_SNAPSHOT_V0.json`
* snapshot atual (pipeline): `data/portfolio/PORTFOLIO_SNAPSHOT_V1.json`

Contrato mínimo (congelado):

* top-level: `capital_brl`, `cash_brl`, `generated_at_utc`, `notes`, `positions`, `version`
* positions[]: `ticker`, `quantity`, `avg_price`

### 5.6 Decision Package Daily

* arquivo: `data/decisions/DECISION_PACKAGE_DAILY_V1.json`
* contém: decisões por ticker (HOLD/EXIT), razões, sumário, inputs (inclui path do snapshot).

---

## 6) Modelo de execução e auditoria

### 6.1 Como rodar o daily completo (recomendado)

```bash
cd /home/wilson/PortfolioZero
python scripts/agno_runner.py --task planning/task_specs/TASK_D_005_DAILY_E2E_SELL_ONLY_SNAPSHOT_V1.json
```

### 6.2 Como rodar apenas a governança de posições

```bash
cd /home/wilson/PortfolioZero
python scripts/agno_runner.py --task planning/task_specs/TASK_A_018_INGEST_PORTFOLIO_POSITIONS_REAL_PARQUET_V1.json
```

### 6.3 Onde verificar evidências

* relatório do run:

  * `planning/runs/<TASK>/report.json`
* artifacts por step:

  * `planning/runs/<TASK>/<STEP>.txt`
* reports consolidados (auditorias/contratos):

  * `planning/reports/`

---