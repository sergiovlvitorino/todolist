"""Testes unitários do widget InlineTaskForm.

Cobre TC-082, TC-083, TC-084, TC-085, TC-093, TC-094.
"""

from __future__ import annotations

from typing import Any

import pytest
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication

from own_board_list.models.task import Prioridade
from own_board_list.ui.kanban.inline_task_form import (
    _STYLE_TITULO_ERRO,
    _STYLE_TITULO_NORMAL,
    InlineTaskForm,
)
from own_board_list.utils.constants import TITULO_MAX_LEN

# ---------------------------------------------------------------------------
# Fixtures locais
# ---------------------------------------------------------------------------


@pytest.fixture
def form(qtbot: Any) -> InlineTaskForm:
    """InlineTaskForm instanciado e registrado no qtbot."""
    f = InlineTaskForm()
    qtbot.addWidget(f)
    f.show()
    QApplication.processEvents()
    return f


# ---------------------------------------------------------------------------
# TC-094 — Prioridade padrão é MEDIA
# ---------------------------------------------------------------------------


class TestPrioridadePadrao:
    """TC-094 — Prioridade padrão ao abrir InlineTaskForm é MEDIA."""

    def test_prioridade_padrao_media(self, form: InlineTaskForm) -> None:
        """Sem interação, o ComboBox de prioridade deve selecionar Prioridade.MEDIA."""
        prioridade = form._combo_prioridade.currentData()
        assert prioridade == Prioridade.MEDIA


# ---------------------------------------------------------------------------
# TC-082 — Foco inicial no campo título
# ---------------------------------------------------------------------------


class TestFocoInicial:
    """TC-082 — InlineTaskForm abre com foco no campo título."""

    def test_focus_title_chama_set_focus(self, form: InlineTaskForm) -> None:
        """focus_title() deve chamar setFocus no QLineEdit de título.

        Em headless (XCB sem display físico), QApplication.focusWidget() retorna
        None — QTimer.singleShot não entrega foco real sem janela ativa. Padrão
        do projeto (DT-033): usar mock/spy para verificar que setFocus foi chamado.
        """
        chamadas: list[bool] = []
        original = form._edit_titulo.setFocus

        def spy(*args: Any, **kwargs: Any) -> None:
            chamadas.append(True)
            original(*args, **kwargs)

        form._edit_titulo.setFocus = spy  # type: ignore[method-assign]

        form.focus_title()
        QApplication.processEvents()

        assert len(chamadas) == 1, (
            "focus_title() deve chamar setFocus() no campo título"
        )


# ---------------------------------------------------------------------------
# TC-083 — Enter confirma / Esc cancela
# ---------------------------------------------------------------------------


class TestAtalhosTeclado:
    """TC-083 — Enter confirma e Esc cancela o formulário."""

    def test_enter_no_titulo_emite_submitted(self, form: InlineTaskForm) -> None:
        """returnPressed do título deve emitir submitted com dados corretos."""
        form._edit_titulo.setText("Minha Tarefa")

        sinais: list[dict] = []  # type: ignore[type-arg]
        form.submitted.connect(sinais.append)

        form._edit_titulo.returnPressed.emit()

        assert len(sinais) == 1
        assert sinais[0]["titulo"] == "Minha Tarefa"
        assert sinais[0]["prioridade"] == Prioridade.MEDIA
        assert sinais[0]["data_vencimento"] is None

    def test_esc_emite_cancelled(self, form: InlineTaskForm) -> None:
        """Tecla Esc deve emitir o signal cancelled."""
        cancelados: list[None] = []
        form.cancelled.connect(lambda: cancelados.append(None))

        event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Escape,
            Qt.KeyboardModifier.NoModifier,
        )
        form.keyPressEvent(event)

        assert len(cancelados) == 1

    def test_esc_aceita_evento_sem_propagacao(self, form: InlineTaskForm) -> None:
        """O evento de Esc deve ser marcado como aceito (sem propagação)."""
        event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Escape,
            Qt.KeyboardModifier.NoModifier,
        )
        form.keyPressEvent(event)
        assert event.isAccepted()

    def test_outras_teclas_nao_interferem(self, form: InlineTaskForm) -> None:
        """Teclas que não sejam Esc não devem emitir cancelled."""
        cancelados: list[None] = []
        form.cancelled.connect(lambda: cancelados.append(None))

        event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_A,
            Qt.KeyboardModifier.NoModifier,
        )
        form.keyPressEvent(event)

        assert len(cancelados) == 0


