# Own Board List

Aplicação desktop de gestão pessoal de tarefas com duas visões complementares: uma **Todo List** para acompanhamento linear e um **Quadro Kanban** para visualização do fluxo de trabalho. Dados armazenados localmente — sem internet, sem autenticação, sem serviços externos.

---

## Visão geral

```
┌──────────────────────────────────────────────────────────────────┐
│  Own Board List                                          [─][□][×]│
├──────────────────────┬───────────────────────────────────────────┤
│  Todo List  │ Kanban │                                            │
├──────────────────────┴───────────────────────────────────────────┤
│                                                                  │
│  ── Aba: Todo List ──────────────────────────────────────────    │
│                                              [+ Nova Tarefa]     │
│  Hoje                                                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ☑ Revisar pull request        Alta   15/04/2026  [Ed][×]│    │
│  └─────────────────────────────────────────────────────────┘    │
│  Próximas                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ☐ Escrever documentação      Média   20/04/2026  [Ed][×]│    │
│  └─────────────────────────────────────────────────────────┘    │
│  Sem data  /  Concluídas                                         │
│                                                                  │
│  ── Aba: Kanban ─────────────────────────────────────────────    │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  A Fazer (2)│  │Em Andamento │  │ Concluído(1)│             │
│  │─────────────│  │    (1)      │  │─────────────│             │
│  │ ┌─────────┐ │  │─────────────│  │ ┌─────────┐ │             │
│  │ │Tarefa A │ │  │ ┌─────────┐ │  │ │Tarefa C │ │             │
│  │ │ Média   │ │  │ │Tarefa B │ │  │ │  Alta   │ │             │
│  │ └─────────┘ │  │ │  Alta   │ │  │ └─────────┘ │             │
│  │ ┌─────────┐ │  │ └─────────┘ │  │             │             │
│  │ │Tarefa D │ │  └─────────────┘  └─────────────┘             │
│  │ │ Baixa   │ │                                                 │
│  │ └─────────┘ │                                                 │
│  └─────────────┘                                                 │
└──────────────────────────────────────────────────────────────────┘
```

---

## Funcionalidades

> Esta seção lista o que já está implementado na versão atual (0.1.x). A visão
> de produto completa, incluindo histórias ainda não desenvolvidas, está em
> [`docs/funcionalidades.md`](docs/funcionalidades.md). O histórico de
> mudanças perceptíveis ao usuário está em [`CHANGELOG.md`](CHANGELOG.md).

### Todo List
- Criar tarefas com título (obrigatório, máx. 200 caracteres), descrição, prioridade e data de vencimento
- Visualizar tarefas agrupadas em seções: **Hoje**, **Próximas**, **Sem data** e **Concluídas**
- Marcar / desmarcar tarefas como concluídas com um clique (checkbox)
- Editar todos os campos de uma tarefa existente
- Excluir tarefa com confirmação obrigatória
- Destaque visual para tarefas vencidas (data em vermelho)
- Tarefas concluídas exibidas com texto riscado
- Atalho `Ctrl+N` para abrir o formulário de nova tarefa

### Quadro Kanban
- Visualizar tarefas em colunas: **A Fazer**, **Em Andamento** e **Concluído** (padrão)
- Mover cards entre colunas via **drag-and-drop**
- Sincronização automática de status: mover para "Concluído" marca a tarefa; mover para outra coluna a reabre
- Contador de cards por coluna
- Destaque visual de drop target ao arrastar um card

### Transversal
- Sincronização bidirecional em tempo real entre as abas (signals/slots Qt)
- Persistência automática a cada alteração — sem botão "Salvar"
- Dados preservados entre sessões

---

## Requisitos

| Ferramenta | Versão mínima |
|------------|--------------|
| Python     | 3.11         |
| uv         | qualquer recente |

> `uv` instala e gerencia o ambiente virtual automaticamente. Não é necessário instalar nada além dele.

---

## Instalação e execução

```bash
git clone https://github.com/seu-usuario/own-board-list.git
cd own-board-list
uv sync
uv run own-board-list
```

---

## Desenvolvimento

```bash
# Rodar testes
uv run pytest

# Testes com relatório de cobertura (src/)
uv run pytest --cov=src

# Cobertura com relatório de linhas faltantes no terminal
uv run pytest --cov=src --cov-report=term-missing

# Lint (verificação de estilo e erros)
uv run ruff check .

# Formatação automática
uv run ruff format .

# Verificação de tipos (modo strict, configurado em pyproject.toml)
uv run mypy src/
```

> Estado atual (2026-04-19): 234 testes passando, cobertura de 94%, `ruff check` e `mypy --strict` sem erros.

---

## Estrutura do projeto

