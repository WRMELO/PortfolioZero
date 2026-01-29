DECISAO RULESET VENCEDOR — Fase 1 (Vendas)

Regras de decisao (criterio deterministico)

- Primary: max(final_value)
- Tie-breakers (em ordem):
  - min(max_drawdown)
  - min(portfolio_var_95_1d_252d) se existir coluna
  - min(n_zero)
  - min(n_orders)

Tabela (summary_rulesets.csv)

| ruleset_id | run_id | output_path | final_value | max_drawdown | n_orders | n_reduce | n_zero | n_quarantine_events |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SELL_RULESET_01 | SELL_RULESET_01 | 0_desenvolvimentos/lab_experimentos/fase1_vendas/outputs/sweep_5_rulesets/SELL_RULESET_01 | 7.850409018797429e+21 | 0.0424983964853887 | 1373 | 2036 | 319 | 319 |
| SELL_RULESET_02 | SELL_RULESET_02 | 0_desenvolvimentos/lab_experimentos/fase1_vendas/outputs/sweep_5_rulesets/SELL_RULESET_02 | 630842.033513607 | 0.2510712720781882 | 9 | 0 | 0 | 0 |
| SELL_RULESET_03 | SELL_RULESET_03 | 0_desenvolvimentos/lab_experimentos/fase1_vendas/outputs/sweep_5_rulesets/SELL_RULESET_03 | 97813977408.29524 | 0.1015408386470274 | 261 | 178 | 68 | 68 |
| SELL_RULESET_04 | SELL_RULESET_04 | 0_desenvolvimentos/lab_experimentos/fase1_vendas/outputs/sweep_5_rulesets/SELL_RULESET_04 | 2.256939935855919e+16 | 0.076142403548573 | 888 | 572 | 230 | 230 |
| SELL_RULESET_05 | SELL_RULESET_05 | 0_desenvolvimentos/lab_experimentos/fase1_vendas/outputs/sweep_5_rulesets/SELL_RULESET_05 | 53182921272.9321 | 0.1090162195530397 | 107 | 0 | 68 | 68 |

Ruleset vencedor

- ruleset_id: SELL_RULESET_01
- final_value: 7.850409018797429e+21
- max_drawdown: 0.0424983964853887
- n_orders: 1373
- n_reduce: 2036
- n_zero: 319
- n_quarantine_events: 319

Observacao
BUY semanal permanece congelado e identico em todos os experimentos.
