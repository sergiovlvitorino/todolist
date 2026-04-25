"""Testes de UI do MigrationSplash — TC-104, TC-105, TC-106.

Cobre os três cenários de exibição do splash de migração:
  - TC-104: indicador de progresso aparece *somente* após ``show_progress()``;
    antes da chamada o splash fica silencioso.
  - TC-105: após receber um ``MigrationReport`` com quarentena, o splash exibe
    o caminho do arquivo de quarentena.
  - TC-106: em modo erro, o splash exibe mensagem de falha + caminho do backup;
    botão "Fechar" fica visível.

Convenção headless (DT-033): ``qtbot.addWidget`` + ``widget.show()`` +
``QApplication.processEvents()`` antes de qualquer asserção de visibilidade.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication

from own_board_list.ui.splash import MigrationSplash
from own_board_list.utils.constants import (
    LIMIAR_PROGRESSO_MIGRACAO_S,
)

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def splash(qtbot):
    """Instância de MigrationSplash exibida em ambiente headless."""
    widget = MigrationSplash()
    qtbot.addWidget(widget)
    widget.show()
    QApplication.processEvents()
    return widget


# ---------------------------------------------------------------------------
# TC-104 — Indicador de progresso condicional (> LIMIAR_PROGRESSO_MIGRACAO_S)
# ---------------------------------------------------------------------------


class TestTC104ProgressoCondicional:
    """TC-104: indicador de progresso só aparece após ``show_progress()``."""

    def test_progresso_oculto_antes_de_show_progress(self, splash: MigrationSplash):
        """Splash recém-criado e exibido não mostra barra de progresso."""
        assert not splash.progresso_visivel, (
            "A barra de progresso deve estar oculta antes de qualquer chamada "
            "a show_progress()."
        )

    def test_progresso_visivel_apos_show_progress(self, splash: MigrationSplash):
        """Após ``show_progress()``, a barra de progresso deve ficar visível."""
        splash.show_progress("Aplicando migration v1 → v2…")
        QApplication.processEvents()

        assert splash.progresso_visivel, (
            "A barra de progresso deve ficar visível após show_progress()."
        )

    def test_mensagem_de_status_exibida_apos_show_progress(
        self, splash: MigrationSplash
    ):
        """O rótulo de status deve exibir a mensagem passada a ``show_progress()``."""
        mensagem = "Aplicando migration v1 → v2…"
        splash.show_progress(mensagem)
        QApplication.processEvents()

        # _lbl_status não é propriedade pública, mas não-oculto + texto correto.
        assert not splash._lbl_status.isHidden(), (
            "O rótulo de status deve estar visível após show_progress()."
        )
        assert splash._lbl_status.text() == mensagem

    def test_limiar_valor_correto(self, splash: MigrationSplash):
        """A propriedade ``limiar_progresso_s`` deve refletir a constante global."""
        assert splash.limiar_progresso_s == LIMIAR_PROGRESSO_MIGRACAO_S
        assert splash.limiar_progresso_s == pytest.approx(1.5)

    def test_progresso_e_quarentena_ocultos_por_padrao(self, splash: MigrationSplash):
        """Nem progresso nem quarentena devem aparecer no splash inicial."""
        assert not splash.progresso_visivel
        assert not splash.quarentena_visivel
        assert not splash.erro_visivel

    def test_progresso_ocultado_apos_show_quarantine_path(
        self, splash: MigrationSplash
    ):
        """Ao exibir quarentena, a barra de progresso deve ser ocultada."""
        splash.show_progress("Migrando…")
        QApplication.processEvents()
        assert splash.progresso_visivel  # pré-condição

        splash.show_quarantine_path(
            Path("/home/usuario/.own-board-list/quarantine_20260425.json")
        )
        QApplication.processEvents()

        assert not splash.progresso_visivel, (
            "A barra de progresso deve ser ocultada ao exibir quarentena."
        )

    def test_progresso_ocultado_apos_show_error(self, splash: MigrationSplash):
        """Ao exibir erro, a barra de progresso deve ser ocultada."""
        splash.show_progress("Migrando…")
        QApplication.processEvents()
        assert splash.progresso_visivel  # pré-condição

        splash.show_error("Falha inesperada.", backup_path=None)
        QApplication.processEvents()

        assert not splash.progresso_visivel, (
            "A barra de progresso deve ser ocultada ao exibir modo de erro."
        )


# ---------------------------------------------------------------------------
# TC-105 — Exibição do caminho de quarentena
# ---------------------------------------------------------------------------


class TestTC105Quarentena:
    """TC-105: splash exibe resumo + caminho do arquivo de quarentena."""

    def test_quarentena_visivel_apos_show_quarantine_path(
        self, splash: MigrationSplash
    ):
        """Após ``show_quarantine_path()``, o painel de quarentena deve aparecer."""
        caminho = Path("/home/usuario/.own-board-list/quarantine_20260425.json")
        splash.show_quarantine_path(caminho)
        QApplication.processEvents()

        assert splash.quarentena_visivel, (
            "O painel de quarentena deve ficar visível após show_quarantine_path()."
        )

    def test_caminho_quarentena_exibido_corretamente(self, splash: MigrationSplash):
        """Caminho exibido bate com o Path passado a ``show_quarantine_path()``."""
        caminho = Path("/home/usuario/.own-board-list/quarantine_20260425.json")
        splash.show_quarantine_path(caminho)
        QApplication.processEvents()

        assert splash.caminho_quarentena_exibido == str(caminho), (
            "O caminho de quarentena exibido deve ser a representação string do Path."
        )

    def test_titulo_quarentena_nao_oculto(self, splash: MigrationSplash):
        """O rótulo de título do painel de quarentena deve estar visível."""
        caminho = Path("/tmp/quarantine_20260425.json")
        splash.show_quarantine_path(caminho)
        QApplication.processEvents()

        assert not splash._lbl_quarentena_titulo.isHidden(), (
            "O título do painel de quarentena deve estar visível."
        )

    def test_caminho_quarentena_nao_oculto(self, splash: MigrationSplash):
        """O rótulo com o caminho de quarentena deve estar visível."""
        caminho = Path("/tmp/quarantine_20260425.json")
        splash.show_quarantine_path(caminho)
        QApplication.processEvents()

        assert not splash._lbl_quarentena_caminho.isHidden(), (
            "O rótulo do caminho de quarentena deve estar visível."
        )

    def test_erro_nao_visivel_apos_quarentena(self, splash: MigrationSplash):
        """O painel de erro não deve aparecer ao exibir apenas quarentena."""
        caminho = Path("/tmp/quarantine_20260425.json")
        splash.show_quarantine_path(caminho)
        QApplication.processEvents()

        assert not splash.erro_visivel, (
            "O painel de erro não deve aparecer quando se exibe apenas quarentena."
        )

    def test_caminho_quarentena_com_path_absoluto(
        self, splash: MigrationSplash, tmp_path: Path
    ):
        """Caminho absoluto real (tmp_path) é exibido corretamente."""
        caminho = tmp_path / "quarantine_20260425.json"
        splash.show_quarantine_path(caminho)
        QApplication.processEvents()

        assert splash.caminho_quarentena_exibido == str(caminho)
        assert splash.quarentena_visivel


# ---------------------------------------------------------------------------
# TC-106 — Modo erro: mensagem, caminho do backup e botão "Fechar"
# ---------------------------------------------------------------------------


class TestTC106Erro:
    """TC-106: em modo erro, splash exibe mensagem + caminho do backup + botão."""

    def test_erro_visivel_apos_show_error(self, splash: MigrationSplash):
        """Após ``show_error()``, o painel de erro deve estar visível."""
        splash.show_error("Não foi possível completar a migração.", backup_path=None)
        QApplication.processEvents()

        assert splash.erro_visivel, (
            "O painel de erro deve ficar visível após show_error()."
        )

    def test_mensagem_erro_exibida(self, splash: MigrationSplash):
        """A mensagem de erro passada deve aparecer no rótulo correspondente."""
        mensagem = "Migration falhou: tabela corrompida."
        splash.show_error(mensagem, backup_path=None)
        QApplication.processEvents()

        assert splash._lbl_erro_mensagem.text() == mensagem
        assert not splash._lbl_erro_mensagem.isHidden()

    def test_botao_fechar_visivel_em_modo_erro(self, splash: MigrationSplash):
        """O botão "Fechar" deve estar visível somente no modo de erro."""
        # Antes de show_error, botão deve estar oculto.
        assert splash._btn_fechar.isHidden(), (
            "Botão 'Fechar' deve estar oculto antes de show_error()."
        )

        splash.show_error("Erro fatal.", backup_path=None)
        QApplication.processEvents()

        assert not splash._btn_fechar.isHidden(), (
            "Botão 'Fechar' deve estar visível após show_error()."
        )

    def test_caminho_backup_exibido_quando_fornecido(
        self, splash: MigrationSplash, tmp_path: Path
    ):
        """Quando ``backup_path`` é fornecido, o caminho deve aparecer no splash."""
        backup = tmp_path / "data_v1_20260425T120000.db"
        splash.show_error("Falha na migration.", backup_path=backup)
        QApplication.processEvents()

        assert splash.caminho_backup_exibido == str(backup), (
            "O caminho do backup deve ser exibido quando fornecido."
        )
        assert not splash._lbl_backup_caminho.isHidden()
        assert not splash._lbl_backup_titulo.isHidden()

    def test_caminho_backup_oculto_quando_none(self, splash: MigrationSplash):
        """Quando ``backup_path`` é ``None``, o painel de backup não deve aparecer."""
        splash.show_error("Falha antes do backup.", backup_path=None)
        QApplication.processEvents()

        assert splash._lbl_backup_caminho.isHidden(), (
            "O rótulo de caminho do backup deve estar oculto quando backup_path=None."
        )
        assert splash._lbl_backup_titulo.isHidden(), (
            "O título do painel de backup deve estar oculto quando backup_path=None."
        )

    def test_instrucoes_visiveis_em_modo_erro(self, splash: MigrationSplash):
        """As instruções de recuperação devem estar visíveis no modo de erro."""
        splash.show_error("Falha.", backup_path=None)
        QApplication.processEvents()

        assert not splash._lbl_instrucoes.isHidden(), (
            "As instruções de recuperação devem estar visíveis no modo de erro."
        )

    def test_quarentena_nao_visivel_em_modo_erro(self, splash: MigrationSplash):
        """O painel de quarentena não deve aparecer em modo de erro."""
        splash.show_error("Falha.", backup_path=None)
        QApplication.processEvents()

        assert not splash.quarentena_visivel, (
            "O painel de quarentena não deve aparecer em modo de erro."
        )

    def test_botao_fechar_fecha_widget(self, splash: MigrationSplash, qtbot):
        """Clicar no botão 'Fechar' deve fechar o widget."""
        splash.show_error("Erro.", backup_path=None)
        QApplication.processEvents()

        with qtbot.waitSignal(splash.destroyed, timeout=2000, raising=False):
            splash._btn_fechar.click()
            QApplication.processEvents()

        # Widget fechado (isVisible deve ser False ou widget destruído).
        assert not splash.isVisible(), (
            "Após clicar em 'Fechar', o splash deve estar fechado/invisível."
        )
