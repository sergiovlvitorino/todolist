"""Widget de coluna no quadro Kanban com suporte a drop e criação inline."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from own_board_list.models.task import Task
from own_board_list.ui.kanban.inline_task_form import InlineTaskForm
from own_board_list.ui.kanban.kanban_card_widget import KanbanCard

# Estilo padrão da coluna
_STYLE_NORMAL = """
    KanbanColumnWidget {
        background-color: #f5f5f5;
        border: 2px solid #dddddd;
        border-radius: 8px;
    }
"""

# Estilo ao receber drop (highlight)
_STYLE_DROP_TARGET = """
    KanbanColumnWidget {
        background-color: #e3f2fd;
        border: 2px dashed #2196f3;
        border-radius: 8px;
    }
"""


class KanbanColumnWidget(QFrame):
    """Coluna do quadro Kanban que aceita drops de cards e criação inline."""

    card_dropped = pyqtSignal(str, str, int)  # task_id, column_name, position
    add_card_requested = pyqtSignal(str)  # column_name
    create_card_submitted = pyqtSignal(str, dict)  # column_name, dados

    def __init__(self, column_name: str, parent: QWidget | None = None) -> None:
        """Inicializa a coluna com o nome fornecido."""
        super().__init__(parent)
        self._column_name = column_name
        self._cards: list[KanbanCard] = []
        self._setup_ui()
        self.setAcceptDrops(True)

    def _setup_ui(self) -> None:
        """Constrói o layout da coluna."""
        self.setStyleSheet(_STYLE_NORMAL)
        self.setMinimumWidth(220)
        self.setMaximumWidth(280)
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Cabeçalho
        header_layout = QHBoxLayout()
        self._label_nome = QLabel(self._column_name)
        self._label_nome.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self._label_nome)

        self._label_count = QLabel("(0)")
        self._label_count.setStyleSheet("color: #666666; font-size: 12px;")
        header_layout.addWidget(self._label_count)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Área de scroll para os cards
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll_area.setStyleSheet("QScrollArea { border: none; }")

        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._cards_layout.setSpacing(6)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)

        self._scroll_area.setWidget(self._cards_container)
        layout.addWidget(self._scroll_area)

        # Rodapé fixo com botão "+ Adicionar card" e form inline
        self._btn_adicionar_card = QPushButton("+ Adicionar card")
        self._btn_adicionar_card.setFlat(True)
        self._btn_adicionar_card.setStyleSheet(
            "QPushButton { color: #555; text-align: left; padding: 4px; }"
            "QPushButton:hover { color: #1976d2; }"
        )
        self._btn_adicionar_card.clicked.connect(self.open_inline_form)
        layout.addWidget(self._btn_adicionar_card)

        self._inline_form = InlineTaskForm(self)
        self._inline_form.submitted.connect(self._on_form_submitted)
        self._inline_form.cancelled.connect(self.close_inline_form)
        self._inline_form.hide()
        layout.addWidget(self._inline_form)

    def add_card(self, task: Task) -> None:
        """Adiciona um card à coluna."""
        card = KanbanCard(task, self._cards_container)
        self._cards.append(card)
        self._cards_layout.addWidget(card)
        self.update_count()

    def clear_cards(self) -> None:
        """Remove todos os cards da coluna."""
        for card in self._cards:
            self._cards_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self.update_count()

    def set_column_name(self, name: str) -> None:
        """Atualiza o nome exibido na coluna."""
        self._column_name = name
        self._label_nome.setText(name)

    def update_count(self) -> None:
        """Atualiza o contador de cards na coluna."""
        self._label_count.setText(f"({len(self._cards)})")

    def set_tasks(self, tasks: list[Task]) -> None:
        """Recarrega os cards da coluna sem tocar no rodapé/form inline.

        Limpa os cards existentes e repopula a partir da lista fornecida.
        O formulário inline (se aberto) e o botão "+ Adicionar card" são
        preservados — apenas a área de cards é atualizada.
        """
        self.clear_cards()
        for task in tasks:
            self.add_card(task)

    def open_inline_form(self) -> None:
        """Exibe o formulário inline e oculta o botão "+ Adicionar card"."""
        self._btn_adicionar_card.hide()
        self._inline_form.show()
        self._inline_form.focus_title()
        self.add_card_requested.emit(self._column_name)

    def close_inline_form(self) -> None:
        """Oculta o formulário inline e exibe o botão "+ Adicionar card"."""
        self._inline_form.hide()
        self._btn_adicionar_card.show()

    def has_inline_form_open(self) -> bool:
        """Retorna True se o formulário inline estiver visível."""
        return self._inline_form.isVisible()

    def reset_form(self) -> None:
        """Reseta os campos do formulário inline (uso em criação em rajada)."""
        self._inline_form.reset()

    def show_form_error(self, msg: str) -> None:
        """Exibe uma mensagem de erro no formulário inline."""
        self._inline_form.show_error(msg)

    def _on_form_submitted(self, dados: dict) -> None:  # type: ignore[type-arg]
        """Repropaga o signal com o nome da coluna."""
        self.create_card_submitted.emit(self._column_name, dados)

    def _get_drop_position(self, y: int) -> int:
        """Calcula a posição de inserção baseada na coordenada Y do drop."""
        for i, card in enumerate(self._cards):
            card_center_y = card.y() + card.height() // 2
            if y < card_center_y:
                return i
        return len(self._cards)

    def dragEnterEvent(self, event: QDragEnterEvent | None) -> None:
        """Aceita o drag e aplica o highlight visual."""
        if event is not None:
            mime = event.mimeData()
            if mime is not None and mime.hasText():
                event.acceptProposedAction()
                self.setStyleSheet(_STYLE_DROP_TARGET)

    def dragMoveEvent(self, event: QDragMoveEvent | None) -> None:
        """Mantém o drop aceito durante o movimento."""
        if event is not None:
            mime = event.mimeData()
            if mime is not None and mime.hasText():
                event.acceptProposedAction()

    def dragLeaveEvent(self, event: QDragLeaveEvent | None) -> None:
        """Remove o highlight quando o drag sai da coluna."""
        self.setStyleSheet(_STYLE_NORMAL)
        if event is not None:
            super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent | None) -> None:
        """Processa o drop do card e emite o signal com a nova posição."""
        if event is not None:
            mime = event.mimeData()
            if mime is not None and mime.hasText():
                task_id = mime.text()
                drop_y = event.position().toPoint().y()
                posicao = self._get_drop_position(drop_y)
                self.card_dropped.emit(task_id, self._column_name, posicao)
                event.acceptProposedAction()
            self.setStyleSheet(_STYLE_NORMAL)
