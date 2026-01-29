PORTIFOLIOZERO — Fase 1 (Experimentos de Venda) — Plano de Ataque

Objetivo
Escolher o melhor mecanismo de venda, mantendo a compra semanal simples e imutável, maximizando o valor final na última data do histórico (22/01/2026).

Princípios operacionais do dry-run
- Preço oficial: Close(D-1).
- Venda: baixa quantidade em D e caixa entra em D+2 líquido de custos.
- Compra: executa em D somente com caixa disponível em D.
- Sem atualização externa de preços nesta fase: usar apenas parquets existentes.

Arquitetura do laboratório (isolamento)
- Tudo roda sob 0_desenvolvimentos/lab_experimentos/fase1_vendas/
- Não alterar tarefas/artefatos do pipeline operacional já PASS.

Forma de teste (um por vez)
- Runner fixo: runners/run_fase1_vendas.py
- Spec fixo: configs/SPEC_FROZEN_MIRROR_V1.json
- Único arquivo variável por rodada: configs/ACTIVE_RULESET.json

Rodadas
1) RULESET_01 (detalhado): baseline conservador com REDUCE vs ZERO + prioridades + rolling windows.
2) RULESET_02
3) RULESET_03
4) RULESET_04
5) RULESET_05

Outputs esperados por rodada (em outputs/<run_id>/)
- Métricas finais: valor final, max drawdown, volatilidade, turnover, número de trades.
- Curvas: carteira vs IBOV (e CDI indexado, quando disponível).
- Visuais por ticker: preço, drawdown, eventos BUY/SELL/REDUCE/ZERO.
- Log de ordens e caixa (incluindo agenda D+2).

Critério de sucesso
Maior valor final em 22/01/2026, seguindo religiosamente o ruleset ao longo do período.
