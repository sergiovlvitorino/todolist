"""Widget principal do quadro Kanban."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from own_board_list.database.column_repository import ColumnRepository
from own_board_list.models.task import Prioridade
from own_board_list.services.task_service import TaskService
from own_board_list.ui.kanban.kanban_column_widget import KanbanColumnWidget


class KanbanWidget(QWidget):
    """Aba do quadro Kanban com suporte a drag and drop entre colunas."""

    def __init__(
        self,
        task_service: TaskService,
        column_repo: ColumnRepository,
        parent: QWidget | None = None,
    ) -> None:
        """Inicializa o widget com os serviços necessários."""
        super().__init__(parent)
        self._task_service = task_service
        self._column_repo = column_repo
        self._column_widgets: list[KanbanColumnWidget] = []
        self._setup_ui()
        self._connect_signals()
        self._reload_board()

    def _setup_ui(self) -> None:
        """Constrói o layout principal do quadro."""
        layout = QVBoxLayout(self)

        # Título
        header = QLabel("<h2>Quadro Kanban</h2>")
        layout.addWidget(header)

        # Área de scroll horizontal para as colunas
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._board_container = QWidget()
        self._board_layout = QHBoxLayout(self._board_container)
        self._board_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._board_layout.setSpacing(12)
        self._board_layout.setContentsMargins(8, 8, 8, 8)

        self._scroll_area.setWidget(self._board_container)
        layout.addWidget(self._scroll_area)

    def _connect_signals(self) -> None:
        """Conecta os signals do serviço para reload do quadro."""
        self._task_service.task_created.connect(lambda _: self._reload_board())
        self._task_service.task_updated.connect(lambda _: self._reload_board())
        self._task_service.task_deleted.connect(lambda _: self._reload_board())
        self._task_service.tasks_reloaded.connect(lambda _: self._reload_board())

    def _clear_board(self) -> None:
        """Remove todas as colunas e spacers do quadro."""
        for col_widget in self._column_widgets:
            col_widget.deleteLater()
        self._column_widgets.clear()
        # Remove todos os itens do layout (widgets + stretch items)
        while self._board_layout.count() > 0:
            self._board_layout.takeAt(0)

    def _column_names_changed(self, new_names: list[str]) -> bool:
        """Retorna True se a lista de colunas for diferente da atual."""
        current_names = [w.property("column_name") for w in self._column_widgets]
        return current_names != new_names

    def _reload_board(self) -> None:
        """Reconstrói o quadro com as colunas e cards atuais.

        Se a lista de colunas não mudou, realiza reload incremental:
        apenas chama ``set_tasks`` em cada coluna existente, preservando
        o formulário inline aberto e o rascunho digitado.

        Se a lista de colunas mudou (ex.: coluna adicionada/removida em US-11),
        reconstrói todas as colunas do zero.
        """
        columns = self._column_repo.get_all()
        new_names = [col.nome for col in columns]

        if self._column_widgets and not self._column_names_changed(new_names):
            # Reload incremental: só atualiza os cards de cada coluna
            for col_widget, column in zip(self._column_widgets, columns, strict=True):
                tasks = self._task_service.get_tasks_by_column(column.nome)
                col_widget.set_tasks(tasks)
            return

        # Rebuild completo (primeira carga ou lista de colunas mudou)
        self._clear_board()

        for column in columns:
            col_widget = KanbanColumnWidget(column.nome, self._board_container)
            col_widget.setProperty("column_name", column.nome)
            col_widget.card_dropped.connect(self._on_card_dropped)
            col_widget.create_card_submitted.connect(self._on_create_card_submitted)

            tasks = self._task_service.get_tasks_by_column(column.nome)
            for task in tasks:
                col_widget.add_card(task)

            self._board_layout.addWidget(col_widget)
            self._column_widgets.append(col_widget)

        # Espaçador no final
        self._board_layout.addStretch()

    def _on_card_dropped(self, task_id: str, column_name: str, position: int) -> None:
        """Processa o drop de um card em uma nova coluna."""
        self._task_service.move_to_column(task_id, column_name, position)

    def _on_create_card_submitted(self, column_name: str, dados: dict) -> None:  # type: ignore[type-arg]
        """Cria o card na coluna via service; em erro exibe mensagem no form inline."""
        from datetime import date

        col_widget = next(
            (
                w
                for w in self._column_widgets
                if w.property("column_name") == column_name
            ),
            None,
        )
        if col_widget is None:
            return

        titulo: str = str(dados.get("titulo", ""))
        prioridade: Prioridade = dados.get("prioridade", Prioridade.MEDIA)
        data_vencimento: date | None = dados.get("data_vencimento")

        try:
            self._task_service.create_task_in_column(
                titulo=titulo,
                coluna=column_name,
                prioridade=prioridade,
                data_vencimento=data_vencimento,
            )
            # Criação em rajada: reset do form (TASK-042)
            col_widget.reset_form()
        except Exception as exc:
            col_widget.show_form_error(str(exc))
