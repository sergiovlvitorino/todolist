"""Splash de migração de banco de dados para o Own Board List.

Exibe feedback visual durante o processo de migration do schema SQLite,
seguindo a política definida no ADR-005 e os critérios da Feature.3 da spec:

- Indicador de progresso (``QProgressBar`` indeterminado) aparece **somente**
  se a migração ultrapassar ``LIMIAR_PROGRESSO_MIGRACAO_S`` (1,5 s).
- Após migração bem-sucedida com registros em quarentena, exibe o caminho
  do arquivo de quarentena para que o usuário possa inspecioná-lo.
- Em caso de falha, exibe mensagem clara + caminho do backup pré-migração
  para recuperação manual, além de instruções de contato.

Camada: ui (topo da hierarquia de layers). Depende apenas de
``services.migration_service.MigrationReport`` e
``utils.constants.LIMIAR_PROGRESSO_MIGRACAO_S``.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from own_board_list.utils.constants import LIMIAR_PROGRESSO_MIGRACAO_S


class MigrationSplash(QWidget):
    """Widget de splash exibido durante (e após) a migração do schema.

    Ciclo de vida típico::

        splash = MigrationSplash()
        splash.show()

        # Durante a migração (chamadas opcionais via QTimer ou thread):
        splash.show_progress("Aplicando migration v1 → v2…")

        # Após concluir:
        splash.show_quarantine_path(report.quarentena_path)  # se houver
        # — ou —
        splash.show_error(report.erro, report.backup_path)   # se falhou

    O indicador de progresso (``QProgressBar`` indeterminado) **só é exibido**
    após ``show_progress`` ser chamado. O chamador decide quando invocar
    ``show_progress`` — tipicamente após transcorridos ``LIMIAR_PROGRESSO_MIGRACAO_S``
    segundos desde o início da migração.

    Em modo standalone (testes ou pré-integração com ``main.py``), o widget
    pode ser instanciado sem pai e exibido diretamente.
    """

    #: Título exibido na barra de título e no cabeçalho do splash.
    _TITULO = "Own Board List — Atualização de dados"

    def __init__(self, parent: QWidget | None = None) -> None:
        """Inicializa o splash com layout mínimo (sem indicador de progresso).

        O indicador de progresso e os painéis de resultado são criados agora
        mas permanecem **ocultos** até que o método correspondente seja chamado.

        Args:
            parent: Widget pai opcional; ``None`` para uso standalone.
        """
        super().__init__(parent)

        self.setWindowTitle(self._TITULO)
        self.setMinimumWidth(480)
        # Janela sem decoração de sistema operacional para aspecto de splash.
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            "MigrationSplash { background-color: #ffffff; border: 1px solid #cccccc; }"
        )

        self._build_layout()

    # ------------------------------------------------------------------
    # Layout interno
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        """Constrói todos os widgets do layout, a maioria inicialmente oculta."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        # Cabeçalho sempre visível.
        self._lbl_titulo = QLabel(self._TITULO, self)
        self._lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_titulo.setStyleSheet(
            "font-size: 14pt; font-weight: bold; color: #333333;"
        )
        layout.addWidget(self._lbl_titulo)

        # Mensagem de status (visível ao chamar show_progress).
        self._lbl_status = QLabel("", self)
        self._lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_status.setWordWrap(True)
        self._lbl_status.setStyleSheet("color: #555555; font-size: 10pt;")
        self._lbl_status.setVisible(False)
        layout.addWidget(self._lbl_status)

        # Barra de progresso indeterminada (visível ao chamar show_progress).
        self._progress_bar = QProgressBar(self)
        self._progress_bar.setRange(0, 0)  # indeterminado
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        # Painel de quarentena (visível ao chamar show_quarantine_path).
        self._lbl_quarentena_titulo = QLabel(
            "Registros saneados durante a atualização:", self
        )
        self._lbl_quarentena_titulo.setStyleSheet(
            "font-weight: bold; color: #e65100;"  # laranja aviso
        )
        self._lbl_quarentena_titulo.setVisible(False)
        layout.addWidget(self._lbl_quarentena_titulo)

        self._lbl_quarentena_caminho = QLabel("", self)
        self._lbl_quarentena_caminho.setWordWrap(True)
        self._lbl_quarentena_caminho.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._lbl_quarentena_caminho.setStyleSheet(
            "font-family: monospace; font-size: 9pt; color: #333333;"
        )
        self._lbl_quarentena_caminho.setVisible(False)
        layout.addWidget(self._lbl_quarentena_caminho)

        # Painel de erro (visível ao chamar show_error).
        self._lbl_erro_titulo = QLabel("Falha na atualização de dados", self)
        self._lbl_erro_titulo.setStyleSheet(
            "font-weight: bold; font-size: 11pt; color: #c62828;"  # vermelho erro
        )
        self._lbl_erro_titulo.setVisible(False)
        layout.addWidget(self._lbl_erro_titulo)

        self._lbl_erro_mensagem = QLabel("", self)
        self._lbl_erro_mensagem.setWordWrap(True)
        self._lbl_erro_mensagem.setStyleSheet("color: #444444; font-size: 10pt;")
        self._lbl_erro_mensagem.setVisible(False)
        layout.addWidget(self._lbl_erro_mensagem)

        self._lbl_backup_titulo = QLabel("Cópia de segurança disponível em:", self)
        self._lbl_backup_titulo.setStyleSheet("font-weight: bold; color: #555555;")
        self._lbl_backup_titulo.setVisible(False)
        layout.addWidget(self._lbl_backup_titulo)

        self._lbl_backup_caminho = QLabel("", self)
        self._lbl_backup_caminho.setWordWrap(True)
        self._lbl_backup_caminho.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._lbl_backup_caminho.setStyleSheet(
            "font-family: monospace; font-size: 9pt; color: #333333;"
        )
        self._lbl_backup_caminho.setVisible(False)
        layout.addWidget(self._lbl_backup_caminho)

        self._lbl_instrucoes = QLabel(
            "Para recuperar seus dados, substitua o arquivo do banco pela cópia acima "
            "e reinstale a versão anterior da aplicação. Em caso de dúvida, entre em "
            "contato com o suporte.",
            self,
        )
        self._lbl_instrucoes.setWordWrap(True)
        self._lbl_instrucoes.setStyleSheet("color: #666666; font-size: 9pt;")
        self._lbl_instrucoes.setVisible(False)
        layout.addWidget(self._lbl_instrucoes)

        # Botão de fechar (só aparece em modo erro — para modo sucesso o
        # chamador controla o fechamento via QTimer ou lógica de negócio).
        self._btn_fechar = QPushButton("Fechar", self)
        self._btn_fechar.setVisible(False)
        self._btn_fechar.clicked.connect(self.close)
        layout.addWidget(self._btn_fechar, alignment=Qt.AlignmentFlag.AlignRight)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def show_progress(self, mensagem: str) -> None:
        """Exibe o indicador de progresso (barra indeterminada) e a mensagem.

        Deve ser chamado **somente** quando a duração da migração ultrapassar
        ``LIMIAR_PROGRESSO_MIGRACAO_S``. Abaixo desse limiar o splash deve
        permanecer silencioso (sem indicador) conforme Feature.3 da spec.

        Args:
            mensagem: Texto descritivo exibido abaixo do título, por exemplo
                ``"Aplicando migration v1 → v2…"``.
        """
        self._lbl_status.setText(mensagem)
        self._lbl_status.setVisible(True)
        self._progress_bar.setVisible(True)
        self.adjustSize()

    def show_quarantine_path(self, caminho: Path) -> None:
        """Exibe o caminho do arquivo de quarentena após migração bem-sucedida.

        Oculta a barra de progresso (migração concluída) e apresenta o aviso
        de registros saneados com o caminho do arquivo de quarentena.

        Args:
            caminho: Caminho absoluto do arquivo de quarentena diário
                (``~/.own-board-list/quarantine_YYYYMMDD.json``).
        """
        # Migração concluiu — ocultar barra de progresso.
        self._progress_bar.setVisible(False)
        self._lbl_status.setVisible(False)

        self._lbl_quarentena_titulo.setVisible(True)
        self._lbl_quarentena_caminho.setText(str(caminho))
        self._lbl_quarentena_caminho.setVisible(True)
        self.adjustSize()

    def show_error(self, mensagem: str, backup_path: Path | None) -> None:
        """Exibe o painel de erro com caminho do backup para recuperação manual.

        Oculta a barra de progresso, exibe a mensagem de falha e, quando
        disponível, o caminho da cópia de segurança pré-migração para que o
        usuário possa restaurar manualmente.

        Args:
            mensagem: Descrição do erro ocorrido.
            backup_path: Caminho do backup criado antes da migration, ou
                ``None`` se nenhum backup foi criado (ex.: falha antes do
                passo de backup).
        """
        # Ocultar indicador de progresso.
        self._progress_bar.setVisible(False)
        self._lbl_status.setVisible(False)

        # Exibir painel de erro.
        self._lbl_erro_titulo.setVisible(True)
        self._lbl_erro_mensagem.setText(mensagem)
        self._lbl_erro_mensagem.setVisible(True)

        if backup_path is not None:
            self._lbl_backup_titulo.setVisible(True)
            self._lbl_backup_caminho.setText(str(backup_path))
            self._lbl_backup_caminho.setVisible(True)

        self._lbl_instrucoes.setVisible(True)
        self._btn_fechar.setVisible(True)
        self.adjustSize()

    # ------------------------------------------------------------------
    # Método utilitário para integração com main.py (TASK-059)
    # ------------------------------------------------------------------

    def fechar_apos(self, ms: int) -> None:
        """Agenda o fechamento automático do splash após ``ms`` milissegundos.

        Usado no fluxo de sucesso silencioso: o splash é criado, a migração
        ocorre sem ultrapassar o limiar e o splash fecha sozinho antes de a
        janela principal aparecer.

        Args:
            ms: Tempo em milissegundos antes do fechamento automático.
        """
        QTimer.singleShot(ms, self.close)

    # ------------------------------------------------------------------
    # Propriedade de acesso (facilita testes)
    # ------------------------------------------------------------------

    @property
    def limiar_progresso_s(self) -> float:
        """Retorna o limiar em segundos a partir do qual o progresso é exibido.

        Exposto como propriedade para que os testes possam verificar o valor
        sem depender da constante diretamente.
        """
        return LIMIAR_PROGRESSO_MIGRACAO_S

    @property
    def progresso_visivel(self) -> bool:
        """Indica se o indicador de progresso está atualmente visível."""
        return self._progress_bar.isVisible()

    @property
    def quarentena_visivel(self) -> bool:
        """Indica se o painel de quarentena está atualmente visível."""
        return self._lbl_quarentena_titulo.isVisible()

    @property
    def erro_visivel(self) -> bool:
        """Indica se o painel de erro está atualmente visível."""
        return self._lbl_erro_titulo.isVisible()

    @property
    def caminho_quarentena_exibido(self) -> str:
        """Retorna o texto do caminho de quarentena exibido (pode ser vazio)."""
        return self._lbl_quarentena_caminho.text()

    @property
    def caminho_backup_exibido(self) -> str:
        """Retorna o texto do caminho de backup exibido (pode ser vazio)."""
        return self._lbl_backup_caminho.text()
