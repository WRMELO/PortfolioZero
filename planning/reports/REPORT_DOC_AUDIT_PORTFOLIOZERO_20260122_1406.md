 # REPORT_DOC_AUDIT_PORTFOLIOZERO_20260122_1406
 
 ## 1. Identificacao do estado do repo (commit, status, ambiente detectado)
 - Repo: `/home/wilson/PortfolioZero` (branch `main`, tracking `origin/main`).
 - Último commit: `cb294bd feat: Update selection log and tickers for supervised task A`.
 - Comandos usados (somente leitura/inspeção): `git rev-parse --show-toplevel`, `git status -sb`, `git log -1 --oneline`, `TZ=America/Sao_Paulo date +%Y%m%d_%H%M`, `mkdir -p /home/wilson/PortfolioZero/planning/reports`, `python3 - <<'PY' ...` (hash de evidências).
 
 ## 2. Inventario de documentos (docs/) e onde estao as definicoes oficiais
 - Plano de negócio/risco/roadmap (V1): `docs/PORTFOLIOZERO_PLAN_V1.md`. Evidências de objetivos, capital, universo, cadência e roadmap (ex.: `docs/PORTFOLIOZERO_PLAN_V1.md` L24-L33, L41-L56, L148-L168, L231-L248, L290-L305, L469-L475).
 - Plano operacional consolidado (V2): `docs/PORTFOLIOZERO — PLAN_V2 (consolidado).md` com tese, artefatos, fases e critérios de pronto (ex.: L1-L35, L38-L58, L61-L71, L73-L118, L139-L149, L154-L156).
 - Briefing para TPM/Planejamento: `docs/TPM_BRIEFING_PORTFOLIOZERO.md` (ex.: L1-L20).
 - Status de desenvolvimento: `docs/DEVELOPMENT_STATUS.md` (ex.: L1-L18).
 - Relatórios de conclusão: `docs/TASK_008_COMPLETION_REPORT.md`, `docs/TASK_010_COMPLETION_REPORT.md`, `docs/TASK_011_COMPLETION_REPORT.md` (ex.: L1-L15 em cada).
 - Documentos do Trilho A: `docs/universe/UNIVERSE_DATA_PIPELINE_V1.md`, `docs/universe/UNIVERSE_SELECTION_CRITERIA_V1.md`, `docs/universe/UNIVERSE_PRELIST_RUNBOOK_V1.md`, `docs/universe/UNIVERSE_SUPERVISED_RUNBOOK_V1.md`, `docs/universe/UNIVERSE_DECISION_LOG_TEMPLATE.md`, `docs/universe/UNIVERSE_TRILHO_A_OVERVIEW.md` (ex.: L1-L19, L1-L19, L1-L21, L1-L22, L1-L14, L1-L11).
 
 ## 3. Leitura fiel do PLAN_V1 (pontos-chave com evidencias)
 - Objetivo do projeto: ferramenta pessoal do Owner, combinando stock picking e Data Science/IA para renda complementar e desafio intelectual (evidência: `docs/PORTFOLIOZERO_PLAN_V1.md` L24-L33).
 - Capital e circuito fechado: bolso R$ 500k, sem aportes/saques, duração mínima 3 anos (evidência: `docs/PORTFOLIOZERO_PLAN_V1.md` L41-L56).
 - Arquitetura: universo supervisionado ~30 e carteira ativa ~10 (8–12), com limites por posição (evidência: `docs/PORTFOLIOZERO_PLAN_V1.md` L148-L168).
 - Cadência operacional: venda diária, compra semanal (evidência: `docs/PORTFOLIOZERO_PLAN_V1.md` L231-L248).
 - Roadmap: fases 0–5 e Trilho A paralelo (evidência: `docs/PORTFOLIOZERO_PLAN_V1.md` L290-L305).
 - GO/NO-GO: decisão final de capital real é exclusiva do Owner (evidência: `docs/PORTFOLIOZERO_PLAN_V1.md` L469-L475).
 
 ## 4. Leitura fiel do PLAN_V2 consolidado (pontos-chave com evidencias)
 - Parâmetros travados (capital, cadência, universo, carteira, long-only) (evidência: `docs/PORTFOLIOZERO — PLAN_V2 (consolidado).md` L1-L35).
 - Tese: execução repetível por TASKs com evidências em `planning/runs/` (evidência: `docs/PORTFOLIOZERO — PLAN_V2 (consolidado).md` L17-L21).
 - Quatro produtos/artefatos (Market Data, Universe, Risk, Decision Package) (evidência: `docs/PORTFOLIOZERO — PLAN_V2 (consolidado).md` L38-L58).
 - Papel do Agno vs shell (contratos vs execução) (evidência: `docs/PORTFOLIOZERO — PLAN_V2 (consolidado).md` L61-L71).
 - Roadmap V2 por fases (0–6) e foco no Decision Package antes de upgrades (evidência: `docs/PORTFOLIOZERO — PLAN_V2 (consolidado).md` L73-L118).
 - Critério de pronto do V2: TASK diária gera Decision Package auditável, invariantes respeitadas e reexecução reproduzível (evidência: `docs/PORTFOLIOZERO — PLAN_V2 (consolidado).md` L139-L149).
 - Próximo passo depende da escolha BUY/SELL vs HOLD/SELL (evidência: `docs/PORTFOLIOZERO — PLAN_V2 (consolidado).md` L154-L156).
 
 ## 5. Diferencas V1 vs V2 (tabela + implicacoes apenas quando explicitamente suportadas)
 | Item | V1 | V2 consolidado | Evidencias |
 | --- | --- | --- | --- |
 | Parametros de negocio | Capital R$ 500k, cadência diária/semanal, universo ~30 e carteira ~10 | Mantém os mesmos parâmetros como invariantes | `docs/PORTFOLIOZERO_PLAN_V1.md` L41-L56, L148-L168, L231-L248; `docs/PORTFOLIOZERO — PLAN_V2 (consolidado).md` L1-L35 |
 | Execução e governança | Plano conceitual de negócio/risco/roadmap | Execução via TASKs com evidências em `planning/runs/` | `docs/PORTFOLIOZERO — PLAN_V2 (consolidado).md` L17-L21 |
 | Artefatos | Não formaliza pacotes como produtos | Define 4 produtos (Market Data, Universe, Risk, Decision Package) | `docs/PORTFOLIOZERO — PLAN_V2 (consolidado).md` L38-L58 |
 | Roadmap | Fases 0–5 e Trilho A paralelo | Fases 0–6, com Decision Package antes de upgrades (MuZero/BL) | `docs/PORTFOLIOZERO_PLAN_V1.md` L290-L305; `docs/PORTFOLIOZERO — PLAN_V2 (consolidado).md` L73-L118 |
 
 ## 6. Mapa plano -> implementacao (o que existe de fato no repo)
 | Item do plano | Arquivos no repo | Status | Evidencias |
 | --- | --- | --- | --- |
 | Market Data Package | `modules/portfoliozero/core/data/market_data_ingestion.py`, `config/experiments/universe_data_sources_v1.yaml`, `scripts/fetch_market_data.py` | Parcial (ingestão implementada, sem contrato explícito do pacote) | `modules/portfoliozero/core/data/market_data_ingestion.py` L1-L35; `config/experiments/universe_data_sources_v1.yaml` L18-L45 |
 | Universe Package (candidates + supervised) | `modules/portfoliozero/core/data/universe_candidates_pipeline.py`, `modules/portfoliozero/core/universe/universe_supervised_selector.py`, scripts de orquestração | Parcial (pipeline existe, mas execução A_010 falhou por erro de schema) | `modules/portfoliozero/core/data/universe_candidates_pipeline.py` L475-L563; `modules/portfoliozero/core/universe/universe_supervised_selector.py` L197-L209; `planning/runs/TASK_A_010/S4_RUN_UNIVERSE_CANDIDATES.txt` L146-L163 |
 | Risk Package | Apenas descrito em docs | Ausente | `docs/PORTFOLIOZERO — PLAN_V2 (consolidado).md` L38-L58; L101-L107 |
 | Decision Package | `scripts/generate_decision_package_v1.py`, `planning/task_specs/TASK_A_011_DECISION_PACKAGE_V1.json`, `data/decisions/decision_TASK_A_011.json` | Existe (baseline HOLD, determinístico) | `scripts/generate_decision_package_v1.py` L76-L105; `planning/task_specs/TASK_A_011_DECISION_PACKAGE_V1.json` L1-L55; `data/decisions/decision_TASK_A_011.json` L1-L46 |
 | Governança Runner + Agno | `scripts/agno_runner.py`, `config/agno/runtime_entrypoint.json`, tasks A_007/A_008 | Existe (contrato agno + smoke) | `scripts/agno_runner.py` L182-L214; `planning/task_specs/TASK_A_007_AGNO_RUNTIME_SMOKE_V1.json` L1-L53; `planning/task_specs/TASK_A_008_AGNO_CONTRACT_ALWAYS_V1.json` L1-L43 |
 
 ## 7. Validacao do handoff (claims controversas) com SIM/NAO e evidencias
 - Claim: Step `type=agno` é contrato com payload (sem `commands`). **SIM.** Evidência: `scripts/agno_runner.py` L182-L214.
 - Claim: Agno runtime executa e smoke passa (TASK_A_007). **SIM.** Evidências: `planning/task_specs/TASK_A_007_AGNO_RUNTIME_SMOKE_V1.json` L1-L53; `planning/runs/TASK_A_007/report.json` L1-L33; `planning/runs/TASK_A_007/S3_AGNO_PROBE.txt` L1-L15.
 - Claim: Contrato agno “sempre” (TASK_A_008) com gate clean. **SIM.** Evidências: `planning/task_specs/TASK_A_008_AGNO_CONTRACT_ALWAYS_V1.json` L1-L43; `planning/runs/TASK_A_008/S1_GATE_CLEAN.txt` L1-L6; `planning/runs/TASK_A_008/S3_AGNO_STEP_CONTRACT.txt` L1-L15.
 - Claim: Gates clean/allowlist existem e se comportam diferente. **SIM.** Evidências: allowlist em TASK_A_007 (`planning/task_specs/TASK_A_007_AGNO_RUNTIME_SMOKE_V1.json` L1-L53), clean gate em TASK_A_008 (`planning/task_specs/TASK_A_008_AGNO_CONTRACT_ALWAYS_V1.json` L1-L43), clean gate falhando em TASK_A_004 (`planning/runs/TASK_A_004/S1_GIT_CLEAN_REQUIRED.txt` L1-L6).
 - Claim: Smokes são “estáveis”. **INCONCLUSIVO.** Há evidência de execução PASS única (A_007/A_008), mas não há série temporal de estabilidade.
 
 ## 8. Lista de lacunas (o que o plano exige e nao existe / existe parcial) com referencia
 - Risk Package não implementado (apenas descrito no V2). Evidências: `docs/PORTFOLIOZERO — PLAN_V2 (consolidado).md` L38-L58; L101-L107.
 - Decision Package ainda é baseline HOLD, sem BUY/SELL/estratégia (gap para fase operacional). Evidências: `scripts/generate_decision_package_v1.py` L76-L105; `data/decisions/decision_TASK_A_011.json` L1-L46.
 - Pipeline de candidatos falhou em execução A_010 (erro de schema). Evidência: `planning/runs/TASK_A_010/S4_RUN_UNIVERSE_CANDIDATES.txt` L146-L163.
 - Execução A_010 usou `UNIVERSE_SUPERVISED.parquet` como “candidates”, sinal de fluxo inconsistente/no-op. Evidência: `planning/runs/TASK_A_010/S6_RUN_UNIVERSE_SUPERVISED.txt` L5-L9.
 
 ## 9. Proposta de proxima sequencia de TASK_A_XXX (apenas se estiver explicitamente suportada pelos planos; caso contrario, marcar como AUSENTE)
 - **AUSENTE.** O PLAN_V2 consolidado pede decisão entre BUY/SELL vs HOLD/SELL, mas não enumera a próxima sequência com IDs `TASK_A_XXX` (evidência: `docs/PORTFOLIOZERO — PLAN_V2 (consolidado).md` L154-L156).
 
 ## 10. Apice de risco: itens que podem induzir execucao falsa-positiva (no-op) ou gates instaveis
 - **Falso-positivo operacional:** Decision Package v1 gera apenas HOLDs e pode “passar” sem estratégia real (evidências: `scripts/generate_decision_package_v1.py` L76-L105; `data/decisions/decision_TASK_A_011.json` L1-L46).
 - **Pipeline inconsistente:** execução A_010 falhou no candidates e ainda assim seguiu com supervised usando `UNIVERSE_SUPERVISED.parquet` como entrada (evidências: `planning/runs/TASK_A_010/S4_RUN_UNIVERSE_CANDIDATES.txt` L146-L163; `planning/runs/TASK_A_010/S6_RUN_UNIVERSE_SUPERVISED.txt` L5-L9).
 - **Gates sensíveis à limpeza:** gate clean existe e pode falhar em repo sujo; isso pode bloquear runs se há alterações fora do allowlist (evidências: `planning/runs/TASK_A_008/S1_GATE_CLEAN.txt` L1-L6; `planning/runs/TASK_A_004/S1_GIT_CLEAN_REQUIRED.txt` L1-L6).
