A seguir está uma reescrita do **Plano V2 (PLAN_V2)**, usando como base o **Plano V1** que você disponibilizou, mantendo as **ideias e relações** (negócio → risco → arquitetura → fases), mas ajustando o roadmap para a realidade atual do repo: **execução por TASK specs, runner padrão e Agno como orquestrador prático** (com contrato), para que você “pense em ações” e não em programação.

---

# PORTFOLIOZERO — Plano V2

Negócio, Risco, Arquitetura e Roadmap orientado a TASKs (Runner + Agno)

Versão: 2.0  
Data: 2026-01-22  
SSOT: /home/wilson/PortfolioZero (branch main)

## 0. Objetivo do V2

O V2 mantém as premissas de negócio e risco do V1 e reancora a execução técnica em um princípio único: **tudo que importa roda como TASK versionada, com evidências em runs, e com um contrato estável para steps “agno”**. O foco não é “usar Agno do jeito mais completo”, e sim usar Agno como **orquestrador pragmático** de um pipeline que gere decisões de portfólio com rastreabilidade.

## 1. Premissas de negócio e posicionamento

O PORTFOLIOZERO continua sendo uma ferramenta pessoal do Owner, com objetivo de renda complementar e desafio intelectual, sem ambição de produto comercial. O nome e a inspiração (MuZero como filosofia de planejamento/decisão) permanecem como norte conceitual, mas o V2 assume explicitamente uma construção incremental: primeiro um motor decisório operacional e auditável; depois sofisticação (RL, BL, etc.).

## 2. Capital, horizonte e métrica de sucesso

Mantém-se o conceito de bolso em circuito fechado e avaliação por retorno composto real, não por “meta mensal rígida”. O sucesso do sistema no V2 é medido por:

1. capacidade de **não quebrar a filosofia de risco** (drawdown controlado e comportamento defensivo coerente),
    
2. decisões compreensíveis e auditáveis,
    
3. performance superior a benchmarks relevantes, sem turnover destrutivo.
    

## 3. Filosofia de risco, drawdown e modos de operação

A estrutura de risco do V1 vira um “contrato de comportamento” do sistema:

- Operação normal enquanto em zona de conforto.
    
- Zona de atenção gera alertas e preparação de redução.
    
- Zona de risco ativa modo defensivo (aumenta caixa, reduz exposição, prioriza menor risco, e permanece até retorno a faixa segura).
    

O V2 transforma isso em duas camadas:

- **Regra de risco explícita** (determinística e audível): o sistema nunca pode “ignorar” o modo defensivo quando a condição disparar.
    
- **Decisão tática** (otimização): dentro das restrições, o motor escolhe o melhor conjunto de ações (venda/redução/manter; compra/alocação).
    

## 4. Universo e restrições de instrumentos

Mantém-se o recorte conservador do V1: long-only, sem alavancagem e sem short. A lógica do V2 separa claramente:

- **Universo supervisionado** (radar): conjunto estável de ativos monitorados continuamente.
    
- **Carteira ativa**: subconjunto menor (faixa alvo) com alocação efetiva.
    

A diferença do V2 é que “universo” deixa de ser um conceito textual e passa a ser um **artefato versionado** (parquet/json) gerado por pipeline, com rastreabilidade de critérios.

## 5. Arquitetura decisória do PORTFOLIOZERO

O V1 descreve o fluxo Dados → Risco curto prazo → Agente (MuZero) → Black-Litterman → Carteira. O V2 preserva a relação entre blocos, mas organiza a arquitetura em quatro “produtos” concretos (artefatos), cada um gerado por TASKs:

### 5.1 Produto A: Market Data Package

Um pacote padronizado de dados de mercado (preços/volumes/ajustes e derivados mínimos), com validação de integridade e versionamento lógico (por data de execução e config).

### 5.2 Produto B: Universe Package

Saídas do pipeline de universo:

- universe_candidates (pré-lista),
    
- universe_supervised (lista final do radar),
    
- metadados (critérios aplicados, cobertura, datas, contagens, setores quando aplicável).
    

### 5.3 Produto C: Risk Package (curto prazo)

Um artefato que estima risco em horizontes curtos (D+1, D+3, D+5) e que é consumido por regras de proteção (venda/redução) e por seleção de compra (para evitar entrar em risco).

No V2, esse componente pode começar simples (baseline determinístico/estatístico) e evoluir, mas o contrato do artefato deve ser estável.

### 5.4 Produto D: Decision Package

O artefato final que você realmente quer ver: um JSON/MD estruturado que diga:

- estado do portfólio (posições, caixa, drawdown, modo defensivo),
    
- recomendações de venda (diárias) e compra (batida semanal),
    
- justificativas rastreáveis (inputs usados e regras/heurísticas/modelos acionados),
    
- “limites e travas” (quarentena, min/max posição, exposição máxima).
    

## 6. Regras operacionais: frequência, quarentena, custos

O V2 mantém a ideia central do V1:

