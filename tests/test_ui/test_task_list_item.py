"""Testes do widget de item de tarefa na lista Todo (TaskListItem)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from own_board_list.models.task import Prioridade, Task
from own_board_list.ui.todo.task_list_item import TaskListItem


class TestTaskListItemRenderizacao:
    """Testes de renderização do widget TaskListItem."""

    def test_cria_widget_sem_excecao(self, qtbot: Any) -> None:
        """Deve instanciar o widget sem lançar exceções."""
        task = Task(titulo="Tarefa Simples")
        widget = TaskListItem(task)
        qtbot.addWidget(widget)

    def test_label_titulo_exibe_nome_correto(self, qtbot: Any) -> None:
        """O label de título deve exibir o título da tarefa."""
        task = Task(titulo="Minha Tarefa Especial")
        widget = TaskListItem(task)
        qtbot.addWidget(widget)

        assert widget._label_titulo.text() == "Minha Tarefa Especial"

    def test_checkbox_desmarcado_para_tarefa_pendente(self, qtbot: Any) -> None:
        """O checkbox deve estar desmarcado para tarefa PENDENTE."""
        task = Task(titulo="Pendente")
        widget = TaskListItem(task)
        qtbot.addWidget(widget)

        assert widget._checkbox.isChecked() is False

    def test_checkbox_marcado_para_tarefa_concluida(self, qtbot: Any) -> None:
        """O checkbox deve estar marcado para tarefa CONCLUIDA."""
        task = Task(titulo="Concluída")
        task.marcar_concluida()
        widget = TaskListItem(task)
        qtbot.addWidget(widget)

        assert widget._checkbox.isChecked() is True

    def test_titulo_riscado_para_tarefa_concluida(self, qtbot: Any) -> None:
        """O título deve ter strikeout quando a tarefa está concluída."""
        task = Task(titulo="Riscada")
        task.marcar_concluida()
        widget = TaskListItem(task)
        qtbot.addWidget(widget)

        assert widget._label_titulo.font().strikeOut() is True

    def test_titulo_nao_riscado_para_tarefa_pendente(self, qtbot: Any) -> None:
        """O título não deve ter strikeout quando a tarefa está pendente."""
        task = Task(titulo="Não Riscada")
        widget = TaskListItem(task)
        qtbot.addWidget(widget)

        assert widget._label_titulo.font().strikeOut() is False

    def test_data_vencimento_exibida_quando_presente(self, qtbot: Any) -> None:
        """Deve exibir a data de vencimento formatada quando existe."""
        task = Task(titulo="Com Data", data_vencimento=date(2026, 12, 31))
        widget = TaskListItem(task)
        qtbot.addWidget(widget)

        # Verifica que um dos labels contém a data formatada
        labels_texts = [
            widget.layout().itemAt(i).widget().text()  # type: ignore[union-attr]
            for i in range(widget.layout().count())  # type: ignore[union-attr]
            if widget.layout().itemAt(i) is not None  # type: ignore[union-attr]
            and widget.layout().itemAt(i).widget() is not None  # type: ignore[union-attr]
        ]
        assert "31/12/2026" in labels_texts

    def test_prioridade_alta_renderiza(self, qtbot: Any) -> None:
        """Deve renderizar sem exceção para prioridade Alta."""
        task = Task(titulo="Alta", prioridade=Prioridade.ALTA)
        widget = TaskListItem(task)
        qtbot.addWidget(widget)

    def test_prioridade_baixa_renderiza(self, qtbot: Any) -> None:
        """Deve renderizar sem exceção para prioridade Baixa."""
        task = Task(titulo="Baixa", prioridade=Prioridade.BAIXA)
        widget = TaskListItem(task)
        qtbot.addWidget(widget)


class TestTaskListItemSignals:
    """Testes dos signals emitidos pelo TaskListItem."""

    def test_signal_status_toggled_emitido_ao_clicar_checkbox(self, qtbot: Any) -> None:
        """Deve emitir status_toggled com o task_id ao clicar no checkbox."""
        task = Task(titulo="Toggle Status")
        widget = TaskListItem(task)
        qtbot.addWidget(widget)

        ids_emitidos: list[str] = []
        widget.status_toggled.connect(ids_emitidos.append)

        widget._on_status_toggled()

        assert len(ids_emitidos) == 1
        assert ids_emitidos[0] == task.id

    def test_signal_edit_requested_emitido_ao_clicar_editar(self, qtbot: Any) -> None:
        """Deve emitir edit_requested com o task_id ao clicar em Editar."""
        task = Task(titulo="Para Editar")
        widget = TaskListItem(task)
        qtbot.addWidget(widget)

        ids_emitidos: list[str] = []
        widget.edit_requested.connect(ids_emitidos.append)

        widget._on_edit_clicked()

        assert len(ids_emitidos) == 1
        assert ids_emitidos[0] == task.id

    def test_signal_delete_requested_emitido_ao_clicar_excluir(
        self, qtbot: Any
    ) -> None:
        """Deve emitir delete_requested com o task_id ao clicar em Excluir."""
        task = Task(titulo="Para Excluir")
        widget = TaskListItem(task)
        qtbot.addWidget(widget)

        ids_emitidos: list[str] = []
        widget.delete_requested.connect(ids_emitidos.append)

        widget._on_delete_clicked()

        assert len(ids_emitidos) == 1
        assert ids_emitidos[0] == task.id

    def test_signal_status_toggled_contem_id_correto(self, qtbot: Any) -> None:
        """O ID emitido pelo status_toggled deve corresponder à tarefa do item."""
        task_a = Task(titulo="Tarefa A")
        task_b = Task(titulo="Tarefa B")
        widget = TaskListItem(task_a)
        qtbot.addWidget(widget)

        ids_emitidos: list[str] = []
        widget.status_toggled.connect(ids_emitidos.append)

        widget._on_status_toggled()

        assert ids_emitidos[0] == task_a.id
        assert ids_emitidos[0] != task_b.id


class TestTaskListItemVencimento:
    """Testes do comportamento para tarefas vencidas."""

    def test_renderiza_sem_excecao_com_data_vencida(self, qtbot: Any) -> None:
        """Deve renderizar sem exceção quando a data de vencimento já passou."""
        ontem = date.today() - timedelta(days=1)
        task = Task(titulo="Vencida", data_vencimento=ontem)
        widget = TaskListItem(task)
        qtbot.addWidget(widget)

    def test_renderiza_sem_excecao_sem_data(self, qtbot: Any) -> None:
        """Deve renderizar sem exceção quando não há data de vencimento."""
        task = Task(titulo="Sem Data")
        widget = TaskListItem(task)
        qtbot.addWidget(widget)
