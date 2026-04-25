"""Widget de formulário inline para criação rápida de card no Kanban."""

from __future__ import annotations

from datetime import date

from PyQt6.QtCore import QDate, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from own_board_list.models.task import Prioridade
from own_board_list.utils.constants import TITULO_MAX_LEN

# Estilo do campo título em erro
_STYLE_TITULO_ERRO = "border: 1px solid #d32f2f;"
_STYLE_TITULO_NORMAL = ""


class InlineTaskForm(QWidget):
    """Formulário enxuto embutido na coluna para criação de card.

    Expõe signals ``submitted`` (com dict de dados) e ``cancelled``.
    Suporta múltiplas instâncias simultâneas — cada coluna tem a sua.

    Atalhos locais ao widget:
    - ``Enter`` no campo título → confirma (equivale a clicar "Adicionar").
    - ``Esc`` em qualquer campo → cancela (equivale a clicar "Cancelar").
    """

    # {"titulo": str, "prioridade": Prioridade, "data_vencimento": date | None}
    submitted = pyqtSignal(dict)
    cancelled = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Inicializa o formulário inline."""
        super().__init__(parent)
        self._setup_ui()

    # ------------------------------------------------------------------
    # Construção do layout
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Constrói o layout do formulário."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Campo título
        self._edit_titulo = QLineEdit()
        self._edit_titulo.setMaxLength(TITULO_MAX_LEN)
        self._edit_titulo.setPlaceholderText("Título do card...")
        self._edit_titulo.returnPressed.connect(self._on_submit)
        layout.addWidget(self._edit_titulo)

        # Label de erro (oculto por padrão)
        self._label_erro = QLabel("")
        self._label_erro.setStyleSheet("color: #d32f2f; font-size: 11px;")
        self._label_erro.setWordWrap(True)
        self._label_erro.hide()
        layout.addWidget(self._label_erro)

        # ComboBox prioridade
        self._combo_prioridade = QComboBox()
        for prioridade in Prioridade:
            self._combo_prioridade.addItem(str(prioridade), prioridade)
        idx_media = self._combo_prioridade.findData(Prioridade.MEDIA)
        if idx_media >= 0:
            self._combo_prioridade.setCurrentIndex(idx_media)
        layout.addWidget(self._combo_prioridade)

        # Checkbox + DateEdit para data de vencimento
        self._check_sem_data = QCheckBox("Sem data de vencimento")
        self._check_sem_data.setChecked(True)
        self._check_sem_data.toggled.connect(self._on_sem_data_toggled)
        layout.addWidget(self._check_sem_data)

        self._date_vencimento = QDateEdit()
        self._date_vencimento.setCalendarPopup(True)
        self._date_vencimento.setDate(QDate.currentDate())
        self._date_vencimento.setEnabled(False)
        layout.addWidget(self._date_vencimento)

        # Botões
        btn_layout = QHBoxLayout()
        self._btn_adicionar = QPushButton("Adicionar")
        self._btn_adicionar.setDefault(False)
        self._btn_adicionar.setAutoDefault(False)
        self._btn_adicionar.clicked.connect(self._on_submit)

        self._btn_cancelar = QPushButton("Cancelar")
        self._btn_cancelar.setDefault(False)
        self._btn_cancelar.setAutoDefault(False)
        self._btn_cancelar.clicked.connect(self._on_cancel)

        btn_layout.addWidget(self._btn_adicionar)
        btn_layout.addWidget(self._btn_cancelar)
        layout.addLayout(btn_layout)

        # Ordem de Tab: título → prioridade → sem_data → data → Adicionar → Cancelar
        self.setTabOrder(self._edit_titulo, self._combo_prioridade)
        self.setTabOrder(self._combo_prioridade, self._check_sem_data)
        self.setTabOrder(self._check_sem_data, self._date_vencimento)
        self.setTabOrder(self._date_vencimento, self._btn_adicionar)
        self.setTabOrder(self._btn_adicionar, self._btn_cancelar)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Limpa todos os campos e devolve o foco ao título."""
        self._edit_titulo.clear()
        self._label_erro.hide()
        self._label_erro.setText("")
        self._edit_titulo.setStyleSheet(_STYLE_TITULO_NORMAL)
        idx_media = self._combo_prioridade.findData(Prioridade.MEDIA)
        if idx_media >= 0:
            self._combo_prioridade.setCurrentIndex(idx_media)
        self._check_sem_data.setChecked(True)
        self._date_vencimento.setDate(QDate.currentDate())
        self._date_vencimento.setEnabled(False)
        self.focus_title()

    def show_error(self, mensagem: str) -> None:
        """Exibe mensagem de erro inline e destaca o campo título."""
        self._edit_titulo.setStyleSheet(_STYLE_TITULO_ERRO)
        self._label_erro.setText(mensagem)
        self._label_erro.show()

    def focus_title(self) -> None:
        """Move o foco para o campo título."""
        QTimer.singleShot(0, self._edit_titulo.setFocus)

    # ------------------------------------------------------------------
    # Slots internos
    # ------------------------------------------------------------------

    def _on_sem_data_toggled(self, checked: bool) -> None:
        """Habilita ou desabilita o DateEdit conforme o checkbox."""
        self._date_vencimento.setEnabled(not checked)

    def _on_submit(self) -> None:
        """Valida e emite o signal submitted, ou mostra erro."""
        titulo = self._edit_titulo.text().strip()
        if not titulo:
            self.show_error("O título é obrigatório.")
            return

        # Limpa estado de erro anterior
        self._edit_titulo.setStyleSheet(_STYLE_TITULO_NORMAL)
        self._label_erro.hide()

        prioridade: Prioridade = self._combo_prioridade.currentData()

        data_vencimento: date | None = None
        if not self._check_sem_data.isChecked():
            qdate = self._date_vencimento.date()
            data_vencimento = date(qdate.year(), qdate.month(), qdate.day())

        dados: dict[str, object] = {
            "titulo": titulo,
            "prioridade": prioridade,
            "data_vencimento": data_vencimento,
        }
        self.submitted.emit(dados)

    def _on_cancel(self) -> None:
        """Emite o signal cancelled."""
        self.cancelled.emit()

    # ------------------------------------------------------------------
    # Tratamento de teclado (atalhos locais)
    # ------------------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        """Captura Esc para cancelar sem propagar para o widget pai."""
        if event is not None and event.key() == Qt.Key.Key_Escape:
            event.accept()
            self._on_cancel()
        else:
            super().keyPressEvent(event)
