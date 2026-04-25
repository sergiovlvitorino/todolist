"""Testes de comportamento inline no KanbanColumnWidget.

Cobre TC-087, TC-088, TC-090:
- TC-087: clicar fora do form não o fecha
- TC-088: set_tasks preserva form aberto e atualiza contador
- TC-090: dois forms simultâneos não interferem
"""

from __future__ import annotations

from typing import Any

import pytest
from PyQt6.QtWidgets import QApplication

from own_board_list.models.task import Task
from own_board_list.ui.kanban.kanban_column_widget import KanbanColumnWidget
from own_board_list.utils.constants import COLUNA_A_FAZER, COLUNA_EM_ANDAMENTO

# ---------------------------------------------------------------------------
# Fixtures locais
# ---------------------------------------------------------------------------


@pytest.fixture
def coluna_a(qtbot: Any) -> KanbanColumnWidget:
    """Coluna 'A Fazer' instanciada, exibida (headless-safe) e registrada.

    show() é necessário para que isVisible() funcione corretamente em
    ambiente headless (XCB) — conforme DT-033 documentado em conftest.py.
    """
    col = KanbanColumnWidget(COLUNA_A_FAZER)
    qtbot.addWidget(col)
    col.show()
    QApplication.processEvents()
    return col


@pytest.fixture
def coluna_b(qtbot: Any) -> KanbanColumnWidget:
    """Coluna 'Em Andamento' instanciada, exibida (headless-safe) e registrada."""
    col = KanbanColumnWidget(COLUNA_EM_ANDAMENTO)
    qtbot.addWidget(col)
    col.show()
    QApplication.processEvents()
    return col


# ---------------------------------------------------------------------------
# TC-087 — Clicar fora do form inline não o fecha
# ---------------------------------------------------------------------------


class TestClicarForaNaoFecha:
    """TC-087 — Clicar em outra coluna não fecha o form da coluna atual."""

    def test_form_permanece_aberto_apos_interacao_em_outra_coluna(
        self, coluna_a: KanbanColumnWidget, coluna_b: KanbanColumnWidget
    ) -> None:
        """Abrir form em A; simular ação em B; form de A deve continuar aberto."""
        coluna_a.open_inline_form()

        assert coluna_a.has_inline_form_open()

        # Simula interação em coluna B (não envia signal de cancel para A)
        coluna_b.open_inline_form()
        QApplication.processEvents()

        # Form de A não deve ter sido fechado
        assert coluna_a.has_inline_form_open()

    def test_conteudo_digitado_em_a_preservado_apos_acao_em_b(
        self, coluna_a: KanbanColumnWidget, coluna_b: KanbanColumnWidget
    ) -> None:
        """Texto digitado em A deve ser preservado quando B recebe interações."""
        coluna_a.open_inline_form()
        coluna_a._inline_form._edit_titulo.setText("rascunho A")

        # Abre form em B
        coluna_b.open_inline_form()
        QApplication.processEvents()

        assert coluna_a._inline_form._edit_titulo.text() == "rascunho A"

    def test_cancelar_form_a_nao_afeta_form_b(
        self, coluna_a: KanbanColumnWidget, coluna_b: KanbanColumnWidget
    ) -> None:
        """Cancelar o form em A não deve fechar o form em B."""
        coluna_a.open_inline_form()
        coluna_b.open_inline_form()

        coluna_a.close_inline_form()

        assert not coluna_a.has_inline_form_open()
        assert coluna_b.has_inline_form_open()

    def test_has_inline_form_open_reflete_estado_correto(
        self, coluna_a: KanbanColumnWidget
    ) -> None:
        """has_inline_form_open() deve retornar False antes e True após abrir."""
        assert not coluna_a.has_inline_form_open()

        coluna_a.open_inline_form()
        assert coluna_a.has_inline_form_open()

        coluna_a.close_inline_form()
        assert not coluna_a.has_inline_form_open()

    def test_botao_adicionar_oculto_quando_form_aberto(
        self, coluna_a: KanbanColumnWidget
    ) -> None:
        """Botão '+ Adicionar card' deve ficar oculto quando form está aberto."""
        coluna_a.open_inline_form()
        assert coluna_a._btn_adicionar_card.isHidden()

    def test_botao_adicionar_visivel_apos_fechar_form(
        self, coluna_a: KanbanColumnWidget
    ) -> None:
        """Botão '+ Adicionar card' deve reaparecer após fechar o form."""
        coluna_a.open_inline_form()
        coluna_a.close_inline_form()
        assert not coluna_a._btn_adicionar_card.isHidden()


# ---------------------------------------------------------------------------
# TC-088 — set_tasks preserva form aberto e atualiza contador
# ---------------------------------------------------------------------------


