# PORTIFOLIOZERO — Guia Mestre Congelado (Operação + Experimentos)

Versão: 1.0  
Data: 2026-01-28  
Estado: CONGELADO (mudanças somente via nova versão deste mesmo arquivo)

Este documento é o único guia normativo do PORTIFOLIOZERO. Ele consolida e substitui, para efeito de referência única, o conteúdo essencial dos antigos Plano V1, Plano V2 e do Acordo Operacional Definitivo (Dry-Run). Os documentos anteriores permanecem como histórico, mas não devem ser usados para “interpretar” regras fora do que está escrito aqui.

---

## 1. Objetivo e filosofia (inalteráveis)

O objetivo do sistema é operar uma carteira de ações de forma disciplinada, auditável e repetível, priorizando preservação de capital. O princípio dominante é: melhor não perder do que ganhar muito.

O projeto será desenvolvido em duas fases de experimentos:

- Fase 1: escolher o melhor mecanismo de venda (sem ML de D+1/D+3/D+5 e sem RL), mantendo uma regra semanal de compra simples e imutável.
- Fase 2: com o mecanismo de venda escolhido e congelado, desenvolver um mecanismo eficiente de compra.

O critério de sucesso de cada fase é o melhor valor final na última data disponível do histórico usado no teste. Nesta etapa de laboratório, não será criada rotina de atualização por Yahoo Finance; os testes usarão exclusivamente o histórico completo que já existe em arquivo no projeto.

---

## 2. Papéis e forma de trabalho (Owner e Planejador)

Owner:
- Opera o sistema (no dry-run e, futuramente, no modo real).
- Mantém o estado de posições e caixa.
- Executa as rotinas de experimento e valida os resultados.

Planejador:
- Define contratos operacionais, regras e critérios de teste.
- Especifica experimentos de forma auditável (spec JSON + runner PY).
- Não “supõe” fatos que podem ser verificados em artefatos. A fonte de verdade é o repositório e os parquets.

Agente/Editor:
- Implementa mudanças no repositório sob instrução do Planejador e validação do Owner.

---

## 3. Definições operacionais (tempo, estado e preços)

3.1. Dia de decisão (D)
D é sempre a manhã de um dia útil.

3.2. Preço oficial para decisões
Para as decisões e valuation no dry-run, o preço oficial é sempre o Close do último dia útil conhecido (Close de D-1).
- Segunda-feira de manhã usa Close da sexta-feira.
- Feriados e fins de semana usam Close do último dia útil anterior.

3.3. Fonte de preços
A fonte-alvo do projeto é Yahoo Finance, porém, nesta etapa de experimento, não haverá aquisição de novos valores: os testes usarão somente os parquets históricos existentes.

3.4. Estado de decisão (snapshot)
O estado considerado para decisão em D é o estado existente na manhã de D: quantidade de ativos + caixa disponível em D. Compra nunca pode usar “caixa futuro”.

3.5. Liquidação (modelo operacional do dry-run)
- Venda: baixa imediata na quantidade (estado lógico). O caixa correspondente entra em D+2 pelo valor quantidade × Close(D-1), líquido de custo.
- Compra: executada com o caixa disponível em D, pelo Close(D-1), respeitando custo por ordem.

---

## 4. Universo do sistema (o que “vale” para operar)

4.1. Regra de ouro
Instrumentos elegíveis são definidos pelo Universe Package vigente. O sistema não opera instrumentos fora do universo.

4.2. Estrutura em camadas (definição do projeto)
- UNIVERSE_CANDIDATES: pré-lista (pool maior) para seleção.
- UNIVERSE_SUPERVISED: subconjunto do candidates, considerado “operável” e usado como base do sistema de decisão.
- CARTEIRA_OPERANDO: subconjunto do supervised, com 10 posições alvo.

Observação: se, em algum momento, um ativo da carteira deixar de pertencer ao supervised vigente, ele passa a ser elegível para saída conforme a política de venda.

4.3. Evidência atual do repositório (inventário de parquets)
Conforme inventário gerado em: 2026-01-28 19:58:06 UTC

- Candidates (canon): data/universe/UNIVERSE_CANDIDATES.parquet
  - Linhas: 68
  - Mtime: 2025-12-02 20:22:40 UTC
  - Schema (13 colunas): ticker, tipo_instrumento, setor, date_first, date_last, history_days, trading_days_ratio_252d, avg_volume_21d_brl, avg_price_recent_brl, last_price, annualized_vol_60d, volatility_class, liquidity_class

- Supervised (existem múltiplas cópias versionadas; o “canon” para consumo operacional deve ser o mais recente):
  - Latest (canon sugerido): data/universe/supervised_TASK_A_012/UNIVERSE_SUPERVISED.parquet (mtime 2026-01-23 10:09:57 UTC, linhas 30)
  - Outras cópias:
  - data/universe/UNIVERSE_SUPERVISED.parquet (mtime 2025-12-02 20:53:07 UTC, linhas 30)
  - data/universe/supervised_TASK_A_010/UNIVERSE_SUPERVISED.parquet (mtime 2026-01-22 14:23:37 UTC, linhas 30)

4.4. Decomposição numérica (sem suposições)
Com os números atuais:
- Candidates = 68
- Supervised = 30
- Carteira operando alvo = 10 (por definição, dentro do supervised)

