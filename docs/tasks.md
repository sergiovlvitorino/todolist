# Breakdown Técnico de Tasks

**Projeto:** Own Board List — Gestor de Tarefas Desktop
**Data inicial:** 2026-04-16
**Última atualização:** 2026-04-20 (fechamento US-07 — code review TL + DTs DT-031 a DT-035)
**Autor:** Tech Lead (agente tl-python)

---

## Sumário

Este documento consolida três tipos de itens de trabalho técnico:

1. **Breakdown de Implementação (TASK-001 a TASK-028):** plano original de desenvolvimento por fases (Setup, MVP, Should Have, Could Have), derivado do roadmap funcional e do ADR-001.
2. **Plano incremental US-07 (TASK-029 a TASK-036):** desdobramento técnico da história "Busca de tarefas por texto na Todo List", entregue pelo PO em 2026-04-19. Backend já existe — resta UI + wiring + hardening de wildcards.
3. **Catálogo de Dívidas Técnicas (DT-001 a DT-030):** itens identificados em análises automáticas do código existente ao longo dos ciclos de desenvolvimento. Cada item tem status, prioridade, esforço, localização e critérios de aceite.

As numerações (TASK-XXX e DT-XXX) são independentes e não conflitam.

---

## Estimativas

- **P (Pequena):** até 2 horas
- **M (Média):** 2–6 horas
- **G (Grande):** 6–16 horas

---

## Estrutura de Diretórios do Projeto

```
own-board-list/
├── pyproject.toml
├── uv.lock
├── README.md
├── docs/
│   ├── funcionalidades.md
│   ├── adr-001-stack.md
│   └── tasks.md
├── src/
│   └── own_board_list/
│       ├── __init__.py
│       ├── main.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── task.py
│       │   └── kanban_column.py
│       ├── database/
│       │   ├── __init__.py
│       │   ├── connection.py
│       │   ├── migrations.py
│       │   ├── task_repository.py
│       │   └── column_repository.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── task_service.py
│       │   └── export_service.py
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── main_window.py
│       │   ├── todo/
│       │   │   ├── __init__.py
│       │   │   ├── todo_widget.py
│       │   │   ├── task_form.py
│       │   │   └── task_list_item.py
│       │   ├── kanban/
│       │   │   ├── __init__.py
│       │   │   ├── kanban_widget.py
│       │   │   ├── kanban_column_widget.py
│       │   │   ├── kanban_card_widget.py
│       │   │   └── card_detail_panel.py
│       │   ├── dialogs/
│       │   │   ├── __init__.py
│       │   │   ├── confirm_dialog.py
│       │   │   └── export_dialog.py
│       │   └── theme/
│       │       ├── __init__.py
│       │       ├── theme_manager.py
│       │       ├── light.qss
│       │       └── dark.qss
│       └── utils/
│           ├── __init__.py
│           └── constants.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_models/
    │   ├── __init__.py
    │   └── test_task.py
    ├── test_database/
    │   ├── __init__.py
    │   ├── test_task_repository.py
    │   └── test_column_repository.py
    ├── test_services/
    │   ├── __init__.py
    │   └── test_task_service.py
    └── test_ui/
        ├── __init__.py
        ├── test_todo_widget.py
        └── test_kanban_widget.py
```

---

## Fase 0 — Setup do Projeto

### TASK-001 — Inicializar projeto com uv e pyproject.toml

**Descrição técnica:**
Criar o `pyproject.toml` com metadados do projeto, dependências de produção (PyQt6) e desenvolvimento (ruff, mypy, pytest, pytest-qt, pytest-cov, pyinstaller). Configurar seções `[tool.ruff]`, `[tool.mypy]` e `[tool.pytest.ini_options]` no mesmo arquivo. Inicializar o ambiente virtual com `uv sync`. Configurar o entry point `own-board-list = "own_board_list.main:main"`.

**Arquivos a criar:**
- `pyproject.toml`

**Estimativa:** P
**Dependências:** nenhuma

---

### TASK-002 — Criar estrutura de diretórios e pacotes

**Descrição técnica:**
Criar toda a árvore de diretórios conforme a estrutura definida acima. Cada diretório Python deve conter um `__init__.py`. O arquivo `src/own_board_list/__init__.py` deve exportar `__version__`. O arquivo `main.py` deve conter a função `main()` com a inicialização mínima da `QApplication` e exibição de uma janela vazia, para validar que o setup funciona.

**Arquivos a criar:**
- Todos os `__init__.py` listados na estrutura
- `src/own_board_list/main.py` (esqueleto mínimo)

**Estimativa:** P
**Dependências:** TASK-001

---

### TASK-003 — Configurar ruff, mypy e pytest

**Descrição técnica:**
Validar que `ruff check .` e `ruff format --check .` passam no esqueleto. Configurar `mypy` com `strict = true` e paths apontando para `src/`. Criar `tests/conftest.py` com fixtures básicas: `db_connection` (SQLite `:memory:`) e importação do `qtbot` do pytest-qt. Rodar `pytest` e garantir que a suíte (vazia) passa. Adicionar um script `justfile` ou seção `[project.scripts]` com comandos de conveniência (`lint`, `format`, `typecheck`, `test`).

**Arquivos a criar/modificar:**
- `pyproject.toml` (ajustes de configuração)
- `tests/conftest.py`

**Estimativa:** P
**Dependências:** TASK-002

---

### TASK-004 — Definir constantes e enums do domínio

**Descrição técnica:**
Criar o módulo `constants.py` com: enum `Prioridade` (BAIXA, MEDIA, ALTA), enum `StatusTarefa` (PENDENTE, CONCLUIDA), constantes para nomes das colunas padrão do Kanban ("A Fazer", "Em Andamento", "Concluído"), limite de caracteres do título (200) e demais valores reutilizáveis. Usar `enum.StrEnum` (Python 3.11+) para compatibilidade com serialização.

**Arquivos a criar:**
- `src/own_board_list/utils/constants.py`

**Testes:**
- `tests/test_models/test_task.py` (testar que os enums existem e têm os valores esperados — pode ser incluído na TASK-005)

**Estimativa:** P
**Dependências:** TASK-002

---

## Fase 1 — MVP

### TASK-005 — Implementar modelo de dados Task

**Descrição técnica:**
Criar a dataclass `Task` em `models/task.py` com todos os campos especificados: `id` (UUID como string), `titulo` (str, obrigatório, máx. 200 chars), `descricao` (str, opcional), `prioridade` (Prioridade, padrão MEDIA), `data_vencimento` (date | None), `status` (StatusTarefa, padrão PENDENTE), `coluna_kanban` (str, padrão "A Fazer"), `posicao_kanban` (int, padrão 0), `criado_em` (datetime, auto), `atualizado_em` (datetime, auto). Implementar validação no `__post_init__`: título não vazio, máximo 200 chars. Adicionar métodos `marcar_concluida()`, `reabrir()`, `to_dict()`, `from_dict()`.

**Arquivos a criar:**
- `src/own_board_list/models/task.py`

**Testes:**
- `tests/test_models/test_task.py` — criação válida, validações, conversão dict

**Estimativa:** M
**Dependências:** TASK-004

---

### TASK-006 — Implementar modelo de dados KanbanColumn

**Descrição técnica:**
Criar a dataclass `KanbanColumn` em `models/kanban_column.py` com campos: `id` (UUID como string), `nome` (str, obrigatório), `posicao` (int), `criado_em` (datetime, auto). Validação: nome não vazio. Métodos `to_dict()`, `from_dict()`.

**Arquivos a criar:**
- `src/own_board_list/models/kanban_column.py`

**Testes:**
- Incluir em `tests/test_models/test_task.py` ou criar arquivo separado

**Estimativa:** P
**Dependências:** TASK-004

---

### TASK-007 — Implementar camada de conexão e migrações SQLite

**Descrição técnica:**
Criar `database/connection.py` com classe `DatabaseConnection` que gerencia a conexão SQLite. O caminho padrão do banco será `~/.own-board-list/data.db` (usar `platformdirs` ou path manual). Implementar context manager para transações. Criar `database/migrations.py` com função `initialize_database(conn)` que cria as tabelas `tasks` e `kanban_columns` com os campos correspondentes, usando `CREATE TABLE IF NOT EXISTS`. Criar índices em `status`, `prioridade`, `coluna_kanban` e `data_vencimento`. Inserir as 3 colunas padrão ("A Fazer", "Em Andamento", "Concluído") se a tabela estiver vazia.

**Arquivos a criar:**
- `src/own_board_list/database/connection.py`
- `src/own_board_list/database/migrations.py`

**Testes:**
- `tests/test_database/test_task_repository.py` (fixture de DB em memória no conftest — os testes de migração podem ser o primeiro test case)

**Estimativa:** M
**Dependências:** TASK-005, TASK-006

---

### TASK-008 — Implementar TaskRepository (CRUD de tarefas)

**Descrição técnica:**
Criar `database/task_repository.py` com classe `TaskRepository` que recebe `DatabaseConnection` no construtor. Métodos: `create(task: Task) -> Task`, `get_by_id(id: str) -> Task | None`, `get_all() -> list[Task]`, `update(task: Task) -> Task`, `delete(id: str) -> bool`, `get_by_column(coluna: str) -> list[Task]` (ordenado por `posicao_kanban`), `update_position(id: str, coluna: str, posicao: int) -> None`, `search(query: str) -> list[Task]` (LIKE em titulo e descricao). Todas as operações devem atualizar o campo `atualizado_em`. Usar queries parametrizadas para segurança.

**Arquivos a criar:**
- `src/own_board_list/database/task_repository.py`

**Testes:**
- `tests/test_database/test_task_repository.py` — CRUD completo, busca, filtros

**Estimativa:** M
**Dependências:** TASK-007

---

### TASK-009 — Implementar ColumnRepository (CRUD de colunas)

**Descrição técnica:**
Criar `database/column_repository.py` com classe `ColumnRepository`. Métodos: `create(column: KanbanColumn) -> KanbanColumn`, `get_all() -> list[KanbanColumn]` (ordenado por `posicao`), `update(column: KanbanColumn) -> KanbanColumn`, `delete(id: str) -> bool`, `reorder(columns: list[str]) -> None` (recebe lista de IDs na nova ordem e atualiza as posições), `has_tasks(id: str) -> bool` (verifica se há tasks na coluna antes de permitir exclusão).

**Arquivos a criar:**
- `src/own_board_list/database/column_repository.py`

**Testes:**
- `tests/test_database/test_column_repository.py`

**Estimativa:** M
**Dependências:** TASK-007

---

### TASK-010 — Implementar TaskService (lógica de negócio + signals)

**Descrição técnica:**
Criar `services/task_service.py` com classe `TaskService(QObject)`. Esta classe é o coração da aplicação: encapsula toda a lógica de negócio e emite signals do Qt para que as views reajam. Signals: `task_created(Task)`, `task_updated(Task)`, `task_deleted(str)` (id), `tasks_reloaded(list)`. Métodos públicos: `create_task(...)`, `update_task(...)`, `delete_task(...)`, `toggle_status(id)`, `move_to_column(id, coluna, posicao)`, `get_all_tasks()`, `get_tasks_by_column(coluna)`, `search_tasks(query)`. O método `move_to_column` deve automaticamente atualizar `status` para CONCLUIDA se a coluna destino for "Concluído" (US-09) e reverter para PENDENTE ao sair de "Concluído". Cada operação de escrita deve: (1) validar, (2) persistir via repository, (3) emitir signal.

**Arquivos a criar:**
- `src/own_board_list/services/task_service.py`

**Testes:**
- `tests/test_services/test_task_service.py` — testar lógica de negócio, emissão de signals (usando `QSignalSpy` ou `qtbot.waitSignal`)

**Estimativa:** G
**Dependências:** TASK-008, TASK-009

---

### TASK-011 — Implementar janela principal com abas

**Descrição técnica:**
Criar `ui/main_window.py` com classe `MainWindow(QMainWindow)`. Configurar: título da janela ("Own Board List"), tamanho mínimo (1024x768), `QTabWidget` central com duas abas ("Todo List" e "Kanban"). Instanciar `DatabaseConnection`, `TaskService` e `ColumnRepository` como dependências compartilhadas. Configurar o menu bar com: Arquivo (Exportar, Sair), Configurações (Tema). Conectar atalho `Ctrl+Q` para sair. A janela é o ponto de composição — ela cria os services e os injeta nas views.

**Arquivos a criar:**
- `src/own_board_list/ui/main_window.py`

**Arquivos a modificar:**
- `src/own_board_list/main.py` (instanciar MainWindow)

**Estimativa:** M
**Dependências:** TASK-010

---

### TASK-012 — Implementar widget de item da Todo List

**Descrição técnica:**
Criar `ui/todo/task_list_item.py` com classe `TaskListItem(QWidget)`. Cada item exibe: checkbox de status, título (riscado se concluído), badge de prioridade (cor), data de vencimento (vermelho se vencida, conforme US-02). Layout horizontal com `QHBoxLayout`. Botões de ação: editar (ícone lápis), excluir (ícone lixeira). Signals emitidos: `status_toggled(str)`, `edit_requested(str)`, `delete_requested(str)` (emitem o id da task). O item recebe um objeto `Task` e se renderiza a partir dele.

**Arquivos a criar:**
- `src/own_board_list/ui/todo/task_list_item.py`

**Estimativa:** M
**Dependências:** TASK-011

---

### TASK-013 — Implementar formulário de criação/edição de tarefa

**Descrição técnica:**
Criar `ui/todo/task_form.py` com classe `TaskForm(QDialog)`. Campos: `QLineEdit` para título (com validação máx 200 chars), `QTextEdit` para descrição, `QComboBox` para prioridade, `QDateEdit` para data de vencimento (com checkbox "Sem data"). Botões: Salvar e Cancelar. O formulário pode receber uma `Task` existente para modo edição (preenche os campos) ou ser aberto vazio para criação. Signal: `task_saved(dict)` com os dados do formulário. Validação: título obrigatório — botão Salvar desabilitado se título vazio. Atalho `Ctrl+N` na aba Todo List abre este formulário (US-01).

**Arquivos a criar:**
- `src/own_board_list/ui/todo/task_form.py`

**Estimativa:** M
**Dependências:** TASK-011

---

### TASK-014 — Implementar widget principal da Todo List

**Descrição técnica:**
Criar `ui/todo/todo_widget.py` com classe `TodoWidget(QWidget)`. Layout: cabeçalho com botão "+ Nova Tarefa" e (placeholder para busca/filtros — será implementado na Fase 2). Corpo: `QScrollArea` contendo `QVBoxLayout` com seções agrupadas: "Hoje", "Próximas", "Sem data", "Concluídas" (conforme US-02). Cada seção é um `QGroupBox` colapsável. Dentro de cada seção, lista de `TaskListItem`. Conectar signals do `TaskService` para recarregar a lista automaticamente (`task_created`, `task_updated`, `task_deleted`). Método `_reload_tasks()` busca todas as tasks via service e re-renderiza as seções. Conectar checkbox para toggle de status (US-03), botão editar para abrir `TaskForm` (US-04), botão excluir com diálogo de confirmação (US-05).

