# PORTIFOLIOZERO — Guia Único Congelado (Plano V1 + Plano V2 + Acordo Operacional Dry-Run)

Versão: 1.0
Data: 2026-01-28
Status: Congelado como SSOT (Single Source of Truth) de regras, operação e contratos do projeto.

Este documento substitui, para fins operacionais, a consulta simultânea a múltiplos arquivos de plano/acordo. Ele consolida:
1. A filosofia e limites de risco (origem no Plano V1 e nas discussões posteriores).
2. O desenho do sistema e seus “4 produtos” (Plano V2).
3. O acordo operacional diário do Dry-Run (como o Owner opera na prática, com fechamento D-1 e liquidação D+2).
4. O estado atual implementado no repositório (o que existe de fato, agora).

Regra de mudança: qualquer alteração só é válida quando registrada aqui como uma nova versão (1.1, 1.2, etc.), com data e resumo de mudanças.

---

## 1. Ponto de situação (estado atual do projeto)

Repositório (SSOT): /home/wilson/PortfolioZero  
Nome do projeto: PORTIFOLIOZERO

Estado atual: o sistema está operando em Dry-Run com rotina diária “sell-only” (venda/hold), com rastreabilidade via Agno (TASK specs) e auditoria em planning/runs e planning/reports.

Inventário de parquets (evidência de estado):
- Inventário gerado em: 2026-01-28 19:58:06 UTC
- Preços em data/raw/market/prices: 121 parquets
  - Ações “_SA” (não-11, não-34): 88
  - BDRs (sufixo 34): 26
  - ETFs/Units (sufixo 11): 7
  - Janela de datas de referência nos preços: 2022-01-03 a 2026-01-22
- Universo:
  - data/universe/UNIVERSE_CANDIDATES.parquet: 68 tickers (rows)
  - data/universe/UNIVERSE_SUPERVISED.parquet: 30 tickers (rows)
- Posições:
  - data/portfolio/incoming/PORTFOLIO_POSITIONS_SOURCE.parquet: 10 linhas (fonte manual do Owner)
  - data/portfolio/PORTFOLIO_POSITIONS_REAL.parquet: arquivo canônico usado pelo pipeline

Observação operacional importante:
- Existe preço armazenado para BDRs e ETFs/Units, mas o que “vale” para o sistema é o que estiver no universo (UNIVERSE_*). Se um instrumento não estiver no universo vigente, ele é ignorado pelo decisor, mesmo que exista preço.

---

## 2. Forma de trabalhar entre Owner e Planejador (governança de execução)

Papéis:
- Owner (Wilson): define as regras de negócio, escolhe o grau de conservadorismo, executa o pipeline no dia a dia e toma a decisão final de operar (no modo real, quando existir).
- Planejador (este chat): consolida regras e contratos, transforma regras em especificações executáveis (TASK specs) e garante consistência do sistema.
- Agente (Cursor): implementa código e ajustes no repositório conforme orientação do Planejador, sem “reinventar” regras.
- Executor (Agno runner): executa tarefas versionadas, gerando evidências (runs) e artefatos (parquets, jsons, reports).

Regras de colaboração:
1. Toda mudança relevante deve aparecer como:
   - um arquivo versionado (TASK spec, config, doc), e
   - uma evidência de run (planning/runs/...), e
   - um artefato gerado (data/...).
2. Se algo não deixa rastro auditável, não faz parte do sistema.
3. Owner aprova mudanças de regra. O Planejador não “inventa” regra nova sem decisão do Owner.

---

## 3. Filosofia e invariantes de risco (conservadorismo como prioridade)

Filosofia do sistema:
- Melhor não perder do que ganhar muito.
- Preservação de capital e controle de drawdown têm prioridade sobre maximização agressiva de retorno.

Invariantes (sempre verdade, a menos de versão nova deste documento):
1. Long-only (sem short e sem alavancagem).
2. Sistema fechado: compra apenas com caixa disponível (não compra com “caixa futuro”).
3. Cadência: venda pode ser diária; compra/rebalance é semanal (quando implementado).
4. Operação manual: não há integração com corretora; o Owner opera via apps de bancos.
5. Fonte de preços base: Yahoo Finance, com preço oficial definido como Close (ver seção 4).

Objetivo de performance (métrica de avaliação, não de decisão intradiária):
- Piso: CDI + 3% a.a.
- Meta: CDI + 8% a.a.

