# Constitution — Own Board List

> **Versão:** 1.0 — 2026-04-24
> **Propósito:** Consolidar os princípios, padrões e gates de qualidade que governam o projeto. Esta constituição é o **contexto inicial obrigatório** para qualquer agente ou contribuidor antes de executar `/specify`, `/plan`, `/tasks` ou `/implement`.

---

## Como ler este documento

- 🔒 **Princípios invioláveis**: mudança requer decisão explícita do usuário + novo ADR. Agentes devem recusar planos que os violem.
- ⚖️ **Padrões fortes**: mudança permitida via ADR justificado.
- ✅ **Gates de qualidade**: nenhuma task pode ser marcada como concluída se um gate estiver vermelho.

---

## 🔒 Princípios invioláveis

1. **Aplicação 100% offline e local.** Sem internet, sem autenticação, sem serviços externos, sem telemetria. Persistência exclusivamente em arquivo SQLite local.
2. **Stack fixo** (definido em [adr-001-stack.md](adr-001-stack.md)):
   - Python ≥ 3.11
   - UI: PyQt6
   - Persistência: `sqlite3` da stdlib (sem ORM)
   - Gerenciador: `uv` (sem pip/poetry/conda)
   - Lint/format: `ruff`
   - Tipos: `mypy --strict`
   - Testes: `pytest` + `pytest-qt` + `pytest-cov`
3. **Layering MVP respeitado estritamente**: `utils → models → database → services → ui`. Dependências só descem; nunca sobem, nunca cruzam lateralmente pulando camadas. UI jamais acessa repositórios diretamente.
4. **Zero SQL injection**: toda query parametrizada (`?` placeholders). Concatenação de strings com input do usuário em SQL é proibida.
5. **`models/enums.py` é módulo-folha** (ver [adr-003-enums-module.md](adr-003-enums-module.md)): não importa nada de `own_board_list/*`. Qualquer import nele quebra a regra.
6. **Privacidade por default**: nenhum log, snapshot ou artefato de teste pode conter dados reais do usuário. `tests/` usa sempre fixtures sintéticas e banco `:memory:`.

---

## ⚖️ Padrões fortes

1. **Padrão arquitetural MVP** adaptado para Qt (ver [adr-001-stack.md](adr-001-stack.md) §"Padrão Arquitetural"):
   - `models/`: dataclasses puras + validação em `__post_init__` + `to_dict`/`from_dict`
   - `database/`: Repository pattern, uma classe por agregado (`TaskRepository`, `ColumnRepository`)
   - `services/`: orquestração + signals Qt. `TaskService` herda `QObject` por decisão consciente (ver ADR-001)
   - `ui/`: widgets puros com injeção de dependência via construtor
2. **Comunicação entre abas via signals Qt** (`task_created`, `task_updated`, `task_deleted`, `tasks_reloaded`). UI nunca faz polling nem acessa outras UIs diretamente.
3. **Timestamps sempre timezone-aware em UTC** (`datetime.now(tz=timezone.utc)`). Naive datetimes são proibidos em `models/` e `services/`.
4. **Transações explícitas via context manager** (`DatabaseConnection.__enter__`/`__exit__`). Operações compostas (ex.: reorder de colunas) vão em transação única.
5. **Type hints completos**: toda função pública anotada. Signals Qt podem exigir workaround documentado para `mypy --strict`.
6. **Testes com `qtbot`** para widgets; `:memory:` para integração; mocks apenas em unit tests de services isolados.

---

## ✅ Gates de qualidade

Antes de marcar qualquer task de `/implement` como concluída:

| Gate | Comando | Critério |
|---|---|---|
| Testes | `uv run pytest` | 100% passando |
| Cobertura | `uv run pytest --cov=src` | ≥ 90% |
| Lint | `uv run ruff check .` | zero erros |
| Format | `uv run ruff format --check .` | sem diff |
| Tipos | `uv run mypy src/` | zero erros (modo `--strict`) |

**Estado de referência (2026-04-19)**: 234 testes, cobertura 94%, ruff e mypy limpos. Qualquer regressão bloqueia o merge.

---

## Numeração e convenções

Preservar as numerações existentes. Nenhuma é renumerada:

| Prefixo | Fonte | Propósito |
|---|---|---|
| **US-NN** | [docs/funcionalidades.md](funcionalidades.md) | User stories (catálogo de produto) |
| **ADR-NNN** | [docs/adr-NNN-*.md](.) | Decisões arquiteturais globais |
| **TASK-NNN** | [docs/tasks.md](tasks.md) | Tasks técnicas do backlog global |
| **DT-NNN** | [docs/tasks.md](tasks.md) | Dívidas técnicas catalogadas |
| **TC-NNN** | [docs/plano-testes.md](plano-testes.md) | Casos de teste |

**Convenção de specs por feature**: `docs/specs/NNN-slug/` onde `NNN` é o número zero-padded da US principal entregue (ex.: `007-busca-todo-list` para US-07). Features sem US prévia ganham uma nova US em `funcionalidades.md` antes de criar o diretório.

**Convenção de commits**:
```
<tipo>(US-NN|TASK-NNN|DT-NNN): <descrição curta>
```
Tipos: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`. Sempre referenciar ao menos um identificador rastreável.

---

## Fluxo SDD

```
/specify   →  docs/specs/NNN-slug/spec.md   (agente: po)         — WHAT e WHY, zero tecnologia
/plan      →  docs/specs/NNN-slug/plan.md   (agente: tl-python)  — HOW, camadas, contratos, ADRs novos
/tasks     →  docs/specs/NNN-slug/tasks.md  (agentes: tl-python + qa)
/implement →  código + testes + commits     (agentes: dev-python + qa)
```

**Gating (enforcement por slash command):**
- `/plan` recusa rodar sem `spec.md` presente no diretório da feature.
- `/tasks` recusa rodar sem `plan.md`.
- `/implement` recusa rodar sem `tasks.md`.

**Escape hatches (trabalho trivial):**
- Correção de dívida técnica catalogada (`DT-NNN`) com escopo ≤ 30 min pula `/specify` e `/plan`, vai direto para `/implement` com commit `fix(DT-NN):`.
- Bugs triviais (typo, string quebrada, import inválido) idem, com commit `fix:` curto.
- Features não-triviais **nunca** pulam fases.