**Arquivos a criar:**
- `src/own_board_list/ui/todo/todo_widget.py`
- `src/own_board_list/ui/dialogs/confirm_dialog.py`

**Testes:**
- `tests/test_ui/test_todo_widget.py` — testes básicos com qtbot (renderização, interação com botões)

**Estimativa:** G
**Dependências:** TASK-012, TASK-013

---

### TASK-015 — Implementar widget de card do Kanban

**Descrição técnica:**
Criar `ui/kanban/kanban_card_widget.py` com classe `KanbanCard(QFrame)`. Exibe: título, badge de prioridade (cor de fundo ou borda lateral colorida), data de vencimento. O card deve suportar drag: sobrescrever `mousePressEvent`, `mouseMoveEvent` para iniciar `QDrag` com `QMimeData` contendo o `task_id`. Definir visual via QSS (borda arredondada, sombra sutil). Ao clicar, emitir signal `card_clicked(str)` com o id da task. Menu de contexto (botão direito): "Mover para..." com submenu listando as colunas disponíveis (alternativa ao drag-and-drop, conforme US-09).

**Arquivos a criar:**
- `src/own_board_list/ui/kanban/kanban_card_widget.py`

**Estimativa:** M
**Dependências:** TASK-011

---

### TASK-016 — Implementar widget de coluna do Kanban

**Descrição técnica:**
Criar `ui/kanban/kanban_column_widget.py` com classe `KanbanColumnWidget(QFrame)`. Layout vertical: cabeçalho (nome da coluna + contador de cards), corpo (`QScrollArea` com `QVBoxLayout` contendo os cards), rodapé (placeholder para botão "+ Adicionar card" — implementação na Fase 2). Suportar drop: sobrescrever `dragEnterEvent`, `dragMoveEvent`, `dropEvent` para aceitar cards arrastados. No `dropEvent`, calcular a posição de inserção baseada na posição Y do drop e emitir signal `card_dropped(task_id, column_id, position)`. Indicador visual de drop zone (highlight da coluna durante drag-over). Método `add_card(task: Task)` e `clear_cards()` para gerenciar os cards.

**Arquivos a criar:**
- `src/own_board_list/ui/kanban/kanban_column_widget.py`

**Estimativa:** G
**Dependências:** TASK-015

---

### TASK-017 — Implementar widget principal do Kanban

**Descrição técnica:**
Criar `ui/kanban/kanban_widget.py` com classe `KanbanWidget(QWidget)`. Layout: `QScrollArea` horizontal contendo `QHBoxLayout` com as instâncias de `KanbanColumnWidget`. Ao inicializar, carrega todas as colunas via `ColumnRepository` e todas as tasks via `TaskService`, distribuindo os cards nas colunas corretas. Conectar signal `card_dropped` de cada coluna para chamar `task_service.move_to_column()`. Conectar signals do `TaskService` (`task_created`, `task_updated`, `task_deleted`) para recarregar o board (US-13 — sincronização). Método `_reload_board()` reconstrói todas as colunas e cards. Scroll horizontal automático quando há muitas colunas (US-08).

**Arquivos a criar:**
- `src/own_board_list/ui/kanban/kanban_widget.py`

**Testes:**
- `tests/test_ui/test_kanban_widget.py` — testes de renderização e interação básica

**Estimativa:** G
**Dependências:** TASK-016, TASK-010

---

### TASK-018 — Integrar sincronização entre abas (US-13)

**Descrição técnica:**
Garantir que os signals do `TaskService` estejam corretamente conectados tanto no `TodoWidget` quanto no `KanbanWidget`. Testar cenários: (1) criar tarefa na Todo List, verificar que aparece no Kanban na coluna "A Fazer"; (2) mover card para "Concluído" no Kanban, verificar que aparece como concluída na Todo List; (3) desmarcar tarefa na Todo List, verificar que o card volta para "A Fazer" no Kanban; (4) excluir tarefa em qualquer aba, verificar remoção na outra. Ajustar lógica se necessário: ao marcar como concluída na Todo List, mover para coluna "Concluído" no Kanban; ao desmarcar, mover de volta para "A Fazer".

**Arquivos a modificar:**
- `src/own_board_list/services/task_service.py` (ajustar lógica de toggle_status para sincronizar coluna)
- `src/own_board_list/ui/todo/todo_widget.py` (garantir conexão de signals)
- `src/own_board_list/ui/kanban/kanban_widget.py` (garantir conexão de signals)

**Testes:**
- `tests/test_services/test_task_service.py` — cenários de sincronização

**Estimativa:** M
**Dependências:** TASK-014, TASK-017

---

### TASK-019 — Testes de integração do MVP e polish

**Descrição técnica:**
Revisar e completar a cobertura de testes do MVP. Garantir que `ruff check`, `ruff format --check`, `mypy --strict` e `pytest` passam com zero erros. Ajustar type hints onde necessário. Testar manualmente os fluxos completos: criar/editar/excluir tarefa, drag-and-drop entre colunas, sincronização entre abas, persistência após fechar e reabrir. Corrigir bugs encontrados. Adicionar docstrings nos módulos públicos.

**Arquivos a modificar:**
- Todos os arquivos do MVP (revisão e ajustes)

**Estimativa:** G
**Dependências:** TASK-018

---

## Fase 2 — Should Have

### TASK-020 — Implementar filtros e ordenação na Todo List (US-06)

**Descrição técnica:**
Adicionar barra de filtros no `TodoWidget`: `QComboBox` para status (Todas/Pendentes/Concluídas), `QComboBox` para prioridade (Todas/Baixa/Média/Alta), `QComboBox` para ordenação (Data de criação, Data de vencimento, Prioridade, Título A-Z). Botão "Limpar filtros" que aparece somente quando algum filtro está ativo. Os filtros devem ser aplicados no lado do Python (filtrando a lista em memória) ou via query SQL parametrizada no `TaskRepository`. Persistir filtros durante a sessão (variáveis de instância, sem salvar em disco). Implementar método `get_filtered_tasks(status, prioridade, ordenacao)` no `TaskRepository` ou `TaskService`.

**Arquivos a modificar:**
- `src/own_board_list/ui/todo/todo_widget.py` (adicionar barra de filtros)
- `src/own_board_list/database/task_repository.py` (query com filtros)
- `src/own_board_list/services/task_service.py` (método de busca filtrada)

**Estimativa:** M
**Dependências:** TASK-019

---

### TASK-021 — Implementar busca por texto na Todo List (US-07)

**Descrição técnica:**
Adicionar `QLineEdit` de busca no topo do `TodoWidget` com placeholder "Buscar tarefas...". Conectar signal `textChanged` para filtrar em tempo real (debounce de 300ms com `QTimer` para evitar queries excessivas). A busca deve ser case-insensitive e pesquisar em `titulo` e `descricao`. Utilizar o método `search_tasks(query)` já definido no `TaskService` (que usa `LIKE` no SQLite). Exibir mensagem "Nenhuma tarefa encontrada" quando a busca não retornar resultados. A busca deve funcionar em conjunto com os filtros (TASK-020): busca texto dentro dos resultados filtrados.

**Arquivos a modificar:**
- `src/own_board_list/ui/todo/todo_widget.py` (adicionar campo de busca)
- `src/own_board_list/services/task_service.py` (garantir que search funciona com filtros)

**Estimativa:** M
**Dependências:** TASK-020

---

### TASK-022 — Implementar criação de card no Kanban (US-10)

**Descrição técnica:**
Adicionar botão "+ Adicionar card" no rodapé de cada `KanbanColumnWidget`. Ao clicar, exibir formulário inline (um `QLineEdit` que aparece no final da coluna para digitar o título rapidamente, similar ao Trello). Ao pressionar Enter, criar a task via `TaskService.create_task()` com a `coluna_kanban` correspondente. Ao pressionar Esc, cancelar. Para campos opcionais (descrição, prioridade, data), o usuário poderá editar depois via detalhes do card (TASK-024). A task criada aparecerá automaticamente na Todo List via sincronização de signals.

**Arquivos a modificar:**
- `src/own_board_list/ui/kanban/kanban_column_widget.py` (botão e formulário inline)

**Estimativa:** M
**Dependências:** TASK-019

---

### TASK-023 — Implementar gerenciamento de colunas do Kanban (US-11)

**Descrição técnica:**
Adicionar ao `KanbanWidget`: (1) Botão "+" no final da área de colunas para criar nova coluna — abre `QInputDialog` para nome. (2) Duplo clique no título da coluna transforma o `QLabel` em `QLineEdit` para renomear (confirma com Enter, cancela com Esc). (3) Menu de contexto na coluna (botão direito ou ícone "...") com opção "Excluir coluna" — ao clicar, verificar se há tasks (`column_repository.has_tasks()`); se houver, exibir aviso e bloquear exclusão; se não houver, confirmar e excluir. (4) Drag-and-drop de colunas inteiras para reordenação — implementar `QDrag` no cabeçalho da coluna e `dropEvent` no `KanbanWidget` para reordenar. (5) Mínimo de 1 coluna — desabilitar exclusão se restar apenas uma.

**Arquivos a modificar:**
- `src/own_board_list/ui/kanban/kanban_widget.py` (botão "+", reorder de colunas)
- `src/own_board_list/ui/kanban/kanban_column_widget.py` (rename, menu contexto, drag cabeçalho)
- `src/own_board_list/database/column_repository.py` (garantir `has_tasks` e `reorder`)

**Estimativa:** G
**Dependências:** TASK-019

---

### TASK-024 — Implementar painel de detalhes do card (US-12)

**Descrição técnica:**
Criar `ui/kanban/card_detail_panel.py` com classe `CardDetailPanel(QWidget)` que funciona como painel lateral (slide-in da direita) ou modal. Exibe todos os campos da task de forma editável: título (`QLineEdit`), descrição (`QTextEdit`), prioridade (`QComboBox`), data de vencimento (`QDateEdit`), status (checkbox), coluna atual (informativo). Exibe `criado_em` e `atualizado_em` como campos somente leitura. Alterações são salvas automaticamente ao perder foco de cada campo (auto-save) ou ao fechar o painel. Conectar signal `card_clicked` do `KanbanCard` para abrir este painel. Botão ou tecla Esc para fechar.

**Arquivos a criar:**
- `src/own_board_list/ui/kanban/card_detail_panel.py`

**Arquivos a modificar:**
- `src/own_board_list/ui/kanban/kanban_widget.py` (abrir painel ao clicar no card)

**Estimativa:** G
**Dependências:** TASK-019

---

### TASK-025 — Testes da Fase 2 e polish

**Descrição técnica:**
Escrever testes para filtros, busca, criação de card no Kanban, gerenciamento de colunas e painel de detalhes. Testar edge cases: busca com caracteres especiais, exclusão de coluna com/sem tasks, reordenação de colunas, auto-save do painel de detalhes. Garantir que `ruff`, `mypy` e `pytest` passam. Revisar performance com listas grandes (simular 100+ tarefas).

**Arquivos a modificar:**
- `tests/test_ui/test_todo_widget.py` (filtros, busca)
- `tests/test_ui/test_kanban_widget.py` (card inline, colunas, detalhes)
- `tests/test_database/test_column_repository.py` (has_tasks, reorder)

**Estimativa:** M
**Dependências:** TASK-020, TASK-021, TASK-022, TASK-023, TASK-024

---

## Fase 3 — Could Have

### TASK-026 — Implementar exportação de dados (US-15)

**Descrição técnica:**
Criar `services/export_service.py` com classe `ExportService`. Métodos: `export_json(tasks: list[Task], filepath: Path) -> None` (exporta lista de tasks como JSON com indentação), `export_csv(tasks: list[Task], filepath: Path) -> None` (exporta como CSV com cabeçalhos em português). Criar `ui/dialogs/export_dialog.py` com `QFileDialog` configurado para filtros "JSON (*.json)" e "CSV (*.csv)". Nome sugerido: `tarefas_YYYY-MM-DD.json` ou `.csv`. Adicionar ação "Exportar dados" no menu Arquivo da `MainWindow`. O export deve incluir todas as tarefas (sem filtro).

**Arquivos a criar:**
- `src/own_board_list/services/export_service.py`
- `src/own_board_list/ui/dialogs/export_dialog.py`

**Arquivos a modificar:**
- `src/own_board_list/ui/main_window.py` (ação no menu)

**Testes:**
- `tests/test_services/test_export_service.py` (verificar formato JSON e CSV gerados)

**Estimativa:** M
**Dependências:** TASK-019

---

### TASK-027 — Implementar tema claro/escuro (US-16)

**Descrição técnica:**
Criar `ui/theme/theme_manager.py` com classe `ThemeManager` que carrega e aplica stylesheets QSS. Métodos: `apply_light()`, `apply_dark()`, `toggle()`, `current_theme() -> str`. Criar `light.qss` e `dark.qss` com estilos para todos os widgets (fundo, texto, bordas, cards, colunas, botões, scrollbars). Persistir a preferência de tema em um arquivo de configuração simples (`~/.own-board-list/settings.json` ou no próprio SQLite em uma tabela `settings`). Adicionar ação "Alternar tema" no menu Configurações da `MainWindow` e/ou ícone de sol/lua na barra de título. Aplicar o tema salvo ao iniciar o aplicativo.

**Arquivos a criar:**
- `src/own_board_list/ui/theme/theme_manager.py`
- `src/own_board_list/ui/theme/light.qss`
- `src/own_board_list/ui/theme/dark.qss`

**Arquivos a modificar:**
- `src/own_board_list/ui/main_window.py` (menu e integração do ThemeManager)
- `src/own_board_list/database/migrations.py` (tabela settings, se usar SQLite)

**Estimativa:** G
**Dependências:** TASK-019

---

### TASK-028 — Testes finais, empacotamento e documentação

**Descrição técnica:**
Rodar suíte completa de testes com cobertura (`pytest --cov`). Alvo: >= 80% de cobertura nas camadas model, database e services. Configurar `PyInstaller` com `.spec` file para gerar executável: incluir arquivos `.qss`, ícone da aplicação, metadados. Testar executável gerado em pelo menos uma plataforma (Linux). Documentar no `README.md`: como instalar dependências (`uv sync`), como rodar (`uv run own-board-list`), como rodar testes (`uv run pytest`), como empacotar (`uv run pyinstaller`).

**Arquivos a criar:**
- `own-board-list.spec` (configuração do PyInstaller)

**Arquivos a modificar:**
- `README.md`
- `pyproject.toml` (se necessário para scripts de empacotamento)

**Estimativa:** G
**Dependências:** TASK-025, TASK-026, TASK-027

---

## Resumo por Fase