---

## 4. Regime operacional do Dry-Run (calendário, preços e liquidação)

Tempo do sistema:
- Execução em dias úteis, pela manhã.
- O “dia D” usa o fechamento do último pregão (D-1).
  - Fechamento de sexta-feira é analisado na segunda-feira de manhã.
  - Fins de semana e feriados usam o último fechamento conhecido.

Preço oficial para valuation e regras:
- Sempre Close do Yahoo Finance.
- Adj Close pode existir como dado auxiliar para estudos históricos, mas não define o preço oficial da decisão diária.

Liquidação e caixa (modelo operacional no Dry-Run):
- Venda:
  - baixa imediata na quantidade (posição reduzida/zerada no dia da decisão);
  - caixa entra em D+2 com valor = quantidade vendida × preço Close(D-1).
- Compra:
  - usa somente o caixa disponível no dia D (não usa recebíveis futuros);
  - quantidade comprada = floor(caixa_disponível / preço Close(D-1)) respeitando limites e custos.

Interpretação prática:
- O caixa funciona como uma conta corrente com:
  - saldo atual (disponível), e
  - recebíveis previstos (vendas em D+2).

---

## 5. Contratos de dados: arquivos, papéis e ordem de atualização

### 5.1 Os 4 produtos (artefatos) do sistema (Plano V2)

1. Market Data Package  
   Preços diários (parquet por ticker) e validações mínimas.
2. Universe Package  
   Universe candidates + universe supervised (e rastreabilidade de critérios).
3. Risk Package (curto prazo)  
   Artefato de risco operacional (contrato estável) que alimenta gatilhos e modo defensivo.
4. Decision Package  
   Produto final: ações recomendadas (sell/reduce/hold/buy quando existir), justificativas e travas.

### 5.2 Arquivos essenciais (caminhos e responsabilidade)

- Market prices (raw):  
  data/raw/market/prices/{TICKER}_SA.parquet
- Universe:  
  data/universe/UNIVERSE_CANDIDATES.parquet  
  data/universe/UNIVERSE_SUPERVISED.parquet  
  data/universe/supervised_TASK_A_012/ (output gerado pela TASK_A_012)
- Posições:  
  Entrada manual: data/portfolio/incoming/PORTFOLIO_POSITIONS_SOURCE.parquet  
  Canônico: data/portfolio/PORTFOLIO_POSITIONS_REAL.parquet
- Snapshot:  
  data/portfolio/snapshots/PORTFOLIO_SNAPSHOT_V1.json
- Risk Package:  
  data/risk/RISK_PACKAGE_V0.json
- Decision Package:  
  data/decision/DECISION_PACKAGE_V1.json

### 5.3 Procedimento operacional definitivo para PORTFOLIO_POSITIONS_SOURCE.parquet

Premissa:
- Não existe extrato/relatório automático de corretora (nem API) no Dry-Run.
- A “verdade” de posições é o que o Owner registra manualmente (quantidades) e o sistema avalia via preço Close(D-1).

Quando o arquivo é produzido/atualizado:
- No início do Dry-Run: o Owner cria o arquivo uma vez, refletindo a carteira inicial.
- Em qualquer dia em que o Owner executar uma operação (compra/venda): o Owner atualiza o arquivo na manhã seguinte antes de rodar o pipeline.
- Em dias sem mudança de posições: o arquivo permanece igual (idempotência).

Como o arquivo é produzido (manual):
- O Owner edita o conteúdo (quantidades e, quando aplicável, preço médio) e salva/atualiza o parquet no caminho:
  data/portfolio/incoming/PORTFOLIO_POSITIONS_SOURCE.parquet

Formato mínimo (colunas obrigatórias e tipos aceitos):
- ticker: string (ex.: PETR4.SA, VALE3.SA)
- quantity: número (aceita int ou float; o pipeline normaliza)
- avg_price: float (pode ser 0.0 se desconhecido no Dry-Run)

Regra de ingestão:
- Sempre que PORTFOLIO_POSITIONS_SOURCE.parquet for alterado, deve-se rodar a ingestão para atualizar o canônico:
  TASK_A_018 (ver seção 6)

---

## 6. O que está implementado e “vale” hoje (TASKs estáveis)