class TestSetTasksPreservaForm:
    """TC-088 — set_tasks recarrega cards sem tocar no form inline."""

    def test_set_tasks_atualiza_contador(self, coluna_a: KanbanColumnWidget) -> None:
        """Após set_tasks, o contador deve refletir a nova quantidade de tasks."""
        tasks = [Task(titulo=f"T{i}") for i in range(3)]
        coluna_a.set_tasks(tasks)

        assert coluna_a._label_count.text() == "(3)"

    def test_set_tasks_substitui_cards_existentes(
        self, coluna_a: KanbanColumnWidget
    ) -> None:
        """set_tasks deve substituir os cards anteriores pelos novos."""
        coluna_a.add_card(Task(titulo="Antigo 1"))
        coluna_a.add_card(Task(titulo="Antigo 2"))

        novos = [Task(titulo=f"Novo {i}") for i in range(5)]
        coluna_a.set_tasks(novos)

        assert len(coluna_a._cards) == 5

    def test_set_tasks_preserva_form_inline_aberto(
        self, coluna_a: KanbanColumnWidget
    ) -> None:
        """set_tasks não deve fechar o form inline se ele estiver aberto."""
        coluna_a.add_card(Task(titulo="Card 1"))
        coluna_a.add_card(Task(titulo="Card 2"))
        coluna_a.open_inline_form()

        assert coluna_a.has_inline_form_open()

        novas_tasks = [Task(titulo=f"T{i}") for i in range(3)]
        coluna_a.set_tasks(novas_tasks)

        assert coluna_a.has_inline_form_open()

    def test_set_tasks_preserva_rascunho_no_form(
        self, coluna_a: KanbanColumnWidget
    ) -> None:
        """set_tasks não deve limpar o texto digitado no form inline."""
        coluna_a.open_inline_form()
        coluna_a._inline_form._edit_titulo.setText("teste")

        coluna_a.set_tasks([Task(titulo="Novo Card")])

        assert coluna_a._inline_form._edit_titulo.text() == "teste"

    def test_set_tasks_com_lista_vazia_zera_contador(
        self, coluna_a: KanbanColumnWidget
    ) -> None:
        """set_tasks com lista vazia deve resultar em contador (0)."""
        coluna_a.add_card(Task(titulo="Algo"))
        coluna_a.set_tasks([])

        assert coluna_a._label_count.text() == "(0)"
        assert len(coluna_a._cards) == 0


# ---------------------------------------------------------------------------
# TC-090 — Dois forms simultâneos não interferem
# ---------------------------------------------------------------------------


class TestDoisFormsSimultaneos:
    """TC-090 — Dois forms abertos em colunas distintas são independentes."""

    def test_dois_forms_abertos_simultaneamente(
        self, coluna_a: KanbanColumnWidget, coluna_b: KanbanColumnWidget
    ) -> None:
        """Ambas as colunas podem ter form aberto ao mesmo tempo."""
        coluna_a.open_inline_form()
        coluna_b.open_inline_form()

        assert coluna_a.has_inline_form_open()
        assert coluna_b.has_inline_form_open()

    def test_rascunho_a_nao_afeta_rascunho_b(
        self, coluna_a: KanbanColumnWidget, coluna_b: KanbanColumnWidget
    ) -> None:
        """Texto digitado em A e em B são independentes."""
        coluna_a.open_inline_form()
        coluna_b.open_inline_form()

        coluna_a._inline_form._edit_titulo.setText("rascunho A")
        coluna_b._inline_form._edit_titulo.setText("rascunho B")

        assert coluna_a._inline_form._edit_titulo.text() == "rascunho A"
        assert coluna_b._inline_form._edit_titulo.text() == "rascunho B"

    def test_submit_em_a_emite_signal_correto(
        self, coluna_a: KanbanColumnWidget, coluna_b: KanbanColumnWidget
    ) -> None:
        """Submissão em A deve emitir create_card_submitted com nome da coluna A."""
        coluna_a.open_inline_form()
        coluna_b.open_inline_form()
        coluna_b._inline_form._edit_titulo.setText("rascunho B")

        sinais: list[tuple[str, dict]] = []  # type: ignore[type-arg]
        coluna_a.create_card_submitted.connect(lambda col, d: sinais.append((col, d)))
        coluna_b.create_card_submitted.connect(lambda col, d: sinais.append((col, d)))

        coluna_a._inline_form._edit_titulo.setText("Card de A")
        coluna_a._inline_form._on_submit()

        # Apenas A deve ter emitido
        assert len(sinais) == 1
        assert sinais[0][0] == COLUNA_A_FAZER

    def test_rascunho_b_preservado_apos_submit_em_a(
        self, coluna_a: KanbanColumnWidget, coluna_b: KanbanColumnWidget
    ) -> None:
        """Após criar card em A, o rascunho de B deve permanecer intacto."""
        coluna_a.open_inline_form()
        coluna_b.open_inline_form()
        coluna_b._inline_form._edit_titulo.setText("rascunho B")

        # Submete em A
        coluna_a._inline_form._edit_titulo.setText("Card de A")
        coluna_a._inline_form._on_submit()
        QApplication.processEvents()

        assert coluna_b._inline_form._edit_titulo.text() == "rascunho B"

    def test_add_card_requested_emite_nome_da_coluna_correta(
        self, coluna_a: KanbanColumnWidget, coluna_b: KanbanColumnWidget
    ) -> None:
        """add_card_requested deve carregar o nome da coluna que abriu o form."""
        sinais_a: list[str] = []
        sinais_b: list[str] = []

        coluna_a.add_card_requested.connect(sinais_a.append)
        coluna_b.add_card_requested.connect(sinais_b.append)

        coluna_a.open_inline_form()
        coluna_b.open_inline_form()

        assert sinais_a == [COLUNA_A_FAZER]
        assert sinais_b == [COLUNA_EM_ANDAMENTO]
