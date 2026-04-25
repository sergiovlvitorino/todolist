"""
Testes de integração: UI + serviço + banco SQLite real.

Verificam que os widgets Qt interagem corretamente com o TaskService
e que as operações são persistidas no banco de dados real (em memória).
"""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import patch

from own_board_list.database.column_repository import ColumnRepository
from own_board_list.models.task import Prioridade, StatusTarefa
from own_board_list.services.task_service import TaskService
from own_board_list.ui.kanban.kanban_widget import KanbanWidget
from own_board_list.ui.todo.todo_widget import TodoWidget


class TestTodoWidgetComBancoReal:
    """Integração: TodoWidget ↔ TaskService ↔ SQLite em memória."""

    def test_criar_task_via_form_reflete_no_banco(
        self,
        qtbot: Any,
        task_service_int: TaskService,
    ) -> None:
        """Criar tarefa pelo método _on_form_saved deve persistir no banco."""
        widget = TodoWidget(task_service_int)
        qtbot.addWidget(widget)

        dados: dict[str, object] = {
            "titulo": "Tarefa Via Widget",
            "descricao": "Criada pelo TodoWidget",
            "prioridade": Prioridade.ALTA,
            "data_vencimento": None,
        }
        widget._on_form_saved(dados)

        tasks = task_service_int.get_all_tasks()
        assert len(tasks) == 1
        assert tasks[0].titulo == "Tarefa Via Widget"
        assert tasks[0].prioridade == Prioridade.ALTA

    def test_toggle_status_via_widget_persiste_no_banco(
        self,
        qtbot: Any,
        task_service_int: TaskService,
    ) -> None:
        """Toggle de status via widget deve persistir no banco."""
        task = task_service_int.create_task("Toggle Via Widget")
        widget = TodoWidget(task_service_int)
        qtbot.addWidget(widget)

        widget._on_toggle_status(task.id)

        recuperada = task_service_int.get_task_by_id(task.id)
        assert recuperada is not None
        assert recuperada.status == StatusTarefa.CONCLUIDA

    def test_editar_task_via_form_persiste_no_banco(
        self,
        qtbot: Any,
        task_service_int: TaskService,
    ) -> None:
        """Editar tarefa pelo _on_form_saved deve atualizar no banco."""
        task = task_service_int.create_task("Original Widget")
        widget = TodoWidget(task_service_int)
        qtbot.addWidget(widget)

        dados: dict[str, object] = {
            "id": task.id,
            "titulo": "Editado Via Widget",
            "descricao": "Nova descrição",
            "prioridade": Prioridade.BAIXA,
            "data_vencimento": None,
        }
        widget._on_form_saved(dados)

        recuperada = task_service_int.get_task_by_id(task.id)
        assert recuperada is not None
        assert recuperada.titulo == "Editado Via Widget"
        assert recuperada.prioridade == Prioridade.BAIXA

    def test_deletar_task_via_widget_remove_do_banco(
        self,
        qtbot: Any,
        task_service_int: TaskService,
    ) -> None:
        """Deletar tarefa com confirmação deve remover do banco."""
        task = task_service_int.create_task("Deletar Widget")
        widget = TodoWidget(task_service_int)
        qtbot.addWidget(widget)

        with patch(
            "own_board_list.ui.todo.todo_widget.confirm_dialog",
            return_value=True,
        ):
            widget._on_delete_task(task.id)

        assert task_service_int.get_task_by_id(task.id) is None

    def test_classificacao_correta_por_data_vencimento(
        self,
        qtbot: Any,
        task_service_int: TaskService,
    ) -> None:
        """Tasks devem ser classificadas nos grupos corretos pelo vencimento."""
        from datetime import timedelta

        hoje = date.today()
        amanha = hoje + timedelta(days=1)

        task_service_int.create_task("Vence Hoje", data_vencimento=hoje)
        task_service_int.create_task("Vence Amanhã", data_vencimento=amanha)
        task_service_int.create_task("Sem Vencimento")
        task_hoje_concluida = task_service_int.create_task(
            "Concluída Hoje", data_vencimento=hoje
        )
        task_service_int.toggle_status(task_hoje_concluida.id)

        widget = TodoWidget(task_service_int)
        qtbot.addWidget(widget)

        from own_board_list.ui.todo.task_list_item import TaskListItem

        # Grupo "Hoje": deve ter "Vence Hoje" (pendente com data <= hoje)
        layout_hoje = widget._group_hoje.layout()
        assert layout_hoje is not None
        assert layout_hoje.count() == 1
        assert isinstance(layout_hoje.itemAt(0).widget(), TaskListItem)  # type: ignore[union-attr]

        # Grupo "Próximas"
        layout_proximas = widget._group_proximas.layout()
        assert layout_proximas is not None
        assert layout_proximas.count() == 1

        # Grupo "Sem data"
        layout_sem_data = widget._group_sem_data.layout()
        assert layout_sem_data is not None
        assert layout_sem_data.count() == 1

        # Grupo "Concluídas"
        layout_concluidas = widget._group_concluidas.layout()
        assert layout_concluidas is not None
        assert layout_concluidas.count() == 1


