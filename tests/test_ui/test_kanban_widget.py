"""Testes do widget principal do quadro Kanban (KanbanWidget)."""

from __future__ import annotations

from typing import Any

from own_board_list.database.column_repository import ColumnRepository
from own_board_list.services.task_service import TaskService
from own_board_list.ui.kanban.kanban_widget import KanbanWidget


class TestKanbanWidgetRenderizacao:
    """Testes de renderização inicial do KanbanWidget."""

    def test_cria_widget_sem_excecao(
        self,
        qtbot: Any,
        task_service_ui: TaskService,
        column_repo_ui: ColumnRepository,
    ) -> None:
        """Deve instanciar o KanbanWidget sem lançar exceções."""
        widget = KanbanWidget(task_service_ui, column_repo_ui)
        qtbot.addWidget(widget)

    def test_renderiza_tres_colunas_padrao(
        self,
        qtbot: Any,
        task_service_ui: TaskService,
        column_repo_ui: ColumnRepository,
    ) -> None:
        """Deve renderizar as 3 colunas padrão (A Fazer, Em Andamento, Concluído)."""
        widget = KanbanWidget(task_service_ui, column_repo_ui)
        qtbot.addWidget(widget)

        assert len(widget._column_widgets) == 3

    def test_nomes_das_colunas_padrao(
        self,
        qtbot: Any,
        task_service_ui: TaskService,
        column_repo_ui: ColumnRepository,
    ) -> None:
        """Os nomes das colunas devem ser os padrões do sistema."""
        widget = KanbanWidget(task_service_ui, column_repo_ui)
        qtbot.addWidget(widget)

        nomes = [col._column_name for col in widget._column_widgets]
        assert "A Fazer" in nomes
        assert "Em Andamento" in nomes
        assert "Concluído" in nomes

    def test_board_container_existe(
        self,
        qtbot: Any,
        task_service_ui: TaskService,
        column_repo_ui: ColumnRepository,
    ) -> None:
        """O contêiner do quadro deve existir após inicialização."""
        widget = KanbanWidget(task_service_ui, column_repo_ui)
        qtbot.addWidget(widget)

        assert widget._board_container is not None
        assert widget._board_layout is not None


class TestKanbanWidgetCards:
    """Testes de exibição de cards no quadro Kanban."""

    def test_task_aparece_na_coluna_correta(
        self,
        qtbot: Any,
        task_service_ui: TaskService,
        column_repo_ui: ColumnRepository,
    ) -> None:
        """Uma tarefa criada em 'A Fazer' deve aparecer na coluna correta."""
        task_service_ui.create_task("Tarefa Kanban")
        widget = KanbanWidget(task_service_ui, column_repo_ui)
        qtbot.addWidget(widget)

        col_a_fazer = next(
            (c for c in widget._column_widgets if c._column_name == "A Fazer"),
            None,
        )
        assert col_a_fazer is not None
        assert len(col_a_fazer._cards) == 1
        assert col_a_fazer._cards[0].task.titulo == "Tarefa Kanban"

    def test_multiplas_tasks_distribuidas_nas_colunas(
        self,
        qtbot: Any,
        task_service_ui: TaskService,
        column_repo_ui: ColumnRepository,
    ) -> None:
        """Tasks em colunas diferentes devem ser distribuídas corretamente."""
        task_a = task_service_ui.create_task("Task A Fazer")
        task_service_ui.move_to_column(task_a.id, "Em Andamento", 0)
        task_service_ui.create_task("Task Em Fazer")

        widget = KanbanWidget(task_service_ui, column_repo_ui)
        qtbot.addWidget(widget)

        col_a_fazer = next(
            c for c in widget._column_widgets if c._column_name == "A Fazer"
        )
        col_em_andamento = next(
            c for c in widget._column_widgets if c._column_name == "Em Andamento"
        )

        assert len(col_a_fazer._cards) == 1
        assert len(col_em_andamento._cards) == 1

    def test_coluna_vazia_tem_zero_cards(
        self,
        qtbot: Any,
        task_service_ui: TaskService,
        column_repo_ui: ColumnRepository,
    ) -> None:
        """Uma coluna sem tasks deve ter zero cards."""
        widget = KanbanWidget(task_service_ui, column_repo_ui)
        qtbot.addWidget(widget)

        col_concluido = next(
            c for c in widget._column_widgets if c._column_name == "Concluído"
        )
        assert len(col_concluido._cards) == 0


