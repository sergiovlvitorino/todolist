"""Formulário de criação e edição de tarefas."""

from __future__ import annotations

from datetime import date

from PyQt6.QtCore import QDate, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from own_board_list.models.task import Prioridade, Task
from own_board_list.utils.constants import TITULO_MAX_LEN


class TaskForm(QDialog):
    """Diálogo para criar ou editar uma tarefa."""

    task_saved = pyqtSignal(dict)  # dados do formulário

    def __init__(
        self,
        task: Task | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Inicializa o formulário.

        Args:
            task: Task existente para edição, ou None para criação.
            parent: Widget pai.
        """
        super().__init__(parent)
        self._task = task
        self._is_edit = task is not None
        self.setWindowTitle("Editar Tarefa" if self._is_edit else "Nova Tarefa")
        self.setMinimumWidth(400)
        self._setup_ui()
        if self._task is not None:
            self._populate_fields(self._task)

    def _setup_ui(self) -> None:
        """Constrói o layout do formulário."""
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Campo título com limite de TITULO_MAX_LEN caracteres
        self._edit_titulo = QLineEdit()
        self._edit_titulo.setMaxLength(TITULO_MAX_LEN)
        self._edit_titulo.setPlaceholderText("Digite o título da tarefa...")
        self._edit_titulo.textChanged.connect(self._on_titulo_changed)
        form_layout.addRow("Título *", self._edit_titulo)

        # Contador de caracteres
        self._label_char_count = QLabel(f"0/{TITULO_MAX_LEN}")
        form_layout.addRow("", self._label_char_count)

        # Campo descrição
        self._edit_descricao = QTextEdit()
        self._edit_descricao.setMaximumHeight(100)
        self._edit_descricao.setPlaceholderText("Descrição opcional...")
        form_layout.addRow("Descrição", self._edit_descricao)

        # ComboBox prioridade
        self._combo_prioridade = QComboBox()
        for prioridade in Prioridade:
            self._combo_prioridade.addItem(str(prioridade), prioridade)
        # Define Média como padrão
        idx = self._combo_prioridade.findData(Prioridade.MEDIA)
        if idx >= 0:
            self._combo_prioridade.setCurrentIndex(idx)
        form_layout.addRow("Prioridade", self._combo_prioridade)

        # Checkbox "Sem data de vencimento" + DateEdit
        self._check_sem_data = QCheckBox("Sem data de vencimento")
        self._check_sem_data.setChecked(True)
        self._check_sem_data.toggled.connect(self._on_sem_data_toggled)
        form_layout.addRow("", self._check_sem_data)

        self._date_vencimento = QDateEdit()
        self._date_vencimento.setCalendarPopup(True)
        self._date_vencimento.setDate(QDate.currentDate())
        self._date_vencimento.setEnabled(False)
        form_layout.addRow("Data de vencimento", self._date_vencimento)

        layout.addLayout(form_layout)

        # Botões Salvar e Cancelar
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        save_btn = self._button_box.button(QDialogButtonBox.StandardButton.Save)
        cancel_btn = self._button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if save_btn is not None:
            save_btn.setText("Salvar")
            save_btn.setEnabled(False)
        if cancel_btn is not None:
            cancel_btn.setText("Cancelar")
        self._button_box.accepted.connect(self._on_save)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)

    def _populate_fields(self, task: Task) -> None:
        """Preenche os campos com os dados de uma tarefa existente."""
        self._edit_titulo.setText(task.titulo)
        self._edit_descricao.setPlainText(task.descricao)

        idx = self._combo_prioridade.findData(task.prioridade)
        if idx >= 0:
            self._combo_prioridade.setCurrentIndex(idx)

        if task.data_vencimento is not None:
            self._check_sem_data.setChecked(False)
            self._date_vencimento.setEnabled(True)
            qdate = QDate(
                task.data_vencimento.year,
                task.data_vencimento.month,
                task.data_vencimento.day,
            )
            self._date_vencimento.setDate(qdate)
        else:
            self._check_sem_data.setChecked(True)
            self._date_vencimento.setEnabled(False)

    def _on_titulo_changed(self, text: str) -> None:
        """Atualiza o contador de caracteres e habilita/desabilita o botão salvar."""
        count = len(text)
        self._label_char_count.setText(f"{count}/{TITULO_MAX_LEN}")
        salvar_btn = self._button_box.button(QDialogButtonBox.StandardButton.Save)
        if salvar_btn is not None:
            salvar_btn.setEnabled(bool(text.strip()))

    def _on_sem_data_toggled(self, checked: bool) -> None:
        """Habilita ou desabilita o DateEdit conforme o checkbox."""
        self._date_vencimento.setEnabled(not checked)

    def _on_save(self) -> None:
        """Coleta os dados do formulário e emite o signal task_saved."""
        titulo = self._edit_titulo.text().strip()
        if not titulo:
            return

        prioridade = self._combo_prioridade.currentData()

        data_vencimento: date | None = None
        if not self._check_sem_data.isChecked():
            qdate = self._date_vencimento.date()
            data_vencimento = date(qdate.year(), qdate.month(), qdate.day())

        dados: dict[str, object] = {
            "titulo": titulo,
            "descricao": self._edit_descricao.toPlainText(),
            "prioridade": prioridade,
            "data_vencimento": data_vencimento,
        }

        if self._task is not None:
            dados["id"] = self._task.id

        self.task_saved.emit(dados)
        self.accept()
