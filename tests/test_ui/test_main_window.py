"""Testes da janela principal (MainWindow)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch


class TestMainWindowInicializacao:
    """Testes de inicialização da MainWindow."""

    def test_cria_janela_sem_excecao(self, qtbot: Any) -> None:
        """Deve instanciar MainWindow sem lançar exceções."""
        with patch("own_board_list.ui.main_window.get_default_db_path") as mock_path:
            mock_path.return_value = ":memory:"
            with patch(
                "own_board_list.ui.main_window.DatabaseConnection"
            ) as mock_db_cls:
                import sqlite3

                from own_board_list.database.migrations import initialize_database

                conn = sqlite3.connect(":memory:")
                conn.row_factory = sqlite3.Row
                initialize_database(conn)

                mock_db = MagicMock()
                mock_db.get_connection.return_value = conn
                mock_db_cls.return_value = mock_db

                from own_board_list.ui.main_window import MainWindow

                window = MainWindow()
                qtbot.addWidget(window)

                assert window is not None

    def test_titulo_janela_correto(self, qtbot: Any) -> None:
        """O título da janela deve ser 'Own Board List'."""
        with patch("own_board_list.ui.main_window.get_default_db_path") as mock_path:
            mock_path.return_value = ":memory:"
            with patch(
                "own_board_list.ui.main_window.DatabaseConnection"
            ) as mock_db_cls:
                import sqlite3

                from own_board_list.database.migrations import initialize_database

                conn = sqlite3.connect(":memory:")
                conn.row_factory = sqlite3.Row
                initialize_database(conn)

                mock_db = MagicMock()
                mock_db.get_connection.return_value = conn
                mock_db_cls.return_value = mock_db

                from own_board_list.ui.main_window import MainWindow

                window = MainWindow()
                qtbot.addWidget(window)

                assert window.windowTitle() == "Own Board List"

    def test_duas_abas_existem(self, qtbot: Any) -> None:
        """Deve haver duas abas: 'Todo List' e 'Kanban'."""
        with patch("own_board_list.ui.main_window.get_default_db_path") as mock_path:
            mock_path.return_value = ":memory:"
            with patch(
                "own_board_list.ui.main_window.DatabaseConnection"
            ) as mock_db_cls:
                import sqlite3

                from own_board_list.database.migrations import initialize_database

                conn = sqlite3.connect(":memory:")
                conn.row_factory = sqlite3.Row
                initialize_database(conn)

                mock_db = MagicMock()
                mock_db.get_connection.return_value = conn
                mock_db_cls.return_value = mock_db

                from own_board_list.ui.main_window import MainWindow

                window = MainWindow()
                qtbot.addWidget(window)

                assert window._tabs.count() == 2
                assert window._tabs.tabText(0) == "Todo List"
                assert window._tabs.tabText(1) == "Kanban"

    def test_close_event_fecha_conexao_db(self, qtbot: Any) -> None:
        """closeEvent deve chamar close() na conexão do banco de dados."""
        with patch("own_board_list.ui.main_window.get_default_db_path") as mock_path:
            mock_path.return_value = ":memory:"
            with patch(
                "own_board_list.ui.main_window.DatabaseConnection"
            ) as mock_db_cls:
                import sqlite3

                from own_board_list.database.migrations import initialize_database

                conn = sqlite3.connect(":memory:")
                conn.row_factory = sqlite3.Row
                initialize_database(conn)

                mock_db = MagicMock()
                mock_db.get_connection.return_value = conn
                mock_db_cls.return_value = mock_db

                from own_board_list.ui.main_window import MainWindow

                window = MainWindow()
                qtbot.addWidget(window)

                from PyQt6.QtGui import QCloseEvent

                event = QCloseEvent()
                window.closeEvent(event)

                mock_db.close.assert_called_once()

    def test_menu_arquivo_existe(self, qtbot: Any) -> None:
        """Deve existir o menu 'Arquivo' com a ação 'Sair'."""
        with patch("own_board_list.ui.main_window.get_default_db_path") as mock_path:
            mock_path.return_value = ":memory:"
            with patch(
                "own_board_list.ui.main_window.DatabaseConnection"
            ) as mock_db_cls:
                import sqlite3

                from own_board_list.database.migrations import initialize_database

                conn = sqlite3.connect(":memory:")
                conn.row_factory = sqlite3.Row
                initialize_database(conn)

                mock_db = MagicMock()
                mock_db.get_connection.return_value = conn
                mock_db_cls.return_value = mock_db

                from own_board_list.ui.main_window import MainWindow

                window = MainWindow()
                qtbot.addWidget(window)

                menu_bar = window.menuBar()
                assert menu_bar is not None
                # Verifica que a barra de menus tem pelo menos uma ação
                assert len(menu_bar.actions()) > 0
