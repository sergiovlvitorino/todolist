"""Widget principal da aba Todo List."""

from __future__ import annotations

from datetime import date

from PyQt6.QtCore import QEvent, QObject, Qt, QTimer
from PyQt6.QtGui import QKeyEvent, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from own_board_list.models.task import Prioridade, StatusTarefa, Task
from own_board_list.services.task_service import TaskService
from own_board_list.ui.dialogs.confirm_dialog import confirm_dialog
from own_board_list.ui.todo.task_form import TaskForm
from own_board_list.ui.todo.task_list_item import TaskListItem


class TodoWidget(QWidget):
    """Aba de visualização e gerenciamento de tarefas no estilo Todo List."""

    def __init__(
        self,
        task_service: TaskService,
        parent: QWidget | None = None,
        debounce_ms: int = 300,
    ) -> None:
        """Inicializa o widget com o serviço de tarefas."""
        super().__init__(parent)
        self._task_service = task_service
        self._debounce_ms = debounce_ms
        self._search_term: str = ""
        self._setup_ui()
        self._connect_signals()
        self._reload_tasks()

    def _setup_ui(self) -> None:
        """Constrói o layout principal do widget."""
        layout = QVBoxLayout(self)

        # Cabeçalho com botão de nova tarefa
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h2>Todo List</h2>"))
        header_layout.addStretch()

        self._btn_nova_tarefa = QPushButton("+ Nova Tarefa")
        self._btn_nova_tarefa.clicked.connect(self._on_nova_tarefa)
        header_layout.addWidget(self._btn_nova_tarefa)
        layout.addLayout(header_layout)

        # Atalho Ctrl+N (contexto restrito ao widget para não conflitar com Ctrl+F)
        shortcut_n = QShortcut(QKeySequence("Ctrl+N"), self)
        shortcut_n.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut_n.activated.connect(self._on_nova_tarefa)

        # Campo de busca com debounce
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Buscar tarefas...")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.textChanged.connect(self._on_search_text_changed)
        self._search_input.installEventFilter(self)
        layout.addWidget(self._search_input)

        # Atalho Ctrl+F para focar o campo de busca
        shortcut_f = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut_f.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut_f.activated.connect(self._focus_search)

        # Área de scroll com as seções
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._scroll_content = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_content)
        self._scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Label de resultado vazio (busca sem resultados)
        self._label_empty_search = QLabel("Nenhuma tarefa encontrada")
        self._label_empty_search.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label_empty_search.setStyleSheet(
            "color: gray; font-style: italic; padding: 20px;"
        )
        self._label_empty_search.setVisible(False)
        self._scroll_layout.addWidget(self._label_empty_search)

        # Grupos por seção
        self._group_hoje = self._create_group("Hoje")
        self._group_proximas = self._create_group("Próximas")
        self._group_sem_data = self._create_group("Sem data")
        self._group_concluidas = self._create_group("Concluídas")

        self._scroll_layout.addWidget(self._group_hoje)
        self._scroll_layout.addWidget(self._group_proximas)
        self._scroll_layout.addWidget(self._group_sem_data)
        self._scroll_layout.addWidget(self._group_concluidas)

        self._scroll_area.setWidget(self._scroll_content)
        layout.addWidget(self._scroll_area)

    def _create_group(self, title: str) -> QGroupBox:
        """Cria um QGroupBox para uma seção de tarefas."""
        group = QGroupBox(title)
        group_layout = QVBoxLayout(group)
        group_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        group_layout.setSpacing(2)
        return group

    def _connect_signals(self) -> None:
        """Conecta os signals do serviço para auto-reload da lista."""
        self._task_service.task_created.connect(lambda _: self._reload_tasks())
        self._task_service.task_updated.connect(lambda _: self._reload_tasks())
        self._task_service.task_deleted.connect(lambda _: self._reload_tasks())
        self._task_service.tasks_reloaded.connect(lambda _: self._reload_tasks())

    def _clear_group(self, group: QGroupBox) -> None:
        """Remove todos os itens de um grupo."""
        layout = group.layout()
        if layout is None:
            return
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

    def _on_search_text_changed(self, text: str) -> None:
        """Agenda a atualização do filtro com debounce."""
        QTimer.singleShot(self._debounce_ms, lambda: self._apply_search(text))

    def _apply_search(self, text: str) -> None:
        """Aplica o termo de busca e recarrega as tarefas."""
        # Ignora disparos de QTimer stale (texto já foi alterado novamente)
        if text != self._search_input.text():
            return
        self._search_term = text.strip()
        self._reload_tasks()

    def _focus_search(self) -> None:
        """Foca o campo de busca e seleciona todo o texto."""
        self._search_input.setFocus()
        self._search_input.selectAll()

    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        """Intercepta Esc no campo de busca para limpar e devolver foco."""
        if watched is self._search_input and isinstance(event, QKeyEvent):
            if event.key() == Qt.Key.Key_Escape:
                self._search_input.clear()
                self._scroll_area.setFocus()
                return True
        return super().eventFilter(watched, event)

    def _reload_tasks(self) -> None:
        """Recarrega as tarefas, aplicando filtro de busca se houver termo."""
        if self._search_term:
            tasks = self._task_service.search_tasks(self._search_term)
        else:
            tasks = self._task_service.get_all_tasks()

        hoje = date.today()

        # Limpa todas as seções
        for group in (
            self._group_hoje,
            self._group_proximas,
            self._group_sem_data,
            self._group_concluidas,
        ):
            self._clear_group(group)

        pendentes_hoje: list[Task] = []
        pendentes_proximas: list[Task] = []
        pendentes_sem_data: list[Task] = []
        concluidas: list[Task] = []

        for task in tasks:
            if task.status == StatusTarefa.CONCLUIDA:
                concluidas.append(task)
            elif task.data_vencimento is None:
                pendentes_sem_data.append(task)
            elif task.data_vencimento <= hoje:
                pendentes_hoje.append(task)
            else:
                pendentes_proximas.append(task)

        # Exibe "Nenhuma tarefa encontrada" quando busca ativa retorna zero resultados
        total = len(tasks)
        has_active_search = bool(self._search_term)
        self._label_empty_search.setVisible(total == 0 and has_active_search)

        self._add_tasks_to_group(self._group_hoje, pendentes_hoje)
        self._add_tasks_to_group(self._group_proximas, pendentes_proximas)
        self._add_tasks_to_group(self._group_sem_data, pendentes_sem_data)
        self._add_tasks_to_group(self._group_concluidas, concluidas)

    def _add_tasks_to_group(self, group: QGroupBox, tasks: list[Task]) -> None:
        """Adiciona widgets de tarefa a um grupo."""
        layout = group.layout()
        if layout is None:
            return

        if not tasks:
            label = QLabel("Nenhuma tarefa")
            label.setStyleSheet("color: gray; font-style: italic;")
            layout.addWidget(label)
            return

        for task in tasks:
            item = TaskListItem(task, self)
            item.status_toggled.connect(self._on_toggle_status)
            item.edit_requested.connect(self._on_edit_task)
            item.delete_requested.connect(self._on_delete_task)
            layout.addWidget(item)

    def _create_task_form(self, task: Task | None = None) -> TaskForm:
        """Fábrica que instancia um ``TaskForm`` para criação ou edição.

        Extraído como método separado para permitir substituição por mock em
        testes — evita dependência de ``form.exec()`` bloqueante em CI headless.
        """
        return TaskForm(task=task, parent=self)

    def _on_nova_tarefa(self) -> None:
        """Abre o formulário para criar uma nova tarefa."""
        form = self._create_task_form()
        form.task_saved.connect(self._on_form_saved)
        form.exec()

    def _on_edit_task(self, task_id: str) -> None:
        """Abre o formulário para editar uma tarefa existente."""
        task_to_edit = self._task_service.get_task_by_id(task_id)
        if task_to_edit is None:
            return

        form = self._create_task_form(task=task_to_edit)
        form.task_saved.connect(self._on_form_saved)
        form.exec()

    def _on_form_saved(self, dados: dict[str, object]) -> None:
        """Cria ou atualiza uma tarefa com os dados do formulário."""
        task_id = dados.get("id")

        if task_id is not None and isinstance(task_id, str):
            # Atualização
            self._task_service.update_task(
                task_id,
                titulo=dados["titulo"],
                descricao=dados.get("descricao", ""),
                prioridade=dados.get("prioridade", Prioridade.MEDIA),
                data_vencimento=dados.get("data_vencimento"),
            )
        else:
            # Criação
            titulo = dados["titulo"]
            if not isinstance(titulo, str):
                raise TypeError(f"titulo deve ser str, recebido: {type(titulo)}")
            descricao = dados.get("descricao", "")
            if not isinstance(descricao, str):
                raise TypeError(f"descricao deve ser str, recebido: {type(descricao)}")
            prioridade = dados.get("prioridade", Prioridade.MEDIA)
            if not isinstance(prioridade, Prioridade):
                raise TypeError(
                    f"prioridade deve ser Prioridade, recebido: {type(prioridade)}"
                )
            data_venc = dados.get("data_vencimento")
            if data_venc is not None and not isinstance(data_venc, date):
                raise TypeError(
                    "data_vencimento deve ser date ou None, "
                    f"recebido: {type(data_venc)}"
                )

            self._task_service.create_task(
                titulo=titulo,
                descricao=descricao,
                prioridade=prioridade,
                data_vencimento=data_venc,
            )

    def _on_toggle_status(self, task_id: str) -> None:
        """Alterna o status de uma tarefa."""
        self._task_service.toggle_status(task_id)

    def _on_delete_task(self, task_id: str) -> None:
        """Exibe confirmação e exclui a tarefa se confirmado."""
        if confirm_dialog(
            self,
            "Excluir Tarefa",
            "Tem certeza que deseja excluir esta tarefa?",
        ):
            self._task_service.delete_task(task_id)
