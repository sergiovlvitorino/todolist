"""Testes do formulário de criação e edição de tarefas (TaskForm)."""

from __future__ import annotations

from datetime import date
from typing import Any

from own_board_list.models.task import Prioridade, Task
from own_board_list.ui.todo.task_form import TaskForm


def _set_titulo(form: TaskForm, texto: str) -> None:
    """Auxilia definindo o texto do campo título e disparando o sinal interno."""
    form._edit_titulo.setText(texto)
    # _on_titulo_changed é conectado ao textChanged; setText já dispara,
    # mas chamamos explicitamente para garantir.
    form._on_titulo_changed(texto)


class TestTaskFormCriacao:
    """Testes do formulário em modo de criação (task=None)."""

    def test_titulo_janela_nova_tarefa(self, qtbot: Any) -> None:
        """Deve exibir 'Nova Tarefa' no título quando criando."""
        form = TaskForm()
        qtbot.addWidget(form)

        assert form.windowTitle() == "Nova Tarefa"

    def test_botao_salvar_desabilitado_inicialmente(self, qtbot: Any) -> None:
        """O botão Salvar deve estar desabilitado quando o título está vazio."""
        from PyQt6.QtWidgets import QDialogButtonBox

        form = TaskForm()
        qtbot.addWidget(form)

        btn = form._button_box.button(QDialogButtonBox.StandardButton.Save)
        assert btn is not None
        assert btn.isEnabled() is False

    def test_botao_salvar_habilitado_apos_definir_titulo(self, qtbot: Any) -> None:
        """O botão Salvar deve ser habilitado ao definir um título."""
        from PyQt6.QtWidgets import QDialogButtonBox

        form = TaskForm()
        qtbot.addWidget(form)

        _set_titulo(form, "Minha Tarefa")

        btn = form._button_box.button(QDialogButtonBox.StandardButton.Save)
        assert btn is not None
        assert btn.isEnabled() is True

    def test_botao_salvar_desabilitado_com_titulo_somente_espacos(
        self, qtbot: Any
    ) -> None:
        """Título com apenas espaços não deve habilitar o botão Salvar."""
        from PyQt6.QtWidgets import QDialogButtonBox

        form = TaskForm()
        qtbot.addWidget(form)

        _set_titulo(form, "   ")

        btn = form._button_box.button(QDialogButtonBox.StandardButton.Save)
        assert btn is not None
        assert btn.isEnabled() is False

    def test_contador_caracteres_atualiza(self, qtbot: Any) -> None:
        """Deve atualizar o label contador ao definir texto no campo título."""
        form = TaskForm()
        qtbot.addWidget(form)

        _set_titulo(form, "abc")

        assert form._label_char_count.text() == "3/200"

    def test_contador_com_200_caracteres(self, qtbot: Any) -> None:
        """Contador deve refletir o máximo de 200 caracteres."""
        form = TaskForm()
        qtbot.addWidget(form)

        texto_200 = "x" * 200
        _set_titulo(form, texto_200)

        assert form._label_char_count.text() == "200/200"

    def test_date_edit_desabilitado_inicialmente(self, qtbot: Any) -> None:
        """O campo de data deve estar desabilitado quando 'Sem data' está marcado."""
        form = TaskForm()
        qtbot.addWidget(form)

        assert form._check_sem_data.isChecked() is True
        assert form._date_vencimento.isEnabled() is False

    def test_desmarcar_sem_data_habilita_date_edit(self, qtbot: Any) -> None:
        """Desmarcar 'Sem data de vencimento' deve habilitar o QDateEdit."""
        form = TaskForm()
        qtbot.addWidget(form)

        form._check_sem_data.setChecked(False)

        assert form._date_vencimento.isEnabled() is True

    def test_marcar_sem_data_desabilita_date_edit(self, qtbot: Any) -> None:
        """Marcar 'Sem data' deve desabilitar o QDateEdit."""
        form = TaskForm()
        qtbot.addWidget(form)

        form._check_sem_data.setChecked(False)
        form._check_sem_data.setChecked(True)

        assert form._date_vencimento.isEnabled() is False

    def test_prioridade_padrao_e_media(self, qtbot: Any) -> None:
        """A prioridade padrão ao abrir o formulário deve ser MÉDIA."""
        form = TaskForm()
        qtbot.addWidget(form)

        prioridade = form._combo_prioridade.currentData()
        assert prioridade == Prioridade.MEDIA

    def test_signal_task_saved_emitido_ao_salvar(self, qtbot: Any) -> None:
        """Deve emitir o signal task_saved com os dados corretos ao salvar."""
        form = TaskForm()
        qtbot.addWidget(form)

        dados_recebidos: list[dict[str, object]] = []
        form.task_saved.connect(dados_recebidos.append)

        _set_titulo(form, "Nova Tarefa Test")
        form._on_save()

        assert len(dados_recebidos) == 1
        dados = dados_recebidos[0]
        assert dados["titulo"] == "Nova Tarefa Test"
        assert "id" not in dados

    def test_signal_task_saved_sem_data_vencimento(self, qtbot: Any) -> None:
        """Sem data de vencimento marcada, data_vencimento deve ser None."""
        form = TaskForm()
        qtbot.addWidget(form)

        dados_recebidos: list[dict[str, object]] = []
        form.task_saved.connect(dados_recebidos.append)

        _set_titulo(form, "Tarefa Sem Data")
        form._check_sem_data.setChecked(True)
        form._on_save()

        assert dados_recebidos[0]["data_vencimento"] is None

    def test_signal_task_saved_com_data_vencimento(self, qtbot: Any) -> None:
        """Com data de vencimento, deve incluir a data no dicionário emitido."""
        from PyQt6.QtCore import QDate

        form = TaskForm()
        qtbot.addWidget(form)

        dados_recebidos: list[dict[str, object]] = []
        form.task_saved.connect(dados_recebidos.append)

        _set_titulo(form, "Tarefa Com Data")
        form._check_sem_data.setChecked(False)
        form._date_vencimento.setDate(QDate(2026, 12, 31))
        form._on_save()

        assert dados_recebidos[0]["data_vencimento"] == date(2026, 12, 31)

    def test_on_save_nao_emite_com_titulo_vazio(self, qtbot: Any) -> None:
        """Não deve emitir task_saved quando o título está vazio após strip."""
        form = TaskForm()
        qtbot.addWidget(form)

        dados_recebidos: list[dict[str, object]] = []
        form.task_saved.connect(dados_recebidos.append)

        # título vazio — não deve emitir
        form._on_save()

        assert len(dados_recebidos) == 0

    def test_prioridade_alta_incluida_no_sinal(self, qtbot: Any) -> None:
        """Ao selecionar prioridade Alta, o sinal deve refletir isso."""
        form = TaskForm()
        qtbot.addWidget(form)

        dados_recebidos: list[dict[str, object]] = []
        form.task_saved.connect(dados_recebidos.append)

        _set_titulo(form, "Urgente")
        idx = form._combo_prioridade.findData(Prioridade.ALTA)
        form._combo_prioridade.setCurrentIndex(idx)
        form._on_save()

        assert dados_recebidos[0]["prioridade"] == Prioridade.ALTA

    def test_prioridade_baixa_incluida_no_sinal(self, qtbot: Any) -> None:
        """Ao selecionar prioridade Baixa, o sinal deve refletir isso."""
        form = TaskForm()
        qtbot.addWidget(form)

        dados_recebidos: list[dict[str, object]] = []
        form.task_saved.connect(dados_recebidos.append)

        _set_titulo(form, "Baixa Prio")
        idx = form._combo_prioridade.findData(Prioridade.BAIXA)
        form._combo_prioridade.setCurrentIndex(idx)
        form._on_save()

        assert dados_recebidos[0]["prioridade"] == Prioridade.BAIXA

    def test_descricao_incluida_no_sinal(self, qtbot: Any) -> None:
        """A descrição preenchida deve ser incluída no sinal emitido."""
        form = TaskForm()
        qtbot.addWidget(form)

        dados_recebidos: list[dict[str, object]] = []
        form.task_saved.connect(dados_recebidos.append)

        _set_titulo(form, "Com Descrição")
        form._edit_descricao.setPlainText("Detalhes importantes")
        form._on_save()

        assert dados_recebidos[0]["descricao"] == "Detalhes importantes"


