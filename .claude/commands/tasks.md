---
description: Fase /tasks do fluxo SDD — decompõe o plan em tasks atômicas executáveis. Delega ao tl-python + qa.
argument-hint: [NNN-slug | <vazio para feature mais recente>]
---

# /tasks — Fase SDD: Decomposição em tasks

Você está iniciando a **fase `/tasks`** do fluxo SDD do projeto `own-board-list`.

## Pré-requisitos (gating)

1. Ler **obrigatoriamente** [docs/constitution.md](../../docs/constitution.md).
2. Identificar a feature (mesma lógica de `/plan`: argumento ou feature mais recente com `plan.md`).
3. **RECUSAR** se não existir `docs/specs/NNN-slug/plan.md`. Instruir o usuário a rodar `/plan` primeiro.

## Tarefa

Delegue a **`tl-python`** (dono) em pair com **`qa`** (definindo TCs de aceite) a produção de `docs/specs/NNN-slug/tasks.md` seguindo o template [docs/specs/_template/tasks.md](../../docs/specs/_template/tasks.md).

Instruções:

1. Ler `spec.md` e `plan.md` da feature.
2. Decompor em tasks atômicas (P ≤ 2h, M ≤ 6h). **Tasks G são proibidas** — quebrar até caber em M.
3. Cada task:
   - Recebe um `TASK-NNN` do próximo número disponível em [docs/tasks.md](../../tasks.md) e é **adicionada lá** também (rastreabilidade global).
   - Tem ao menos um TC de aceite (criar entrada em `docs/plano-testes.md` se não existir).
   - Declara dependências por número (`#1`, `#2`, ...) para facilitar ordem.
4. Produzir ordem topológica de execução no final do documento.
5. Incluir plano de rollback se alguma task introduzir mudança irreversível de dados.

## Saída esperada

- Caminho do `tasks.md` criado.
- Total estimado em P/M.
- Ordem de execução sugerida.
- Próximo passo: rodar `/implement`.
