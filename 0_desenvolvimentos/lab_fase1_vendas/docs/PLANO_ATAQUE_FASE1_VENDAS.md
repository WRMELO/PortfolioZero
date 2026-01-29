PLANO DE ATAQUE EM GRANDES LINHAS
Fase 1 — Experimentos de Vendas (PortfolioZero, dry-run)

Objetivo
Selecionar o melhor conjunto de critérios de venda (SELL/REDUCE) maximizando o dinheiro final na data 2026-01-22, seguindo religiosamente as regras do dry-run e os limites de risco combinados do experimento.

Princípios congelados do laboratório
1) Isolamento total: o laboratório escreve somente em /home/wilson/PortfolioZero/0_desenvolvimentos.
2) Dados canônicos: apenas leitura (referências via symlinks em 0_desenvolvimentos/data/ro_links).
3) Um JSON por experimento: é o único artefato que muda entre execuções.
4) BUY congelado: compra semanal simples e homogênea; usa 100% do caixa disponível no dia de compra.
5) História para estimativas: ano completo de 2022 como base de warmup/estimativas de indicadores.
6) Start: primeira compra no primeiro leilão/pregão de 2023, carteira inicial de 10 tickers com R$ 500.000 (R$ 50.000 por ticker).
7) Quarentena: ticker zerado entra em quarentena por 10 sessões (definição operacional a ser testada como parte dos conjuntos).

Plano de execução (macro-etapas)

Etapa 1 — Preparação do laboratório (isolamento e estrutura)
- Confirmar estrutura de diretórios do lab e logs.
- Garantir que a execução não escreve fora de 0_desenvolvimentos.
- Preparar pastas padrão de runs, outputs e tabelas.

Etapa 2 — Contrato de configuração (JSON único)
- Definir schema mínimo do JSON de experimento:
  - Identificação do experimento (experiment_id, run_id)
  - Datas (warmup_start, start_date, end_date)
  - Capital inicial e carteira inicial
  - Regra BUY semanal (dia fixo e distribuição do caixa)
  - Política SELL/REDUCE (ações, prioridades, parâmetros rolling/expanding/fixos)
  - Quarentena (duração e regra de veto)
  - Marcadores de risco e limites (gatilhos e combinações)
  - Outputs esperados (figuras/tabelas)

Etapa 3 — Runner determinístico (simulação diária)
- Carregar dataset e universo.
- Loop diário de start_date até end_date.
- Ordem operacional por dia:
  1) Atualizar métricas e risco (conforme JSON)
  2) Avaliar gatilhos -> gerar decisões de SELL/REDUCE
  3) Aplicar ordens respeitando o modelo de liquidação do dry-run
  4) Se for dia de BUY semanal, executar BUY usando 100% do caixa disponível, respeitando travas do experimento
- Persistir outputs intermediários e finais por run.

Etapa 4 — Outputs mínimos obrigatórios por run
- Carteira:
  - Equity curve, retorno acumulado, retorno diário
  - Drawdown (atual e máximo)
  - Caixa ao longo do tempo
  - Turnover e número de ordens
  - Exposição por grupos (operando/supervised/candidates e/ou grupos definidos)
- Por ticker:
  - Peso e valor ao longo do tempo
  - Contribuição de retorno
  - Eventos de SELL/REDUCE/ZERO e período em quarentena
- Benchmarks:
  - IBOV (do dataset) como série comparativa
  - CDI como índice 100 em jan/23 e evolução mensal
- Risco:
  - Um marcador principal + auxiliares (definidos no JSON)

Etapa 5 — Execução iterativa (um conjunto por vez)
- Rodar Conjunto 1 (detalhado) e produzir:
  - Resultados (dinheiro final) e principais curvas/figuras
  - Diagnóstico de efeitos de cada variável (gatilhos, prioridades, quarentena, rolling)
- Ajustar apenas o JSON para Conjunto 2, mantendo o runner e pipeline idênticos.
- Repetir até Conjunto 5.

Etapa 6 — Seleção do vencedor
- Critério final: dinheiro final em 2026-01-22.
- Métricas de apoio (não decisórias): max drawdown, volatilidade, turnover, tempo em caixa, etc.
- Registrar lições aprendidas e recomendações para a Fase 2 (compras).

Checklist de controle (para acompanhamento)
- E1 Estrutura e isolamento OK
- E2 Schema do JSON definido e validado
- E3 Runner determinístico implementado e reprodutível
- E4 Outputs mínimos gerados e validados
- E5 Conjunto 1 executado e analisado
- E6 Conjuntos 2–5 executados e analisados
- E7 Critério final aplicado e vencedor selecionado