| Fase | Tasks | Estimativa total |
|------|-------|-----------------|
| **Fase 0 — Setup** | TASK-001 a TASK-004 | 4P = ~6h |
| **Fase 1 — MVP** | TASK-005 a TASK-019 | 5P + 5M + 5G = ~70h |
| **Fase 2 — Should Have** | TASK-020 a TASK-025 | 3M + 2G + 1M = ~36h |
| **Fase 3 — Could Have** | TASK-026 a TASK-028 | 1M + 2G = ~26h |
| **US-07 (incremento Fase 2)** | TASK-029 a TASK-036 | 6P + 2M = ~18–24h |
| **US-10 (incremento Fase 2)** | TASK-037 a TASK-046 | 7P + 3M = ~20–26h |
| **Total** | 36 tasks | ~156–162h |

---

## Grafo de Dependências (simplificado)

```
TASK-001 → TASK-002 → TASK-003
                    → TASK-004 → TASK-005 → TASK-007 → TASK-008 → TASK-010 → TASK-011
                               → TASK-006 → TASK-007 → TASK-009 → TASK-010

TASK-011 → TASK-012 → TASK-014 ──────────────────────────────┐
        → TASK-013 → TASK-014                                │
        → TASK-015 → TASK-016 → TASK-017 ────────────────────┤
                                                              ↓
                                                         TASK-018 → TASK-019
                                                                        │
                                                         ┌──────────────┤
                                                         ↓              ↓
                                                    TASK-020 → TASK-021  TASK-022
                                                    TASK-023             TASK-024
                                                         │              │
                                                         ↓              ↓
                                                         TASK-025 ──→ TASK-028
                                                    TASK-026 ──────→ TASK-028
                                                    TASK-027 ──────→ TASK-028
```

---

# Plano US-07 — Busca de tarefas por texto na Todo List

**História:** US-07 (PO, handoff 2026-04-19)
**Escopo:** UI + wiring no `TodoWidget` + hardening de wildcards no `TaskRepository.search`.
**Backend pré-existente:** `TaskService.search_tasks` e `TaskRepository.search` com `PY_UPPER` Unicode (ver ADR-002 e DT-021).
**Prioridade:** Alta — valor/esforço máximo, backend pronto, <= 1 sprint.

## Problema técnico

Usuário não consegue localizar tarefas em listas longas sem rolar toda a aba Todo List. Backend de busca já entrega resultados case-insensitive Unicode, mas a UI não expõe o recurso. Falta um campo de busca com debounce, reaplicação automática em eventos CRUD, atalho de foco e um tratamento correto de wildcards `%`/`_` no `LIKE`.

## Alternativas avaliadas e decisões

### D1 — Arquitetura do filtro: query no banco vs. filtro em memória

- **Opção A — Query no banco a cada tecla (usar `TaskService.search_tasks`):** simples, reusa código pronto, performance OK com índice + debounce. Retorna flat list — cabe ao widget redistribuir em "Hoje/Próximas/Sem data/Concluídas".
- **Opção B — `get_all_tasks()` uma vez e filtrar em memória via Python:** zero roundtrip ao banco por keystroke, mas duplica lógica de matching (Unicode upper + LIKE semântico) no client, criando risco de divergência com o backend (ADR-002).

**Escolha: A (query no banco).** Debounce 300ms já reduz carga; reuso de `search_tasks` mantém única fonte de verdade para matching Unicode. Redistribuição em seções é pura categorização por `status`/`data_vencimento`, não duplica lógica de busca.
**Reversibilidade:** alta — trocar para B é uma refatoração local do `_reload_tasks`.

### D2 — Debounce: `QTimer` vs. signal throttle manual vs. async

- **Opção A — `QTimer.singleShot` reinicializado a cada `textChanged`:** idiomático Qt, testável injetando intervalo = 0 nos testes.
- **Opção B — Throttle manual com `time.monotonic()`:** não-idiomático, propenso a bugs, não integra com event loop Qt.
- **Opção C — `asyncio` / qasync:** dep nova, overkill para o caso.

**Escolha: A (`QTimer.singleShot` com timer reutilizável).** Convenção Qt, zero deps novas. Para testabilidade, aceitar parâmetro `debounce_ms: int = 300` no `__init__` do `TodoWidget` — testes passam `0` para execução síncrona (ou usam `qtbot.wait`).
**Reversibilidade:** alta.

### D3 — Escape de wildcards `%` e `_` no `LIKE`

Situação atual: `TaskRepository.search()` interpola `f"%{query.upper()}%"` sem escapar. Usuário digitando `"50%"` recebe matching excessivo; digitando `"a_b"` também.

- **Opção A — Escape explícito com `ESCAPE '\'` no SQL:** substituir `%` → `\%`, `_` → `\_`, `\` → `\\` antes da interpolação, e adicionar `ESCAPE '\\'` à cláusula `LIKE`. Seguro, portável, 4 linhas de código.
- **Opção B — Usar `instr(PY_UPPER(col), PY_UPPER(?)) > 0` ao invés de `LIKE`:** elimina wildcards como mecanismo, mas muda semântica e pode regredir o suporte Unicode (depende de como `instr` trata bytes vs. chars).
- **Opção C — Validar/rejeitar termos contendo `%`/`_`:** afeta UX (usuário pode querer buscar esses literais).

**Escolha: A (escape explícito + `ESCAPE '\\'`).** Único lugar tocado é `TaskRepository.search`. Testes de regressão garantem que buscas existentes continuam funcionando e novos testes cobrem os casos `%`, `_`, `\`.
**Reversibilidade:** alta — mudança localizada numa função.
**Observação:** SQL injection já mitigada por queries parametrizadas (parâmetros `?`); o escape trata apenas wildcards como literais, não segurança.

### D4 — Onde guardar o termo de busca

- **Opção A — Atributo de instância `self._search_term: str` no `TodoWidget`:** simples, KISS, sessão-scoped (não persiste entre sessões conforme AC).
- **Opção B — Estender `TaskService` com estado de busca:** viola SRP (service = orquestração, não estado de UI) e cria acoplamento entre Todo e Kanban.

**Escolha: A.** Termo é estado local da view.
**Reversibilidade:** alta.

### D5 — Termo vazio / só-espaços equivale a "sem busca"

Normalizar via `stripped = query.strip()`. Se vazio, chamar `get_all_tasks()` ao invés de `search_tasks("")`. Evita round-trip desnecessário e mantém semântica clara.

### D6 — Não criar `SearchService` separado (KISS)

A busca é uma single-query passthrough. Abstração prematura piora legibilidade sem ganho. Manter `TaskService.search_tasks` como ponto único.

## Impacto

- **Módulos tocados (produção):** 2
  - `src/own_board_list/ui/todo/todo_widget.py` (novo: QLineEdit, QTimer, slots, redistribuição com filtro ativo)
  - `src/own_board_list/database/task_repository.py` (escape de wildcards em `search()`)
- **Módulos tocados (testes):** 3-4
  - `tests/test_database/test_task_repository.py` (casos `%`, `_`, `\`)
  - `tests/test_ui/test_todo_widget.py` (campo busca, debounce, Ctrl+F, Esc, reaplicação em CRUD)
  - `tests/test_integration/test_fluxo_completo.py` ou novo `test_fluxo_busca.py` (UI + service + DB com Unicode / edge cases)
  - `tests/test_ui/test_todo_widget_performance.py` (novo, opcional, marcado `@pytest.mark.slow`)
- **Esforço total estimado:** ~3-4 dias (1 sprint folgada). Dentro do budget de <= 1 semana e <= 5 módulos.
- **Deps novas:** 0.
- **Risco:** baixo. Backend estável; mudança de UI é aditiva; escape de wildcards é correção pontual com testes cobrindo regressão.

## Plano de migração/implementação

1. [x] **TASK-029** (dev) — Hardening: escape de `%`/`_`/`\` + `ESCAPE '\\'` em `TaskRepository.search`. Testes antes de qualquer UI.
2. [x] **TASK-030** (dev) — QLineEdit + QTimer debounce no `TodoWidget`, parâmetro `debounce_ms` injetável.
3. [x] **TASK-031** (dev) — Integração do filtro com redistribuição por seções + mensagem "Nenhuma tarefa encontrada" quando global vazia.
4. [x] **TASK-032** (dev) — Atalho `Ctrl+F` (foco no campo) + botão limpar (X) + tecla `Esc` (limpa termo e devolve foco à lista).
5. [x] **TASK-033** (dev) — Wiring com signals de CRUD do `TaskService` reaplicando `self._search_term` no `_reload_tasks`.
6. **TASK-034** (qa) — Testes unitários de UI: debounce (injetando 0ms), Ctrl+F, Esc, botão X, foco pós-TaskForm.
7. **TASK-035** (qa) — Testes de integração UI+Service+DB: Unicode, SQL wildcards, só-espaços, seções vazias, reaplicação pós-CRUD.
8. **TASK-036** (qa) — Teste de performance com 1k-5k tarefas (`pytest.mark.slow`, threshold documentado).

Ordem sugerida de execução: **T029 -> T030 -> T031 -> T032 -> T033** (dev-python serial), **T034 | T035 | T036** (qa em paralelo ao final, dependentes de T029-T033).

## Critério de rollback

Critérios de monitoramento pós-merge (primeiros 7 dias):
- Se teste de performance regredir threshold em >= 20% -> desabilitar debounce (intervalo 0) ou aumentar para 500ms.
- Se bug crítico em escape de wildcards aparecer -> reverter apenas o commit do escape (TASK-029) e manter UI funcional com comportamento antigo de `LIKE` (aceita falso positivo temporário).
- Se UI quebrar reload com filtro ativo -> feature flag local: atributo `self._search_enabled: bool = False` no `__init__` esconde o QLineEdit e cai no comportamento anterior. Commit dedicado para facilitar `git revert`.

Como o escopo é aditivo e isolado em 2 módulos de produção, `git revert` dos commits das tasks T029-T033 restaura o estado anterior sem colateral.

## ADR

Não requer ADR completo: não é decisão estrutural (nenhum framework/stack/padrão arquitetural muda). Decisões D1-D6 ficam registradas inline neste plano e como ADR-lites nas tasks correspondentes.

---

## Fase 2 (continuação) — US-07 Busca de tarefas por texto

### TASK-029 — Escapar wildcards LIKE (`%`, `_`, `\`) em `TaskRepository.search`

**Descrição técnica:**
Corrigir a implementação atual de `TaskRepository.search` que interpola o termo diretamente em `f"%{query.upper()}%"` sem escapar caracteres coringa do operador `LIKE`. Isso faz com que termos legítimos contendo `%` ou `_` retornem resultados incorretos (ex.: buscar `"50%"` mataria todo o filtro). Solução: aplicar escape dos três caracteres (`\` primeiro, depois `%` e `_`) antes de compor o pattern e adicionar `ESCAPE '\\'` à cláusula LIKE. Manter uso de `PY_UPPER` conforme ADR-002.

**Arquivos a modificar:**
- `src/own_board_list/database/task_repository.py` (função `search`)

**Critérios de aceite técnicos:**
- [ ] Busca por `"50%"` retorna apenas tarefas cujo título ou descrição contêm literalmente `"50%"`.
- [ ] Busca por `"a_b"` retorna apenas tarefas contendo literalmente `"a_b"` (underscore tratado como literal, não wildcard de 1-char).
- [ ] Busca por `"c:\path"` retorna apenas tarefas com essa substring literal.
- [ ] Query parametrizada preservada (injeção SQL continua mitigada).
- [ ] `PY_UPPER` continua aplicado em ambos os lados para manter matching Unicode case-insensitive.
- [ ] Testes existentes (`test_search_*`) continuam verdes.

**Testes a adicionar (nesta mesma task, pelo dev — são testes próximos da unidade):**
- `test_search_escapa_percent` — cria 2 tasks, uma com `"50%"` no título e outra com `"desconto"`; busca `"50%"` retorna só a primeira.
- `test_search_escapa_underscore` — task com `"a_b"` e task com `"aXb"`; busca `"a_b"` retorna só a primeira.
- `test_search_escapa_backslash` — task com `"c:\dir"`; busca `"c:\dir"` retorna a task.

**ADR-lite inline:**
```
[DECISÃO] Escape de wildcards LIKE com ESCAPE '\\'.
  Alternativas: A) escape explicito + ESCAPE | B) substituir LIKE por instr() | C) validar/rejeitar termos com %/_
  Escolha: A
  Por quê: mínima mudança, preserva ADR-002 (PY_UPPER), cobre casos reais sem limitar UX.
  Reversibilidade: alta (função isolada).
```

**Estimativa:** P
**Dependências:** nenhuma (backend pronto)
**Responsável sugerido:** dev-python

---

### TASK-030 — Adicionar campo de busca (QLineEdit) e debounce no `TodoWidget`

**Descrição técnica:**
Inserir um `QLineEdit` no topo do `TodoWidget`, acima das seções "Hoje / Próximas / Sem data / Concluídas", com placeholder `"Buscar tarefas..."`. Conectar o signal `textChanged` a um slot que reinicia um `QTimer` (single-shot) com intervalo configurável (padrão 300ms). Quando o timer dispara, o slot `_apply_search_filter` é chamado e atualiza `self._search_term` + invoca `_reload_tasks`. O construtor aceita o parâmetro `debounce_ms: int = 300` para permitir injetar `0` em testes (execução síncrona). Normalizar termo: `stripped = query.strip()`; se vazio, trata como "sem busca" e usa `get_all_tasks()`.

**Arquivos a modificar:**
- `src/own_board_list/ui/todo/todo_widget.py`

**Critérios de aceite técnicos (pareados aos AC PO):**
- [ ] `QLineEdit` visível no topo do `TodoWidget` com placeholder correto.
- [ ] `QTimer` reiniciado a cada keystroke; após 300ms de inatividade chama `_apply_search_filter`.
- [ ] Termo vazio ou só-espaços equivale a "sem busca" (AC PO: "termo vazio ou só espaços equivale a sem busca").
- [ ] Campo não persiste entre sessões: reabrir a aplicação retorna com campo vazio (AC PO: "campo não persiste entre sessões"). Como `TodoWidget` é instanciado a cada abertura, basta não persistir.
- [ ] Construtor aceita `debounce_ms: int = 300` para testabilidade.
- [ ] `self._search_term: str = ""` como atributo de instância, inicializado vazio.
- [ ] Type hints completos, docstrings em português.

**ADR-lite inline:**
```
[DECISÃO] Debounce com QTimer single-shot e parâmetro debounce_ms injetável.
  Alternativas: A) QTimer idiomático | B) throttle manual com time.monotonic | C) asyncio
  Escolha: A
  Por quê: idiomático Qt, zero deps, testável com debounce_ms=0.
  Reversibilidade: alta.
