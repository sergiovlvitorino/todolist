# Tasks — Criar card diretamente no Kanban

> **Plan:** [plan.md](plan.md)
> **Fase:** `/tasks` → artefato de entrada para `/implement`
> **Autores:** agentes `tl-python` + `qa`
> **Data:** 2026-04-24
> **Status:** Pronto para `/implement`

---

## Regras desta fase

- Cada task é **atômica**: um `dev-python` fecha em uma sentada sem decisão arquitetural.
- Toda task referencia `TASK-NNN` do backlog global (ver [docs/tasks.md §Plano US-10](../../tasks.md#plano-incremental-us-10-task-037-a-task-046--criar-card-diretamente-no-kanban)).
- Toda task tem ≥ 1 TC de aceite em [docs/plano-testes.md §2.10](../../plano-testes.md#210-criação-de-card-no-kanban-us-10).
- Ordem respeita dependências (topologia ao final).

---

## Estimativas

- **P (Pequena):** até 2 horas
- **M (Média):** 2–6 horas
- **G (Grande):** proibida — deve ser quebrada.

---

## Decomposição

| # | ID | Descrição | Camada | Esforço | Depende | TC aceite |
|---|---|---|---|---|---|---|
| 1 | TASK-037 ✅ | `TaskService.create_task_in_column(titulo, coluna, prioridade, data_vencimento)` encapsulando regra coluna→status (`COLUNA_CONCLUIDO`→CONCLUIDA; demais→PENDENTE). Emite `task_created`. | services | P | — | TC-080, TC-081 |
| 2 | TASK-038 ✅ | Widget `InlineTaskForm` (`ui/kanban/inline_task_form.py`): título (maxlength 200) + prioridade + data, signals `submitted(dict)`/`cancelled()`, foco inicial no título, `Enter` confirma / `Esc` cancela (locais), `reset()`, `show_error()`. | ui | M | #1 | TC-082, TC-083, TC-084, TC-085, TC-093, TC-094 |
| 3 | TASK-039 ✅ | `KanbanColumnWidget`: rodapé fixo com botão "+ Adicionar card", toggle para `InlineTaskForm`, métodos `open_inline_form`/`close_inline_form`/`has_inline_form_open`, signals `add_card_requested` e `create_card_submitted`. | ui | M | #2 | TC-086, TC-087 |
| 4 | TASK-040 ✅ | `KanbanColumnWidget.set_tasks(tasks)` para reload incremental dos cards preservando form inline + contador da coluna. | ui | P | #3 | TC-088 |
| 5 | TASK-041 ✅ | `KanbanWidget._reload_board` incremental: reutilizar colunas existentes via `set_tasks`; handler conecta `create_card_submitted` → `create_task_in_column`; erros acionam `inline_form.show_error`. | ui | M | #4 | TC-089, TC-090, TC-091 |
| 6 | TASK-042 ✅ | Criação em rajada: após confirmar com sucesso, `InlineTaskForm.reset()` + foco no título; novo card sempre entra no final da coluna. | ui | P | #5 | TC-089 |
| 7 | TASK-043 ✅ | Testes unitários de `InlineTaskForm` (`test_ui/test_inline_task_form.py`). | testes | P | #2 | TC-082–TC-085, TC-093, TC-094 |
| 8 | TASK-044 ✅ | Testes de integração UI+Service+DB (`test_integration/test_kanban_create_card.py`): criação em cada coluna padrão, regra de status, sincronização Todo List, contador, último card no final. | testes | M | #5, #6 | TC-080, TC-081, TC-089 |
| 9 | TASK-045 ✅ | Testes multi-form (`test_ui/test_kanban_column_inline.py`): dois forms simultâneos, clicar fora não fecha, cancelar um não afeta outro, reload preserva rascunho. | testes | P | #5 | TC-087, TC-088, TC-090 |
| 10 | TASK-046 ✅ | Teste `slow` de benchmark com 10k tarefas (TC-092) + teste de falha de persistência com service mockado (TC-091). | testes | P | #5 | TC-091, TC-092 |

**Total:** 7P + 3M ≈ 20–26 h. Nenhuma task G.

## Ordem de execução

```
TASK-037
   └─ TASK-038
        ├─ TASK-043              (pode rodar em paralelo assim que 038 estiver pronta)
        └─ TASK-039
             └─ TASK-040
                  └─ TASK-041
                       └─ TASK-042
                            ├─ TASK-044
                            ├─ TASK-045
                            └─ TASK-046
```

Forma compacta: **037 → 038 → (043 ∥ 039) → 040 → 041 → 042 → (044 ∥ 045 ∥ 046).**

## Plano de rollback

Feature **aditiva**, sem migração de dados, sem mudança de schema, sem nova dependência. Em caso de regressão:

- **Regressão contida na UI do form inline** (TASK-038/039/040/042): reverter os commits correspondentes; o Kanban volta ao comportamento pré-feature sem efeito colateral.
- **Regressão no `_reload_board` incremental** (TASK-041) — único ponto com risco em telas existentes: reverter apenas o commit de TASK-041; `_reload_board` volta ao reload full. O form inline deixa de preservar rascunho no signal de outras colunas (degradação, mas não violação funcional dos caminhos existentes anteriores à US-10).
- **Regressão no service** (TASK-037): reverter commit; UI passa a não ter ponto de entrada funcional (botão "+" sem efeito válido). Preferir reverter da ponta para a base.

## Checklist de encerramento da feature

- [x] Todos os TCs TC-080 a TC-094 passando
- [x] Gates de qualidade verdes (ver [../../constitution.md §Gates](../../constitution.md#-gates-de-qualidade))
- [x] `funcionalidades.md` marca US-10 como implementada
- [x] Entrada em [CHANGELOG.md](../../../CHANGELOG.md) ("Criação de card direto no Kanban")
- [ ] Review TL de encerramento (como no padrão US-07); DTs emergidas catalogadas em `docs/tasks.md`

## Ligações

- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)
- **Backlog global:** [docs/tasks.md §Plano US-10](../../tasks.md)
- **Plano de testes:** [docs/plano-testes.md §2.10](../../plano-testes.md)
