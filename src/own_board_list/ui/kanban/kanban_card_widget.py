"""Widget de card no quadro Kanban."""

from __future__ import annotations

from datetime import date

from PyQt6.QtCore import QMimeData, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QDrag, QMouseEvent
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from own_board_list.models.task import StatusTarefa, Task
from own_board_list.utils.constants import COR_PRIORIDADE

# Limiar em pixels para iniciar arrasto
_DRAG_THRESHOLD = 10


class KanbanCard(QFrame):
    """Card visual representando uma tarefa no quadro Kanban com suporte a drag."""

    card_clicked = pyqtSignal(str)  # task_id

    def __init__(self, task: Task, parent: QWidget | None = None) -> None:
        """Inicializa o card com os dados da tarefa."""
        super().__init__(parent)
        self._task = task
        self._drag_start_pos: QPoint | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Constrói o layout visual do card."""
        self.setFrameShape(QFrame.Shape.Box)
        self.setStyleSheet("""
            KanbanCard {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 4px;
            }
            KanbanCard:hover {
                border: 1px solid #2196f3;
            }
        """)
        self.setMinimumWidth(180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Título
        label_titulo = QLabel(self._task.titulo)
        label_titulo.setWordWrap(True)
        label_titulo.setStyleSheet("font-weight: bold;")
        layout.addWidget(label_titulo)

        # Prioridade
        cor = COR_PRIORIDADE.get(self._task.prioridade, "#000000")
        label_prioridade = QLabel(str(self._task.prioridade))
        label_prioridade.setStyleSheet(
            f"color: {cor}; font-size: 11px; font-weight: bold;"
        )
        layout.addWidget(label_prioridade)

        # Data de vencimento
        if self._task.data_vencimento is not None:
            texto_data = self._task.data_vencimento.strftime("%d/%m/%Y")
            label_data = QLabel(texto_data)
            vencida = (
                self._task.data_vencimento < date.today()
                and self._task.status != StatusTarefa.CONCLUIDA
            )
            if vencida:
                label_data.setStyleSheet("color: #d32f2f; font-size: 11px;")
            else:
                label_data.setStyleSheet("color: #666666; font-size: 11px;")
            layout.addWidget(label_data)

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        """Registra a posição inicial para avaliação de arrasto."""
        if event is not None:
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag_start_pos = event.pos()
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:
        """Inicia o drag após mover o mouse além do limiar."""
        if event is not None:
            if (
                event.buttons() == Qt.MouseButton.LeftButton
                and self._drag_start_pos is not None
            ):
                delta = event.pos() - self._drag_start_pos
                if abs(delta.x()) > _DRAG_THRESHOLD or abs(delta.y()) > _DRAG_THRESHOLD:
                    self._start_drag()
            super().mouseMoveEvent(event)

    def _start_drag(self) -> None:
        """Inicia o processo de drag com o task_id no QMimeData."""
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self._task.id)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.MoveAction)

    @property
    def task(self) -> Task:
        """Retorna a tarefa associada ao card."""
        return self._task