```

**Estimativa:** P
**Dependências:** TASK-029 (para já usar a busca saneada)
**Responsável sugerido:** dev-python

---

### TASK-031 — Aplicar filtro por seções e mensagem "Nenhuma tarefa encontrada"

**Descrição técnica:**
Modificar `TodoWidget._reload_tasks` para: (1) se `self._search_term` (stripped) estiver vazio, chamar `self._task_service.get_all_tasks()` como hoje; (2) caso contrário, chamar `self._task_service.search_tasks(self._search_term)`; (3) manter o mesmo pipeline de categorização por `status` e `data_vencimento` em "Hoje / Próximas / Sem data / Concluídas" — ou seja, o filtro é ortogonal às seções. Quando a busca retorna lista global vazia (nenhuma task em nenhuma seção) E há termo ativo, exibir uma única linha "Nenhuma tarefa encontrada" no lugar dos grupos, ou manter as seções e em cada uma exibir "Nenhuma tarefa" como hoje — a UX final é: mensagem agregada "Nenhuma tarefa encontrada" no topo do scroll_content, abaixo do campo de busca. Seções vazias mantêm layout (mesmo sem itens).

**Arquivos a modificar:**
- `src/own_board_list/ui/todo/todo_widget.py` (método `_reload_tasks` e UI auxiliar)

**Critérios de aceite técnicos (pareados aos AC PO):**
- [ ] Com termo vazio, comportamento atual preservado (AC: "termo vazio equivale a sem busca").
- [ ] Com termo, apenas tasks matching título/descrição aparecem (AC: "procura em título e descrição").
- [ ] Seções "Hoje/Próximas/Sem data/Concluídas" mantidas com filtro aplicado (AC: "seções mantidas com filtro aplicado por seção").
- [ ] Quando busca global vazia, exibe "Nenhuma tarefa encontrada" visível (AC: "mensagem quando busca global vazia").
- [ ] Case-insensitive Unicode preservado via `search_tasks` (AC: "case-insensitive e Unicode").
- [ ] Procura em título E descrição (AC: "procura em título e descrição") — delegado a `TaskRepository.search` que já faz OR.
- [ ] Seções vazias mantêm layout sem quebrar (AC qa: "seções vazias mantêm layout").

**Estimativa:** P
**Dependências:** TASK-030
**Responsável sugerido:** dev-python

---

### TASK-032 — Atalho `Ctrl+F`, botão limpar (X) e tecla `Esc`

**Descrição técnica:**
(1) Registrar `QShortcut(QKeySequence("Ctrl+F"), self)` no `TodoWidget` conectado a `self._search_input.setFocus() + self._search_input.selectAll()`. Coexiste com `Ctrl+N` já registrado (qa validará ausência de conflito). (2) Botão limpar dentro do `QLineEdit`: usar `QLineEdit.setClearButtonEnabled(True)` — recurso nativo Qt, zero código extra. Alternativamente/adicionalmente, ao pressionar `Esc` com o foco no campo, limpar o termo e devolver foco à lista/scroll area — implementar via subclasse ou `eventFilter` no `QLineEdit` OU conectar `QAction` interno. **Escolha: subclasse mínima ou `installEventFilter` no widget** (manter simples — preferir `eventFilter` para evitar nova classe).

**Arquivos a modificar:**
- `src/own_board_list/ui/todo/todo_widget.py`

**Critérios de aceite técnicos (pareados aos AC PO):**
- [ ] `Ctrl+F` foca o campo de busca (AC: "atalho Ctrl+F foca o campo").
- [ ] `Ctrl+F` não conflita com `Ctrl+N` existente (ambos disparam sua ação correspondente).
- [ ] Botão X nativo do `QLineEdit` visível quando há texto, limpa o campo ao clicar (AC: "botão limpar X").
- [ ] `Esc` com foco no campo limpa o texto e devolve foco ao scroll area (AC: "tecla Esc").
- [ ] Clique em X ou `Esc` dispara o mesmo fluxo de reload com termo vazio, restaurando a lista completa (AC: "restaura lista completa").

**ADR-lite inline:**
```
[DECISÃO] Usar QLineEdit.setClearButtonEnabled(True) + eventFilter para Esc.
  Alternativas: A) botão X customizado + subclasse de QLineEdit | B) setClearButtonEnabled nativo + eventFilter para Esc
  Escolha: B
  Por quê: nativo Qt, menor superfície de código, testável.
  Reversibilidade: alta.
```

**Estimativa:** P
**Dependências:** TASK-030
**Responsável sugerido:** dev-python

---

### TASK-033 — Reaplicação do filtro em eventos CRUD (create/update/delete)

**Descrição técnica:**
Garantir que, com filtro ativo, qualquer operação CRUD reaplique o filtro automaticamente. Os signals `task_created`, `task_updated`, `task_deleted`, `tasks_reloaded` do `TaskService` já estão conectados a `self._reload_tasks`. O `_reload_tasks` (modificado na TASK-031) já respeita `self._search_term`. Esta task é um **wiring check** + teste de regressão: validar que a cadeia completa funciona — incluindo o cenário "abrir TaskForm com busca ativa, salvar, voltar com campo preenchido e lista filtrada". **Sem mudança de código de produção se TASK-031 foi implementada corretamente** — a task garante que nenhum caminho alternativo (ex.: `_on_form_saved`) chama reload sem passar pelo `_reload_tasks` centralizado.

**Arquivos a revisar/modificar:**
- `src/own_board_list/ui/todo/todo_widget.py` (confirmar fluxos)

**Critérios de aceite técnicos (pareados aos AC PO):**
- [ ] Criar tarefa com busca ativa: se matching, aparece na lista filtrada; se não, fica oculta até limpar o filtro (AC qa: "create/edit/delete com busca ativa reaplica o filtro").
- [ ] Editar tarefa com busca ativa: se título/descrição alterados removerem o match, sai da lista filtrada; se passarem a matching, aparecem.
- [ ] Deletar tarefa: some da lista filtrada.
- [ ] Ao abrir TaskForm com busca ativa e voltar (salvar/cancelar), o campo de busca continua preenchido (AC qa: "foco pós-TaskForm").

**Estimativa:** P
**Dependências:** TASK-031, TASK-032
**Responsável sugerido:** dev-python

---

### TASK-034 — Testes unitários de UI do campo de busca

**Descrição técnica:**
Cobrir o comportamento isolado do campo de busca no `TodoWidget`, usando `pytest-qt` e `debounce_ms=0` para evitar dependência de timer real. Cenários mínimos:

1. **Renderização:** `QLineEdit` presente, placeholder correto, botão clear habilitado.
2. **Debounce:** com `debounce_ms=300`, digitar 3 caracteres em sequência rápida dispara apenas 1 chamada a `search_tasks` (usar `qtbot.wait`).
3. **Debounce síncrono:** com `debounce_ms=0`, cada keystroke dispara reload imediatamente (facilita asserts).
4. **Último estado vence:** simular digitação e verificar que o termo final do campo é o usado em `search_tasks` (AC qa: "último estado do QLineEdit deve vencer").
5. **`Ctrl+F`:** disparar atalho, verificar que `QLineEdit` recebe foco.
6. **`Ctrl+F` vs. `Ctrl+N`:** ambos os atalhos funcionam; `Ctrl+N` continua abrindo TaskForm; `Ctrl+F` não abre o form.
7. **Botão X (setClearButtonEnabled):** após digitar, simular click no action de clear, verificar que termo volta a vazio e lista completa é restaurada.
8. **`Esc`:** com foco no campo e texto digitado, pressionar Esc -> campo limpo, foco sai do QLineEdit.
9. **Termo só-espaços:** digitar `"   "` não filtra (lista completa).
10. **Foco pós-TaskForm:** digitar termo, abrir TaskForm (mockar ou usar qtbot), fechar; campo de busca continua preenchido.

**Arquivos a criar/modificar:**
- `tests/test_ui/test_todo_widget.py` (acrescentar classe `TestTodoWidgetBusca`)

**Critérios de aceite técnicos:**
- [ ] Todos os 10 cenários acima verdes.
- [ ] Nenhum teste depende de `QTimer` real (sempre `debounce_ms=0` OU `qtbot.wait` explícito com timeout determinístico).
- [ ] Cobertura do campo de busca no `TodoWidget` >= 90%.
- [ ] `ruff` e `mypy --strict` limpos.

**Estimativa:** M
**Dependências:** TASK-030, TASK-031, TASK-032, TASK-033
**Responsável sugerido:** qa

---

### TASK-035 — Testes de integração UI + Service + DB para busca

**Descrição técnica:**
Cobrir o fluxo completo da busca com DB em memória real — sem mocks do repositório. Cenários (alinhados com DT-023: classificação como "integração"):

1. **Unicode case-insensitive:** criar tasks com `"Reunião"`, `"reuniao"`, `"outra"`. Buscar `"reuniao"` encontra ambas as duas primeiras.
2. **Acentos e ç:** tasks com `"ação"`, `"acao"`, `"preço"`. Buscar `"acao"` e `"preco"` retorna matching apropriado via `PY_UPPER`.
3. **Emojis:** task com título `"Tarefa 🎯"`. Buscar `"🎯"` encontra a task.
4. **SQL wildcards `%` e `_`:** tasks com `"50%"`, `"a_b"`, `"percentual"`. Buscar `"50%"` só retorna a primeira (regressão de TASK-029). Buscar `"a_b"` só retorna a segunda.
5. **Aspas simples e duplas:** task com `"it's"` e `"quote\"ok"`. Busca deve funcionar sem erro (injeção SQL já mitigada por parametrização).
6. **Termo só-espaços:** com tasks no banco, busca `"   "` retorna lista completa (reuso de `get_all_tasks`).
7. **Termo vazio:** idem (retorna lista completa).
8. **Seções vazias com filtro:** criar apenas tasks concluídas; buscar termo que casa — "Concluídas" populada, demais seções mostram "Nenhuma tarefa" sem quebra de layout.
9. **Reaplicação pós-create:** com filtro ativo `"bug"`, criar task `"Corrigir bug"` -> aparece na lista filtrada. Criar task `"Feature nova"` -> não aparece.
10. **Reaplicação pós-update:** task `"Bug login"` com filtro `"bug"` ativo; renomear para `"Login OK"` -> some da lista filtrada.
11. **Reaplicação pós-delete:** deletar task visível -> some imediatamente.
12. **Busca global vazia:** com 3 tasks no banco, buscar `"zzzz"` -> mensagem "Nenhuma tarefa encontrada" visível, seções vazias ou ocultas conforme decisão de TASK-031.

**Arquivos a criar:**
- `tests/test_integration/test_fluxo_busca.py` (novo, preferencial, para agrupar os 12 cenários)
- Opcionalmente acrescentar em `tests/test_integration/test_fluxo_completo.py` se fizer mais sentido para o qa.

**Critérios de aceite técnicos:**
- [ ] Todos os 12 cenários verdes.
- [ ] Usa `TodoWidget` real + `TaskService` real + DB SQLite em memória real.
- [ ] Classificados como "integração" (contribuem para a fatia de 42%+ da pirâmide, ajudando a endereçar DT-023).
- [ ] `ruff` e `mypy --strict` limpos.

**Estimativa:** M
**Dependências:** TASK-029, TASK-030, TASK-031, TASK-032, TASK-033
**Responsável sugerido:** qa

---

### TASK-036 — Teste de performance com 1k–5k tarefas

**Descrição técnica:**
Validar o RNF implícito (AC PO "Tempo para localizar < 3s em lista 50+" e AC qa "Performance com 1k–5k tarefas"). Criar teste marcado `@pytest.mark.slow` que:
1. Popula o DB em memória com 5.000 tasks (seed determinístico — metade com termo buscável, metade sem).
2. Instancia `TodoWidget` com `debounce_ms=0` e `task_service` real.
3. Mede o tempo entre setar o termo e o reload completar (via `time.perf_counter` ou `qtbot.waitSignal` no `tasks_reloaded`).
4. Asserta que o tempo fica abaixo de um threshold documentado (sugestão inicial: **1,5s** para 5k, **500ms** para 1k). Threshold será ajustado após primeira execução local/CI e registrado no próprio teste como constante.
5. Executa o mesmo cenário com 1.000 tasks para estabelecer baseline.

**Arquivos a criar:**
- `tests/test_ui/test_todo_widget_performance.py` OU `tests/test_integration/test_performance_busca.py`

**Critérios de aceite técnicos:**
- [ ] Teste marcado `@pytest.mark.slow` para permitir skip no CI rápido.
- [ ] Threshold documentado como constante no arquivo com comentário justificando a origem do valor.
- [ ] Asserts de tempo suites: 1k < 500ms e 5k < 1.5s (ajustável pós-baseline).
- [ ] Se falhar, relatar no relatório de qa com sugestão: subir debounce para 500ms ou adicionar índice full-text (fora de escopo desta US).

**ADR-lite inline:**
```
[DECISÃO] Threshold de performance documentado em constante, não em fixture.
  Alternativas: A) hardcode no teste | B) ler de arquivo de config | C) pytest-benchmark
  Escolha: A
  Por quê: zero deps novas, threshold auto-documentado na suite.
  Reversibilidade: alta.
```

**Estimativa:** P
**Dependências:** TASK-033
**Responsável sugerido:** qa

---

## Resumo US-07

| Task | Título | Resp. | Est. | Depende de |
|------|--------|-------|------|------------|
| [x] TASK-029 | Escape de wildcards LIKE | dev-python | P | — |
| [x] TASK-030 | QLineEdit + QTimer debounce | dev-python | P | T029 |
| [x] TASK-031 | Filtro por seções + msg vazia | dev-python | P | T030 |
| [x] TASK-032 | Ctrl+F + botão X + Esc | dev-python | P | T030 |
| [x] TASK-033 | Reaplicação filtro em CRUD | dev-python | P | T031, T032 |
| [x] TASK-034 | Testes unitários UI | qa | M | T030, T031, T032, T033 |
| [x] TASK-035 | Testes integração UI+Service+DB | qa | M | T029–T033 |
| [x] TASK-036 | Teste de performance 1k-5k | qa | P | T033 |

**Esforço total:** 5P + 2M + 1P = ~18-24h (dentro do budget de 1 semana).
**Módulos de produção afetados:** 2 (dentro do budget de 5).
**Deps novas:** 0.
**Ordem recomendada:** T029 -> T030 -> T031 -> T032 -> T033 (dev-python), depois T034 | T035 | T036 (qa em paralelo).

---

# Catálogo de Dívidas Técnicas

**Data da análise mais recente:** 2026-04-19
**Autor:** Tech Lead (análise automatizada)

Esta seção rastreia dívidas técnicas identificadas no código já implementado. Cada item inclui status (checkbox), prioridade, esforço, descrição, localização e critérios de aceite. Numeração DT-XXX é independente de TASK-XXX.

---

## Dívidas Técnicas Identificadas

### DT-001 — Corrigir erros de mypy (11 erros em 3 arquivos)

- [x] **Prioridade:** Alta
- **Esforço:** P
- **Descrição:** O projeto usa `mypy --strict`, mas há 11 erros em 3 arquivos: `kanban_card_widget.py`, `kanban_column_widget.py` e `main_window.py`. Os problemas incluem comentários `type: ignore` desnecessários e acessos a `QMimeData | None` sem checagem de `None` (erros `union-attr`). Os overrides de eventos Qt usam `event: object` com `type: ignore[override]` de forma inconsistente — alguns são marcados como "unused ignore" pelo mypy.
- **Localização:**
  - `src/own_board_list/ui/kanban/kanban_card_widget.py` (linhas 84, 91)
  - `src/own_board_list/ui/kanban/kanban_column_widget.py` (linhas 126, 130, 134, 138, 141, 146, 150-151)
  - `src/own_board_list/ui/main_window.py` (linha 73)
- **Critérios de aceite:**
  - `mypy --strict src/` passa com zero erros
  - Eventos Qt devidamente tipados com checagem de `None` em `mimeData()`
  - Nenhum `type: ignore` desnecessário

---

### DT-002 — Corrigir erros de ruff (9 erros, incluindo imports não utilizados)

- [x] **Prioridade:** Alta
- **Esforço:** P
- **Descrição:** `ruff check src/ tests/` reporta 9 erros, incluindo imports de `pytest` não utilizados nos arquivos de teste (`F401`). Três dos erros são auto-corrigíveis com `--fix`.
- **Localização:**
  - `tests/test_database/test_column_repository.py` (linha 5)
  - `tests/test_database/test_task_repository.py` (linha 5)
  - Outros arquivos com erros reportados pelo ruff
- **Critérios de aceite:**
  - `ruff check src/ tests/` passa com zero erros
  - `ruff format --check src/ tests/` passa com zero erros

---

### DT-003 — Ausência de .gitignore

- [x] **Prioridade:** Alta
- **Esforço:** P
- **Descrição:** O projeto não possui um arquivo `.gitignore`. Isso resulta em arquivos `__pycache__/`, `.venv/`, `*.pyc`, `uv.lock` (dependendo da estratégia), `data.db` e outros artefatos podendo ser versionados acidentalmente. Foram encontrados múltiplos diretórios `__pycache__` dentro de `src/`.
- **Localização:** Raiz do projeto
- **Critérios de aceite:**
  - Arquivo `.gitignore` criado com entradas para: `__pycache__/`, `*.pyc`, `.venv/`, `*.egg-info/`, `dist/`, `build/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `.coverage`, `htmlcov/`
  - Diretórios `__pycache__` removidos do rastreamento (se já estiverem no git)