Rotina diária (execução diária):
- TASK_D_002 — Market Data Daily Idempotent v1 (atualiza preços; janela de refresh)
- TASK_D_003 — Audit Market Prices Post Daily (auditoria pós-update)
- TASK_A_012 — Universe E2E Strict v1 (gera supervised_TASK_A_012)
- TASK_A_013 — Risk Package v0 (gera RISK_PACKAGE_V0; ainda sem limiares fechados)
- TASK_A_014 — Daily Decision SELL-ONLY v1 (decisão diária sell-only)
- TASK_D_004 — Daily E2E SELL-ONLY v1 (encadeamento)
- TASK_D_005 — Daily E2E SELL-ONLY com Snapshot V1 (encadeamento + snapshot)

Rotina esporádica (quando necessário):
- TASK_A_018 — Ingestão oficial de posições reais (SOURCE.parquet → REAL.parquet, com archive/manifest/report)
- TASK_A_017 — Build Portfolio Snapshot v1 from Parquet (REAL.parquet → SNAPSHOT_V1.json)

Rotina semanal (a definir; não implementado):
- BUY / rebalance semanal (Plano V2)

---

## 7. Custos operacionais no Dry-Run (regra conservadora)

Objetivo:
- Não subestimar fricções. O sistema deve “sofrer” um custo conservador por ordem no backtest e no dry-run.

Regra adotada (congelada para o Dry-Run, até revisão):
- Custo fixo por ordem (BRL): 10.00
- Custo percentual por ordem (sobre o financeiro): 0.10% (0.0010)

Aplicação:
- Aplica em BUY e em SELL.
- O custo total de cada ordem é: custo_fixo + (custo_percentual × financeiro_da_ordem).

Nota:
- Essa regra é uma aproximação conservadora que engloba emolumentos, taxas e slippage operacional. Antes do modo real, este bloco deve ser recalibrado com base nas condições reais do canal de operação do Owner (banco/app).

---

## 8. Política de atualização diária: verificações mínimas antes do risco e da decisão

Objetivo:
- Garantir que a análise de risco e a decisão diária usem sempre dados do último fechamento disponível, com rastreabilidade e sem ambiguidade.

Ordem lógica mínima (manhã do dia D):
1. Se houve mudança de posições desde o último snapshot: atualizar PORTFOLIO_POSITIONS_SOURCE.parquet e rodar TASK_A_018.
2. Rodar TASK_D_002 (atualizar preços com política idempotente e janela de refresh).
3. Rodar TASK_D_003 (auditar pós-update; falhar se houver inconsistências críticas).
4. Rodar TASK_A_012 (regerar universe supervised, se aplicável).
5. Rodar TASK_A_013 (gerar Risk Package v0).
6. Rodar TASK_A_017 (regerar snapshot se necessário).
7. Rodar TASK_A_014 ou TASK_D_005 (gerar decisão diária).

Verificações mínimas (gates conceituais):
- Cobertura: todo ticker do universo supervisionado e toda posição atual devem ter preço disponível.
- Data: última data do preço deve ser o último pregão (D-1).
- Preço oficial: Close deve existir e ser > 0.
- Integridade: artefatos publicados devem ter hash/manifest coerente com os arquivos no disco.

---

## 9. Regras de risco: SELL, REDUCE, HOLD (e remoção de null no Risk Package)

Estado atual (agora):
- O sistema está operacional com SELL-ONLY.
- REDUCE ainda não está ativado porque o Risk Package v0 não tem limiares numéricos “travados” (campos podem estar null).

Regra de decisão vigente (SELL-ONLY):
- Se ticker fora do universo supervisionado: SELL (saída total).
- Se ticker no universo supervisionado: HOLD (sem redução, por enquanto).

Como REDUCE será ativado (definição sem ambiguidade, com parâmetros ainda a escolher):
1. Será criado um conjunto de limiares explícitos (Risk Policy v1) para:
   - risco do ativo (DD/vol/VaR/ES/liquidez), e
   - risco da carteira (MaxDD/VaR/ES/concentração/correlação/modo defensivo).
2. A partir dessa política, a TASK_A_013 deixará de publicar null e passará a preencher:
   - limites (hard/soft),
   - flags de violação,
   - recomendação de ação (HOLD/REDUCE/SELL).
3. REDUCE ocorrerá quando:
   - o ativo permanecer elegível (no universo supervisionado), mas violar um limite “soft” (não-exit).