class TestKanbanWidgetComBancoReal:
    """Integração: KanbanWidget ↔ TaskService ↔ SQLite em memória."""

    def test_kanban_exibe_tasks_por_coluna_corretamente(
        self,
        qtbot: Any,
        task_service_int: TaskService,
        column_repo_int: ColumnRepository,
    ) -> None:
        """KanbanWidget deve exibir tasks nas colunas corretas após inicialização."""
        task_service_int.create_task("A Fazer 1")
        task_service_int.create_task("A Fazer 2")
        task_em = task_service_int.create_task("Em Andamento 1")
        task_service_int.move_to_column(task_em.id, "Em Andamento", 0)

        widget = KanbanWidget(task_service_int, column_repo_int)
        qtbot.addWidget(widget)

        col_a_fazer = next(
            c for c in widget._column_widgets if c._column_name == "A Fazer"
        )
        col_em_andamento = next(
            c for c in widget._column_widgets if c._column_name == "Em Andamento"
        )
        col_concluido = next(
            c for c in widget._column_widgets if c._column_name == "Concluído"
        )

        assert len(col_a_fazer._cards) == 2
        assert len(col_em_andamento._cards) == 1
        assert len(col_concluido._cards) == 0

    def test_drop_card_persiste_nova_coluna(
        self,
        qtbot: Any,
        task_service_int: TaskService,
        column_repo_int: ColumnRepository,
    ) -> None:
        """Drop de card via _on_card_dropped deve persistir a mudança de coluna."""
        task = task_service_int.create_task("Drop Integração")
        widget = KanbanWidget(task_service_int, column_repo_int)
        qtbot.addWidget(widget)

        widget._on_card_dropped(task.id, "Em Andamento", 0)

        recuperada = task_service_int.get_task_by_id(task.id)
        assert recuperada is not None
        assert recuperada.coluna_kanban == "Em Andamento"

    def test_kanban_reload_apos_todo_widget_criar_task(
        self,
        qtbot: Any,
        task_service_int: TaskService,
        column_repo_int: ColumnRepository,
    ) -> None:
        """KanbanWidget deve recarregar quando TodoWidget cria uma task."""
        todo_widget = TodoWidget(task_service_int)
        qtbot.addWidget(todo_widget)

        kanban_widget = KanbanWidget(task_service_int, column_repo_int)
        qtbot.addWidget(kanban_widget)

        # Ambos conectados ao mesmo serviço — criar via todo deve atualizar kanban
        dados: dict[str, object] = {
            "titulo": "Sync Widgets",
            "descricao": "",
            "prioridade": Prioridade.MEDIA,
            "data_vencimento": None,
        }
        todo_widget._on_form_saved(dados)

        col_a_fazer = next(
            c for c in kanban_widget._column_widgets if c._column_name == "A Fazer"
        )
        assert len(col_a_fazer._cards) == 1
        assert col_a_fazer._cards[0].task.titulo == "Sync Widgets"

    def test_sincronizacao_bidirecional_todo_e_kanban(
        self,
        qtbot: Any,
        task_service_int: TaskService,
        column_repo_int: ColumnRepository,
    ) -> None:
        """Mover card no Kanban deve refletir no TodoWidget (via signal)."""
        task = task_service_int.create_task("Sincronizar")
        todo_widget = TodoWidget(task_service_int)
        qtbot.addWidget(todo_widget)
        kanban_widget = KanbanWidget(task_service_int, column_repo_int)
        qtbot.addWidget(kanban_widget)

        # Move para Concluído via KanbanWidget
        kanban_widget._on_card_dropped(task.id, "Concluído", 0)

        # Verifica no banco que o status foi atualizado
        recuperada = task_service_int.get_task_by_id(task.id)
        assert recuperada is not None
        assert recuperada.status == StatusTarefa.CONCLUIDA

        # Verifica que TodoWidget recarregou (task concluída no grupo certo)
        layout_concluidas = todo_widget._group_concluidas.layout()
        assert layout_concluidas is not None
        from own_board_list.ui.todo.task_list_item import TaskListItem

        assert isinstance(layout_concluidas.itemAt(0).widget(), TaskListItem)  # type: ignore[union-attr]