- venda é reativa ao risco e pode ser diária,
    
- compra é processo de realocação e pode ser semanal,
    
- quarentena evita “entra-e-sai caótico”,
    
- custos e turnover entram como penalização estrutural do sistema.
    

A mudança prática do V2: essas regras deixam de ser só “documento” e viram **validações automáticas** (gates) dentro do pipeline. Se a decisão violar regra, o artefato é gerado com FAIL explícito (evidência) ou é corrigido antes de publicar o pacote.

## 7. Padrão de execução e governança (Runner + Agno)

Este é o pivô do V2.

### 7.1 Um único caminho de execução

O comando oficial do projeto é sempre o runner executando uma TASK spec versionada. A TASK define:

- inputs (repo_path, configs, allowlists),
    
- workflow (steps),
    
- artifacts esperados,
    
- critérios de PASS/FAIL.
    

### 7.2 Step types e contrato

No V2, a regra é:

- **shell**: usado quando a ação é “rodar um script do próprio repo” ou comandos de verificação (py_compile, testes, validações). Shell não é “anti-contrato”; ele só não é o lugar onde o “cérebro” decide. Ele executa.
    
- **agno**: usado quando o step precisa de um “contrato de payload” e de uma execução padronizada, especialmente para geração de artefatos estruturados (por exemplo: produzir Decision Package com justificativa padronizada).
    

O V2 não tenta eliminar shell; ele elimina “decisão escondida em shell”. A decisão fica no step “agno” (ou em scripts com contratos claros), e o shell apenas dispara e verifica.

### 7.3 Evidências e auditabilidade

Tudo que importa deixa trilha em:

- planning/runs/<TASK_ID>/ (artefatos por step + report.json),
    
- artefatos de dados em data/ (ou diretórios acordados), com resumos.  
    A capacidade de reproduzir uma execução vira requisito.
    

## 8. Roadmap V2 (fases)

O V1 tinha fases 0–5 (regras, dados, MuZero, BL, backtest, dry run). O V2 preserva isso, mas reordena para maximizar “valor operacional cedo” e reduzir dependências.

### Fase 0 (mantida): Regras e contratos de negócio

Congelar parâmetros de risco, universo, restrições e regras operacionais como “contratos” consumíveis pelo pipeline (configs e validações).

### Fase 1 (antecipada): Pipeline executável de Universo + Dados

Objetivo: gerar Produto A e Produto B de forma totalmente reprodutível por TASKs, com artefatos e validações.

### Fase 2 (redefinida): Risk Package baseline (operacional antes de sofisticar)

Objetivo: produzir Produto C com um baseline simples, mas com contrato estável e testável, para já habilitar venda defensiva e filtros de compra.

### Fase 3 (redefinida): Decision Package V1 (engine híbrido)

Objetivo: gerar Produto D com regras + heurísticas + (opcionalmente) scores do Risk Package.  
Aqui o sistema já “opera” conceitualmente, mesmo antes de RL/MuZero.

### Fase 4 (mantida): Backtest integrado e métricas

Objetivo: validar o conjunto (A+B+C+D) em janelas históricas e comparar com benchmarks, com foco em drawdown e turnover.

### Fase 5 (mantida): Dry run em tempo real

Objetivo: simular em tempo real e construir confiança operacional e interpretabilidade.

### Fase 6 (opcional, posterior): MuZero + Black-Litterman

Somente depois do pipeline e do Decision Package estarem maduros e auditáveis. Mantém-se a arquitetura conceitual do V1, mas ela passa a ser “upgrade”, não pré-requisito.

## 9. Critérios de pronto do V2

O V2 está “pronto para evolução” quando:

1. Você consegue rodar uma TASK diária que gera um Decision Package consistente, com justificativa e validações.
    
2. O sistema respeita invariantes: long-only, limites por posição, quarentena, modo defensivo.
    
3. As execuções são reproduzíveis e auditáveis (runs + report).
    
4. A passagem de “universo → risco → decisão” não depende de ação manual nem de edição de scripts fora do fluxo.
    

## 10. Pontos que eu preciso confirmar com você (só se houver mudança do V1)

Aqui vão as únicas dúvidas que podem alterar o plano (se a resposta for “mantém como no V1”, não muda nada):

1. Capital de referência do bolso no PORTFOLIOZERO continua em R$ 500k (V1) ou houve atualização?
    
2. A cadência “venda diária / compra semanal” permanece como regra de negócio no V2?
    
3. O universo supervisionado alvo permanece em ~30 e carteira ativa em ~10 (com faixa 8–12)?
    

---

Se esse **PLAN_V2** está alinhado, o próximo passo lógico antes da A_012 é: **transformar “Decision Package” no centro do sistema**, e fazer a A_012 ser a primeira TASK que conecta explicitamente Universo + (baseline de risco, se já existir) + geração de Decision Package, com PASS/FAIL por invariantes (limites, quarentena, drawdown/mode).