"""Ponto de entrada da aplicação Own Board List."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication, QMessageBox

from own_board_list import __version__
from own_board_list.database.connection import get_default_db_path
from own_board_list.services.migration_service import MigrationReport, MigrationService
from own_board_list.ui.main_window import MainWindow


def _exibir_erro_migracao(app: QApplication, report: MigrationReport) -> None:
    """Exibe mensagem de erro de migration via console e QMessageBox.

    Garante que o usuário veja o caminho do backup (quando disponível) para
    permitir recuperação manual caso necessário.

    Args:
        app: Instância ativa de ``QApplication`` (necessária para exibir diálogos).
        report: ``MigrationReport`` com ``sucesso=False`` e ``erro`` preenchido.
    """
    backup_info = (
        f"\n\nBackup disponível em:\n  {report.backup_path}"
        if report.backup_path
        else "\n\n(Nenhum backup foi criado — o banco original não foi modificado.)"
    )

    mensagem = (
        f"Falha na migration do banco de dados.\n\n"
        f"Erro: {report.erro}"
        f"{backup_info}"
        f"\n\nA aplicação será encerrada para proteger os dados."
    )

    # Emite para stderr para garantir visibilidade mesmo sem interface gráfica.
    print(f"[MIGRATION ERROR] {mensagem}", file=sys.stderr)

    caixa = QMessageBox()
    caixa.setWindowTitle("Own Board List — Erro de Migration")
    caixa.setIcon(QMessageBox.Icon.Critical)
    caixa.setText("Falha na atualização do banco de dados.")
    caixa.setInformativeText(f"Erro: {report.erro}")
    caixa.setDetailedText(
        f"Versão de origem: {report.versao_origem}\n"
        f"Versão de destino: {report.versao_destino}\n"
        f"Duração: {report.duracao_s:.2f}s\n"
        f"Backup: {report.backup_path or 'não criado'}"
    )
    caixa.setStandardButtons(QMessageBox.StandardButton.Ok)
    caixa.exec()


def _executar_migrations(app: QApplication) -> bool:
    """Executa o processo de migration antes de inicializar a UI principal.

    Deve ser chamada após a criação da ``QApplication`` (para permitir uso de
    ``QMessageBox`` em caso de falha) e antes de instanciar ``MainWindow``.

    Args:
        app: Instância ativa de ``QApplication``.

    Returns:
        ``True`` se a migration foi bem-sucedida (ou não era necessária).
        ``False`` se houve falha — a aplicação deve ser encerrada.
    """
    db_path = get_default_db_path()
    service = MigrationService()
    report = service.executar(db_path)

    if not report.sucesso:
        _exibir_erro_migracao(app, report)
        return False

    return True


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
    """Inicializa e executa a aplicação.

    Sequência de bootstrap:
    1. Criar ``QApplication``.
    2. Executar ``MigrationService`` — aborta em caso de falha.
    3. Criar ``MainWindow`` e iniciar o loop de eventos.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    assert isinstance(app, QApplication)
    app.setApplicationName("Own Board List")
    app.setApplicationVersion(__version__)

    if not _executar_migrations(app):  # pragma: no cover
        sys.exit(1)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())  # pragma: no cover


if __name__ == "__main__":
    main()  # pragma: no cover