class TestKanbanWidgetReload:
    """Testes de recarga automática do quadro Kanban."""

    def test_reload_apos_criar_task(
        self,
        qtbot: Any,
        task_service_ui: TaskService,
        column_repo_ui: ColumnRepository,
    ) -> None:
        """O quadro deve ser recarregado quando uma tarefa é criada."""
        widget = KanbanWidget(task_service_ui, column_repo_ui)
        qtbot.addWidget(widget)

        col_a_fazer = next(
            c for c in widget._column_widgets if c._column_name == "A Fazer"
        )
        assert len(col_a_fazer._cards) == 0

        task_service_ui.create_task("Nova no Kanban")

        col_a_fazer_novo = next(
            c for c in widget._column_widgets if c._column_name == "A Fazer"
        )
        assert len(col_a_fazer_novo._cards) == 1

    def test_reload_apos_deletar_task(
        self,
        qtbot: Any,
        task_service_ui: TaskService,
        column_repo_ui: ColumnRepository,
    ) -> None:
        """O quadro deve ser recarregado quando uma tarefa é deletada."""
        task = task_service_ui.create_task("Deletar do Kanban")
        widget = KanbanWidget(task_service_ui, column_repo_ui)
        qtbot.addWidget(widget)

        col_a_fazer = next(
            c for c in widget._column_widgets if c._column_name == "A Fazer"
        )
        assert len(col_a_fazer._cards) == 1

        task_service_ui.delete_task(task.id)

        col_a_fazer_novo = next(
            c for c in widget._column_widgets if c._column_name == "A Fazer"
        )
        assert len(col_a_fazer_novo._cards) == 0

    def test_reload_manual_reconstroi_colunas(
        self,
        qtbot: Any,
        task_service_ui: TaskService,
        column_repo_ui: ColumnRepository,
    ) -> None:
        """_reload_board deve reconstruir as colunas corretamente."""
        widget = KanbanWidget(task_service_ui, column_repo_ui)
        qtbot.addWidget(widget)

        task_service_ui.create_task("Task Para Reload Manual")
        widget._reload_board()

        assert len(widget._column_widgets) == 3


class TestKanbanWidgetCardDropped:
    """Testes do processamento de drop de cards."""

    def test_on_card_dropped_move_task_para_coluna(
        self,
        qtbot: Any,
        task_service_ui: TaskService,
        column_repo_ui: ColumnRepository,
    ) -> None:
        """_on_card_dropped deve mover a tarefa para a coluna alvo."""
        task = task_service_ui.create_task("Mover via Drop")
        widget = KanbanWidget(task_service_ui, column_repo_ui)
        qtbot.addWidget(widget)

        widget._on_card_dropped(task.id, "Em Andamento", 0)

        task_atualizada = task_service_ui.get_task_by_id(task.id)
        assert task_atualizada is not None
        assert task_atualizada.coluna_kanban == "Em Andamento"

    def test_on_card_dropped_para_concluido_altera_status(
        self,
        qtbot: Any,
        task_service_ui: TaskService,
        column_repo_ui: ColumnRepository,
    ) -> None:
        """Drop na coluna 'Concluído' deve marcar a tarefa como concluída."""
        from own_board_list.models.task import StatusTarefa

        task = task_service_ui.create_task("Concluir via Drop")
        widget = KanbanWidget(task_service_ui, column_repo_ui)
        qtbot.addWidget(widget)

        widget._on_card_dropped(task.id, "Concluído", 0)

        task_atualizada = task_service_ui.get_task_by_id(task.id)
        assert task_atualizada is not None
        assert task_atualizada.status == StatusTarefa.CONCLUIDA
