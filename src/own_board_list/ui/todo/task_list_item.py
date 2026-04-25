"""Widget de item de tarefa na lista Todo."""

from __future__ import annotations

from datetime import date

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from own_board_list.models.task import StatusTarefa, Task
from own_board_list.utils.constants import COR_PRIORIDADE


class TaskListItem(QWidget):
    """Exibe uma tarefa na lista Todo com controles de ação."""

    status_toggled = pyqtSignal(str)  # task_id
    edit_requested = pyqtSignal(str)  # task_id
    delete_requested = pyqtSignal(str)  # task_id

    def __init__(self, task: Task, parent: QWidget | None = None) -> None:
        """Inicializa o item com os dados da tarefa."""
        super().__init__(parent)
        self._task = task
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Constrói o layout visual do item."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        # Checkbox de conclusão
        self._checkbox = QCheckBox()
        self._checkbox.setChecked(self._task.status == StatusTarefa.CONCLUIDA)
        self._checkbox.toggled.connect(self._on_status_toggled)
        layout.addWidget(self._checkbox)

        # Título (riscado se concluída)
        self._label_titulo = QLabel(self._task.titulo)
        font = QFont()
        if self._task.status == StatusTarefa.CONCLUIDA:
            font.setStrikeOut(True)
        self._label_titulo.setFont(font)
        self._label_titulo.setMinimumWidth(200)
        layout.addWidget(self._label_titulo, stretch=1)

        # Prioridade colorida
        cor = COR_PRIORIDADE.get(self._task.prioridade, "#000000")
        label_prioridade = QLabel(str(self._task.prioridade))
        label_prioridade.setStyleSheet(f"color: {cor}; font-weight: bold;")
        label_prioridade.setFixedWidth(60)
        layout.addWidget(label_prioridade)

        # Data de vencimento
        if self._task.data_vencimento is not None:
            texto_data = self._task.data_vencimento.strftime("%d/%m/%Y")
            label_data = QLabel(texto_data)
            vencida = self._task.data_vencimento < date.today()
            if vencida and self._task.status != StatusTarefa.CONCLUIDA:
                label_data.setStyleSheet("color: #d32f2f; font-weight: bold;")
            layout.addWidget(label_data)
        else:
            layout.addWidget(QLabel(""))

        # Botão editar
        btn_editar = QPushButton("Editar")
        btn_editar.setFixedWidth(60)
        btn_editar.clicked.connect(self._on_edit_clicked)
        layout.addWidget(btn_editar)

        # Botão excluir
        btn_excluir = QPushButton("Excluir")
        btn_excluir.setFixedWidth(60)
        btn_excluir.setStyleSheet("color: #d32f2f;")
        btn_excluir.clicked.connect(self._on_delete_clicked)
        layout.addWidget(btn_excluir)

    def _on_status_toggled(self) -> None:
        """Emite o signal quando o checkbox é alterado."""
        self.status_toggled.emit(self._task.id)

    def _on_edit_clicked(self) -> None:
        """Emite o signal de solicitação de edição."""
        self.edit_requested.emit(self._task.id)

    def _on_delete_clicked(self) -> None:
        """Emite o signal de solicitação de exclusão."""
        self.delete_requested.emit(self._task.id)
