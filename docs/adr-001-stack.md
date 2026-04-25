# ADR-001 — Escolha do Stack Técnico

**Status:** Aceito
**Data:** 2026-04-16
**Autor:** Tech Lead (agente tl-python)

---

## Contexto

Precisamos construir um aplicativo desktop multiplataforma (Windows 10+, macOS 12+, Linux/Ubuntu 22.04+) para gestão pessoal de tarefas. O aplicativo terá duas visões — Todo List e Kanban — com drag-and-drop obrigatório, persistência local e execução offline. Não há autenticação, rede ou backend envolvidos.

O principal desafio técnico é entregar uma UI responsiva com drag-and-drop funcional, boa aparência nativa, e manutenção simples para um projeto Python puro.

---

## Decisão

### Framework UI: PyQt6

**Escolhido: PyQt6 6.7+**

Alternativas avaliadas:

| Framework | Prós | Contras | Veredicto |
|-----------|------|---------|-----------|
| **PyQt6** | Maduro, documentação vasta, suporte nativo a drag-and-drop (`QDrag`, `QMimeData`), widgets ricos (`QTableView`, `QListWidget`), estilização via QSS, boa performance, empacotamento via PyInstaller | Licença GPL (aceitável para projeto pessoal), API verbosa | **Escolhido** |
| **PySide6** | API idêntica ao PyQt6, licença LGPL | Ecossistema ligeiramente menor, algumas diferenças sutis em signals/slots | Boa alternativa, mas PyQt6 tem mais exemplos e respostas no Stack Overflow |
| **Tkinter** | Incluso na stdlib, leve | Visual datado, drag-and-drop é trabalhoso e frágil, sem suporte nativo a Kanban-style boards | Descartado |
| **Dear PyGui** | Renderização GPU, boa performance | Paradigma immediate-mode, drag-and-drop limitado, comunidade menor | Descartado |
| **Kivy** | Cross-platform incluindo mobile | Visual não-nativo em desktop, curva de aprendizado, drag-and-drop requer implementação manual | Descartado |
| **CustomTkinter** | Visual moderno sobre Tkinter | Mesmas limitações de drag-and-drop do Tkinter | Descartado |

**Justificativa principal:** O drag-and-drop é requisito obrigatório (US-09, US-11). PyQt6 oferece a melhor infraestrutura nativa para isso (`QDrag`, `QDropEvent`, `QMimeData`), além de widgets como `QGraphicsView` ou `QListWidget` que suportam reordenação visual com mínimo esforço. Nenhum outro framework Python oferece drag-and-drop tão robusto e bem documentado.

### Banco de Dados: SQLite via sqlite3

**Escolhido: SQLite 3 (módulo `sqlite3` da stdlib)**

| Opção | Prós | Contras | Veredicto |
|-------|------|---------|-----------|
| **sqlite3 (stdlib)** | Zero dependências externas, ACID, suporta 10k+ registros sem degradação, queries SQL para filtros/busca, arquivo único portável | Requer SQL (não é grande problema) | **Escolhido** |
| **JSON (arquivo)** | Simples, legível | Não escala bem para 10k tarefas (RNF-02), sem índices, sem transações atômicas, risco de corrupção | Descartado |
| **SQLAlchemy** | ORM robusto | Overhead desnecessário para modelo simples com 2 tabelas | Descartado — usaremos SQL direto com um Repository Pattern leve |
| **TinyDB** | API simples, baseado em JSON | Mesmos problemas de performance do JSON para volume alto | Descartado |

**Justificativa principal:** O RNF-02 exige suporte a 10.000 tarefas sem degradação. SQLite é a única opção que garante isso com consultas indexadas. O módulo `sqlite3` já faz parte da stdlib, eliminando dependências extras. O arquivo `.db` é portável e permite backup simples (RNF-06).

### Ferramentas de Desenvolvimento

