ROADMAP DE DESENVOLVIMENTO
Fase 1 — Experimentos de Vendas (lab isolado)

Formato de configuração
1) Base congelada (não muda): specs/frozen/frozen_v1.json
2) Delta do experimento (muda a cada run): specs/experiments/EXP_F1_00X.json
3) Config resolvida (gerada por run): runs/<run_id>/resolved_config.json

Macro-tarefas (DEV_F1_001 .. DEV_F1_005)

DEV_F1_001 — Bootstrap de specs e schema
Entregas:
- specs/frozen/frozen_v1.json
- specs/schema/experiment_schema_v1.json
- specs/experiments/EXP_F1_001.json
Gates:
- JSONs válidos e consistentes

DEV_F1_002 — Resolver/merge + auditoria por run
Entregas:
- deep_merge determinístico
- runs/<run_id>/resolved_config.json
- runs/<run_id>/run_report.json (OVERALL)
Gates:
- resolved_config e report sempre gerados

DEV_F1_003 — Data adapter (somente leitura)
Entregas:
- loader por data/ro_links
- validação de isolamento (não escrever fora do lab)
Gates:
- smoke run sem escrita fora do lab

DEV_F1_004 — Simulator engine (dry-run)
Entregas:
- loop diário 2023-01..2026-01-22
- ordem do dia: risco→SELL/REDUCE→BUY semanal (100% caixa)
- settlement D+2
- quarentena parametrizável
Gates:
- run completa sem exceções
- estado final persistido

DEV_F1_005 — Outputs e visuais
Entregas:
- carteira: equity, drawdown, caixa, turnover
- tickers: peso/valor/eventos/quarentena
- exposição por grupos
- benchmarks: IBOV + CDI (índice 100 jan/23; evolução mensal)
Gates:
- outputs gerados conforme checklist

Regra de controle
Entre experimentos, o único arquivo editado é o delta JSON em specs/experiments.