# ---------------------------------------------------------------------------
# TC-084 — Validações de entrada
# ---------------------------------------------------------------------------


class TestValidacoes:
    """TC-084 — Validações de entrada do InlineTaskForm."""

    def test_titulo_vazio_nao_emite_submitted(self, form: InlineTaskForm) -> None:
        """Submit com título vazio não deve emitir submitted."""
        form._edit_titulo.setText("")

        sinais: list[dict] = []  # type: ignore[type-arg]
        form.submitted.connect(sinais.append)

        form._on_submit()

        assert len(sinais) == 0

    def test_titulo_so_espacos_nao_emite_submitted(self, form: InlineTaskForm) -> None:
        """Submit com título apenas de espaços não deve emitir submitted."""
        form._edit_titulo.setText("   ")

        sinais: list[dict] = []  # type: ignore[type-arg]
        form.submitted.connect(sinais.append)

        form._on_submit()

        assert len(sinais) == 0

    def test_titulo_vazio_exibe_erro_inline(self, form: InlineTaskForm) -> None:
        """Submit vazio deve exibir label de erro e bordar o título em vermelho."""
        form._edit_titulo.setText("")

        form._on_submit()

        assert not form._label_erro.isHidden()
        assert form._edit_titulo.styleSheet() == _STYLE_TITULO_ERRO

    def test_titulo_maxlength_200_respeitado(self, form: InlineTaskForm) -> None:
        """setMaxLength deve limitar o campo título a 200 caracteres."""
        assert form._edit_titulo.maxLength() == TITULO_MAX_LEN

    def test_sem_data_checkbox_ativo_desabilita_dateedit(
        self, form: InlineTaskForm
    ) -> None:
        """Com 'Sem data' marcado, o DateEdit deve estar desabilitado."""
        form._check_sem_data.setChecked(True)
        QApplication.processEvents()
        assert not form._date_vencimento.isEnabled()

    def test_sem_data_checkbox_desmarcado_habilita_dateedit(
        self, form: InlineTaskForm
    ) -> None:
        """Desmarcar 'Sem data' deve habilitar o DateEdit."""
        form._check_sem_data.setChecked(False)
        QApplication.processEvents()
        assert form._date_vencimento.isEnabled()

    def test_submit_com_data_definida_inclui_data(self, form: InlineTaskForm) -> None:
        """Quando 'Sem data' desmarcado e data definida, submitted inclui data."""
        from datetime import date

        form._edit_titulo.setText("Com Data")
        form._check_sem_data.setChecked(False)
        form._date_vencimento.setDate(QDate(2026, 12, 31))
        QApplication.processEvents()

        sinais: list[dict] = []  # type: ignore[type-arg]
        form.submitted.connect(sinais.append)

        form._on_submit()

        assert len(sinais) == 1
        assert sinais[0]["data_vencimento"] == date(2026, 12, 31)


# ---------------------------------------------------------------------------
# TC-085 — reset() após submissão limpa campos e retorna foco
# ---------------------------------------------------------------------------