| Ferramenta | Função | Justificativa |
|------------|--------|---------------|
| **uv** | Gerenciador de pacotes e ambientes virtuais | Rápido (escrito em Rust), substitui pip + venv + pip-tools. Resolve dependências em segundos. |
| **ruff** | Linter e formatter | Substitui flake8 + isort + black. Extremamente rápido, configuração unificada em `pyproject.toml`. |
| **mypy** | Type checking estático | Garante segurança de tipos, especialmente importante nas interfaces entre camadas (models, repositories, UI). Modo `--strict` recomendado. |
| **pytest** | Framework de testes | Padrão da indústria. Suporte a fixtures, parametrize, coverage. Usaremos `pytest-qt` para testes de widgets. |
| **pytest-qt** | Testes de widgets Qt | Plugin que expõe o `qtbot` para simular interações de UI (cliques, drag, teclado). |
| **pytest-cov** | Cobertura de testes | Relatório de cobertura integrado ao pytest. |
| **PyInstaller** | Empacotamento | Gera executável único para Windows, macOS e Linux (RNF-03). Amplamente usado com PyQt6. |

### Padrão Arquitetural: MVP (Model-View-Presenter)

Adotaremos o padrão MVP adaptado para Qt:

- **Model:** Classes de domínio (`Task`, `KanbanColumn`) + Repository para persistência
- **View:** Widgets PyQt6 (telas, painéis, formulários) — responsáveis apenas por renderização e captura de eventos
- **Presenter/Controller:** Camada intermediária que orquestra lógica de negócio, validações e coordenação entre views

Isso garante testabilidade (presenters podem ser testados sem UI) e separação de responsabilidades.

### Comunicação entre Componentes: Signals/Slots do Qt

Para a sincronização entre abas (US-13), usaremos o sistema nativo de signals e slots do Qt. Um `TaskService` central emitirá sinais (`task_created`, `task_updated`, `task_deleted`, `tasks_reloaded`) e ambas as views (Todo List e Kanban) se conectarão a esses sinais. Isso evita acoplamento direto entre views.

#### Decisão consciente: `TaskService` herda `QObject`

A consequência direta da escolha acima é que `TaskService` **herda de `QObject`** para poder declarar `pyqtSignal`. Isso acopla a camada de serviço ao framework Qt. Alternativas avaliadas:

| Abordagem | Prós | Contras |
|-----------|------|---------|
| **Service herda QObject (adotado)** | Zero overhead de roteamento; signals diretos para UI; simples e idiomático Qt | Testes de serviço precisam de `QApplication` (via `qtbot`); lógica não é 100% portável para outro framework |
| Observer Pattern puro + bridge Qt | Service 100% testável sem Qt; portável | Dobra a superfície de código (subject + bridge); signals duplicados em duas APIs |
| Event Bus externo | Desacopla totalmente service e UI | Sobrepõe-se ao mecanismo nativo do Qt; custo de boilerplate sem ganho real dada a escala |

**Justificativa:** dado o escopo (app desktop pessoal, 1 service, 2 views), o ganho de testabilidade pura não compensa a complexidade adicional. `pytest-qt` já resolve a dependência de `QApplication` em testes com custo mínimo. A decisão é reversível (DT-011 no backlog) caso o projeto cresça para justificar um service framework-agnóstico. **Status:** aceito; revisitar se surgirem mais de 2 views ou se houver intenção de reuso fora do Qt.

---

## Estrutura de Diretórios

