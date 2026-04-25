"""Testes para o entrypoint da aplicação (DT-030, TASK-059).

Cobre ``create_app()`` — função extraída de ``main()`` para permitir
instanciar e inspecionar a janela principal sem iniciar o loop de eventos.
O trecho ``app.exec()`` permanece com ``# pragma: no cover`` em ``main.py``.

Cobre também ``_executar_migrations()`` e ``_exibir_erro_migracao()`` (TASK-059):
integração do ``MigrationService`` no bootstrap antes da UI.

[DECISÃO] Testar fiação de dependências via create_app(), sem chamar app.exec()
  Alternativas: A) teste E2E completo com app.exec() | B) testar apenas create_app()
  Escolha: B
  Por quê: app.exec() bloqueia o processo; testes devem ser não-bloqueantes.
  Risco aceito: o loop de eventos em si não é testado — mas esse é o comportamento
               esperado para um entrypoint de aplicação desktop.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication, QMessageBox

from own_board_list.main import (
    _executar_migrations,
    _exibir_erro_migracao,
    create_app,
)
from own_board_list.services.migration_service import MigrationReport
from own_board_list.ui.main_window import MainWindow


class TestCreateApp:
    """Testes de fiação de dependências do create_app()."""

    def test_create_app_retorna_qapplication_e_mainwindow(self, qtbot: Any) -> None:
        """create_app() deve retornar (QApplication, MainWindow)."""
        app, window = create_app()
        qtbot.addWidget(window)

        assert isinstance(app, QApplication)
        assert isinstance(window, MainWindow)

    def test_create_app_reutiliza_qapplication_existente(self, qtbot: Any) -> None:
        """Se já houver uma QApplication, create_app() deve reutilizá-la.

        pytest-qt já cria uma QApplication antes de rodar os testes; a segunda
        chamada a create_app() não deve criar uma segunda instância (Qt proíbe).
        """
        app1, _ = create_app()
        app2, _ = create_app()

        assert app1 is app2

    def test_create_app_configura_nome_aplicacao(self, qtbot: Any) -> None:
        """create_app() deve setar applicationName como 'Own Board List'."""
        app, window = create_app()
        qtbot.addWidget(window)

        assert app.applicationName() == "Own Board List"

    def test_create_app_configura_versao_aplicacao(self, qtbot: Any) -> None:
        """create_app() deve setar applicationVersion com a versão do pacote."""
        from own_board_list import __version__

        app, window = create_app()
        qtbot.addWidget(window)

        assert app.applicationVersion() == __version__

    def test_create_app_mainwindow_tem_titulo_correto(self, qtbot: Any) -> None:
        """A MainWindow criada por create_app() deve ter o título esperado."""
        _, window = create_app()
        qtbot.addWidget(window)

        assert "Own Board List" in window.windowTitle()

    def test_create_app_cria_qapplication_quando_nao_existe(self, qtbot: Any) -> None:
        """Branch ``if app is None`` deve criar QApplication com sys.argv (linha 24).

        Simula o cenário em que ``QApplication.instance()`` retorna ``None``
        (sem instância prévia), forçando a criação via ``QApplication(sys.argv)``.
        Mocka apenas o método de classe ``instance`` para retornar ``None`` na
        primeira chamada e, na segunda, retornar a instância real (para que o
        ``assert isinstance`` do código de produção passe com a classe real).
        """
        existing_app = QApplication.instance()
        assert isinstance(existing_app, QApplication)

        call_count = 0

        def instance_side_effect() -> QApplication | None:
            nonlocal call_count
            call_count += 1
            # Primeira chamada (verificação ``if app is None``) -> None
            # Chamadas seguintes -> instância real (para o assert isinstance)
            if call_count == 1:
                return None
            return existing_app  # type: ignore[return-value]

        with patch.object(QApplication, "instance", side_effect=instance_side_effect):
            # Também mocka o construtor para NÃO criar segunda instância Qt
            with patch(
                "own_board_list.main.QApplication.__init__", return_value=None
            ) as mock_init:
                app, window = create_app()
                qtbot.addWidget(window)

        # Construtor foi chamado com sys.argv (branch if app is None executou)
        mock_init.assert_called_once_with(sys.argv)
        assert isinstance(window, MainWindow)


class TestMain:
    """Testes da função main() — bootstrap com migration + show + exec."""

    def test_main_chama_show_e_exec(self, qtbot: Any) -> None:
        """main() deve chamar window.show() e sys.exit(app.exec()).

        Mocka _executar_migrations para retornar True (sucesso), MainWindow e
        sys.exit para não encerrar o processo, e QApplication.exec para não
        bloquear o loop de eventos. Verifica que o fluxo de chamadas ocorre
        corretamente — não testa o loop de eventos em si.
        """
        from own_board_list.main import main

        mock_window = MagicMock(spec=MainWindow)

        with (
            patch(
                "own_board_list.main._executar_migrations",
                return_value=True,
            ),
            patch(
                "own_board_list.main.MainWindow",
                return_value=mock_window,
            ),
            patch("own_board_list.main.sys.exit") as mock_exit,
            patch(
                "own_board_list.main.QApplication.exec",
                return_value=0,
            ),
        ):
            main()

        mock_window.show.assert_called_once()
        mock_exit.assert_called_once_with(0)


class TestExecutarMigrations:
    """Testes para _executar_migrations() (TASK-059 / TC-094)."""

    def test_retorna_true_quando_migration_bem_sucedida(self, qtbot: Any) -> None:
        """_executar_migrations() retorna True quando MigrationService tiver sucesso."""
        mock_app = MagicMock(spec=QApplication)
        report_sucesso = MigrationReport(
            versao_origem=1,
            versao_destino=2,
            sucesso=True,
        )

        with patch(
            "own_board_list.main.MigrationService.executar",
            return_value=report_sucesso,
        ):
            resultado = _executar_migrations(mock_app)

        assert resultado is True

    def test_retorna_false_quando_migration_falha(self, qtbot: Any) -> None:
        """_executar_migrations() retorna False quando executar() falhar."""
        mock_app = MagicMock(spec=QApplication)
        report_falha = MigrationReport(
            versao_origem=1,
            versao_destino=1,
            sucesso=False,
            erro="Falha simulada",
        )

        with (
            patch(
                "own_board_list.main.MigrationService.executar",
                return_value=report_falha,
            ),
            patch("own_board_list.main._exibir_erro_migracao"),
        ):
            resultado = _executar_migrations(mock_app)

        assert resultado is False

    def test_chama_exibir_erro_quando_falha(self, qtbot: Any) -> None:
        """_executar_migrations() deve chamar _exibir_erro_migracao quando falha."""
        mock_app = MagicMock(spec=QApplication)
        report_falha = MigrationReport(
            versao_origem=1,
            versao_destino=1,
            sucesso=False,
            erro="Falha simulada",
        )

        with (
            patch(
                "own_board_list.main.MigrationService.executar",
                return_value=report_falha,
            ),
            patch("own_board_list.main._exibir_erro_migracao") as mock_exibir,
        ):
            _executar_migrations(mock_app)

        mock_exibir.assert_called_once_with(mock_app, report_falha)

    def test_nao_chama_exibir_erro_quando_sucesso(self, qtbot: Any) -> None:
        """_executar_migrations() NÃO deve chamar _exibir_erro_migracao em sucesso."""
        mock_app = MagicMock(spec=QApplication)
        report_sucesso = MigrationReport(
            versao_origem=2,
            versao_destino=2,
            sucesso=True,
        )

        with (
            patch(
                "own_board_list.main.MigrationService.executar",
                return_value=report_sucesso,
            ),
            patch("own_board_list.main._exibir_erro_migracao") as mock_exibir,
        ):
            _executar_migrations(mock_app)

        mock_exibir.assert_not_called()

    def test_usa_caminho_padrao_do_banco(self, qtbot: Any) -> None:
        """_executar_migrations() deve usar get_default_db_path() para o banco."""
        mock_app = MagicMock(spec=QApplication)
        db_path_esperado = Path("/tmp/fake_db/data.db")
        report_sucesso = MigrationReport(
            versao_origem=2,
            versao_destino=2,
            sucesso=True,
        )

        with (
            patch(
                "own_board_list.main.get_default_db_path",
                return_value=db_path_esperado,
            ) as mock_get_path,
            patch(
                "own_board_list.main.MigrationService.executar",
                return_value=report_sucesso,
            ) as mock_executar,
        ):
            _executar_migrations(mock_app)

        mock_get_path.assert_called_once()
        mock_executar.assert_called_once_with(db_path_esperado)


class TestExibirErroMigracao:
    """Testes para _exibir_erro_migracao() (TASK-059 / TC-094)."""

    def test_emite_para_stderr(self, qtbot: Any, capsys: Any) -> None:
        """_exibir_erro_migracao() deve emitir mensagem de erro para stderr."""
        mock_app = MagicMock(spec=QApplication)
        report = MigrationReport(
            versao_origem=1,
            versao_destino=1,
            sucesso=False,
            erro="Integridade comprometida",
        )

        with patch("own_board_list.main.QMessageBox") as mock_caixa_cls:
            mock_caixa = MagicMock()
            mock_caixa_cls.return_value = mock_caixa
            _exibir_erro_migracao(mock_app, report)

        captured = capsys.readouterr()
        assert "MIGRATION ERROR" in captured.err
        assert "Integridade comprometida" in captured.err

    def test_inclui_caminho_backup_no_stderr_quando_disponivel(
        self, qtbot: Any, capsys: Any
    ) -> None:
        """stderr deve conter o caminho do backup quando ele existir."""
        mock_app = MagicMock(spec=QApplication)
        backup = Path("/home/user/.own-board-list/data.db.bak")
        report = MigrationReport(
            versao_origem=1,
            versao_destino=1,
            backup_path=backup,
            sucesso=False,
            erro="Falha de migration",
        )

        with patch("own_board_list.main.QMessageBox") as mock_caixa_cls:
            mock_caixa = MagicMock()
            mock_caixa_cls.return_value = mock_caixa
            _exibir_erro_migracao(mock_app, report)

        captured = capsys.readouterr()
        assert str(backup) in captured.err

    def test_mensagem_sem_backup_indica_banco_intacto(
        self, qtbot: Any, capsys: Any
    ) -> None:
        """Sem backup, a mensagem deve indicar que o banco não foi modificado."""
        mock_app = MagicMock(spec=QApplication)
        report = MigrationReport(
            versao_origem=1,
            versao_destino=1,
            backup_path=None,
            sucesso=False,
            erro="Versão futura detectada",
        )

        with patch("own_board_list.main.QMessageBox") as mock_caixa_cls:
            mock_caixa = MagicMock()
            mock_caixa_cls.return_value = mock_caixa
            _exibir_erro_migracao(mock_app, report)

        captured = capsys.readouterr()
        assert "não foi modificado" in captured.err

    def test_exibe_qmessagebox_com_icone_critico(self, qtbot: Any) -> None:
        """_exibir_erro_migracao() deve exibir QMessageBox com ícone Critical.

        Usa a instância real de QMessageBox (sem mock de classe) para que
        ``QMessageBox.Icon.Critical`` seja resolvido para o enum real.
        """
        mock_app = MagicMock(spec=QApplication)
        report = MigrationReport(
            versao_origem=1,
            versao_destino=1,
            sucesso=False,
            erro="Erro de teste",
        )

        chamadas_setIcon: list[Any] = []

        with (
            patch.object(
                QMessageBox,
                "setIcon",
                side_effect=lambda icon: chamadas_setIcon.append(icon),
            ),
            patch.object(QMessageBox, "exec"),
        ):
            _exibir_erro_migracao(mock_app, report)

        assert len(chamadas_setIcon) == 1
        assert chamadas_setIcon[0] == QMessageBox.Icon.Critical

    def test_qmessagebox_e_executado(self, qtbot: Any) -> None:
        """_exibir_erro_migracao() deve chamar exec() no QMessageBox para bloqueá-lo."""
        mock_app = MagicMock(spec=QApplication)
        report = MigrationReport(
            versao_origem=1,
            versao_destino=1,
            sucesso=False,
            erro="Erro",
        )

        with patch("own_board_list.main.QMessageBox") as mock_caixa_cls:
            mock_caixa = MagicMock()
            mock_caixa_cls.return_value = mock_caixa
            _exibir_erro_migracao(mock_app, report)

        mock_caixa.exec.assert_called_once()
