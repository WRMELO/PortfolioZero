Perfeito — então ficam **travados como no V1** os três pontos:

- Capital de referência: **R$ 500k**
    
- Cadência: **venda diária / compra semanal**
    
- Alvos: **universo supervisionado ~30** e **carteira ativa ~10** (faixa **8–12**)
    

Abaixo está o **PLAN_V2 consolidado** já com isso incorporado (sem pendências).

---




## 1) Tese do V2

O V2 transforma o PORTFOLIOZERO em um sistema onde você só se preocupa com **decisão e gestão**, e o resto vira **execução repetível**: tudo roda por **TASK spec versionada**, com **evidências em `planning/runs/`**, e com **contratos estáveis** para os artefatos.

A regra é simples: se não deixa rastro auditável (task + run + artifact), não faz parte do sistema.

## 2) Parâmetros de negócio travados

- Capital: **R$ 500k**
    
- Vendas: **diárias** (reativas ao risco e ao estado)
    
- Compras: **semanais** (realocação e entrada em posições)
    
- Universo supervisionado: **~30**
    
- Carteira ativa: **~10** (faixa 8–12)
    
- Long-only, sem alavancagem/short (como no V1)
    

## 3) Os 4 produtos (artefatos) do sistema

Tudo no V2 gira em torno de quatro pacotes gerados por pipeline:

1. Market Data Package  
    Dados brutos e derivados mínimos validados (ex.: parquet padronizado, cobertura, datas).
    
2. Universe Package  
    `universe_candidates` + `universe_supervised` + metadados de critérios e rastreabilidade.
    
3. Risk Package (curto prazo)  
    Um artefato de risco operacional, com contrato estável, que alimenta:
    
    - gatilhos de proteção (vendas/reduções),
        
    - filtros de compra (evitar entrar em risco),
        
    - modo defensivo.
        
4. Decision Package  
    O produto final: ações recomendadas (venda/compra/hold) + justificativas + travas + estado (caixa, exposição, modo defensivo).
    

## 4) Onde Agno entra (prático, sem preciosismo)

Agno no V2 é **orquestrador** do que importa (contrato + rastreabilidade), não “framework completo”.

- **shell** continua existindo para: rodar scripts do repo, checks, validações, `py_compile`, asserts, etc.  
    Shell é execução, não inteligência.
    
- **agno** é reservado para: gerar artefatos **com contrato** e de preferência com payload padronizado (principalmente Decision Package e, depois, Risk Package).
    

A ideia não é “não usar shell”; é impedir “decisão escondida em shell”.

## 5) Roadmap V2 por fases

### Fase 0 — Contratos e regras (congelar invariantes)

Congelar como contratos executáveis:

- limites por posição/exposição,
    
- quarentena,
    
- modo defensivo e gatilhos,
    
- cadência diária/semanal.
    

Entregável: validações automáticas (gates) que falham se violar regra.

### Fase 1 — Dados + Universo (pipeline reprodutível)

Entregáveis:

- gerar Market Data Package (mesmo que comece com sample)
    
- gerar Universe Package (candidates + supervised)
    
- tudo via TASKs, com evidências e reexecução “sempre verde”.
    

### Fase 2 — Risk Package baseline (antes de sofisticar)

Entregável:

- um Risk Package simples, mas com contrato estável,
    
- acionando o modo defensivo e filtros básicos.
    

### Fase 3 — Decision Package operacional (primeiro sistema “usável”)

Entregável:

- Decision Package diário/semanal respeitando invariantes,
    
- com trilha completa: universo + risco + regras + decisão,
    
- com logs e justificativas.
    

### Fase 4 — Backtest integrado

Entregável:

- backtest do conjunto (A+B+C+D) com métricas (drawdown, turnover, aderência a regras).
    

### Fase 5 — Dry run em tempo real

Entregável:

- execução diária/semanal em “paper mode”, sem corretora.
    

### Fase 6 (opcional) — MuZero/BL como upgrade

Só entra depois que o sistema operacional estiver estável e auditável.

## 6) Critério de pronto do V2 (o que “fecha” a fase operacional)

O V2 está operacional quando:

1. Uma TASK diária gera um Decision Package válido e auditável.
    
2. Nenhuma decisão viola as invariantes (long-only, limites, quarentena, modo defensivo).
    
3. Reexecução reproduz os resultados (ou explica diferenças por inputs versionados).
    
4. Você não edita scripts “na unha” para rodar o dia; você só roda tasks.
    

---

Agora que está tudo “mantido como V1”, eu só preciso de uma confirmação objetiva para escolher o **melhor próximo passo** (e aqui eu realmente preciso perguntar porque muda o desenho):

1. No V2, você quer que o **Decision Package** já comece **com BUY/SELL reais** (mesmo que baseline), ou quer primeiro consolidar apenas **HOLD/SELL (risk-first)** e deixar BUY para a etapa semanal?
    

Responde com:

- **A)** “já com BUY/SELL”  
    ou
    
- **B)** “primeiro HOLD/SELL (risk-first)”