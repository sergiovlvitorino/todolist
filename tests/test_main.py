"""Testes para o entrypoint da aplicação (DT-030).

Cobre ``create_app()`` — função extraída de ``main()`` para permitir
instanciar e inspecionar a janela principal sem iniciar o loop de eventos.
O trecho ``app.exec()`` permanece com ``# pragma: no cover`` em ``main.py``.

[DECISÃO] Testar fiação de dependências via create_app(), sem chamar app.exec()
  Alternativas: A) teste E2E completo com app.exec() | B) testar apenas create_app()
  Escolha: B
  Por quê: app.exec() bloqueia o processo; testes devem ser não-bloqueantes.
  Risco aceito: o loop de eventos em si não é testado — mas esse é o comportamento
               esperado para um entrypoint de aplicação desktop.
"""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication

from own_board_list.main import create_app
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
    """Testes da função main() — fiação de create_app + show + exec."""

    def test_main_chama_show_e_exec(self, qtbot: Any) -> None:
        """main() deve chamar window.show() e sys.exit(app.exec()) (linhas 35-36).

        Mocka sys.exit para não encerrar o processo e QApplication.exec para
        não bloquear o loop de eventos. Verifica apenas que o fluxo de chamadas
        ocorre corretamente — não testa o loop de eventos em si.
        """
        from own_board_list.main import main

        mock_window = MagicMock(spec=MainWindow)
        mock_app = MagicMock(spec=QApplication)
        mock_app.exec.return_value = 0

        with (
            patch(
                "own_board_list.main.create_app",
                return_value=(mock_app, mock_window),
            ),
            patch("own_board_list.main.sys.exit") as mock_exit,
        ):
            main()

        mock_window.show.assert_called_once()
        mock_exit.assert_called_once_with(mock_app.exec.return_value)
