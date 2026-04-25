# Tasks — Busca de tarefas por texto na Todo List

> **Plan:** [plan.md](plan.md)
> **Fase:** `/tasks` → entrada para `/implement`
> **Autores:** agentes `tl-python` + `qa`
> **Data original:** 2026-04-19 · **Migrado para SDD:** 2026-04-24
> **Status:** ✅ Implementado (todas as tasks com `[x]`)

---

## Decomposição

| # | ID | Descrição | Camada | Esforço | Depende | TC aceite | Status |
|---|---|---|---|---|---|---|---|
| 1 | TASK-029 | Escapar wildcards LIKE (`%`, `_`, `\`) + `ESCAPE '\\'` em `TaskRepository.search` | database | P | — | plano-testes.md §Busca item "wildcards literais" | ✅ |
| 2 | TASK-030 | `QLineEdit` + `QTimer` debounce no `TodoWidget`, parâmetro `debounce_ms` injetável | ui | P | TASK-029 | UI §debounce | ✅ |
| 3 | TASK-031 | Integração do filtro com redistribuição por seções + mensagem "Nenhuma tarefa encontrada" | ui | P | TASK-030 | UI §seções vazias | ✅ |
| 4 | TASK-032 | Atalho `Ctrl+F` + botão limpar (X) + tecla `Esc` | ui | P | TASK-030 | UI §teclado | ✅ |
| 5 | TASK-033 | Wiring: signals CRUD do `TaskService` reaplicam `self._search_term` em `_reload_tasks` | ui | P | TASK-031, TASK-032 | Integração §reaplicação | ✅ |
| 6 | TASK-034 | Testes unitários de UI: debounce, Ctrl+F, Esc, botão X, foco pós-TaskForm | testes | M | TASK-030..033 | suite `test_ui/test_todo_search.py` | ✅ |
| 7 | TASK-035 | Testes de integração UI+Service+DB: Unicode, SQL wildcards, só-espaços, seções vazias, reaplicação CRUD | testes | M | TASK-029..033 | suite `test_integration/test_busca.py` | ✅ |
| 8 | TASK-036 | Teste de performance 1k–5k tarefas (`pytest.mark.slow`, threshold documentado) | testes | P | TASK-033 | `test_integration/test_busca_perf.py` | ✅ |

**Total:** 6P + 2M ≈ 18–24 h.

## Ordem de execução

TASK-029 → TASK-030 → (TASK-031 ∥ TASK-032) → TASK-033 → (TASK-034 ∥ TASK-035) → TASK-036.

## Plano de rollback

Se bug crítico em escape de wildcards (TASK-029) aparecer em produção, reverter **apenas** o commit de TASK-029 mantendo a UI funcional. Comportamento regredirá a LIKE "puro" (aceita falso positivo de `%`/`_` como curingas) até correção.

## Dívidas técnicas criadas durante esta feature

Ver [docs/tasks.md](../../tasks.md) DT-031 a DT-035 (derivadas do code-review TL de encerramento em 2026-04-20).

## Checklist de encerramento

- [x] Todos os TCs da spec passando
- [x] Gates de qualidade verdes (ver [../../constitution.md §Gates](../../constitution.md#-gates-de-qualidade))
- [x] `funcionalidades.md` mantém US-07 como "implementada"
- [x] ADR-002 e ADR-003 merged
- [x] Entrada em [CHANGELOG.md](../../../CHANGELOG.md)

## Ligações

- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)
- **Backlog global:** [docs/tasks.md §Plano US-07](../../tasks.md)
- **Plano de testes:** [docs/plano-testes.md](../../plano-testes.md)
