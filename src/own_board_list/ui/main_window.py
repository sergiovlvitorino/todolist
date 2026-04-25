"""Janela principal da aplicação Own Board List."""

from __future__ import annotations

from PyQt6.QtGui import QAction, QCloseEvent, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QWidget,
)

from own_board_list.database.column_repository import ColumnRepository
from own_board_list.database.connection import DatabaseConnection, get_default_db_path
from own_board_list.database.migrations import initialize_database
from own_board_list.database.task_repository import TaskRepository
from own_board_list.services.task_service import TaskService
from own_board_list.ui.kanban.kanban_widget import KanbanWidget
from own_board_list.ui.todo.todo_widget import TodoWidget


class MainWindow(QMainWindow):
    """Janela principal que agrega as abas Todo List e Kanban."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Inicializa a janela, o banco de dados e os widgets."""
        super().__init__(parent)
        self.setWindowTitle("Own Board List")
        self.setMinimumSize(1024, 768)

        self._setup_database()
        self._setup_menu()
        self._setup_central_widget()

    def _setup_database(self) -> None:
        """Inicializa a conexão com o banco de dados e os repositórios."""
        db_path = get_default_db_path()
        self._db_connection = DatabaseConnection(db_path)
        conn = self._db_connection.get_connection()
        initialize_database(conn)

        self._task_repo = TaskRepository(conn)
        self._column_repo = ColumnRepository(conn)
        self._task_service = TaskService(self._task_repo, self._column_repo, self)

    def _setup_menu(self) -> None:
        """Cria a barra de menus com as ações disponíveis."""
        menu_bar = self.menuBar()
        if menu_bar is None:
            return

        menu_arquivo = menu_bar.addMenu("Arquivo")
        if menu_arquivo is None:
            return

        action_sair = QAction("Sair", self)
        action_sair.setShortcut(QKeySequence("Ctrl+Q"))
        action_sair.triggered.connect(self.close)
        menu_arquivo.addAction(action_sair)

    def _setup_central_widget(self) -> None:
        """Cria o QTabWidget central com as abas de Todo e Kanban."""
        self._tabs = QTabWidget(self)
        self.setCentralWidget(self._tabs)

        self._todo_widget = TodoWidget(self._task_service, self)
        self._kanban_widget = KanbanWidget(self._task_service, self._column_repo, self)

        self._tabs.addTab(self._todo_widget, "Todo List")
        self._tabs.addTab(self._kanban_widget, "Kanban")

    def closeEvent(self, event: QCloseEvent | None) -> None:
        """Fecha a conexão com o banco de dados ao encerrar."""
        self._db_connection.close()
        if event is not None:
            super().closeEvent(event)
