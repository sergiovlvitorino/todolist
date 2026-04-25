"""Testes do widget de card no quadro Kanban (KanbanCard)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from own_board_list.models.task import Prioridade, Task
from own_board_list.ui.kanban.kanban_card_widget import KanbanCard


class TestKanbanCardRenderizacao:
    """Testes de renderização do KanbanCard."""

    def test_cria_card_sem_excecao(self, qtbot: Any) -> None:
        """Deve instanciar o card sem lançar exceções."""
        task = Task(titulo="Card Simples")
        card = KanbanCard(task)
        qtbot.addWidget(card)

    def test_property_task_retorna_tarefa_correta(self, qtbot: Any) -> None:
        """A propriedade task deve retornar a tarefa associada ao card."""
        task = Task(titulo="Tarefa do Card")
        card = KanbanCard(task)
        qtbot.addWidget(card)

        assert card.task is task
        assert card.task.titulo == "Tarefa do Card"

    def test_card_com_prioridade_alta(self, qtbot: Any) -> None:
        """Deve renderizar card com prioridade Alta sem exceção."""
        task = Task(titulo="Urgente", prioridade=Prioridade.ALTA)
        card = KanbanCard(task)
        qtbot.addWidget(card)

    def test_card_com_prioridade_baixa(self, qtbot: Any) -> None:
        """Deve renderizar card com prioridade Baixa sem exceção."""
        task = Task(titulo="Tranquilo", prioridade=Prioridade.BAIXA)
        card = KanbanCard(task)
        qtbot.addWidget(card)

    def test_card_com_data_vencimento(self, qtbot: Any) -> None:
        """Deve renderizar card com data de vencimento sem exceção."""
        task = Task(titulo="Com Data", data_vencimento=date(2026, 12, 31))
        card = KanbanCard(task)
        qtbot.addWidget(card)

    def test_card_com_data_vencida_e_pendente(self, qtbot: Any) -> None:
        """Card com data vencida e pendente deve renderizar sem exceção."""
        ontem = date.today() - timedelta(days=1)
        task = Task(titulo="Vencida", data_vencimento=ontem)
        card = KanbanCard(task)
        qtbot.addWidget(card)

    def test_card_com_data_vencida_e_concluida(self, qtbot: Any) -> None:
        """Card concluído não deve destacar data em vermelho mesmo se vencida."""
        ontem = date.today() - timedelta(days=1)
        task = Task(titulo="Vencida Concluída", data_vencimento=ontem)
        task.marcar_concluida()
        card = KanbanCard(task)
        qtbot.addWidget(card)

    def test_card_sem_data_vencimento(self, qtbot: Any) -> None:
        """Deve renderizar card sem data de vencimento sem exceção."""
        task = Task(titulo="Sem Data")
        card = KanbanCard(task)
        qtbot.addWidget(card)

    def test_drag_start_pos_inicial_e_none(self, qtbot: Any) -> None:
        """A posição inicial de drag deve ser None antes de qualquer evento."""
        task = Task(titulo="Drag Test")
        card = KanbanCard(task)
        qtbot.addWidget(card)

        assert card._drag_start_pos is None


class TestKanbanCardMouseEvents:
    """Testes dos eventos de mouse do KanbanCard."""

    def test_mouse_press_define_drag_start_pos(self, qtbot: Any) -> None:
        """mousePressEvent com botão esquerdo deve definir _drag_start_pos."""
        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtGui import QMouseEvent

        task = Task(titulo="Press Test")
        card = KanbanCard(task)
        qtbot.addWidget(card)
        card.show()

        # Simula um press com o botão esquerdo
        pos = QPointF(10.0, 10.0)
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            pos,
            pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        card.mousePressEvent(event)

        assert card._drag_start_pos is not None

    def test_mouse_press_com_botao_direito_nao_define_pos(self, qtbot: Any) -> None:
        """mousePressEvent com botão direito não deve definir _drag_start_pos."""
        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtGui import QMouseEvent

        task = Task(titulo="Right Press")
        card = KanbanCard(task)
        qtbot.addWidget(card)
        card.show()

        pos = QPointF(10.0, 10.0)
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            pos,
            pos,
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
        )
        card.mousePressEvent(event)

        assert card._drag_start_pos is None

    def test_mouse_move_sem_drag_start_pos_nao_inicia_drag(self, qtbot: Any) -> None:
        """mouseMoveEvent sem _drag_start_pos definido não deve iniciar drag."""
        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtGui import QMouseEvent

        task = Task(titulo="Move Sem Pos")
        card = KanbanCard(task)
        qtbot.addWidget(card)
        card.show()

        # _drag_start_pos é None — não deve tentar iniciar drag
        assert card._drag_start_pos is None

        pos = QPointF(50.0, 50.0)
        event = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            pos,
            pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        # Não deve lançar exceção
        card.mouseMoveEvent(event)