4. SELL ocorrerá quando:
   - o ativo estiver fora do universo, ou violar um limite “hard”.

Parâmetros de REDUCE (a decidir por testes históricos; não executa enquanto não houver valores):
- reduce_pct (percentual de redução por evento)
- cooldown_days (dias mínimos antes de recomprar após SELL/REDUCE)

Aviso (decisão por testes históricos):
- Os valores numéricos de limiares (DD, vol, VaR/ES, liquidez) e os parâmetros de reduce_pct/cooldown serão decididos por uma série de testes históricos, buscando minimizar perdas e drawdowns, antes de qualquer uso em modo real.

---

## 10. Horizontes D+1, D+3 e D+5 (uso permitido e restrições)

Regra congelada para o Dry-Run:
- A decisão diária operacional usa somente informação baseada em D-1 e histórico (backward-looking), mais regras de universo e risco.
- Qualquer uso de predição D+1/D+3/D+5 é permitido apenas como:
  - pesquisa/diagnóstico de modelos,
  - features candidatas em backtests,
  - comparação de desempenho entre modelos.

Para virar regra operacional (influenciar SELL/REDUCE/BUY), precisa:
- estar descrito neste documento em uma versão nova, e
- ter passado pela bateria de testes históricos definida pelo Owner.

---

## 11. Rotina semanal de BUY/rebalance (Plano V2; ainda não implementada)

Princípio:
- Compra é processo de realocação; não é evento contínuo diário.
- A compra usa somente o caixa disponível no dia da decisão.

Estado:
- Não implementado.

Critérios e regras de compra (congelados como “a decidir por testes”):
- seleção da primeira carteira (carteira inicial),
- critério de ranking para reposição semanal,
- limites por posição, por setor e por liquidez,
- regras de substituição disciplinada (reservas e cooldown).

Aviso:
- Estes pontos serão decididos em uma série de testes utilizando dados históricos, priorizando o conjunto de regras/modelos que produza a menor perda (e menor drawdown) sob os custos conservadores definidos na seção 7.

---

## 12. Caminho de desenvolvimento de modelos (do simples ao MuZero/RL)

Princípio:
- O Owner não precisa dominar a matemática, mas precisa compreender a lógica operacional de cada modelo/regra.
- O objetivo é testar múltiplas abordagens com dados históricos e escolher as que reduzem perdas e drawdowns.

Roadmap de validação (congelado):
1. Montar um conjunto mínimo de dados históricos (suficiente para backtests estáveis).
2. Desenvolver e comparar modelos/regras interpretáveis (baselines).
3. Trazer os modelos até o presente e avaliar robustez (rolling windows e out-of-sample).
4. Selecionar 1–2 melhores e rodar em Dry-Run por 6 meses (sem operar dinheiro real).
5. Somente após desempenho consistente e alinhado ao perfil do Owner, discutir entrada em modo real.

---

## 13. Pendências e decisões abertas (explicitadas sem ambiguidade)

1. Limiar de risco por ativo (DD, vol, VaR/ES, liquidez): a decidir por testes históricos.
2. Limiar de risco agregado da carteira (MaxDD, VaR/ES, concentração, correlação): a decidir por testes históricos.
3. Parâmetros de REDUCE (reduce_pct, cooldown): a decidir por testes históricos.
4. Regras completas de BUY/rebalance semanal: a decidir por testes históricos.
5. Critério de seleção da carteira inicial: a decidir por testes históricos.
6. Recalibração de custo de ordens antes do modo real: depende do canal operacional efetivo do Owner (banco/app).

---

## 14. Registro das duas últimas ações relevantes (evidência de alinhamento)

1. Verificação do universo quanto a BDR/ETF:
   - UNIVERSE_CANDIDATES: 68 tickers; 0 com sufixo 34 e 0 com sufixo 11.
   - UNIVERSE_SUPERVISED: 30 tickers; 0 com sufixo 34 e 0 com sufixo 11.
   - Conclusão: o universo vigente não inclui BDRs nem ETFs/Units (mesmo que existam preços armazenados para eles).

2. Geração do inventário de parquets:
   - PARQUET_INVENTARIO_E_MANIFESTOS.json gerado, registrando o estado dos parquets e checagens de manifestos.

---

Fim do documento.