class TestTaskFormEdicao:
    """Testes do formulário em modo de edição (task existente)."""

    def test_titulo_janela_editar_tarefa(self, qtbot: Any) -> None:
        """Deve exibir 'Editar Tarefa' no título quando editando."""
        task = Task(titulo="Tarefa Existente")
        form = TaskForm(task=task)
        qtbot.addWidget(form)

        assert form.windowTitle() == "Editar Tarefa"

    def test_campos_populados_com_dados_da_task(self, qtbot: Any) -> None:
        """Deve preencher o formulário com os dados da tarefa existente."""
        task = Task(
            titulo="Tarefa Populada",
            descricao="Descrição da tarefa",
            prioridade=Prioridade.ALTA,
        )
        form = TaskForm(task=task)
        qtbot.addWidget(form)

        assert form._edit_titulo.text() == "Tarefa Populada"
        assert form._edit_descricao.toPlainText() == "Descrição da tarefa"
        assert form._combo_prioridade.currentData() == Prioridade.ALTA

    def test_campo_data_populado_quando_task_tem_data(self, qtbot: Any) -> None:
        """Deve preencher o campo de data quando a tarefa tem data_vencimento."""
        task = Task(titulo="Com Data", data_vencimento=date(2026, 6, 15))
        form = TaskForm(task=task)
        qtbot.addWidget(form)

        assert form._check_sem_data.isChecked() is False
        assert form._date_vencimento.isEnabled() is True
        qdate = form._date_vencimento.date()
        assert qdate.year() == 2026
        assert qdate.month() == 6
        assert qdate.day() == 15

    def test_sem_data_marcado_quando_task_nao_tem_data(self, qtbot: Any) -> None:
        """Deve marcar 'Sem data' quando a tarefa não tem data_vencimento."""
        task = Task(titulo="Sem Data")
        form = TaskForm(task=task)
        qtbot.addWidget(form)

        assert form._check_sem_data.isChecked() is True
        assert form._date_vencimento.isEnabled() is False

    def test_botao_salvar_habilitado_em_modo_edicao(self, qtbot: Any) -> None:
        """O botão Salvar deve estar habilitado ao editar (título já preenchido)."""
        from PyQt6.QtWidgets import QDialogButtonBox

        task = Task(titulo="Tarefa Para Editar")
        form = TaskForm(task=task)
        qtbot.addWidget(form)

        btn = form._button_box.button(QDialogButtonBox.StandardButton.Save)
        assert btn is not None
        assert btn.isEnabled() is True

    def test_signal_inclui_id_ao_editar(self, qtbot: Any) -> None:
        """No modo de edição, o sinal deve incluir o ID da tarefa."""
        task = Task(titulo="Tarefa para Editar")
        form = TaskForm(task=task)
        qtbot.addWidget(form)

        dados_recebidos: list[dict[str, object]] = []
        form.task_saved.connect(dados_recebidos.append)

        form._on_save()

        assert dados_recebidos[0]["id"] == task.id

    def test_edicao_com_titulo_modificado(self, qtbot: Any) -> None:
        """Deve emitir o novo título ao editar uma tarefa."""
        task = Task(titulo="Título Original")
        form = TaskForm(task=task)
        qtbot.addWidget(form)

        dados_recebidos: list[dict[str, object]] = []
        form.task_saved.connect(dados_recebidos.append)

        # Usa setText diretamente para evitar problemas com janela não visível
        form._edit_titulo.setText("Título Modificado")
        form._on_save()

        assert dados_recebidos[0]["titulo"] == "Título Modificado"

    def test_edicao_preserva_id_original(self, qtbot: Any) -> None:
        """O ID da tarefa deve ser preservado mesmo alterando outros campos."""
        task = Task(titulo="Tarefa com ID Específico")
        id_original = task.id
        form = TaskForm(task=task)
        qtbot.addWidget(form)

        dados_recebidos: list[dict[str, object]] = []
        form.task_saved.connect(dados_recebidos.append)

        _set_titulo(form, "Título Novo")
        form._on_save()

        assert dados_recebidos[0]["id"] == id_original
