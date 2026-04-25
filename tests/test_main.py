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

from typing import Any

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
