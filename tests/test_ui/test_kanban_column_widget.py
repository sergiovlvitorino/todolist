"""Testes do widget de coluna no quadro Kanban (KanbanColumnWidget)."""

from __future__ import annotations

from typing import Any

from own_board_list.models.task import Task
from own_board_list.ui.kanban.kanban_column_widget import (
    _STYLE_DROP_TARGET,
    _STYLE_NORMAL,
    KanbanColumnWidget,
)


class TestKanbanColumnWidgetRenderizacao:
    """Testes de renderização e estado inicial da coluna."""

    def test_cria_coluna_sem_excecao(self, qtbot: Any) -> None:
        """Deve instanciar a coluna sem lançar exceções."""
        col = KanbanColumnWidget("A Fazer")
        qtbot.addWidget(col)

    def test_nome_da_coluna_exibido_no_header(self, qtbot: Any) -> None:
        """O label de nome deve exibir o nome passado ao construtor."""
        col = KanbanColumnWidget("Em Andamento")
        qtbot.addWidget(col)

        assert col._label_nome.text() == "Em Andamento"

    def test_contador_inicial_zero(self, qtbot: Any) -> None:
        """O contador de cards deve ser (0) ao inicializar."""
        col = KanbanColumnWidget("A Fazer")
        qtbot.addWidget(col)

        assert col._label_count.text() == "(0)"

    def test_aceita_drops(self, qtbot: Any) -> None:
        """A coluna deve estar configurada para aceitar drops."""
        col = KanbanColumnWidget("A Fazer")
        qtbot.addWidget(col)

        assert col.acceptDrops() is True


class TestKanbanColumnWidgetCards:
    """Testes de adição e remoção de cards."""

    def test_add_card_aumenta_contador(self, qtbot: Any) -> None:
        """Adicionar um card deve incrementar o contador."""
        col = KanbanColumnWidget("A Fazer")
        qtbot.addWidget(col)

        task = Task(titulo="Tarefa 1")
        col.add_card(task)

        assert col._label_count.text() == "(1)"

    def test_add_multiplos_cards(self, qtbot: Any) -> None:
        """Adicionar vários cards deve refletir no contador."""
        col = KanbanColumnWidget("A Fazer")
        qtbot.addWidget(col)

        for i in range(3):
            col.add_card(Task(titulo=f"Tarefa {i}"))

        assert col._label_count.text() == "(3)"
        assert len(col._cards) == 3

    def test_clear_cards_remove_todos(self, qtbot: Any) -> None:
        """clear_cards deve remover todos os cards e zerar o contador."""
        col = KanbanColumnWidget("A Fazer")
        qtbot.addWidget(col)

        col.add_card(Task(titulo="Tarefa 1"))
        col.add_card(Task(titulo="Tarefa 2"))
        col.clear_cards()

        assert col._label_count.text() == "(0)"
        assert len(col._cards) == 0

    def test_update_count_reflete_estado_atual(self, qtbot: Any) -> None:
        """update_count deve sincronizar o label com o tamanho de _cards."""
        col = KanbanColumnWidget("Concluído")
        qtbot.addWidget(col)

        col._cards.append(None)  # type: ignore[arg-type]
        col._cards.append(None)  # type: ignore[arg-type]
        col.update_count()

        assert col._label_count.text() == "(2)"

    def test_set_column_name_atualiza_label(self, qtbot: Any) -> None:
        """set_column_name deve atualizar o nome exibido no header."""
        col = KanbanColumnWidget("Nome Antigo")
        qtbot.addWidget(col)

        col.set_column_name("Nome Novo")

        assert col._column_name == "Nome Novo"
        assert col._label_nome.text() == "Nome Novo"