class TestReset:
    """TC-085 — reset() limpa campos, restaura prioridade MEDIA e foco."""

    def test_reset_limpa_titulo(self, form: InlineTaskForm) -> None:
        """reset() deve esvaziar o campo título."""
        form._edit_titulo.setText("Algo aqui")
        form.reset()
        QApplication.processEvents()
        assert form._edit_titulo.text() == ""

    def test_reset_restaura_prioridade_media(self, form: InlineTaskForm) -> None:
        """reset() deve restaurar o ComboBox para Prioridade.MEDIA."""
        idx_alta = form._combo_prioridade.findData(Prioridade.ALTA)
        form._combo_prioridade.setCurrentIndex(idx_alta)

        form.reset()
        QApplication.processEvents()

        assert form._combo_prioridade.currentData() == Prioridade.MEDIA

    def test_reset_oculta_label_erro(self, form: InlineTaskForm) -> None:
        """reset() deve ocultar e limpar o label de erro."""
        form.show_error("Erro qualquer")
        form.reset()
        QApplication.processEvents()
        assert form._label_erro.isHidden()
        assert form._label_erro.text() == ""

    def test_reset_remove_estilo_de_erro_do_titulo(self, form: InlineTaskForm) -> None:
        """reset() deve limpar o stylesheet de erro do campo título."""
        form.show_error("Erro")
        form.reset()
        QApplication.processEvents()
        assert form._edit_titulo.styleSheet() == _STYLE_TITULO_NORMAL

    def test_reset_marca_sem_data(self, form: InlineTaskForm) -> None:
        """reset() deve reativar o checkbox 'Sem data de vencimento'."""
        form._check_sem_data.setChecked(False)
        form.reset()
        QApplication.processEvents()
        assert form._check_sem_data.isChecked()

    def test_reset_move_foco_ao_titulo(self, form: InlineTaskForm) -> None:
        """reset() deve chamar setFocus no campo título via QTimer (DT-033).

        Mesmo padrão de spy usado em test_focus_title_chama_set_focus:
        em headless, QTimer.singleShot não entrega foco real sem janela ativa.
        """
        chamadas: list[bool] = []
        original = form._edit_titulo.setFocus

        def spy(*args: Any, **kwargs: Any) -> None:
            chamadas.append(True)
            original(*args, **kwargs)

        form._edit_titulo.setFocus = spy  # type: ignore[method-assign]

        form.reset()
        QApplication.processEvents()

        assert len(chamadas) == 1, "reset() deve chamar setFocus() no campo título"


# ---------------------------------------------------------------------------
# TC-093 — Enter com título vazio exibe erro e não cria card
# ---------------------------------------------------------------------------


class TestEnterTituloVazio:
    """TC-093 — Enter com título vazio exibe erro e não emite submitted."""

    def test_enter_titulo_vazio_nao_emite_submitted(self, form: InlineTaskForm) -> None:
        """returnPressed com campo vazio não deve emitir submitted."""
        form._edit_titulo.setText("")

        sinais: list[dict] = []  # type: ignore[type-arg]
        form.submitted.connect(sinais.append)

        form._edit_titulo.returnPressed.emit()

        assert len(sinais) == 0

    def test_enter_titulo_vazio_exibe_erro(self, form: InlineTaskForm) -> None:
        """returnPressed com campo vazio deve exibir erro inline."""
        form._edit_titulo.setText("")
        form._edit_titulo.returnPressed.emit()

        assert not form._label_erro.isHidden()

    def test_enter_titulo_vazio_form_permanece_aberto(
        self, form: InlineTaskForm
    ) -> None:
        """Após submit vazio, o form deve continuar visível (não fechar)."""
        cancelados: list[None] = []
        form.cancelled.connect(lambda: cancelados.append(None))
        form._edit_titulo.setText("")

        form._edit_titulo.returnPressed.emit()

        # cancelled não emitido = form não solicitou fechamento
        assert len(cancelados) == 0


# ---------------------------------------------------------------------------
# show_error
# ---------------------------------------------------------------------------


class TestShowError:
    """Testa a API pública show_error()."""

    def test_show_error_exibe_mensagem(self, form: InlineTaskForm) -> None:
        """show_error deve exibir o texto passado no label de erro."""
        form.show_error("Falha ao salvar")

        assert not form._label_erro.isHidden()
        assert "Falha ao salvar" in form._label_erro.text()

    def test_show_error_aplica_borda_vermelha(self, form: InlineTaskForm) -> None:
        """show_error deve aplicar o estilo de erro no campo título."""
        form.show_error("Qualquer erro")
        assert form._edit_titulo.styleSheet() == _STYLE_TITULO_ERRO