---

### DT-004 — Ausência total de testes para a camada UI (cobertura 0%)

- [x] **Prioridade:** Alta
- **Esforço:** G
- **Descrição:** Toda a camada `ui/` (7 módulos, ~486 linhas) tem 0% de cobertura de testes. O diretório `tests/test_ui/` planejado na documentação não existe. A cobertura geral do projeto é de apenas 30%. Os módulos sem cobertura incluem: `main_window.py`, `todo_widget.py`, `task_form.py`, `task_list_item.py`, `kanban_widget.py`, `kanban_card_widget.py`, `kanban_column_widget.py`, `confirm_dialog.py`.
- **Localização:** `tests/test_ui/` (inexistente)
- **Critérios de aceite:**
  - Diretório `tests/test_ui/` criado com `__init__.py`
  - Testes para `TodoWidget`: renderização, interação com botões, reload de tasks
  - Testes para `KanbanWidget`: renderização de colunas, drag-and-drop básico
  - Testes para `TaskForm`: validação de campos, emissão de signal `task_saved`
  - Testes para `TaskListItem`: renderização, emissão de signals
  - Cobertura geral do projeto >= 60%

---

### DT-005 — Ausência de testes para o modelo KanbanColumn

- [x] **Prioridade:** Média
- **Esforço:** P
- **Descrição:** O modelo `KanbanColumn` não possui testes unitários próprios. Apenas o `TaskRepository` e o `ColumnRepository` exercitam indiretamente a classe. Não há testes para: validação de nome vazio, `to_dict()`, `from_dict()`, round-trip de serialização.
- **Localização:** `tests/test_models/test_kanban_column.py` (inexistente)
- **Critérios de aceite:**
  - Arquivo `tests/test_models/test_kanban_column.py` criado
  - Testes para: criação válida, validação de nome vazio, `to_dict()`, `from_dict()`, round-trip

---

### DT-006 — Duplicação do mapeamento `_COR_PRIORIDADE`

- [x] **Prioridade:** Média
- **Esforço:** P
- **Descrição:** O dicionário `_COR_PRIORIDADE` que mapeia prioridades para cores HTML está duplicado em dois arquivos distintos com conteúdo idêntico. Qualquer alteração nas cores exige modificação em dois lugares, violando o princípio DRY.
- **Localização:**
  - `src/own_board_list/ui/todo/task_list_item.py` (linhas 20-24)
  - `src/own_board_list/ui/kanban/kanban_card_widget.py` (linhas 13-17)
- **Critérios de aceite:**
  - Mapeamento extraído para um único local (ex: `ui/constants.py` ou `models/task.py`)
  - Ambos os widgets importam do local centralizado
  - Nenhuma duplicação remanescente

---

### DT-007 — Strings mágicas para nomes de colunas Kanban espalhadas pelo código

- [x] **Prioridade:** Média
- **Esforço:** M
- **Status:** Concluída no ciclo 2026-04-19. `task.py` agora importa `COLUNA_PADRAO` de `utils/constants.py` e não contém mais a string literal `"A Fazer"`. `task_repository.py`, `task_service.py` e `migrations.py` já usavam as constantes centralizadas. Nenhuma string literal remanescente no código de produção.
- **Descrição:** As strings `"A Fazer"`, `"Em Andamento"` e `"Concluído"` apareciam como literais em pelo menos 5 arquivos diferentes: `task.py` (default do campo `coluna_kanban`), `task_repository.py` (fallback), `task_service.py` (constantes locais), `migrations.py` (seed). O `task_service.py` definia constantes `COLUNA_CONCLUIDO` e `COLUNA_PADRAO`, mas essas não eram usadas nos demais módulos, gerando risco de inconsistência se um nome de coluna mudasse.
- **Localização:**
  - `src/own_board_list/models/task.py` (linhas 44, 102)
  - `src/own_board_list/database/task_repository.py` (linha 40)
  - `src/own_board_list/database/migrations.py` (linhas 56-58)
  - `src/own_board_list/services/task_service.py` (linhas 24-26)
- **Critérios de aceite:**
  - [x] Constantes centralizadas em um único módulo (`utils/constants.py`, conforme TASK-004)
  - [x] Todos os módulos importam as constantes do local centralizado
  - [x] Zero strings literais de nomes de colunas no código (exceto em testes)

---

### DT-008 — Uso de `datetime.now()` sem timezone (naive datetimes)

- [x] **Prioridade:** Média
- **Esforço:** M
- **Descrição:** Todos os timestamps do projeto usam `datetime.now()` sem timezone, produzindo objetos "naive". Isso pode causar problemas de ordenação e comparação caso o sistema mude de fuso horário, e é uma má prática reconhecida. O Python 3.12 já deprecou `datetime.utcnow()` em favor de `datetime.now(tz=timezone.utc)`.
- **Localização:**
  - `src/own_board_list/models/task.py` (linhas 46-47, 62, 67)
  - `src/own_board_list/database/task_repository.py` (linha 90)
  - `src/own_board_list/database/migrations.py` (linha 54)
- **Critérios de aceite:**
  - Todos os `datetime.now()` substituídos por `datetime.now(tz=timezone.utc)` ou equivalente
  - `from_dict()` e `_row_to_task()` tratam corretamente datetimes com timezone
  - Migrações existentes continuam compatíveis (leitura de dados antigos sem timezone)

---

### DT-009 — Módulo `utils/constants.py` planejado mas não implementado

- [x] **Prioridade:** Média
- **Esforço:** P
- **Descrição:** O ADR-001 e o plano de tasks (TASK-004) previam um módulo `utils/constants.py` para centralizar enums e constantes reutilizáveis. Esse módulo agora foi criado. Os enums `Prioridade` e `StatusTarefa` permanecem em `models/task.py` (o que é aceitável), e as constantes de nomes de colunas e limites foram centralizadas (ver DT-007).
- **Localização:** `src/own_board_list/utils/`
- **Critérios de aceite:**
  - Diretório `utils/` criado com `__init__.py` e `constants.py`
  - Constantes de nomes de colunas padrão e limite de caracteres do título centralizadas
  - Integrado com a resolução de DT-007

---

### DT-010 — Repositórios acoplados diretamente a `sqlite3.Connection`

- [ ] **Prioridade:** Média (parecer PO 2026-04-19: aceita para próximo ciclo com ressalva de prioridade no backlog)
- **Esforço:** M
- **Descrição:** `TaskRepository` e `ColumnRepository` recebem `sqlite3.Connection` diretamente no construtor em vez de usar a abstração `DatabaseConnection` que já existe. Além disso, ambos redefinem `self._conn.row_factory = sqlite3.Row` no construtor, duplicando lógica que já está em `DatabaseConnection.get_connection()`. Isso dificulta a substituição do mecanismo de persistência e viola o princípio de inversão de dependência (DIP do SOLID).
- **Localização:**
  - `src/own_board_list/database/task_repository.py` (linhas 22-25)
  - `src/own_board_list/database/column_repository.py` (linhas 20-22)
  - `src/own_board_list/ui/main_window.py` (linhas 40-42 — injeta `conn` bruto)
- **Critérios de aceite:**
  - Definir interface/protocolo para o repositório (opcional, mas recomendado)
  - Repositórios recebem `DatabaseConnection` em vez de `sqlite3.Connection` OU o padrão atual é documentado como decisão consciente
  - Remover duplicação de `row_factory` nos repositórios

---

### DT-011 — `TaskService` acoplado ao Qt (`QObject`) — viola testabilidade pura

- [ ] **Prioridade:** Baixa (parecer PO 2026-04-19: aceita para próximo ciclo com ressalva de prioridade no backlog)
- **Esforço:** M
- **Descrição:** A classe `TaskService` herda de `QObject` e usa `pyqtSignal` para comunicação com a UI. Isso foi uma decisão arquitetural documentada no ADR-001, porém causa acoplamento da camada de serviço com o framework Qt. Os testes de `TaskService` exigem `qtbot` (e portanto um `QApplication`), mesmo que nenhum widget seja testado. Uma alternativa seria separar a lógica pura de negócio de um "bridge" Qt, mas o custo pode não compensar para o tamanho atual do projeto.
- **Localização:** `src/own_board_list/services/task_service.py`
- **Critérios de aceite:**
  - Documentar a decisão como ADR (se mantiver o design atual)
  - OU extrair lógica pura para classe separada e criar wrapper Qt para signals

---

### DT-012 — Repositório `update()` altera o objeto recebido (side effect)

- [x] **Prioridade:** Média
- **Esforço:** P
- **Descrição:** O método `TaskRepository.update()` modifica o campo `atualizado_em` do objeto `Task` recebido como parâmetro (linha 90). Isso é um efeito colateral inesperado — o chamador espera que o repositório persista os dados, não que modifique o objeto de domínio. A responsabilidade de atualizar timestamps deveria estar no modelo ou no serviço.
- **Localização:** `src/own_board_list/database/task_repository.py` (linha 90)
- **Critérios de aceite:**
  - Timestamp `atualizado_em` atualizado no `TaskService` ou no próprio modelo antes de chamar o repositório
  - `TaskRepository.update()` apenas persiste sem modificar o objeto recebido

---

### DT-013 — Relação tasks-colunas via nome (string) em vez de ID (foreign key)

- [ ] **Prioridade:** Média (parecer PO 2026-04-19: aceita para próximo ciclo com ressalva de prioridade no backlog)
- **Esforço:** G
- **Descrição:** A tabela `tasks` referencia colunas Kanban pelo campo `coluna_kanban` (nome da coluna como string) em vez de usar `column_id` como foreign key. Isso significa que renomear uma coluna quebra a associação com as tasks existentes. O método `ColumnRepository.has_tasks()` precisa fazer duas queries (buscar nome da coluna, depois buscar tasks) justamente por conta dessa modelagem.
- **Localização:**
  - `src/own_board_list/database/migrations.py` (schema da tabela `tasks`)
  - `src/own_board_list/database/column_repository.py` (linhas 83-98, `has_tasks`)
  - `src/own_board_list/models/task.py` (campo `coluna_kanban`)
- **Critérios de aceite:**
  - Campo `coluna_kanban` substituído por `coluna_id` referenciando `kanban_columns.id`
  - Foreign key com `ON UPDATE CASCADE` para manter integridade
  - Migração para converter dados existentes
  - `has_tasks()` simplificado para uma única query

---

### DT-014 — Falta de índices no banco de dados

- [x] **Prioridade:** Média
- **Esforço:** P
- **Descrição:** A TASK-007 do plano original especifica criação de índices em `status`, `prioridade`, `coluna_kanban` e `data_vencimento`, mas nenhum índice foi criado no `migrations.py` no ciclo inicial. Para o volume atual de dados, não há impacto de performance, mas o RNF-02 especifica suporte a 10.000 tarefas sem degradação.
- **Localização:** `src/own_board_list/database/migrations.py`
- **Critérios de aceite:**
  - Índices criados para: `coluna_kanban`, `status`, `prioridade`, `data_vencimento`
  - Queries de busca e filtragem beneficiadas pelos índices
  - Testes de performance com volume de 10k registros (opcional, mas recomendado)

---

### DT-015 — `DatabaseConnection` não implementa context manager

- [x] **Prioridade:** Baixa
- **Esforço:** P
- **Descrição:** A TASK-007 especifica que `DatabaseConnection` deveria implementar context manager para transações. Na análise inicial, a classe tinha apenas `get_connection()` e `close()`. Cada operação de repositório fazia `commit()` individualmente, sem suporte a transações multi-operação. Isso podia causar inconsistência se uma operação composta falhasse no meio (ex: mover task + atualizar posições).
- **Localização:** `src/own_board_list/database/connection.py`
- **Critérios de aceite:**
  - `DatabaseConnection` implementa `__enter__` e `__exit__` com gerenciamento de transação
  - Opção de usar `with db_connection:` para transações atômicas
  - Repositórios opcionalmente usam transações para operações compostas

---

### DT-016 — `ColumnRepository.reorder()` faz N updates individuais sem transação

- [x] **Prioridade:** Média
- **Esforço:** P
- **Status:** Concluída no ciclo 2026-04-19. QA entregou o teste `test_reorder_rollback_em_erro_parcial` usando `ConnectionProxy` para simular falha no meio do loop e validar que nenhuma posição é persistida em caso de erro. Transação explícita já estava encapsulada via `BEGIN`/`COMMIT` no `reorder()`.
- **Descrição:** O método `reorder()` executava um `UPDATE` por coluna em loop e fazia `commit()` apenas no final. Se ocorresse um erro no meio do loop, as posições ficavam parcialmente atualizadas e inconsistentes.
- **Localização:** `src/own_board_list/database/column_repository.py` (linhas 74-81)
- **Critérios de aceite:**
  - [x] Operação de reorder encapsulada em transação explícita
  - [x] Em caso de erro, rollback completo
  - [x] Teste para cenário de erro parcial (`test_reorder_rollback_em_erro_parcial`)

---

### DT-017 — `closeEvent` com tipagem forjada via `type: ignore`

