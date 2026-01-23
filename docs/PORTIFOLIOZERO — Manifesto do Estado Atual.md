

Data de referência: 2026-01-22  
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

- Uma TASK “base” só é considerada estável quando passa repetidamente sem mudanças de código.
    
- Para A_012, o critério foi **PASS 3 vezes seguidas** (sem alterações entre runs).
    

### 1.3 Política de gates (prática)

- Evitar gate “repo clean” para TASKs que geram outputs.
    
- Preferir allowlist focada em:
    
    - `planning/runs/**`
        
    - `data/**`
        
    - e bloquear mudanças inesperadas fora do escopo quando isso estiver sendo controlado.
        

---

## 2) Papéis e responsabilidades

### 2.1 Atores

- Owner: Wilson  
    Decide direção, valida entregáveis, executa os comandos no ambiente.
    
- Estrategista: ChatGPT (GPT-5.2 Thinking)  
    Autor de TASKs e contratos; decide sequência técnica; corrige quando há falhas.
    
- Agente/Editor: Cursor com GPT-5.2-CODEX  
    Aplica alterações no repo (JSON e Python), executa ajustes no código conforme instrução.
    

### 2.2 Regra prática

- TASK e scripts são “autoria do Estrategista”, “aplicação pelo Cursor”, “execução/validação pelo Owner”.
    

---

## 3) Infra e runtime

### 3.1 Runner (ponto único de execução)

- Script: `scripts/agno_runner.py`
    
- Entrada padrão:
    
    ```bash
    python scripts/agno_runner.py --task planning/task_specs/<TASK>.json
    ```
    
- Saída padrão:
    
    - imprime PASS/FAIL por step
        
    - grava `planning/runs/<TASK>/report.json`
        
    - grava artifacts por step em `planning/runs/<TASK>/<STEP>.txt`
        

### 3.2 Estrutura de diretórios relevante

- TASK specs: `planning/task_specs/`
    
- Runs/artefatos: `planning/runs/`
    
- Dados: `data/`
    
    - mercado (amostra): `data/raw/market/prices/`
        
    - universo: `data/universe/`
        
    - risco: `data/risk/`
        
    - carteira: `data/portfolio/`
        
    - decisões: `data/decisions/`
        

---

## 4) O que está implementado e congelado

### 4.1 TASK_A_012 — Universe E2E Strict (congelada)

Spec:

- `planning/task_specs/TASK_A_012_UNIVERSE_E2E_STRICT_V1.json`
    

Objetivo:

- Pipeline estrito de universo: sample → candidates validado → supervised
    
- Evita “fallback silencioso” por seleção errada de parquet/schema.
    

Artefatos principais:

- Runs: `planning/runs/TASK_A_012/`
    
- Candidates parquet (esperado): `data/universe/UNIVERSE_CANDIDATES.parquet`
    
- Supervised output (gerado pela task): `data/universe/supervised_TASK_A_012/` (contém parquet)
    

Scripts relevantes:

- `scripts/select_universe_candidates_parquet.py`  
    Estado atual: seleciona a tabela correta do `schema.md` com base em overlap com colunas reais do parquet e valida candidates.
    

Validação:

- PASS 3 vezes seguidas (estabilidade comprovada).
    

---

### 4.2 TASK_A_013 — Risk Package v0 (congelada)

Spec:

- `planning/task_specs/TASK_A_013_RISK_PACKAGE_V0.json`
    

Saída:

- `data/risk/RISK_PACKAGE_V0.json`
    

Características do v0:

- Declarativo e auditável.
    
- Não impõe thresholds numéricos (campos de limites ficam `null` por design, até definição explícita).
    

Validação:

- Script de verificação:
    
    - `scripts/validate_risk_package_v0.py`
        
- PASS.
    

---

### 4.3 TASK_A_014 — Daily Decision SELL-ONLY v1 (congelada)

Spec:

- `planning/task_specs/TASK_A_014_DAILY_DECISION_SELL_ONLY_V1.json`
    

Entradas:

- Risk package: `data/risk/RISK_PACKAGE_V0.json`
    
- Universo supervisionado: `data/universe/supervised_TASK_A_012/`
    
- Snapshot v0 (sintético): `data/portfolio/PORTFOLIO_SNAPSHOT_V0.json`
    

Saída:

- `data/decisions/DECISION_PACKAGE_DAILY_V1.json`
    

Regra atual (v1 sell-only):

- Se ticker do portfolio está no universo supervisionado → `HOLD`
    
- Se ticker está fora do universo supervisionado → `EXIT`
    
- `REDUCE` reservado para quando houver regras/limites explícitos
    

Validação:

- PASS.
    

---

## 5) Contratos de dados atuais (o que existe de fato)

### 5.1 Universe (candidates/supervised)

- Candidates:
    
    - arquivo: `data/universe/UNIVERSE_CANDIDATES.parquet`
        
    - schema referência: `data/universe/UNIVERSE_CANDIDATES.schema.md`
        
- Supervised:
    
    - diretório: `data/universe/supervised_TASK_A_012/`
        
    - parquet mais recente dentro desse diretório é tomado como fonte.
        

### 5.2 Risk Package

- arquivo: `data/risk/RISK_PACKAGE_V0.json`
    
- contém: universo (lista), restrições de portfólio (capital, posições), limites ainda indefinidos (null).
    

### 5.3 Decision Package Daily

- arquivo: `data/decisions/DECISION_PACKAGE_DAILY_V1.json`
    
- contém: decisões por ticker (HOLD/EXIT), razões, sumário.
    

### 5.4 Portfolio Snapshot

- arquivo atual (sintético): `data/portfolio/PORTFOLIO_SNAPSHOT_V0.json`
    
- finalidade: destravar pipeline até chegarmos em snapshot real.
    

---

## 6) Modelo de execução e auditoria

### 6.1 Como rodar cada tarefa

Exemplos:

```bash
cd /home/wilson/PortfolioZero

python scripts/agno_runner.py --task planning/task_specs/TASK_A_012_UNIVERSE_E2E_STRICT_V1.json
python scripts/agno_runner.py --task planning/task_specs/TASK_A_013_RISK_PACKAGE_V0.json
python scripts/agno_runner.py --task planning/task_specs/TASK_A_014_DAILY_DECISION_SELL_ONLY_V1.json
```

### 6.2 Onde verificar evidências

- relatório do run:
    
    - `planning/runs/<TASK>/report.json`
        
- artifacts por step:
    
    - `planning/runs/<TASK>/<STEP>.txt`
        

---

## 7) O que está pronto para discussão agora

### 7.1 Tema imediato

Dados e aquisição de snapshots:

- substituição do snapshot sintético por snapshot real
    
- formatos possíveis (manual JSON/CSV, export de corretora, API, etc.)
    
- periodicidade (diária/semana) e governança (log/audit/versionamento)
    

### 7.2 Itens que ainda não existem (abertos)

- Snapshot real de carteira (formato e fonte)
    
- Integração com dados reais de preços/posições (quando e como)
    
- Regras explícitas de risco para ativar `REDUCE` e limites não-nulos no risk package
    
- Rotina semanal de BUY/rebalance (ainda não implementada)
    

---

Se você quiser, eu já organizo o próximo bloco de trabalho como um “manifesto de dados” separado (fontes, formatos, campos mínimos, versionamento e auditoria), mas só depois que você começar a definir como quer obter o snapshot real (manual, export, API, etc.).