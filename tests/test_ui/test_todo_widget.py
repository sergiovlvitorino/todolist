"""Testes do widget principal da aba Todo List (TodoWidget)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from unittest.mock import patch

from own_board_list.models.task import Prioridade, StatusTarefa
from own_board_list.services.task_service import TaskService
from own_board_list.ui.todo.todo_widget import TodoWidget


class TestTodoWidgetRenderizacao:
    """Testes de renderização e inicialização do TodoWidget."""

    def test_cria_widget_sem_excecao(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Deve instanciar o widget sem lançar exceções."""
        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

    def test_btn_nova_tarefa_existe(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """O botão '+ Nova Tarefa' deve existir."""
        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        assert widget._btn_nova_tarefa is not None
        assert "Nova Tarefa" in widget._btn_nova_tarefa.text()

    def test_grupos_existem_apos_inicializacao(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Os quatro grupos (Hoje, Próximas, Sem data, Concluídas) devem existir."""
        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        assert widget._group_hoje is not None
        assert widget._group_proximas is not None
        assert widget._group_sem_data is not None
        assert widget._group_concluidas is not None

    def test_grupos_com_label_sem_tarefa_quando_vazio(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Com banco vazio, os grupos devem exibir 'Nenhuma tarefa'."""
        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        # Verifica que o grupo "Sem data" tem o label "Nenhuma tarefa"
        layout = widget._group_sem_data.layout()
        assert layout is not None
        item = layout.itemAt(0)
        assert item is not None
        label = item.widget()
        assert label is not None
        assert label.text() == "Nenhuma tarefa"  # type: ignore[attr-defined]


class TestTodoWidgetReloadTasks:
    """Testes de recarga de tarefas no widget."""

    def test_reload_exibe_tarefa_sem_data(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Tarefa sem data deve aparecer no grupo 'Sem data'."""
        task_service_ui.create_task("Tarefa Sem Data")
        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        layout = widget._group_sem_data.layout()
        assert layout is not None
        # Deve ter um TaskListItem (não o label "Nenhuma tarefa")
        assert layout.count() == 1
        item = layout.itemAt(0)
        assert item is not None
        from own_board_list.ui.todo.task_list_item import TaskListItem

        assert isinstance(item.widget(), TaskListItem)

    def test_reload_exibe_tarefa_para_hoje(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Tarefa com data de vencimento igual a hoje deve aparecer no grupo 'Hoje'."""
        task_service_ui.create_task("Tarefa Hoje", data_vencimento=date.today())
        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        layout = widget._group_hoje.layout()
        assert layout is not None
        assert layout.count() == 1
        from own_board_list.ui.todo.task_list_item import TaskListItem

        assert isinstance(layout.itemAt(0).widget(), TaskListItem)  # type: ignore[union-attr]

    def test_reload_exibe_tarefa_proxima(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Tarefa com data futura deve aparecer no grupo 'Próximas'."""
        amanha = date.today() + timedelta(days=1)
        task_service_ui.create_task("Tarefa Futura", data_vencimento=amanha)
        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        layout = widget._group_proximas.layout()
        assert layout is not None
        assert layout.count() == 1
        from own_board_list.ui.todo.task_list_item import TaskListItem

        assert isinstance(layout.itemAt(0).widget(), TaskListItem)  # type: ignore[union-attr]

    def test_reload_exibe_tarefa_concluida(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Tarefa concluída deve aparecer no grupo 'Concluídas'."""
        task = task_service_ui.create_task("Para Concluir")
        task_service_ui.toggle_status(task.id)

        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        layout = widget._group_concluidas.layout()
        assert layout is not None
        assert layout.count() == 1
        from own_board_list.ui.todo.task_list_item import TaskListItem

        assert isinstance(layout.itemAt(0).widget(), TaskListItem)  # type: ignore[union-attr]

    def test_reload_automatico_apos_criar_task_via_service(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """O widget deve recarregar automaticamente quando uma tarefa é criada."""
        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        # Antes: nenhuma tarefa
        layout_antes = widget._group_sem_data.layout()
        assert layout_antes is not None
        from PyQt6.QtWidgets import QLabel

        assert isinstance(layout_antes.itemAt(0).widget(), QLabel)  # type: ignore[union-attr]

        # Cria via serviço — deve disparar signal e recarregar
        task_service_ui.create_task("Auto Reload")

        # Após: deve ter um TaskListItem
        from own_board_list.ui.todo.task_list_item import TaskListItem

        assert isinstance(layout_antes.itemAt(0).widget(), TaskListItem)

    def test_reload_automatico_apos_deletar_task(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """O widget deve recarregar automaticamente quando uma tarefa é deletada."""
        task = task_service_ui.create_task("Para Deletar")
        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        # Confirma que tem a tarefa
        layout = widget._group_sem_data.layout()
        assert layout is not None
        from own_board_list.ui.todo.task_list_item import TaskListItem

        assert isinstance(layout.itemAt(0).widget(), TaskListItem)

        # Deleta via serviço
        task_service_ui.delete_task(task.id)

        # Agora deve ter o label "Nenhuma tarefa"
        from PyQt6.QtWidgets import QLabel

        assert isinstance(layout.itemAt(0).widget(), QLabel)


class TestTodoWidgetToggleStatus:
    """Testes de alternância de status via widget."""

    def test_on_toggle_status_chama_service(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """_on_toggle_status deve delegar ao serviço corretamente."""
        task = task_service_ui.create_task("Toggle")
        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        widget._on_toggle_status(task.id)

        task_atualizada = task_service_ui.get_task_by_id(task.id)
        assert task_atualizada is not None
        assert task_atualizada.status == StatusTarefa.CONCLUIDA


class TestTodoWidgetFormSaved:
    """Testes do processamento do formulário salvo."""

    def test_on_form_saved_cria_nova_task(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """_on_form_saved sem ID deve criar uma nova tarefa."""
        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        dados: dict[str, object] = {
            "titulo": "Nova Tarefa Form",
            "descricao": "Descrição",
            "prioridade": Prioridade.ALTA,
            "data_vencimento": None,
        }
        widget._on_form_saved(dados)

        tasks = task_service_ui.get_all_tasks()
        assert any(t.titulo == "Nova Tarefa Form" for t in tasks)

    def test_on_form_saved_atualiza_task_existente(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """_on_form_saved com ID deve atualizar a tarefa existente."""
        task = task_service_ui.create_task("Original")
        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        dados: dict[str, object] = {
            "id": task.id,
            "titulo": "Atualizado via Form",
            "descricao": "",
            "prioridade": Prioridade.MEDIA,
            "data_vencimento": None,
        }
        widget._on_form_saved(dados)

        task_atualizada = task_service_ui.get_task_by_id(task.id)
        assert task_atualizada is not None
        assert task_atualizada.titulo == "Atualizado via Form"

    def test_on_delete_task_com_confirmacao(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """_on_delete_task deve excluir a tarefa quando o usuário confirma."""
        task = task_service_ui.create_task("Para Deletar")
        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        with patch(
            "own_board_list.ui.todo.todo_widget.confirm_dialog",
            return_value=True,
        ):
            widget._on_delete_task(task.id)

        assert task_service_ui.get_task_by_id(task.id) is None

    def test_on_delete_task_sem_confirmacao_nao_exclui(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """_on_delete_task não deve excluir quando o usuário cancela."""
        task = task_service_ui.create_task("Não Deletar")
        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        with patch(
            "own_board_list.ui.todo.todo_widget.confirm_dialog",
            return_value=False,
        ):
            widget._on_delete_task(task.id)

        assert task_service_ui.get_task_by_id(task.id) is not None

    def test_on_form_saved_tipo_invalido_titulo_lanca_erro(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Deve lançar TypeError se titulo não for str (linha 267 — DT-032)."""
        import pytest

        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        dados: dict[str, object] = {
            "titulo": 42,  # tipo errado propositalmente
            "descricao": "",
            "prioridade": Prioridade.MEDIA,
            "data_vencimento": None,
        }
        with pytest.raises(TypeError, match="titulo deve ser str"):
            widget._on_form_saved(dados)

    def test_on_form_saved_tipo_invalido_descricao_lanca_erro(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Deve lançar TypeError se descricao não for str (linha 270 — DT-032)."""
        import pytest

        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        dados: dict[str, object] = {
            "titulo": "Título OK",
            "descricao": 99,  # tipo errado propositalmente
            "prioridade": Prioridade.MEDIA,
            "data_vencimento": None,
        }
        with pytest.raises(TypeError, match="descricao deve ser str"):
            widget._on_form_saved(dados)

    def test_on_form_saved_tipo_invalido_prioridade_lanca_erro(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Deve lançar TypeError se prioridade não for Prioridade (DT-032)."""
        import pytest

        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        dados: dict[str, object] = {
            "titulo": "Título OK",
            "descricao": "",
            "prioridade": "alta",  # string ao invés de enum
            "data_vencimento": None,
        }
        with pytest.raises(TypeError, match="prioridade deve ser Prioridade"):
            widget._on_form_saved(dados)

    def test_on_form_saved_tipo_invalido_data_vencimento_lanca_erro(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Deve lançar TypeError se data_vencimento não for date/None (DT-032)."""
        import pytest

        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        dados: dict[str, object] = {
            "titulo": "Título OK",
            "descricao": "",
            "prioridade": Prioridade.MEDIA,
            "data_vencimento": "2024-01-01",  # string ao invés de date
        }
        with pytest.raises(TypeError, match="data_vencimento deve ser date ou None"):
            widget._on_form_saved(dados)


class TestTodoWidgetDialogsModais:
    """Testes dos handlers que abrem diálogos modais (DT-032).

    Usa o padrão de factory method (_create_task_form) para injetar um mock
    do formulário — evitando form.exec() bloqueante em CI headless.
    """

    def test_on_nova_tarefa_abre_form_e_conecta_signal(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """_on_nova_tarefa deve instanciar o TaskForm e conectar task_saved.

        Substitui _create_task_form por um spy que registra chamadas e retorna
        um mock que simula o comportamento de form.exec() sem bloquear.
        """
        from unittest.mock import MagicMock

        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        form_mock = MagicMock()
        form_mock.exec.return_value = None

        create_form_calls: list[Any] = []

        def _spy_create_form(task: Any = None) -> Any:
            create_form_calls.append(task)
            return form_mock

        widget._create_task_form = _spy_create_form  # type: ignore[method-assign]

        widget._on_nova_tarefa()

        # O form deve ter sido criado sem task (modo criação)
        assert len(create_form_calls) == 1
        assert create_form_calls[0] is None
        # exec() deve ter sido chamado
        form_mock.exec.assert_called_once()
        # task_saved deve ter sido conectado
        form_mock.task_saved.connect.assert_called_once()

    def test_on_edit_task_abre_form_com_task_existente(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """_on_edit_task deve instanciar o TaskForm com a task para edição."""
        from unittest.mock import MagicMock

        task = task_service_ui.create_task("Para Editar")
        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        form_mock = MagicMock()
        form_mock.exec.return_value = None

        create_form_calls: list[Any] = []

        def _spy_create_form(task: Any = None) -> Any:
            create_form_calls.append(task)
            return form_mock

        widget._create_task_form = _spy_create_form  # type: ignore[method-assign]

        widget._on_edit_task(task.id)

        # O form deve ter sido criado com a task (modo edição)
        assert len(create_form_calls) == 1
        assert create_form_calls[0] is not None
        assert create_form_calls[0].id == task.id
        form_mock.exec.assert_called_once()

    def test_on_edit_task_com_id_inexistente_nao_abre_form(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """ID inexistente deve retornar sem abrir o formulário (DT-032)."""
        from unittest.mock import MagicMock

        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        form_mock = MagicMock()
        widget._create_task_form = lambda task=None: form_mock  # type: ignore[method-assign]

        widget._on_edit_task("id-que-nao-existe")

        # exec() não deve ter sido chamado
        form_mock.exec.assert_not_called()

    def test_clear_group_sem_layout_nao_falha(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Grupo sem layout deve retornar sem erro (DT-032)."""
        from PyQt6.QtWidgets import QGroupBox

        widget = TodoWidget(task_service_ui)
        qtbot.addWidget(widget)

        # Cria um QGroupBox sem layout associado
        grupo_sem_layout = QGroupBox("Sem layout")
        # Não chama setLayout() nem cria QVBoxLayout — layout() retorna None
        # Deve retornar silenciosamente sem AttributeError
        widget._clear_group(grupo_sem_layout)  # não deve lançar