class TestPersistenciaEntreConexoes:
    """Testes de persistência entre reconexões ao banco (arquivo físico)."""

    def test_criar_e_recuperar_apos_reconexao(
        self,
        qtbot: Any,
        db_file: Any,
    ) -> None:
        """Dados criados em uma sessão devem persistir em nova conexão."""
        import sqlite3

        from own_board_list.database.column_repository import ColumnRepository
        from own_board_list.database.migrations import initialize_database
        from own_board_list.database.task_repository import TaskRepository

        # Sessão 1: criar tarefa
        conn1 = sqlite3.connect(str(db_file))
        conn1.row_factory = sqlite3.Row
        initialize_database(conn1)
        repo1 = TaskRepository(conn1)
        col_repo1 = ColumnRepository(conn1)
        service1 = TaskService(repo1, col_repo1)

        task = service1.create_task(
            "Persiste Entre Sessões",
            descricao="Deve sobreviver",
            prioridade=Prioridade.ALTA,
        )
        task_id = task.id
        conn1.close()

        # Sessão 2: verificar que a tarefa persiste
        conn2 = sqlite3.connect(str(db_file))
        conn2.row_factory = sqlite3.Row
        initialize_database(conn2)
        repo2 = TaskRepository(conn2)
        col_repo2 = ColumnRepository(conn2)
        service2 = TaskService(repo2, col_repo2)

        recuperada = service2.get_task_by_id(task_id)
        assert recuperada is not None
        assert recuperada.titulo == "Persiste Entre Sessões"
        assert recuperada.descricao == "Deve sobreviver"
        assert recuperada.prioridade == Prioridade.ALTA
        conn2.close()

    def test_update_e_verificar_apos_reconexao(
        self,
        qtbot: Any,
        db_file: Any,
    ) -> None:
        """Edição de tarefa deve persistir entre reconexões."""
        import sqlite3

        from own_board_list.database.column_repository import ColumnRepository
        from own_board_list.database.migrations import initialize_database
        from own_board_list.database.task_repository import TaskRepository

        # Sessão 1: criar e editar
        conn1 = sqlite3.connect(str(db_file))
        conn1.row_factory = sqlite3.Row
        initialize_database(conn1)
        service1 = TaskService(TaskRepository(conn1), ColumnRepository(conn1))

        task = service1.create_task("Antes da Edição")
        service1.update_task(task.id, titulo="Depois da Edição")
        task_id = task.id
        conn1.close()

        # Sessão 2: verificar edição persistida
        conn2 = sqlite3.connect(str(db_file))
        conn2.row_factory = sqlite3.Row
        initialize_database(conn2)
        service2 = TaskService(TaskRepository(conn2), ColumnRepository(conn2))

        recuperada = service2.get_task_by_id(task_id)
        assert recuperada is not None
        assert recuperada.titulo == "Depois da Edição"
        conn2.close()

    def test_movimento_kanban_persiste_entre_sessoes(
        self,
        qtbot: Any,
        db_file: Any,
    ) -> None:
        """Movimento de coluna Kanban deve persistir entre reconexões."""
        import sqlite3

        from own_board_list.database.column_repository import ColumnRepository
        from own_board_list.database.migrations import initialize_database
        from own_board_list.database.task_repository import TaskRepository

        # Sessão 1: criar e mover
        conn1 = sqlite3.connect(str(db_file))
        conn1.row_factory = sqlite3.Row
        initialize_database(conn1)
        service1 = TaskService(TaskRepository(conn1), ColumnRepository(conn1))

        task = service1.create_task("Mover e Persistir")
        assert task.coluna_kanban == "A Fazer"
        service1.move_to_column(task.id, "Em Andamento", 0)
        task_id = task.id
        conn1.close()

        # Sessão 2: verificar nova coluna
        conn2 = sqlite3.connect(str(db_file))
        conn2.row_factory = sqlite3.Row
        initialize_database(conn2)
        service2 = TaskService(TaskRepository(conn2), ColumnRepository(conn2))

        recuperada = service2.get_task_by_id(task_id)
        assert recuperada is not None
        assert recuperada.coluna_kanban == "Em Andamento"
        conn2.close()

    def test_delete_persiste_entre_sessoes(
        self,
        qtbot: Any,
        db_file: Any,
    ) -> None:
        """Task deletada não deve aparecer em nova sessão."""
        import sqlite3

        from own_board_list.database.column_repository import ColumnRepository
        from own_board_list.database.migrations import initialize_database
        from own_board_list.database.task_repository import TaskRepository

        # Sessão 1: criar e deletar
        conn1 = sqlite3.connect(str(db_file))
        conn1.row_factory = sqlite3.Row
        initialize_database(conn1)
        service1 = TaskService(TaskRepository(conn1), ColumnRepository(conn1))

        task = service1.create_task("Deletar e Verificar")
        task_id = task.id
        service1.delete_task(task_id)
        conn1.close()

        # Sessão 2: confirmar que não existe
        conn2 = sqlite3.connect(str(db_file))
        conn2.row_factory = sqlite3.Row
        initialize_database(conn2)
        service2 = TaskService(TaskRepository(conn2), ColumnRepository(conn2))

        recuperada = service2.get_task_by_id(task_id)
        assert recuperada is None
        conn2.close()
