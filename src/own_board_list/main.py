"""Ponto de entrada da aplicação Own Board List."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from own_board_list import __version__
from own_board_list.ui.main_window import MainWindow


def create_app() -> tuple[QApplication, MainWindow]:
    """Cria e configura a QApplication e a janela principal.

    Separa a fiação de dependências de ``app.exec()``, permitindo que testes
    instanciem e inspecionem a janela sem iniciar o loop de eventos.

    Returns:
        Tupla ``(app, window)`` prontos para uso.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    assert isinstance(app, QApplication)
    app.setApplicationName("Own Board List")
    app.setApplicationVersion(__version__)

    window = MainWindow()
    return app, window


def main() -> None:
    """Inicializa e executa a aplicação."""
    app, window = create_app()
    window.show()
    sys.exit(app.exec())  # pragma: no cover


if __name__ == "__main__":
    main()  # pragma: no cover