class TestKanbanColumnWidgetDropPosition:
    """Testes do cálculo de posição de drop."""

    def test_drop_position_sem_cards_retorna_zero(self, qtbot: Any) -> None:
        """Com coluna vazia, qualquer coordenada Y deve retornar posição 0."""
        col = KanbanColumnWidget("A Fazer")
        qtbot.addWidget(col)

        pos = col._get_drop_position(100)
        assert pos == 0

    def test_drop_position_apos_todos_cards(self, qtbot: Any) -> None:
        """Drop abaixo de todos os cards deve retornar posição igual ao total."""
        col = KanbanColumnWidget("A Fazer")
        qtbot.addWidget(col)
        col.show()

        col.add_card(Task(titulo="Tarefa 1"))
        col.add_card(Task(titulo="Tarefa 2"))

        # Y muito grande (abaixo de tudo)
        pos = col._get_drop_position(99999)
        assert pos == len(col._cards)


class TestKanbanColumnWidgetDragEvents:
    """Testes dos eventos de drag and drop na coluna."""

    def test_drag_enter_event_com_none_nao_lanca_excecao(self, qtbot: Any) -> None:
        """dragEnterEvent com None não deve lançar exceção."""
        col = KanbanColumnWidget("A Fazer")
        qtbot.addWidget(col)

        col.dragEnterEvent(None)

    def test_drag_move_event_com_none_nao_lanca_excecao(self, qtbot: Any) -> None:
        """dragMoveEvent com None não deve lançar exceção."""
        col = KanbanColumnWidget("A Fazer")
        qtbot.addWidget(col)

        col.dragMoveEvent(None)

    def test_drag_leave_event_restaura_estilo_normal(self, qtbot: Any) -> None:
        """dragLeaveEvent deve restaurar o estilo normal da coluna."""
        from PyQt6.QtGui import QDragLeaveEvent

        col = KanbanColumnWidget("A Fazer")
        qtbot.addWidget(col)
        col.setStyleSheet(_STYLE_DROP_TARGET)

        event = QDragLeaveEvent()
        col.dragLeaveEvent(event)

        # Após o leave, o estilo volta ao normal
        assert col.styleSheet() == _STYLE_NORMAL

    def test_drop_event_com_none_nao_lanca_excecao(self, qtbot: Any) -> None:
        """dropEvent com None não deve lançar exceção."""
        col = KanbanColumnWidget("A Fazer")
        qtbot.addWidget(col)

        col.dropEvent(None)

    def test_drag_enter_com_mime_sem_texto_nao_aplica_highlight(
        self, qtbot: Any
    ) -> None:
        """dragEnterEvent com mime sem texto não deve aplicar o highlight."""
        from PyQt6.QtCore import QMimeData, QPoint, Qt
        from PyQt6.QtGui import QDragEnterEvent

        col = KanbanColumnWidget("A Fazer")
        qtbot.addWidget(col)
        col.show()

        mime = QMimeData()
        # Não define texto no mime data
        event = QDragEnterEvent(
            QPoint(0, 0),
            Qt.DropAction.MoveAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        col.dragEnterEvent(event)

        # O estilo não deve ter mudado para drop target
        assert col.styleSheet() != _STYLE_DROP_TARGET

    def test_drop_event_emite_signal_card_dropped(self, qtbot: Any) -> None:
        """dropEvent com texto no mime deve emitir o signal card_dropped."""
        from PyQt6.QtCore import QMimeData, Qt
        from PyQt6.QtGui import QDropEvent

        col = KanbanColumnWidget("Em Andamento")
        qtbot.addWidget(col)
        col.show()

        sinais_emitidos: list[tuple[str, str, int]] = []
        col.card_dropped.connect(
            lambda tid, col_name, pos: sinais_emitidos.append((tid, col_name, pos))
        )

        mime = QMimeData()
        mime.setText("task-id-xyz")

        event = QDropEvent(
            col.rect().center().toPointF(),
            Qt.DropAction.MoveAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        col.dropEvent(event)

        assert len(sinais_emitidos) == 1
        task_id, col_name, _ = sinais_emitidos[0]
        assert task_id == "task-id-xyz"
        assert col_name == "Em Andamento"