- [x] **Prioridade:** Baixa
- **Esforço:** P
- **Descrição:** O método `closeEvent` em `MainWindow` usava `event: object` com `type: ignore[override]` para contornar incompatibilidades de tipagem com PyQt6. Isso funcionava em runtime, mas mascarava o contrato real da API e gerava warnings desnecessários no mypy (conforme DT-001).
- **Localização:** `src/own_board_list/ui/main_window.py` (linhas 73-76)
- **Critérios de aceite:**
  - Tipagem correta usando `QCloseEvent` de `PyQt6.QtGui`
  - Zero `type: ignore` nessas linhas

---

### DT-018 — Diretórios `__pycache__` presentes no source tree

- [x] **Prioridade:** Baixa
- **Esforço:** P
- **Descrição:** Existiam 8 diretórios `__pycache__/` dentro de `src/`. Esses artefatos de compilação não deveriam estar no repositório. Relacionado com DT-003 (ausência de .gitignore).
- **Localização:** `src/own_board_list/` (múltiplos subdiretórios)
- **Critérios de aceite:**
  - Todos os `__pycache__/` removidos
  - `.gitignore` impede que retornem ao repositório (ver DT-003)

---

### DT-019 — Cobertura de testes do `connection.py` muito baixa (36%)

- [x] **Prioridade:** Baixa
- **Esforço:** P
- **Descrição:** O módulo `connection.py` tinha apenas 36% de cobertura. Os testes usavam `sqlite3.connect(":memory:")` direto no `conftest.py` em vez de usar `DatabaseConnection`, fazendo com que a classe `DatabaseConnection` e a função `get_default_db_path()` nunca fossem exercitadas nos testes.
- **Localização:**
  - `src/own_board_list/database/connection.py` (linhas 19-48 sem cobertura)
  - `tests/conftest.py`
- **Critérios de aceite:**
  - Testes unitários para `DatabaseConnection` (abrir, obter conexão, fechar, reabrir)
  - Testes para `get_default_db_path()` (mockar `Path.home()`)
  - Cobertura de `connection.py` >= 90%

---

### DT-020 — Arquivos planejados na arquitetura que não existem

- [ ] **Prioridade:** Baixa (parecer PO 2026-04-19: aceita para próximo ciclo com ressalva de prioridade no backlog)
- **Esforço:** Varia (informativo)
- **Descrição:** Vários arquivos previstos no ADR-001 e no plano de tasks ainda não foram implementados. Isso não é necessariamente um problema (pode ser trabalho futuro das Fases 2 e 3), mas deve ser rastreado para não se perder:
  - `src/own_board_list/utils/constants.py` (TASK-004) — concluído via DT-009
  - `src/own_board_list/services/export_service.py` (TASK-026)
  - `src/own_board_list/ui/kanban/card_detail_panel.py` (TASK-024)
  - `src/own_board_list/ui/dialogs/export_dialog.py` (TASK-026)
  - `src/own_board_list/ui/theme/` (TASK-027)
  - `tests/test_ui/` (TASK-014, TASK-017)
- **Localização:** Conforme listado acima
- **Critérios de aceite:**
  - Itens rastreados no backlog do projeto
  - Implementados conforme o plano de fases

---

### DT-021 — Bug search case-insensitive com caracteres Unicode (RESOLVIDO)

- [x] **Prioridade:** Alta
- **Esforço:** P
- **Status:** Corrigido no ciclo 2026-04-19 por dev-python.
- **Descrição:** `TaskService.search()` falhava ao comparar strings com acentos/Unicode porque SQLite usa `LOWER()` em ASCII por padrão. A correção registra uma função `PY_UPPER` via `sqlite3.Connection.create_function()` que delega para `str.upper()` do Python (Unicode-aware). Para evitar dependência circular `services -> models -> services`, os enums `Prioridade` e `StatusTarefa` foram extraídos para `models/enums.py` e re-exportados por `models/task.py`.
- **Localização:**
  - `src/own_board_list/models/enums.py` (novo módulo)
  - `src/own_board_list/models/task.py` (re-export dos enums)
  - `src/own_board_list/services/task_service.py` (registro de `PY_UPPER`)
  - `src/own_board_list/database/task_repository.py` (uso de `PY_UPPER` na query `LIKE`)
- **Critérios de aceite:**
  - [x] Busca por `"acao"` encontra tasks com título `"Ação"` (case-insensitive Unicode)
  - [x] Teste `TestFluxoBusca::test_busca_retorna_apenas_tasks_correspondentes` passando
  - [x] Sem dependência circular entre `models` e `services`
- **Observação:** Incidente durante o ciclo: QA reportou esse teste como falhando, mas a execução do Tech Lead em 2026-04-19 (após merge das entregas) mostrou 234/234 passando. Trabalho paralelo causou inconsistência transitória, já resolvida.

---

### DT-022 — Bug `super()` chamado com argumento `None` em handlers Qt (RESOLVIDO)

- [x] **Prioridade:** Alta
- **Esforço:** P
- **Status:** Corrigido no ciclo 2026-04-19 por dev-python.
- **Descrição:** Em 4 ocorrências, handlers de evento Qt (`mousePressEvent`, `dragEnterEvent`, `dropEvent`, `closeEvent`) chamavam `super().xxx(event)` com `event` podendo ser `None`, o que levantava `TypeError` em runtime quando o Qt entregava evento nulo (ex: fechamento abrupto). Correção: checagem `if event is not None` antes de delegar para o super.
- **Localização:**
  - `src/own_board_list/ui/kanban/kanban_card_widget.py`
  - `src/own_board_list/ui/kanban/kanban_column_widget.py`
  - `src/own_board_list/ui/main_window.py`
- **Critérios de aceite:**
  - [x] Nenhum `super().xxx(event)` sem checagem de `None`
  - [x] `ruff check .` e `mypy --strict src/` limpos
  - [x] Testes UI continuam passando

---

### DT-023 — Alinhar com PO split de testes (47% E2E/UI vs 42% integração)

- [ ] **Prioridade:** Alta
- **Esforço:** P
- **Descrição:** QA reportou split atual: 11% unitários, 42% integração, 47% E2E/UI. O PO rejeitou a entrega anterior exigindo que a suíte seja "principalmente integrados". E2E/UI passou a ser a maior fatia, o que pode violar o critério. Necessário alinhar com o PO se o split atual satisfaz o critério ou se o QA precisa converter parte dos testes de UI em testes de integração puros (sem `QApplication`), ou se o critério do PO será reinterpretado como "integração + E2E juntos dominam a suíte" (89% no total).
- **Localização:** `tests/test_ui/`, `tests/test_integration/`
- **Critérios de aceite:**
  - [ ] Decisão documentada com o PO sobre aceitação do split atual
  - [ ] Se rejeitado: plano de reclassificação/migração de testes aprovado
  - [ ] Se aceito: atualizar critério no documento de definição de pronto

---

### DT-024 — `TITULO_MAX_LEN` definido mas não utilizado

- [x] **Prioridade:** Baixa
- **Esforço:** P
- **Descrição:** A constante `TITULO_MAX_LEN = 200` em `utils/constants.py` não é referenciada por nenhum módulo de domínio. A validação de tamanho de título em `models/task.py` usa literal ou não valida. Ou se elimina a constante, ou se passa a aplicá-la consistentemente em modelo, form UI e validações.
- **Localização:**
  - `src/own_board_list/utils/constants.py` (linha 34)
  - Possíveis consumidores: `src/own_board_list/models/task.py`, `src/own_board_list/ui/todo/task_form.py`
- **Critérios de aceite:**
  - [ ] `TITULO_MAX_LEN` utilizada na validação de título em `Task.__post_init__` (ou equivalente)
  - [ ] `TITULO_MAX_LEN` aplicada como `maxLength` no `QLineEdit` de título do `TaskForm`
  - [ ] Teste que comprova rejeição de título com tamanho > `TITULO_MAX_LEN`

---

### DT-025 — `_parse_datetime` com prefixo `_` mas importado externamente

- [x] **Prioridade:** Baixa
- **Esforço:** P
- **Descrição:** A função `_parse_datetime` em `models/task.py` (linha 22) tem prefixo `_` (convenção de "privado" em Python), mas é importada diretamente por `database/task_repository.py` (linha 15). Isso viola a convenção e dificulta refatorações. Duas opções: (a) renomear para `parse_datetime` e marcar como público; (b) mover para um módulo utilitário (`utils/datetime.py`).
- **Localização:**
  - `src/own_board_list/models/task.py` (linha 22)
  - `src/own_board_list/database/task_repository.py` (linha 15)
- **Critérios de aceite:**
  - [ ] Função sem prefixo `_` OU movida para `utils/` com nome público
  - [ ] Todos os importadores atualizados
  - [ ] Nenhum warning de ruff sobre uso de nome `_private`

---

### DT-026 — Duplicação de fixtures entre `conftest.py` de cada camada

- [ ] **Prioridade:** Média
- **Esforço:** P
- **Descrição:** As fixtures `db_conn`, `task_repo`, `column_repo`, `task_service` estão duplicadas em 3 arquivos com sufixos diferentes:
  - `tests/conftest.py` (`db_conn`, `task_repo`, ...)
  - `tests/test_ui/conftest.py` (`db_conn_ui`, `task_repo_ui`, ...)
  - `tests/test_integration/conftest.py` (`db_conn_integration`, `task_repo_int`, ...)
  O corpo das fixtures é praticamente idêntico (mesmo setup de `sqlite3.connect(":memory:")` + migrações + repos). Isso triplica a manutenção e divergências já começam a aparecer.
- **Localização:**
  - `tests/conftest.py`
  - `tests/test_ui/conftest.py`
  - `tests/test_integration/conftest.py`
- **Critérios de aceite:**
  - [ ] Fixtures-base unificadas em `tests/conftest.py` com nomes canônicos (`db_conn`, `task_repo`, etc.)
  - [ ] Camadas UI/integração reutilizam as fixtures-base ou definem apenas derivadas quando necessário
  - [ ] Zero duplicação de lógica de setup de banco entre conftests
  - [ ] 234 testes continuam passando após a unificação

---

### DT-027 — Gap de cobertura em `column_repository.py` (linhas 34 e 106)

- [x] **Prioridade:** Baixa
- **Esforço:** P
- **Descrição:** Relatório de cobertura (`pytest --cov`) mostra que `column_repository.py` tem 96% de cobertura com as linhas 34 e 106 não exercitadas. São branches de tratamento de erro / caminhos alternativos que precisam de teste explícito.
- **Localização:** `src/own_board_list/database/column_repository.py` (linhas 34, 106)
- **Critérios de aceite:**
  - [x] Testes que exercitam especificamente os caminhos das linhas 34 e 106
  - [x] Cobertura de `column_repository.py` >= 99% (atual: 100%)

---

### DT-028 — Gap de cobertura em `task_service.py` (linha 140)

- [x] **Prioridade:** Baixa
- **Esforço:** P
- **Descrição:** Relatório de cobertura mostra que `task_service.py` tem 99% com a linha 140 não exercitada (branch de tratamento de exceção ou caso limite). (Observação: usuário reportou "linha 134" ao abrir a task, mas a linha real ausente no relatório de cobertura do ciclo 2026-04-19 é a 140 — verificar no momento de implementar.)
- **Localização:** `src/own_board_list/services/task_service.py` (linha 140)
- **Critérios de aceite:**
  - [x] Teste que exercita a linha 140
  - [x] Cobertura de `task_service.py` = 100% (confirmado)

---

### DT-029 — `BEGIN` aninhado em `DatabaseConnection.__enter__` e `reorder()`

- [x] **Prioridade:** Média
- **Esforço:** P
- **Descrição:** Tanto `DatabaseConnection.__enter__` (connection.py:62) quanto `ColumnRepository.reorder()` (column_repository.py:87) emitem `execute("BEGIN")` explicitamente. Se um consumidor futuro chamar `reorder()` dentro de um bloco `with DatabaseConnection(...) as conn:`, o segundo `BEGIN` levantará `sqlite3.OperationalError: cannot start a transaction within a transaction`. Armadilha latente: ainda não há caminho de código que encadeie os dois, mas qualquer refatoração que adote o context manager como padrão no `main_window.py`/services vai detonar o bug.
- **Localização:**
  - `src/own_board_list/database/connection.py` (linha 62)
  - `src/own_board_list/database/column_repository.py` (linha 87)
- **Critérios de aceite:**
  - [ ] Estratégia unificada: ou só o context manager gerencia transação (repositórios não emitem `BEGIN`), ou repositórios detectam se já estão em transação (`conn.in_transaction`) antes de emitir novo `BEGIN`
  - [ ] Teste regressivo que aninha `with DatabaseConnection(...)` + `reorder()` e valida sucesso
  - [ ] Decisão documentada em comentário de módulo ou ADR-lite

---

### DT-030 — `main.py` com 0% de cobertura

- [x] **Prioridade:** Baixa
- **Esforço:** P
- **Descrição:** `src/own_board_list/main.py` (14 statements, linhas 3-26) não tem nenhum teste. É o entrypoint que cria `QApplication`, instancia `MainWindow` e chama `app.exec()`. Testar `main()` end-to-end via `qtbot` é possível, mas tem custo: bootar app completo no CI. Alternativa mais barata: extrair `create_app()` e testar apenas a fiação de dependências, deixando `app.exec()` como `pragma: no cover`.
- **Localização:** `src/own_board_list/main.py`
- **Critérios de aceite:**
  - [x] `create_app()` ou função equivalente extraída com dependências injetáveis
  - [x] Teste que verifica a fiação de dependências (conexão, repositórios, serviço, janela principal)
  - [x] `app.exec()` marcado com `# pragma: no cover`
  - [x] Cobertura de `main.py` >= 85% (atual: 100%)

---

### DT-031 — Virtual scrolling / cache de `TaskListItem` no `TodoWidget._reload_tasks`

- [ ] **Prioridade:** Média
- **Esforço:** M
- **Descrição:** Identificado em revisão da US-07 (TASK-036). Testes de performance mostram que o custo dominante do ciclo de busca não é a query SQL (~5ms para 1k tasks), mas a recriação de todos os `TaskListItem` (QWidget) a cada `_reload_tasks`. Com 5k tasks, o ciclo completo leva ~3-4s — dentro do threshold conservador de 8s, mas perceptível para o usuário. Opções: (a) virtual scrolling via `QListView` + `QAbstractItemModel` (migração maior, mas idiomática Qt); (b) cache interno de `dict[task_id, TaskListItem]` no `TodoWidget` reaproveitando widgets quando a task já existia; (c) `QListWidget` com itens leves. Como o app ainda não tem usuários com listas grandes e o threshold atual é aceitável, classificar como otimização futura.
- **Localização:**
  - `src/own_board_list/ui/todo/todo_widget.py` (`_reload_tasks`, `_add_tasks_to_group`, `_clear_group`)
  - `src/own_board_list/ui/todo/task_list_item.py`
- **Critérios de aceite:**
  - [ ] Threshold de performance 5k tasks cai abaixo de 1.5s (base atual documentada em `test_performance_busca.py`: ~3-4s)
  - [ ] Sem regressão funcional nos 15 testes de integração de busca
  - [ ] Decisão documentada: virtual view vs. cache de widgets

