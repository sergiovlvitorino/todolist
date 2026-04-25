# Plan — Busca de tarefas por texto na Todo List

> **Spec:** [spec.md](spec.md)
> **Fase:** `/plan` → entrada para `/tasks`
> **Autor:** agente `tl-python` (plano original 2026-04-19; migrado para SDD em 2026-04-24)
> **Status:** ✅ Implementado

---

## Resumo técnico

Backend de busca já existia em `TaskRepository.search` (usado internamente). Esta feature adiciona a camada de UI (`QLineEdit` com debounce no `TodoWidget`), fecha dois gaps de robustez no backend (escape de wildcards LIKE e normalização Unicode case-insensitive) e fia o filtro na cadeia de signals do `TaskService` para que operações CRUD reapliquem automaticamente o filtro ativo.

## Camadas afetadas

| Camada | Muda? | Natureza da mudança |
|---|---|---|
| `utils/` | não | — |
| `models/` | sim | Extração de `Prioridade`/`StatusTarefa` para `models/enums.py` (módulo-folha) para quebrar ciclo com `utils/constants.py` (ver ADR-003) |
| `database/` | sim | `TaskRepository.search`: escape de `%`, `_`, `\` + `ESCAPE '\\'` no LIKE; função SQL customizada `PY_UPPER` registrada em `DatabaseConnection` para case-insensitive Unicode (ver ADR-002) |
| `services/` | não | Signals existentes (`task_created`, `task_updated`, `task_deleted`, `tasks_reloaded`) já suportam a reaplicação; apenas uso |
| `ui/` | sim | `TodoWidget`: `QLineEdit` com `QTimer` debounce, filtro por seções, mensagem vazia, atalho `Ctrl+F`, botão limpar, tecla `Esc`, atributo `self._search_term` reaplicado em `_reload_tasks` |

## Contratos

```python
# database/task_repository.py
class TaskRepository:
    def search(self, termo: str) -> list[Task]:
        """Busca case-insensitive Unicode em titulo/descricao.
        Trata '%' e '_' como caracteres literais (não curingas).
        Termo vazio ou só-espaços retorna todas as tarefas."""

# database/connection.py
class DatabaseConnection:
    # Registra função SQL PY_UPPER(texto) -> str.upper() Python ao abrir a conexão
```

UI (`TodoWidget`) ganha atributos privados:
- `self._search_input: QLineEdit`
- `self._search_timer: QTimer`  (debounce)
- `self._search_term: str`
- método privado `_apply_search(termo: str)` chamado pelo timer

## Migração de dados / schema

Nenhuma. Apenas registro de função SQL em runtime (`PY_UPPER`).

## ADRs novos necessários

- [x] **ADR-002** — Busca case-insensitive Unicode via `PY_UPPER` (decisão irreversível; afeta toda query que use LIKE sobre texto do usuário). Ver [../../adr-002-unicode-search.md](../../adr-002-unicode-search.md).
- [x] **ADR-003** — `models/enums.py` como módulo-folha (side effect do ADR-002: quebra ciclo entre `utils/constants.py` ↔ `models/task.py`). Ver [../../adr-003-enums-module.md](../../adr-003-enums-module.md).

## Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Regressão em buscas com `%`/`_` literais | média | alto (falsos positivos silenciosos) | TC dedicado (TC em TASK-035 item 4); escape isolado em função utilitária com testes unitários |
| Debounce mascarando bug de wiring | baixa | médio | `debounce_ms` injetável (= 0 em testes) para exercitar reload síncrono |
| Perda do termo ao abrir TaskForm | média | médio | `_reload_tasks` central único; TASK-033 é wiring check explícito |
| Performance ruim em 10k tarefas | baixa | médio | TASK-036 benchmark com `pytest.mark.slow` e threshold documentado |

## Plano de testes

- [x] TC — escape de `%`, `_`, `\` no `TaskRepository.search` (unit)
- [x] TC — busca Unicode case-insensitive (unit, via `PY_UPPER`)
- [x] TC — debounce: múltiplas teclas resultam em um único reload (UI, `debounce_ms=0`)
- [x] TC — atalho `Ctrl+F` foca o campo (UI)
- [x] TC — tecla `Esc` limpa termo e devolve foco (UI)
- [x] TC — botão limpar zera o campo (UI)
- [x] TC — filtro reaplicado após create/update/delete (integração UI+Service+DB)
- [x] TC — mensagem "Nenhuma tarefa encontrada" quando busca global vazia (UI)
- [x] TC — termo só-espaços equivale a busca vazia (unit + UI)
- [x] TC — benchmark 1k–5k tarefas dentro do threshold (slow)

Detalhe em [docs/plano-testes.md](../../plano-testes.md), seção Busca, e em [tasks.md](tasks.md) TASK-034 a TASK-036.

## Dependências

- Tasks bloqueantes no backlog global: TASK-029 (escape de wildcards) — pré-requisito técnico.
- Features: nenhuma.

## Ligações

- **Constitution:** [../../constitution.md](../../constitution.md)
- **ADRs relevantes:** [ADR-002](../../adr-002-unicode-search.md), [ADR-003](../../adr-003-enums-module.md), [ADR-001](../../adr-001-stack.md) (stack base)
- **Backlog global:** [docs/tasks.md](../../tasks.md) §"Plano US-07"
