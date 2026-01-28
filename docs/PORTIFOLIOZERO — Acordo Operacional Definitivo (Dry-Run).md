
Data: 24/01/2026 (sábado)
Partes: Owner (Wilson) e Planejador (GPT-5.2 Thinking)
Escopo: regras operacionais e de governança para operação em modo Dry-Run, sem integração com corretora, com decisões diárias e compras semanais, baseadas em preços de fechamento.

## 1. Objetivo e princípio diretor

O objetivo primário do sistema é preservar capital e reduzir perdas. A maximização de retorno não é prioridade sobre o controle de risco. A escolha de políticas e modelos será orientada por desempenho histórico com foco em menor perda, menor drawdown e maior estabilidade, antes de qualquer transição para modo real.

## 2. Regime de operação (calendário e tempo do sistema)

2.1. A rotina é executada na manhã de cada dia útil D.
2.2. O preço de referência do ciclo do dia D é sempre o fechamento (Close) do último pregão disponível (D-1 útil).
2.3. Em finais de semana e feriados, o sistema utiliza o último fechamento útil conhecido. Não há criação de barras sintéticas; apenas reutilização do último Close disponível como referência.

## 3. Fonte de preços e definição do preço oficial

3.1. Durante o Dry-Run, a fonte base de preços é Yahoo Finance.
3.2. O preço oficial para decisões e avaliações operacionais é sempre o campo Close.
3.3. Qualquer correção/refresh de janela existe apenas como mecanismo de consistência do pacote de preços; não altera a definição de preço oficial do sistema (Close).

## 4. Estado de decisão (manhã do dia D)

4.1. O estado usado para decisões na manhã de D é composto por:

* posições atuais (quantidade por ativo);
* caixa disponível na manhã de D.

4.2. Compras são permitidas somente com o caixa disponível na manhã de D. Não se utiliza caixa futuro, esperado ou a liquidar.

## 5. Ledger de caixa (conta corrente com recebíveis)

5.1. O caixa é tratado como uma conta corrente do sistema, com:

* saldo disponível;
* recebíveis previstos (créditos futuros);
* despesas executadas no dia da decisão.

5.2. Regras de venda:

* a venda reduz imediatamente a quantidade do ativo no dia D (efeito econômico imediato);
* o crédito no caixa ocorre em D+2;
* o valor creditado no Dry-Run é calculado como: quantidade vendida × Close(D-1), descontado o custo fixo conservador por ordem.

5.3. Regras de compra:

* a compra é realizada em D usando apenas o caixa disponível na manhã de D;
* o volume comprado no Dry-Run é derivado do caixa disponível e do Close(D-1), descontado o custo fixo conservador por ordem.

## 6. Universo de ativos

6.1. O universo elegível inclui ativos brasileiros (ações) e ETFs (BR + ETF).
6.2. Regras adicionais de elegibilidade (ex.: liquidez mínima) serão definidas em política própria, versionada, sem alterar este acordo.

## 7. Custos e conservadorismo

7.1. O sistema aplica custo fixo conservador por ordem (pessimista) em operações de compra e venda no Dry-Run.
7.2. O valor numérico do custo fixo e sua eventual evolução serão definidos em política versionada e auditável.

## 8. Sequência obrigatória do ciclo diário

8.1. Antes de qualquer análise de risco ou geração de decisão, é obrigatório atualizar e auditar o pacote de preços.
8.2. Ordem mínima obrigatória do ciclo diário:

1. atualização de preços (Yahoo Finance; preço oficial Close);
2. auditoria do pacote de preços;
3. geração/atualização do pacote de risco;
4. geração da decisão diária (SELL/REDUCE/HOLD).

8.3. Se a atualização ou auditoria de preços falhar, o ciclo diário não prossegue para risco e decisão.

## 9. Horizontes D+1, D+3 e D+5: uso permitido e restrições

9.1. D+1, D+3 e D+5 serão tratados como horizontes de previsão (quando houver modelo de ML), nunca como informação realizada para tomada de decisão.
9.2. A decisão de venda e redução, quando habilitada, será baseada em regras explícitas:

* limites (gatilhos) para venda;
* inclinações (trend/slope do sinal) para venda e redução.

9.3. Essas regras, uma vez definidas e validadas, servirão como base para evolução posterior para MuZero/RL, sem alterar o princípio diretor de preservação de capital.

## 10. Primeira carteira e compras semanais

10.1. A primeira carteira será inicializada por regra do sistema (não manual).
10.2. A rotina semanal de compra/rebalance será definida e implementada separadamente, respeitando:

* uso exclusivo do caixa disponível na manhã do dia da rotina;
* rastreabilidade completa das razões de compra/rebalance;
* compatibilidade com o regime diário de risco (SELL/REDUCE/HOLD).

## 11. Governança e rastreabilidade

11.1. Toda execução deve ser rastreável por artefatos versionados e auditáveis (inputs, outputs, manifests, reports).
11.2. Decisões e movimentos devem ser classificáveis por motivo (por exemplo: venda por risco, venda por saída do universo, redução por limite, compra por reposição, compra por rebalance), de modo a permitir avaliação histórica, auditoria e treinamento futuro.

## 12. Validade e mudanças

12.1. Este acordo é válido para o modo Dry-Run e permanece em vigor até revisão formal.
12.2. Qualquer alteração de premissas (fonte de preços, preço oficial, regra de caixa, calendário operacional) exige revisão explícita deste documento e versionamento.

Assinaturas (aceite operacional):
Owner: Wilson
Planejador: GPT-5.2 Thinking