```
own-board-list/
├── pyproject.toml              # Metadados, dependências, configuração de ruff/mypy/pytest
├── uv.lock                     # Lock de dependências (gerado pelo uv)
├── README.md                   # Visão geral do projeto
├── docs/
│   ├── funcionalidades.md      # Documento de funcionalidades (PO)
│   ├── adr-001-stack.md        # Este ADR
│   └── tasks.md                # Breakdown técnico de tasks
├── src/
│   └── own_board_list/
│       ├── __init__.py          # Versão do pacote
│       ├── main.py              # Entry point — inicializa QApplication
│       ├── models/
│       │   ├── __init__.py
│       │   ├── enums.py         # Enums Prioridade e StatusTarefa (módulo folha — ver ADR-003)
│       │   ├── task.py          # Dataclass Task
│       │   └── kanban_column.py # Dataclass KanbanColumn
│       ├── database/
│       │   ├── __init__.py
│       │   ├── connection.py    # Gerenciamento de conexão SQLite
│       │   ├── migrations.py    # Criação/migração de tabelas
│       │   ├── task_repository.py      # CRUD de tarefas
│       │   └── column_repository.py    # CRUD de colunas Kanban
│       ├── services/
│       │   ├── __init__.py
│       │   ├── task_service.py         # Lógica de negócio + signals
│       │   └── export_service.py       # Exportação JSON/CSV
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── main_window.py          # Janela principal com QTabWidget
│       │   ├── todo/
│       │   │   ├── __init__.py
│       │   │   ├── todo_widget.py      # Widget principal da aba Todo List
│       │   │   ├── task_form.py        # Formulário de criação/edição
│       │   │   └── task_list_item.py   # Widget de item individual
│       │   ├── kanban/
│       │   │   ├── __init__.py
│       │   │   ├── kanban_widget.py    # Widget principal da aba Kanban
│       │   │   ├── kanban_column_widget.py  # Widget de coluna
│       │   │   ├── kanban_card_widget.py    # Widget de card (draggable)
│       │   │   └── card_detail_panel.py     # Painel lateral de detalhes
│       │   ├── dialogs/
│       │   │   ├── __init__.py
│       │   │   ├── confirm_dialog.py   # Diálogo de confirmação reutilizável
│       │   │   └── export_dialog.py    # Diálogo de exportação
│       │   └── theme/
│       │       ├── __init__.py
│       │       ├── theme_manager.py    # Gerenciador de temas
│       │       ├── light.qss           # Stylesheet tema claro
│       │       └── dark.qss            # Stylesheet tema escuro
│       └── utils/
│           ├── __init__.py
│           └── constants.py            # Constantes (prioridades, status, etc.)
└── tests/
    ├── __init__.py
    ├── conftest.py              # Fixtures compartilhadas (db em memória, qtbot)
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

## Consequências

### Positivas

- **Drag-and-drop robusto:** PyQt6 oferece a melhor implementação de drag-and-drop entre os frameworks Python, atendendo diretamente US-09 e US-11.
- **Performance garantida:** SQLite com índices atende facilmente os 10.000 registros do RNF-02. PyQt6 renderiza milhares de widgets sem engasgar.
- **Testabilidade:** A arquitetura MVP permite testar lógica de negócio isoladamente. `pytest-qt` cobre testes de UI.
- **Empacotamento confiável:** PyInstaller + PyQt6 é uma combinação consolidada para gerar executáveis em todas as plataformas.
- **Tooling moderno:** uv + ruff + mypy garantem qualidade de código e experiência de desenvolvimento ágil.
- **Temas:** PyQt6 suporta stylesheets QSS, facilitando a implementação de tema claro/escuro (US-16).

### Negativas

- **Licença GPL:** PyQt6 é GPL. Para um projeto pessoal/open source não há impacto, mas se o projeto fosse proprietário e fechado, seria necessário adquirir licença comercial ou migrar para PySide6 (LGPL).
- **Peso do pacote:** PyQt6 adiciona ~80MB ao executável empacotado. Aceitável para desktop, mas é o maior contribuinte ao tamanho final.
- **Curva de aprendizado:** PyQt6 tem API extensa e verbosa. Mitigado pela vasta documentação e exemplos disponíveis.

### Riscos

- **Compatibilidade PyInstaller + PyQt6 em macOS ARM:** Pode haver edge cases ao empacotar para Apple Silicon. Mitigação: testar empacotamento cedo (Fase 0).
- **Performance do drag-and-drop com muitos cards:** Se uma coluna tiver centenas de cards, o repaint pode ser lento. Mitigação: virtualização de lista ou paginação (se necessário no futuro).