---

### DT-032 — Cobertura de dialogs modais em `TodoWidget` (linhas 228-270)

- [x] **Prioridade:** Baixa
- **Esforço:** P
- **Descrição:** Identificado na revisão da US-07. O relatório de cobertura aponta `todo_widget.py` em 91% com gap concentrado em `_on_nova_tarefa` (L228-230), `_on_edit_task` (L234-240) e `_on_form_saved` (L259-270). São handlers que abrem `TaskForm` modal via `form.exec()` — não são exercitados nos testes atuais pois dialogs modais bloqueiam o event loop. Estratégia sugerida: extrair a instanciação do form para um método factory injetável (`_create_task_form(task: Task | None) -> TaskForm`), permitindo mock em testes. Alternativa mais barata: testar `_on_form_saved` diretamente com dicionário (já parcialmente feito em `test_foco_pos_abertura_formulario_nao_limpa_busca`).
- **Localização:** `src/own_board_list/ui/todo/todo_widget.py` (linhas 228-270)
- **Critérios de aceite:**
  - [ ] Cobertura de `todo_widget.py` >= 95%
  - [ ] Testes sem depender de `form.exec()` real (bloqueante em CI headless)
  - [ ] Padrão de factory method documentado se adotado (replicável em outros dialogs)

---

### DT-033 — Convenções de testes Qt em ambiente headless (BUG-QA-001 e BUG-QA-002)

- [ ] **Prioridade:** Média
- **Esforço:** P
- **Descrição:** QA identificou durante a US-07 duas armadilhas em testes pytest-qt sob XCB headless: (1) `QWidget.isVisible()` retorna `False` quando o widget raiz não foi exibido via `show()`, mesmo que o widget filho esteja logicamente visível. Usar `QWidget.isHidden()` como inverso não-equivalente resolve; (2) `qtbot.keyClicks(widget, ...)` causa SIGABRT se o widget alvo não foi exibido — workaround é usar `widget.setText(...)` diretamente. Essas duas armadilhas vão reaparecer em qualquer teste futuro de UI que não entende a nuance. Ação: documentar convenção única e reutilizável em `tests/README.md` ou docstring de `conftest.py` raiz, e revisar se algum lint/check automatizado (ex.: grep de `isVisible()`/`keyClicks` nos testes) ajuda a prevenir reincidência.
- **Localização:**
  - `tests/test_ui/test_todo_widget_busca.py` (cenário 9 e 8)
  - `tests/test_integration/test_fluxo_busca.py` (helper `_aplicar_busca`)
  - `tests/test_integration/test_performance_busca.py` (assert de label vazio)
- **Critérios de aceite:**
  - [ ] Convenção documentada (arquivo único, localização canônica)
  - [ ] Template de fixture/helper para "widget visible headless" centralizado
  - [ ] Zero uso de `qtbot.keyClicks` sem `widget.show()` nos testes existentes
  - [ ] Zero uso de `isVisible()` como negação de `isHidden()` quando o widget raiz não está visível

---

### DT-034 — Expor `TaskRepository.bulk_insert` para substituir acesso a `service._task_repo` em testes

- [x] **Prioridade:** Baixa
- **Esforço:** P
- **Descrição:** Identificado na revisão de TASK-036. O helper `_popular_banco` em `tests/test_integration/test_performance_busca.py` acessa `service._task_repo` diretamente com `# type: ignore[attr-defined]` para inserir 1k-5k tasks bypassando o signal `task_created` (que dispararia `_reload_tasks` quadrático). O acesso a atributo privado viola encapsulamento. Solução: expor `TaskRepository.bulk_insert(tasks: list[Task]) -> None` que insere em uma única transação + `executemany`, disponível via `TaskService.bulk_create_tasks()` sem emitir signal por task (ou com um signal `tasks_bulk_created` agregador). Além de limpar os testes, o método tem valor de produção para futuras features de import/seeder.
- **Localização:**
  - `src/own_board_list/database/task_repository.py` (novo método)
  - `src/own_board_list/services/task_service.py` (exposição opcional)
  - `tests/test_integration/test_performance_busca.py` (consumidor)
- **Critérios de aceite:**
  - [ ] `TaskRepository.bulk_insert(tasks)` usando `executemany` em uma transação
  - [ ] Teste unitário do novo método
  - [ ] `_popular_banco` refatorado sem `# type: ignore[attr-defined]`
  - [ ] Documentado se bulk emite signal agregador ou é silencioso

---

### DT-035 — Flakiness potencial do teste `test_debounce_agrega_3_keystrokes_em_uma_chamada`

- [ ] **Prioridade:** Baixa
- **Esforço:** P
- **Descrição:** Identificado na revisão da US-07 (TASK-034, cenário 3). O único teste que exercita o debounce real usa `debounce_ms=300` + `qtbot.wait(450)`. Em máquinas lentas (CI compartilhado, containers com CPU limitada), 150ms de margem pode não bastar — o assert após `wait(450)` pode ler um estado ainda-não-aplicado do QTimer. Opções: (a) aumentar `wait` para `750ms` (aceitar o custo de +300ms no teste); (b) usar `qtbot.waitUntil(lambda: widget._search_term == "abc", timeout=2000)` que faz polling adaptativo; (c) converter para `qtbot.waitSignal(task_service.tasks_reloaded)` se o fluxo emitir esse signal. Opção (b) é a mais robusta e idiomática.
- **Localização:** `tests/test_ui/test_todo_widget_busca.py` (linhas 78-81)
- **Critérios de aceite:**
  - [ ] Teste convertido para `qtbot.waitUntil` ou equivalente não-determinístico-timing
  - [ ] Documentado pattern para "testar debounce de verdade" no projeto

---

### DT-036 — Encapsular acesso ao form inline em `KanbanColumnWidget`

- [x] **Prioridade:** Baixa
- **Esforço:** P
- **Descrição:** Identificada na implementação da US-10 (criação inline de cards no Kanban). O método `KanbanWidget._on_create_card_submitted` acessava o atributo protegido `col_widget._inline_form` para chamar `reset()` e `show_error()`, violando encapsulamento entre o widget pai (board) e o widget filho (coluna). Solução: expor métodos públicos `reset_form()` e `show_form_error(msg: str)` em `KanbanColumnWidget` e atualizar o caller para usar a API pública. Risco baixo, escopo cirúrgico — qualifica para escape hatch de DT trivial.
- **Localização:**
  - `src/own_board_list/ui/kanban/kanban_column_widget.py` (novos métodos públicos)
  - `src/own_board_list/ui/kanban/kanban_widget.py` (caller atualizado)
- **Critérios de aceite:**
  - [x] `KanbanColumnWidget.show_form_error(msg)` público implementado
  - [x] `KanbanColumnWidget.reset_form()` público implementado
  - [x] `KanbanWidget._on_create_card_submitted` usa apenas a API pública
  - [x] Gates verdes (pytest, ruff, mypy)

---

### DT-037 — Helper `make_focus_spy` para testes headless de foco

- [ ] **Prioridade:** Baixa
- **Esforço:** P
- **Descrição:** Identificada na implementação da US-10. O padrão de fazer spy em `setFocus` para validar transferência de foco em ambiente headless aparece pelo menos em 3 testes: 2 cenários da US-10 (form inline do Kanban) e 1 precedente em `tests/test_ui/test_todo_widget_busca.py`. A duplicação do boilerplate (substituir `widget.setFocus`, registrar chamadas, restaurar) prejudica legibilidade e dificulta evolução. Solução: extrair helper `make_focus_spy(widget)` em `tests/conftest.py` (ou `tests/test_ui/conftest.py` conforme escopo) que retorne um objeto com `.called`/`.call_count` e instale o spy automaticamente. Não é bloqueante; melhor abordar em sprint dedicada a testes (alinhada com DT-026 e DT-033) para revisar as 3 ocorrências e padronizar o pattern.
- **Localização:**
  - `tests/conftest.py` ou `tests/test_ui/conftest.py` (novo helper)
  - `tests/test_ui/test_todo_widget_busca.py` (refatorar consumidor)
  - Testes da US-10 envolvendo foco no form inline do Kanban (refatorar consumidores)
- **Critérios de aceite:**
  - [ ] Helper `make_focus_spy(widget)` documentado e testado
  - [ ] Pelo menos 3 ocorrências do padrão refatoradas para usar o helper
  - [ ] Pattern documentado como convenção de testes Qt headless (cruzar com DT-033)

---

## Análise de segurança e validação (ciclo 2026-04-25)

Revisão proativa do Tech Lead em 2026-04-25 buscando vulnerabilidades OWASP aplicáveis a app desktop local (SQLi, path traversal, validação de entrada, race conditions, deserialização insegura, secrets hardcoded). Conclusão geral:

- **Zero SQL injection**: todas as queries em `task_repository.py`, `column_repository.py` e `migrations.py` usam placeholders `?`. Conformidade com princípio 🔒 §4 da constitution.
- **Zero pickle/eval/exec**: nenhum uso encontrado em `src/`.
- **Zero secrets hardcoded**: aplicação 100% offline, sem credenciais.
- **Path traversal**: `get_default_db_path` usa `Path.home() / ".own-board-list"` — sem input do usuário; `DatabaseConnection(db_path)` recebe o path apenas via `MainWindow` (caminho fixo). Risco baixo enquanto não houver feature de "abrir banco em path arbitrário" (US-15 export pode reintroduzir o vetor — avaliar no `/specify` da feature).

DTs novas catalogadas abaixo (DT-038 a DT-042). Nenhuma é Crítica dado o modelo de ameaças (single-user, offline, sem network), mas três são Médias com flag ⚠️ por representarem armadilhas latentes.

### DT-038 — ⚠️ Ausência de limite de tamanho em `Task.descricao` e `KanbanColumn.nome`

- [x] **Prioridade:** Média
- **Tipo:** Vulnerabilidade (validação de entrada) / Bug
- **Descrição:** Identificado em revisão de segurança 2026-04-25. `Task.__post_init__` valida `titulo` contra `TITULO_MAX_LEN`, mas `descricao` aceita string de tamanho arbitrário. Idem para `KanbanColumn.nome`. Em app local single-user o risco de DoS é teórico, mas:
  1. Permite que o usuário cole acidentalmente um arquivo grande (megabytes) em campo livre de UI e infle o `data.db` — degradando RNF-02 (10k tarefas sem degradação).
  2. UI (`task_form.py`) não impõe `maxLength` no `QTextEdit` da descrição (em contraste com o `QLineEdit` do título que já tem maxlength 200).
  3. Quebra simetria do contrato: validação só em um campo é fácil de esquecer ao adicionar novos.
- **Solução:** adicionar `DESCRICAO_MAX_LEN = 5000` (ou similar) e `NOME_COLUNA_MAX_LEN = 100` em `utils/constants.py`; validar em `__post_init__` de `Task` e `KanbanColumn`; impor `maxLength` correspondente nos widgets `task_form.py`, `inline_task_form.py` e formulários de coluna Kanban (US-11).
- **Localização:**
  - `src/own_board_list/utils/constants.py` (novas constantes)
  - `src/own_board_list/models/task.py` (`__post_init__`)
  - `src/own_board_list/models/kanban_column.py` (`__post_init__`)
  - `src/own_board_list/ui/todo/task_form.py` (UI guard)
  - `src/own_board_list/ui/kanban/inline_task_form.py` (UI guard)
- **Critérios de aceite:**
  - [ ] Constantes `DESCRICAO_MAX_LEN` e `NOME_COLUNA_MAX_LEN` definidas
  - [ ] `Task.__post_init__` rejeita `descricao` acima do limite (`ValueError`)
  - [ ] `KanbanColumn.__post_init__` rejeita `nome` acima do limite
  - [ ] UI impede digitação acima dos limites (não só backend)
  - [ ] Testes de borda: limite-1, limite, limite+1
- **Caminho SDD:** escape hatch (DT catalogada, ≤ 2h) → `/implement` direto via `dev-python`.

### DT-039 — ⚠️ `posicao_kanban` aceita valores negativos

- [x] **Prioridade:** Baixa
- **Tipo:** Bug / Validação de entrada
- **Descrição:** `Task.posicao_kanban: int = 0` e `KanbanColumn.posicao: int = 0` não validam `>= 0` em `__post_init__`. O contrato implícito do Kanban é que posição é índice não-negativo. Hoje nada produz negativo, mas `update_task(posicao_kanban=-1)` passa direto até o banco. Quebra invariantes silenciosamente.
- **Solução:** adicionar validação `if self.posicao_kanban < 0: raise ValueError(...)` em `__post_init__` de ambos os modelos. Idem para `posicao` em `KanbanColumn`.
- **Localização:**
  - `src/own_board_list/models/task.py`
  - `src/own_board_list/models/kanban_column.py`
- **Critérios de aceite:**
  - [ ] Validação `>= 0` em ambos os modelos
  - [ ] Teste de unidade cobrindo o cenário negativo
- **Caminho SDD:** escape hatch → `/implement` direto via `dev-python`.

### DT-040 — ⚠️ Schema SQLite sem `NOT NULL` nem `CHECK` em campos críticos

- [ ] **Prioridade:** Média
- **Tipo:** Vulnerabilidade (integridade de dados)
- **Descrição:** Identificado em revisão de segurança 2026-04-25. `migrations.py` cria as tabelas com a maioria dos campos como `TEXT` nullable, sem constraints:
  - `prioridade TEXT` (deveria ser NOT NULL CHECK IN ('BAIXA','MEDIA','ALTA'))
  - `status TEXT` (deveria ser NOT NULL CHECK IN ('PENDENTE','CONCLUIDA'))
  - `coluna_kanban TEXT` (deveria ser NOT NULL)
  - `criado_em TEXT`, `atualizado_em TEXT` (deveriam ser NOT NULL)
  - `kanban_columns.criado_em TEXT` idem
  
  O modelo Python valida em `__post_init__`, mas o banco aceita estados inválidos se manipulado por fora (ex.: ferramenta externa, importação futura, bug de regressão). Defesa em profundidade exige validação em ambas as camadas.
  
  Exige migração — primeira do projeto. Considerar `ALTER TABLE` sequencial ou `CREATE TABLE … AS SELECT` + rename. Cruzar com DT-013 (FK coluna_kanban) para fazer ambas em uma migração única.
- **Solução:** criar `migrations/002_constraints.sql` (ou função em `migrations.py` versionada) que adiciona NOT NULL + CHECK. Documentar política de versionamento de schema (ainda inexistente).
- **Localização:**
  - `src/own_board_list/database/migrations.py` (refatorar para suportar versões)
  - Possível ADR novo: política de migrations
- **Critérios de aceite:**
  - [ ] Política de versionamento de schema definida (tabela `schema_version` ou similar)
  - [ ] Migração aplica NOT NULL + CHECK em campos enum
  - [ ] Rollback documentado (backup do `data.db` antes de migrar)
  - [ ] Testes garantem que dados legacy ainda carregam