Logo, a decomposição por “camadas úteis” fica:
- 10 “operando” (dentro do supervised)
- 20 “supervised disponíveis” (30 - 10), para rotação/alternativas
- 38 “candidates fora do supervised” (68 - 30), para observação/possível promoção futura

Esta decomposição é coerente com a ideia de camadas e evita o erro de tratar “10, 30 e 68” como conjuntos independentes.

---

## 5. Diretório de laboratório (para não contaminar o sistema atual)

Para os experimentos descritos neste guia, será criado um único diretório novo sob a raiz do repositório, que concentrará tudo o que for laboratório:

- lab_experimentos/

Regras:
- Nenhum arquivo existente do sistema operacional atual deve ser alterado diretamente por experimentos.
- Todo experimento deve gerar saídas somente dentro de lab_experimentos/.
- Cada experimento terá:
  - um spec JSON (contrato do experimento),
  - um runner Python (execução),
  - e um diretório de outputs com logs e parquets/resultados.

---

## 6. Parquets de preços (histórico disponível para os testes)

O histórico de preços está armazenado em parquets por ticker (grupo de prices). Evidência do inventário:

- Count de parquets de preços: 121
- Range de datas de referência (grupo): ['2022-01-03', '2026-01-22']

Os experimentos trabalharão exclusivamente com esse histórico existente, sem atualização externa nesta etapa.

---

## 7. Carteira inicial (D0) para os testes

7.1. D0
D0 é a data de compra inicial da carteira para o experimento. D0 deve ser escolhido dentro do histórico, considerando um período mínimo de “warmup” necessário para calcular os indicadores do critério de venda.

7.2. Seleção dos 10 tickers iniciais (regra conservadora)
A carteira inicial será formada escolhendo 10 tickers do UNIVERSE_SUPERVISED vigente no D0, segundo ranking conservador (ordem de prioridade):

1) Menor drawdown no lookback (janela a ser parametrizada no experimento);
2) Menor volatilidade no lookback;
3) Melhor retorno no lookback (como desempate, não como objetivo primário).

7.3. Alocação inicial
Alocação equal-weight:
- Capital de referência: R$ 500.000,00
- 10 posições: R$ 50.000,00 por ativo (antes de custos)
- Quantidade: floor( (valor_por_ativo - custo) / Close(D0-1) )

O objetivo aqui é reduzir concentração e simplificar auditoria.

---

## 8. Modelo de custos (regra de mercado, conservadora para testes)

O modelo de custos tem dois componentes:

8.1. Custos explícitos de bolsa (B3)
A B3 cobra taxa de negociação, liquidação e registro, incidindo sobre o valor financeiro da operação e cobradas de comprador e vendedor. Para pessoa física, a ordem de grandeza total é 0,0390% por lado (negociação 0,0100% + liquidação 0,0275% + registro 0,0015%). Fonte: tabela pública de tarifas da B3 (ações e fundos à vista).  

8.2. Custos implícitos (spread/slippage/impacto) e custos do intermediário (banco/corretora)
Mesmo quando a corretagem é “zero”, há custos implícitos de execução. Para testes conservadores (favorecer estratégias menos giradoras), adotamos um buffer.

8.3. Default congelado para experimentos (até recalibração)
Aplicar em BUY e SELL:
- fee_percent_per_order = 0,15% do notional por ordem (inclui a taxa explícita e buffer conservador)
- fee_fixed_brl_per_order = R$ 10,00 por ordem

Este default é propositalmente conservador. Qualquer ajuste só entra após rodada de testes comparativos.

---

## 9. Programa de experimentos

9.1. Fase 1 — Seleção do mecanismo de venda
Objetivo: escolher o mecanismo de venda que produz o melhor valor final (última data do histórico), mantendo compra semanal simples e imutável.

Regras:
- Não usar ML preditivo D+1/D+3/D+5.
- Não usar RL.
- O mecanismo de compra semanal não muda entre experimentos (para isolar o efeito do critério de venda).

Entregas da fase:
- ranking dos mecanismos de venda testados,
- métricas de auditoria (valor final, drawdown, volatilidade, turnover, número de trades),
- decisão do mecanismo vencedor (congelamento para fase 2).

9.2. Fase 2 — Melhoria do mecanismo de compra
Objetivo: com o mecanismo de venda vencedor congelado, buscar o mecanismo de compra semanal que produz o melhor valor final, com disciplina e risco controlado.

---

## 10. Aviso normativo (substitui “pendências” de risco e weekly)

Os seguintes pontos serão decididos por uma série de testes históricos, com evidência quantitativa e logs reprodutíveis. Enquanto não houver decisão final, eles não entram como regras fixas do sistema operacional:

- Conjunto de limites do Risk Package e os thresholds numéricos para remover “null”.
- Política de REDUCE (quando ativar, quanto reduzir, em quantas etapas, e como reverter).
- Detalhamento completo do weekly BUY/rebalance (ranking, alocação, vetos e modo defensivo).

---

## 11. Controle de mudanças

Este guia é congelado. Qualquer alteração de regra só pode ocorrer por criação de uma nova versão (1.1, 1.2, …), sempre com:
- justificativa,
- impacto esperado,
- e evidência mínima (resultado de experimento ou necessidade operacional).

Fim do documento.