```
own-board-list/
├── pyproject.toml                   # Metadados, dependências, configuração de ferramentas
├── uv.lock                          # Lock de dependências (gerado pelo uv)
├── docs/
│   ├── adr-001-stack.md             # ADR — Stack técnico (PyQt6, SQLite, MVP)
│   ├── adr-002-unicode-search.md    # ADR — Case-insensitive Unicode via PY_UPPER
│   ├── adr-003-enums-module.md      # ADR — Extração de enums para módulo próprio
│   ├── adr-004-coluna-kanban-fk.md  # ADR — Adiamento da FK tasks→kanban_columns
│   ├── funcionalidades.md           # Especificação de funcionalidades (user stories)
│   ├── plano-testes.md              # Plano de testes
│   ├── code-review.md               # Revisão de código
│   └── tasks.md                     # Breakdown técnico e catálogo de dívidas técnicas
├── src/
│   └── own_board_list/
│       ├── __init__.py              # Versão do pacote
│       ├── main.py                  # Entry point — inicializa QApplication
│       ├── models/
│       │   ├── enums.py             # Enums Prioridade e StatusTarefa (módulo folha)
│       │   ├── task.py              # Dataclass Task (re-exporta enums de enums.py)
│       │   └── kanban_column.py     # Dataclass KanbanColumn
│       ├── utils/
│       │   └── constants.py         # Nomes de colunas Kanban, TITULO_MAX_LEN, COR_PRIORIDADE
│       ├── database/
│       │   ├── connection.py        # DatabaseConnection (context manager, pragmas WAL/FK)
│       │   ├── migrations.py        # Criação de tabelas, índices e dados padrão
│       │   ├── task_repository.py   # CRUD de tarefas (com busca Unicode via PY_UPPER)
│       │   └── column_repository.py # CRUD de colunas Kanban (reorder em transação)
│       ├── services/
│       │   └── task_service.py      # Lógica de negócio + signals Qt (TaskService)
│       └── ui/
│           ├── main_window.py       # Janela principal com QTabWidget
│           ├── todo/
│           │   ├── todo_widget.py   # Aba Todo List
│           │   ├── task_form.py     # Diálogo de criação/edição de tarefa
│           │   └── task_list_item.py # Widget de item individual na lista
│           ├── kanban/
│           │   ├── kanban_widget.py         # Aba do quadro Kanban
│           │   ├── kanban_column_widget.py  # Coluna com suporte a drop
│           │   └── kanban_card_widget.py    # Card arrastável (draggable)
│           └── dialogs/
│               └── confirm_dialog.py        # Diálogo de confirmação reutilizável
└── tests/
    ├── conftest.py                  # Fixtures compartilhadas (db em memória, qtbot)
    ├── test_models/
    │   └── test_task.py
    ├── test_database/
    │   ├── test_task_repository.py
    │   └── test_column_repository.py
    ├── test_services/
    │   └── test_task_service.py
    ├── test_integration/            # Integração services + repos + DB :memory:
    └── test_ui/                     # Widgets isolados com qtbot
```

---

## Arquitetura

O projeto segue o padrão **MVP (Model-View-Presenter)** adaptado para Qt, organizado em cinco camadas:

```
utils ──► models ──► database ──► services ──► ui
```

| Camada | Responsabilidade |
|--------|-----------------|
| **utils** | Constantes compartilhadas (`COLUNA_*`, `TITULO_MAX_LEN`, `COR_PRIORIDADE`). Não depende de nenhuma outra camada do projeto. |
| **models** | Classes de domínio puras (`Task`, `KanbanColumn`) e enums (`Prioridade`, `StatusTarefa`). Os enums vivem em `models/enums.py` — módulo folha sem dependências internas — para evitar ciclo com `utils/constants.py` (ver ADR-003). Contêm validações básicas (`__post_init__`) e serialização (`to_dict` / `from_dict`). Timestamps são sempre timezone-aware em UTC. |
| **database** | Persistência em SQLite. `DatabaseConnection` gerencia o ciclo de vida da conexão, aplica pragmas (`foreign_keys=ON`, `journal_mode=WAL`) e implementa o protocolo de context manager (`__enter__`/`__exit__`) para transações explícitas. `TaskRepository` e `ColumnRepository` implementam o padrão Repository com SQL direto (sem ORM). O schema inclui índices em `coluna_kanban`, `status`, `prioridade` e `data_vencimento`. `migrations.py` cria o schema e popula os dados padrão. |
| **services** | `TaskService` herda de `QObject` (acoplamento consciente ao Qt — ver ADR-001 §"Comunicação entre Componentes") e orquestra a lógica de negócio (criar, atualizar, mover, alternar status). Emite signals Qt (`task_created`, `task_updated`, `task_deleted`, `tasks_reloaded`) para desacoplar completamente a camada de UI dos repositórios. |
| **ui** | Widgets PyQt6 puros. Recebem o `TaskService` por injeção de dependência, conectam-se aos seus signals para recarregar a tela e delegam toda a lógica de negócio ao service. Nunca acessam os repositórios diretamente. |

A sincronização entre as abas Todo List e Kanban é feita pelos signals/slots do Qt: qualquer alteração emitida pelo `TaskService` é recebida por ambos os widgets simultaneamente.

### Regras de dependência entre módulos