- **Caminho SDD:** **NÃO trivial** — exige `/specify` (decisão de design sobre migrations) → `po` para definir critério de aceite + `tl-python` para ADR de política de migrations. Cruzar com DT-013.

### DT-041 — ⚠️ `check_same_thread=False` sem lock explícito

- [ ] **Prioridade:** Baixa
- **Tipo:** Vulnerabilidade (race condition latente)
- **Descrição:** `DatabaseConnection.get_connection` chama `sqlite3.connect(..., check_same_thread=False)`. Hoje a aplicação é single-threaded (loop Qt único), então não há race. Porém, o flag desabilita o guard nativo do `sqlite3` — qualquer feature futura que use `QThread` ou `concurrent.futures` (ex.: exportação assíncrona da US-15, importação em background) introduzirá race conditions silenciosas em `commit`/`rollback`.
- **Solução:** documentar invariante "conexão usada apenas no thread principal" em docstring; adicionar `assert threading.get_ident() == self._owner_thread` opcional em modo debug; ou trocar para `check_same_thread=True` (default) e revisar testes — a maioria dos repos é single-thread mesmo. Alternativa: encapsular acesso em `Lock` se houver necessidade de threads.
- **Localização:** `src/own_board_list/database/connection.py:46`
- **Critérios de aceite:**
  - [ ] Decisão registrada (manter `False` com guard / voltar a `True`)
  - [ ] Documentação explícita do contrato
  - [ ] Teste cobrindo o caminho escolhido
- **Caminho SDD:** escape hatch (DT catalogada, ≤ 1h decisão + implementação) → `/implement` via `dev-python`. Se decidir mudar contrato, escalar para SRE.

### DT-042 — Validação semântica de `coluna_kanban` em `Task` (referencial soft)

- [ ] **Prioridade:** Baixa
- **Tipo:** Refactor / Validação
- **Descrição:** `Task.coluna_kanban` é string livre. `TaskService.create_task`, `update_task`, `move_to_column` não verificam se a coluna informada existe na tabela `kanban_columns`. Resultado: é possível criar tarefa em coluna inexistente, que ficará "órfã" e invisível no Kanban (mas aparece na Todo List). Já parcialmente coberto por DT-013 (mudar para FK), mas DT-013 é refatoração maior; este item é a guarda mínima imediata: validar no `TaskService`.
- **Solução:** `TaskService` consulta `column_repo.get_all()` (cacheável) e levanta `ValueError` se a coluna não existir, em `create_task`, `create_task_in_column`, `update_task` (quando `coluna_kanban` está em kwargs) e `move_to_column`.
- **Localização:** `src/own_board_list/services/task_service.py`
- **Critérios de aceite:**
  - [ ] Tentativa de criar/mover task para coluna inexistente levanta `ValueError`
  - [ ] Mensagem de erro orienta o usuário
  - [ ] Testes de unidade cobrem os 4 métodos
  - [ ] Marca como precursor de DT-013 (FK real)
- **Caminho SDD:** escape hatch → `/implement` direto via `dev-python`.

---

## Resumo por Prioridade (Dívidas Técnicas)

| Prioridade | Tasks | IDs |
|-----------|-------|-----|
| **Alta** | 6 | DT-001, DT-002, DT-003, DT-004, DT-021, DT-022 |
| **Média** | 17 | DT-005 a DT-010, DT-012 a DT-014, DT-016, DT-026, DT-029, DT-031, DT-033, DT-038 ⚠️, DT-040 ⚠️ |
| **Baixa** | 18 | DT-011, DT-015, DT-017 a DT-020, DT-024, DT-025, DT-027, DT-028, DT-030, DT-032, DT-034, DT-035, DT-036, DT-037, DT-039 ⚠️, DT-041 ⚠️, DT-042 |
| **Alinhamento** | 1 | DT-023 (exige decisão do PO) |

---

## Estado do ciclo 2026-04-19

**Entregas concluídas neste ciclo:**
- DT-007 finalizada (centralização de `COLUNA_PADRAO` em `task.py`)
- DT-016 finalizada (teste de rollback em erro parcial entregue pelo QA)
- DT-021 (bug Unicode na busca) corrigida
- DT-022 (bug `super()` com `None` em handlers Qt) corrigida

**Validação técnica (Tech Lead, 2026-04-19):**
- `ruff check .` — All checks passed
- `mypy --strict src/` — Success, no issues in 27 files
- `pytest` — 234 passed em 2.34s
- Cobertura total: 94% (gaps em `main.py`, `column_repository.py`, `task_service.py`, widgets UI)

**Pendências abertas emergidas no ciclo:**
- DT-023: alinhar com PO se split atual 11/42/47 satisfaz "principalmente integrados"
- DT-024 a DT-030: dívida técnica pontual rastreada para próximos ciclos

**Divergências resolvidas:**
- QA reportou 1 teste falhando (`test_busca_retorna_apenas_tasks_correspondentes`) como pré-existente. Execução do Tech Lead após merge das entregas paralelas confirma 234/234 passando — não há regressão.

---

## Estado do ciclo 2026-04-20 (fechamento US-07)

**Entregas concluídas neste ciclo:**
- TASK-029 — Escape de wildcards LIKE (`%`, `_`, `\`) em `TaskRepository.search` com `ESCAPE '\\'`
- TASK-030 — QLineEdit + QTimer debounce (singleShot com guard stale) no `TodoWidget`
- TASK-031 — Filtro por seções + label "Nenhuma tarefa encontrada" permanente show/hide
- TASK-032 — Ctrl+F + botão X nativo + Esc (via `eventFilter`) com `WidgetWithChildrenShortcut`
- TASK-033 — Reaplicação do filtro em eventos CRUD via signals já conectados
- TASK-034 — 10 testes unitários UI do campo de busca
- TASK-035 — 15 testes de integração UI+Service+DB para busca (contribui para DT-023)
- TASK-036 — 4 testes de performance (marks `slow` e `integration` registrados em `pyproject.toml`)

**Validação técnica (Tech Lead, 2026-04-20):**
- `ruff check .` — All checks passed
- `ruff format --check .` — 55 files already formatted
- `mypy --strict src/` — Success, no issues in 27 source files
- `pytest` — 266 passed em 25.8s (incluindo 4 `slow`)
- `pytest -m integration` — 15 passed em 0.99s
- `pytest -m slow` — 4 passed em 23.0s
- Cobertura total: 95% (94% → 95%); `todo_widget.py` 91% (gap nos handlers de dialog modal, ver DT-032)

**Parecer do Code Review (Tech Lead, 2026-04-20):**
- **Veredito:** APROVADO COM RESSALVAS — implementação atende aos 11 ACs da PO, tem qualidade para merge; ressalvas são não-bloqueantes e viram DTs para próximos ciclos.
- Escape de wildcards correto (ordem `\` → `%` → `_` + `ESCAPE '\\'`).
- Debounce com guard stale (`if text != self._search_input.text(): return`) é correto e idiomático.
- Atalhos `Ctrl+F`/`Ctrl+N` com `WidgetWithChildrenShortcut` não conflitam entre si nem com `Ctrl+Q` da `MainWindow`.
- Testes de integração são realmente integração (zero mocks de repositório).
- Label "Nenhuma tarefa encontrada" respeita condição `total == 0 AND has_active_search`.

**DTs novas emergidas do review:**
- DT-031 — Virtual scrolling / cache de `TaskListItem` (M, Média)
- DT-032 — Cobertura de dialogs modais em `TodoWidget` (P, Baixa)
- DT-033 — Convenções de testes Qt headless (BUG-QA-001/002) (P, Média)
- DT-034 — `TaskRepository.bulk_insert` para limpar `# type: ignore[attr-defined]` em testes (P, Baixa)
- DT-035 — Flakiness potencial do teste de debounce real (P, Baixa)

---

## Plano incremental US-10 (TASK-037 a TASK-046) — Criar card diretamente no Kanban

Entrega especificada em [docs/specs/010-criar-card-kanban/](specs/010-criar-card-kanban/) (spec + plan em 2026-04-24). Esta sequência **substitui** o escopo outrora representado pela TASK-022 (MVP Fase 2), que era placeholder com escopo reduzido. Sem mudanças de schema, sem novos ADRs. Detalhamento técnico em `specs/010-criar-card-kanban/plan.md`; TCs em `plano-testes.md §2.10`.

### TASK-037 — `TaskService.create_task_in_column` com regra coluna→status ✅

**Descrição:** novo método que cria tarefa já vinculada à coluna informada, aplicando a regra `COLUNA_CONCLUIDO → CONCLUIDA`, demais → `PENDENTE` (espelho de `move_to_column`). Emite signal `task_created`.
**Camada:** services. **Esforço:** P. **Dependências:** nenhuma. **TC aceite:** TC-080, TC-081.

### TASK-038 — Widget `InlineTaskForm` (título, prioridade, data) ✅

**Descrição:** novo `ui/kanban/inline_task_form.py`. `QWidget` enxuto com `QLineEdit` (título, maxlength 200), `QComboBox` (prioridade, default MEDIA), `QDateEdit` (opcional), botões Adicionar/Cancelar. Signals `submitted(dict)` e `cancelled()`. Foco inicial no título via `QTimer.singleShot(0, ...)`. Atalhos locais `Enter`/`Esc` (via `keyPressEvent` com `event.accept()`). Método `reset()`, `show_error(msg)`, `focus_title()`. **Camada:** ui. **Esforço:** M. **Depende:** TASK-037. **TC aceite:** TC-082, TC-083, TC-084, TC-085.

### TASK-039 — Rodapé "+ Adicionar card" e toggle em `KanbanColumnWidget` ✅

**Descrição:** adicionar rodapé fixo abaixo do `_scroll_area` com botão "+ Adicionar card". Implementar `open_inline_form()`, `close_inline_form()`, `has_inline_form_open()`; emitir `create_card_submitted(column_name, dados)` e `add_card_requested(column_name)`. Alternar visibilidade entre botão e form. **Camada:** ui. **Esforço:** M. **Depende:** TASK-038. **TC aceite:** TC-086, TC-087.

### TASK-040 — `KanbanColumnWidget.set_tasks(tasks)` reload incremental ✅

**Descrição:** método que limpa cards existentes (com `deleteLater`) e repopula a partir da lista, **sem** tocar no rodapé/form inline. Contador de cards atualizado em seguida. **Camada:** ui. **Esforço:** P. **Depende:** TASK-039. **TC aceite:** TC-088.

### TASK-041 — `KanbanWidget._reload_board` incremental preservando forms ✅

**Descrição:** refatorar `_reload_board` para: (a) se a lista de colunas não mudou, chamar `col.set_tasks(...)` em cada coluna existente; (b) se mudou, recriar como hoje. Conectar signals novos; chamar `TaskService.create_task_in_column` no handler; em exceção, chamar `col_widget._inline_form.show_error(...)`. **Camada:** ui. **Esforço:** M. **Depende:** TASK-040. **TC aceite:** TC-089, TC-090, TC-091.

### TASK-042 — Criação em rajada: form permanece aberto e limpo após confirmar ✅

**Descrição:** após `create_task_in_column` bem-sucedido, chamar `InlineTaskForm.reset()` e devolver foco ao título. Garantir que o card recém-criado aparece como último da coluna. **Camada:** ui. **Esforço:** P. **Depende:** TASK-041. **TC aceite:** TC-089.

### TASK-043 ✅ — Testes unitários de `InlineTaskForm`

**Descrição:** `tests/test_ui/test_inline_task_form.py` cobrindo foco inicial, `Enter`/`Esc`, maxlength, validação de título vazio, `reset()`, ordem de Tab, `show_error`. **Camada:** testes. **Esforço:** P. **Depende:** TASK-038. **TC aceite:** TC-082–TC-085, TC-093, TC-094.

### TASK-044 ✅ — Testes de integração UI+Service+DB

**Descrição:** `tests/test_integration/test_kanban_create_card.py` cobrindo criação em cada coluna padrão (regra coluna→status), sincronização Todo List (signal `task_created`), contador atualizado, último card no final. **Camada:** testes. **Esforço:** M. **Depende:** TASK-041, TASK-042. **TC aceite:** TC-080, TC-081, TC-089.

### TASK-045 ✅ — Testes multi-form e preservação de rascunho

**Descrição:** `tests/test_ui/test_kanban_column_inline.py` cobrindo: dois forms abertos simultaneamente; clicar fora não fecha; cancelar um não afeta outro; reload incremental preserva rascunho. **Camada:** testes. **Esforço:** P. **Depende:** TASK-041. **TC aceite:** TC-087, TC-088, TC-090.

### TASK-046 ✅ — Benchmark e falha de persistência

**Descrição:** teste `pytest.mark.slow` com banco pré-populado com 10k tarefas medindo criação ≤ 200ms (TC-092). Teste de falha de persistência (mock levantando exceção) verificando que o form permanece aberto com dados e `show_error` é exibido (TC-091). **Camada:** testes. **Esforço:** P. **Depende:** TASK-041. **TC aceite:** TC-091, TC-092.

**Totais US-10:** 6P + 3M = 9 tasks atômicas + 1 (TASK-042 P) — **total 10 tasks: 7P + 3M ≈ 20–26h.**

**Ordem topológica:** TASK-037 → TASK-038 → (TASK-043 ∥ TASK-039) → TASK-040 → TASK-041 → TASK-042 → (TASK-044 ∥ TASK-045 ∥ TASK-046).

**Rollback:** feature aditiva, sem migração de dados. Em caso de regressão crítica, reverter commits na ordem inversa (TASK-046 → TASK-037). A refatoração de `_reload_board` (TASK-041) é o único ponto com risco de regressão em telas existentes do Kanban — se necessário, reverter apenas TASK-041 (volta a reload full) mantendo TASK-037/038 disponíveis.

---

## Ordem de ataque sugerida (dívidas técnicas, atualizada)

1. **DT-023** (alinhamento com PO sobre split de testes) — bloqueante para definir trabalho de testes
2. **DT-033** (convenções Qt headless) — armadilha recorrente que amplificou custo do QA na US-07
3. **DT-006** (duplicação _COR_PRIORIDADE) + **DT-009** (utils/constants) — resolver junto com DT-007 (já concluída)
4. **DT-026** (unificar conftests) + **DT-029** (BEGIN aninhado) — reduz armadilhas futuras
5. **DT-012** (side effect no update) + **DT-008** (datetime naive) — melhorar modelo de dados
6. **DT-027** + **DT-028** + **DT-030** + **DT-032** + **DT-019** — fechar gaps de cobertura
7. **DT-024** (`TITULO_MAX_LEN`) + **DT-025** (`_parse_datetime`) + **DT-017** + **DT-034** + **DT-035** — ajustes de convenção/polish
8. **DT-014** (índices) + **DT-015** (context manager) + **DT-031** (virtual scrolling) — performance / escala
9. **DT-010** (acoplamento repositórios) + **DT-013** (FK colunas) + **DT-011** (Qt no service) — refatorações maiores (parecer PO: backlog)
9. **DT-020** (arquivos planejados) — informativo, aguarda roadmap
