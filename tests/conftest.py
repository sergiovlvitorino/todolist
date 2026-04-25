"""Fixtures compartilhadas entre os testes.

Convenção de nomenclatura (DT-026):
  Fixtures canônicas (db_conn, task_repo, column_repo, task_service) estão
  definidas aqui e são reutilizadas por todas as camadas de teste.
  Aliases com sufixos (_ui, _int) são fornecidos neste mesmo arquivo para
  compatibilidade com os testes existentes — evitando renomeação em massa.
  Conftests locais (test_ui/, test_integration/) não devem mais redefinir o
  corpo dessas fixtures; devem apenas importar ou delegar para as canônicas.

Convenções para testes Qt em ambiente headless (DT-033):
  Este projeto roda em XCB headless (sem display físico) — pytest-qt usa
  um servidor X virtual ou offscreen. Duas armadilhas recorrentes:

  1. ``QWidget.isVisible()`` vs ``QWidget.isHidden()``
     Em ambiente headless, ``isVisible()`` retorna ``False`` se o widget
     raiz não foi exibido via ``show()``, mesmo que o widget filho esteja
     logicamente ativo. Use ``not widget.isHidden()`` para verificar se
     o widget está lógicamente visível/ativo sem depender da hierarquia de
     janelas do sistema operacional.

     Regra: NUNCA use ``assert widget.isVisible()`` em testes sem
     ``widget.show()`` explícito. Prefira ``assert not widget.isHidden()``.

  2. ``qtbot.keyClicks()`` em widget não exibido causa SIGABRT
     ``qtbot.keyClicks(widget, "abc")`` — e outros métodos de simulação de
     teclado do qtbot — requerem que o widget alvo tenha sido exibido via
     ``show()``. Sem isso, o XCB levanta SIGABRT encerrando o processo.

     Regra: para simular entrada de texto use ``widget.setText("abc")``
     diretamente (equivalente para campos de texto). Se precisar de
     ``keyClicks``, certifique-se de chamar ``widget.show()`` e
     ``QApplication.processEvents()`` antes.

  Template para "widget visível em headless":
    widget = MyWidget(...)
    qtbot.addWidget(widget)
    widget.show()
    QApplication.processEvents()
    # a partir daqui isVisible() == True e keyClicks é seguro

  Referências internas: tests/test_ui/test_todo_widget_busca.py (cenário 8),
  tests/test_integration/test_fluxo_busca.py (_aplicar_busca).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from typing import Any

import pytest

from own_board_list.database.column_repository import ColumnRepository
from own_board_list.database.migrations import initialize_database
from own_board_list.database.task_repository import TaskRepository
from own_board_list.models.task import Task
from own_board_list.services.task_service import TaskService

# ---------------------------------------------------------------------------
# Fixtures canônicas — usadas por test_database/, test_models/, test_services/
# ---------------------------------------------------------------------------


@pytest.fixture
def db_conn() -> Generator[sqlite3.Connection, None, None]:
    """Cria uma conexão em memória com o schema inicializado."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    initialize_database(conn)
    yield conn
    conn.close()


@pytest.fixture
def task_repo(db_conn: sqlite3.Connection) -> TaskRepository:
    """Repositório de tarefas usando banco em memória."""
    return TaskRepository(db_conn)


@pytest.fixture
def column_repo(db_conn: sqlite3.Connection) -> ColumnRepository:
    """Repositório de colunas usando banco em memória."""
    return ColumnRepository(db_conn)


@pytest.fixture
def task_service(
    qtbot: Any,
    task_repo: TaskRepository,
    column_repo: ColumnRepository,
) -> TaskService:
    """Serviço de tarefas com repositórios em memória."""
    return TaskService(task_repo, column_repo)


@pytest.fixture
def sample_task() -> Task:
    """Tarefa de exemplo para uso nos testes."""
    return Task(titulo="Tarefa de Teste")


# ---------------------------------------------------------------------------
# Aliases _ui — compatibilidade com tests/test_ui/ (DT-026)
# ---------------------------------------------------------------------------


@pytest.fixture
def db_conn_ui() -> Generator[sqlite3.Connection, None, None]:
    """Alias canônico para db_conn — uso em testes de UI."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    initialize_database(conn)
    yield conn
    conn.close()


@pytest.fixture
def task_repo_ui(db_conn_ui: sqlite3.Connection) -> TaskRepository:
    """Repositório de tarefas para testes de UI."""
    return TaskRepository(db_conn_ui)


@pytest.fixture
def column_repo_ui(db_conn_ui: sqlite3.Connection) -> ColumnRepository:
    """Repositório de colunas para testes de UI."""
    return ColumnRepository(db_conn_ui)


@pytest.fixture
def task_service_ui(
    qtbot: Any,
    task_repo_ui: TaskRepository,
    column_repo_ui: ColumnRepository,
) -> TaskService:
    """Serviço de tarefas configurado para testes de UI."""
    return TaskService(task_repo_ui, column_repo_ui)


# ---------------------------------------------------------------------------
# Aliases _int — compatibilidade com tests/test_integration/ (DT-026)
# ---------------------------------------------------------------------------


@pytest.fixture
def db_conn_integration() -> Generator[sqlite3.Connection, None, None]:
    """Alias canônico para db_conn — uso em testes de integração."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    initialize_database(conn)
    yield conn
    conn.close()


@pytest.fixture
def task_repo_int(db_conn_integration: sqlite3.Connection) -> TaskRepository:
    """Repositório de tarefas para testes de integração."""
    return TaskRepository(db_conn_integration)


@pytest.fixture
def column_repo_int(db_conn_integration: sqlite3.Connection) -> ColumnRepository:
    """Repositório de colunas para testes de integração."""
    return ColumnRepository(db_conn_integration)


@pytest.fixture
def task_service_int(
    qtbot: Any,
    task_repo_int: TaskRepository,
    column_repo_int: ColumnRepository,
) -> TaskService:
    """Serviço de tarefas configurado para testes de integração."""
    return TaskService(task_repo_int, column_repo_int)