```
utils/constants.py ──► models/enums.py
      ▲                     ▲
      │                     │
      └──── models/task.py ─┘
              ▲
              │
         database/* ──► services/* ──► ui/*
```

- `models/enums.py` é o único módulo de domínio que **não importa nada** do projeto — serve de base para quebrar ciclos.
- `utils/constants.py` importa apenas de `models/enums.py` (para o mapeamento `COR_PRIORIDADE`).
- Camadas superiores só importam das inferiores; nunca o contrário.

---

## Stack técnico

| Tecnologia | Versão | Justificativa |
|------------|--------|--------------|
| **Python** | 3.11+ | `StrEnum`, `match/case`, `from __future__ import annotations`; ecossistema robusto para desktop |
| **PyQt6** | 6.6+ | Melhor suporte a drag-and-drop nativo (`QDrag`, `QMimeData`, `QDropEvent`) entre os frameworks Python; widgets ricos; estilização via QSS; signals/slots para desacoplamento |
| **SQLite / sqlite3** | stdlib | Zero dependências extras; ACID; suporta 10k+ registros sem degradação; arquivo único portável para backup |
| **uv** | — | Gerenciador de pacotes moderno (escrito em Rust): rápido, substitui pip + venv + pip-tools |
| **ruff** | 0.4+ | Substitui flake8 + isort + black; configuração unificada em `pyproject.toml` |
| **mypy** | 1.9+ | Type checking estático em modo `--strict`; garante segurança nas interfaces entre camadas |
| **pytest + pytest-qt** | 7+ / 4+ | `pytest-qt` expõe o `qtbot` para simular interações de UI (cliques, teclado, drag) |

> Consulte [docs/adr-001-stack.md](docs/adr-001-stack.md) para a análise completa de alternativas avaliadas.

---

## Decisões arquiteturais (ADRs)

Decisões técnicas não óbvias estão registradas em `docs/` no formato ADR (contexto → problema → alternativas → decisão → consequências):

| ADR | Tema | Status |
|-----|------|--------|
| [ADR-001](docs/adr-001-stack.md) | Escolha do stack técnico (PyQt6, SQLite, MVP, signals/slots) | Aceito |
| [ADR-002](docs/adr-002-unicode-search.md) | Busca case-insensitive Unicode no SQLite via `PY_UPPER` (função Python registrada) | Aceito |
| [ADR-003](docs/adr-003-enums-module.md) | Extração de enums de domínio para `models/enums.py` (quebra dependência circular com `utils/constants.py`) | Aceito |
| [ADR-004](docs/adr-004-coluna-kanban-fk.md) | Adiamento da substituição de `coluna_kanban` (string) por `coluna_id` (FK) | Aceito (com revisão programada) |

---

## Dados locais

O banco de dados SQLite é salvo automaticamente em:

```
~/.own-board-list/data.db
```

O diretório é criado na primeira execução. Para fazer backup, basta copiar esse arquivo. Para resetar todos os dados, basta apagá-lo.

### Esquema e performance

- Tabelas: `tasks` e `kanban_columns` (PKs `TEXT` com UUID).
- Pragmas aplicadas pela `DatabaseConnection`: `foreign_keys = ON` e `journal_mode = WAL`.
- Índices (criados por `migrations.initialize_database`): `idx_tasks_coluna_kanban`, `idx_tasks_status`, `idx_tasks_prioridade`, `idx_tasks_data_vencimento` — atendem o RNF-02 (10k tarefas sem degradação).
- Timestamps (`criado_em`, `atualizado_em`) armazenados em ISO 8601 timezone-aware (UTC).
- Transações compostas podem usar a conexão como context manager:

  ```python
  with db_connection:
      repo_a.update(...)
      repo_b.update(...)
  # commit automático; rollback em caso de exceção
  ```

- A busca de tarefas (`TaskRepository.search`) é case-insensitive com suporte a Unicode via função `PY_UPPER` registrada na conexão — detalhes em [ADR-002](docs/adr-002-unicode-search.md).

---

## Roadmap e próximos passos

O produto está na versão 0.1.x e segue evoluindo em pequenos ciclos. Há três documentos vivos que descrevem o rumo:

- [`CHANGELOG.md`](CHANGELOG.md) — histórico de mudanças visíveis ao usuário, por ciclo.
- [`docs/funcionalidades.md`](docs/funcionalidades.md) — **visão de produto completa** (16 histórias). As histórias marcadas como *Must Have* já estão implementadas; as *Should Have* / *Could Have* (busca na UI, filtros/ordenação, criar card diretamente no Kanban, gerenciar colunas do Kanban, detalhes do card em painel, exportação, tema escuro) estão pendentes de priorização nos próximos ciclos.
- [`docs/tasks.md`](docs/tasks.md) — plano técnico detalhado, incluindo as **13 dívidas técnicas remanescentes** do ciclo atual, cada uma com justificativa, esforço estimado e critérios de aceite.

Sugestões de feature, feedback ou priorização são bem-vindos via issue.

---

## Licença

MIT — veja [LICENSE](LICENSE) para detalhes.
