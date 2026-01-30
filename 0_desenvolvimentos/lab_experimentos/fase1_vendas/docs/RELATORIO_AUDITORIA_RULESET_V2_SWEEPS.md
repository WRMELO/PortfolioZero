# Relatorio: Auditoria e Sweeps do Ruleset (C21, C22, C23)

## Contexto e objetivo
Este relatorio documenta o que foi implementado e observado nas celulas **21, 22 e 23** do notebook `LV_F1_PROP2_Q1_2023_INSPECAO.ipynb`. O objetivo foi:

- validar a simulacao completa (v2) com auditoria detalhada;
- testar variacoes de parametros dos stops de ticker (ruleset) contra o IBOV e baseline;
- testar variacoes das regras de freio do IBOV (base) para tentar garantir que a carteira **nunca** tenha drawdown maior que o IBOV, ou que, se ocorrer, seja **corrigido em D+1**.

O periodo analisado vai do primeiro leilao de 2023 ate **22/01/2026**, com dados de precos e IBOV (local quando disponivel, com fallback via `yfinance`).

---

## Celula 21 (v2 completo): simulacao com auditoria detalhada

### O que foi implementado
A Celula 21 executa a simulacao completa com as regras vigentes e gera uma trilha de auditoria detalhada. Principais pontos:

- **Estado inicial**: usa `qty_series` (compra inicial D0) e `cash_left`.
- **Processo diario** (para cada data da amostra):
  - liquida cash de vendas com **D+2**;
  - aplica **freio do IBOV** (reducoes uniformes em todos os tickers quando ha sinal);
  - aplica **stops de ticker** (soft/hard), com reducao ou zeragem;
  - respeita **quarentena** apos zerar (hard stop);
  - executa **compras semanais na segunda-feira** para equalizar a carteira.
- **Regras do IBOV (base)**:
  - **SOFT** quando `ibov_dd20 >= 0.04`, reduz 15%;
  - **HARD** quando `ibov_dd60 >= 0.08`, reduz 30%.
- **Stops de ticker (base)**:
  - **soft** se `dd20 >= 0.04` ou `vol_ratio >= 1.40`;
  - **hard** se `dd60 >= 0.10` e `vol_ratio >= 1.60`;
  - soft vende 25% da posicao, hard zera.
- **Invariantes**:
  - `cash_eod >= 0`;
  - `pos_eod >= 0`.

### Auditoria e logs gerados
Saidas salvas em `outputs/`:

- `day_audit.csv`: snapshot diario (cash, equity, sinais IBOV, posicoes etc).
- `ticker_day_audit.csv`: status por ticker/dia (posicoes, sinais, decisoes, execucao).
- `event_log.csv`: eventos com **SIGNAL**, **ORDER** e **SKIP**, incluindo motivo.

### Visualizacoes geradas
Graficos de:

- **Base100**: baseline vs regras vs IBOV;
- **cash ao longo do tempo**;
- **numero de posicoes**;
- **drawdown 60d** carteira vs IBOV.

### Observacao central
Mesmo com regras ativas, a curva **com regras** segue abaixo do baseline por longos periodos, com quedas frequentes, indicando que:

- as reducoes estao acontecendo sem entregar protecao superior ao IBOV;
- o baseline continua mais consistente.

---

## Celula 22 (sweep ruleset de ticker)

### Objetivo
Automatizar testes variando parametros de **stops de ticker** e comparar a carteira com regras contra:

- **Baseline**;
- **IBOV**;

com a meta: **nao permitir drawdown maior que o IBOV** ou, se ocorrer, **corrigir em D+1**.

### O que foi implementado
Um grid search simples com os seguintes parametros:

- `soft_dd20`: [0.03, 0.04, 0.05]
- `hard_dd60`: [0.08, 0.10, 0.12]
- `soft_vol`: [1.30, 1.40, 1.50]
- `hard_vol`: [1.50, 1.60, 1.70]
- `soft_reduce`: [0.25, 0.40, 0.50]

Cada combinacao:

1. simula toda a carteira;
2. calcula **drawdown** da carteira e do IBOV;
3. marca **violacoes** quando a carteira fica pior que o IBOV e **continua pior no dia seguinte**.

### Resultado observado
Nenhuma configuracao zerou as violacoes. Exemplo (melhor aproximacao):

- `violations` em torno de **651** dias;
- `max_excess_dd` ~ **0.34**, muito acima do IBOV;
- `port_max_dd` ~ **0.44** contra **0.14** do IBOV.

### Conclusao
Somente ajustar stops de ticker **nao** foi suficiente para garantir protecao consistente contra o IBOV.

---

## Celula 23 (sweep IBOV-base)

### Objetivo
Testar **apenas** variacoes do freio do IBOV como regra base (macro), antes de reintroduzir stops de ticker.

### O que foi implementado
Grid search com parametros do IBOV:

- `ibov_dd20`: [0.03, 0.04, 0.05]
- `ibov_dd60`: [0.06, 0.08, 0.10]
- `ibov_soft_reduce`: [0.10, 0.15, 0.20]
- `ibov_hard_reduce`: [0.25, 0.30, 0.40]

Com **stops de ticker desativados** (`use_ticker_stops = False`) para isolar o efeito.

### Resultado observado
Nenhuma configuracao zerou as violacoes. Melhor aproximacao:

- `violations` = **489**
- `exceed_days` = **525**
- `max_excess_dd` ~ **0.292**
- `port_max_dd` ~ **0.410**
- `ibov_max_dd` ~ **0.142**
- `final_value` ~ **677k**

### Conclusao
Mesmo calibrando o freio do IBOV, a carteira ainda tem drawdowns piores que o indice em muitos momentos.

---

## Diagnostico consolidado

1. **Baseline continua superior**: nao ha evidencias de que os stops atuais protegem a carteira melhor que ficar comprado.
2. **Regras reativas nao bastam**: tanto stops de ticker quanto freio IBOV isolado falharam em manter o drawdown abaixo do IBOV.
3. **Excesso de quedas**: a carteira com regras apresenta drawdowns frequentes e profundos.

---

## Proximos passos sugeridos

1. **Aprimorar IBOV-base** com reducoes mais agressivas:
   - elevar `ibov_soft_reduce` e `ibov_hard_reduce` (ex.: 0.40/0.70);
   - antecipar thresholds (ex.: 0.02/0.05).
2. **Reintroduzir stops de ticker** apenas depois do IBOV-base estabilizado.
3. **Adicionar metricas de recuperacao D+1** mais estritas:
   - penalizar qualquer dia com drawdown acima do IBOV, mesmo se reverter.
4. **Explorar regras de entrada** (nao apenas saida) para evitar exposicao excessiva em regimes de queda.

---

## Arquivos relacionados

- Notebook principal: `notebooks/LV_F1_PROP2_Q1_2023_INSPECAO.ipynb`
- Logs gerados: `outputs/.../day_audit.csv`, `ticker_day_audit.csv`, `event_log.csv`
- Este relatorio: `docs/RELATORIO_AUDITORIA_RULESET_V2_SWEEPS.md`

