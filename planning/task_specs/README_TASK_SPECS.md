# Arquivo de JSONs de Planejamento (TASK SPECS)

Esta pasta armazena **TODOS os JSONs de especificação de tasks gerados pelo TPM** do projeto PortfolioZero.

---

## Convenção de Nomes

Cada arquivo JSON de task deve seguir o padrão:

```
TASK_XXX_<NOME_DESCRITIVO>.json
```

Onde:
- `XXX` é o número sequencial da task (001, 002, 003, ...)
- `<NOME_DESCRITIVO>` é um identificador curto e descritivo em UPPER_SNAKE_CASE

O campo `task_id` dentro do JSON deve coincidir com o prefixo do arquivo.

**Exemplos:**
- `TASK_001_SETUP_INFRA.json`
- `TASK_005_TRILHO_A_UNIVERSE_AND_JSON_ARCHIVE.json`

---

## Relação com o Plano V1

- O documento base de negócio e risco é [`docs/PORTFOLIOZERO_PLAN_V1.md`](../../docs/PORTFOLIOZERO_PLAN_V1.md)
- Cada JSON aqui representa uma **instância de decomposição do Plano V1 em tarefas técnicas**
- Os JSONs são a especificação formal que o agente (Cursor) executa para implementar o projeto

---

## Regras para o Agente

Sempre que o TPM fornecer um novo JSON de task no chat:

1. **Criar** um arquivo correspondente nesta pasta, seguindo a convenção de nome
2. **Garantir** que o conteúdo do arquivo seja exatamente o JSON recebido
3. **Não modificar** o conteúdo do JSON (é um registro histórico)

---

## Rastreabilidade

Esta pasta deve ser **versionada no Git**, garantindo rastreabilidade histórica das decisões de planejamento.

Cada commit que adiciona um novo JSON de task representa um ponto de decisão no projeto.

---

## Histórico de Tasks Arquivadas

| Task ID | Arquivo | Descrição |
|---------|---------|-----------|
| TASK_005 | `TASK_005_TRILHO_A_UNIVERSE_AND_JSON_ARCHIVE.json` | Criação desta área + setup Trilho A |

> **Nota:** Tasks anteriores (001-004) foram executadas antes da criação desta área de arquivamento. Os JSONs correspondentes podem ser adicionados retroativamente se disponíveis.



