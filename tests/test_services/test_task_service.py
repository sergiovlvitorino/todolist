"""Testes do serviço de tarefas."""

from __future__ import annotations

from typing import Any

import pytest

from own_board_list.models.task import Prioridade, StatusTarefa, Task
from own_board_list.services.task_service import TaskService


class TestTaskServiceCreateTask:
    """Testes de criação de tarefas pelo serviço."""

    def test_create_task_retorna_task(self, task_service: TaskService) -> None:
        """Deve retornar a tarefa criada."""
        task = task_service.create_task("Nova Tarefa")

        assert task.titulo == "Nova Tarefa"
        assert task.id != ""

    def test_create_task_emite_signal_task_created(
        self, task_service: TaskService, qtbot: Any
    ) -> None:
        """Deve emitir o signal task_created ao criar uma tarefa."""
        emitidas: list[Task] = []
        task_service.task_created.connect(emitidas.append)

        task_service.create_task("Tarefa Signal")

        assert len(emitidas) == 1
        assert emitidas[0].titulo == "Tarefa Signal"

    def test_create_task_com_prioridade_alta(self, task_service: TaskService) -> None:
        """Deve criar tarefa com a prioridade especificada."""
        task = task_service.create_task("Urgente", prioridade=Prioridade.ALTA)
        assert task.prioridade == Prioridade.ALTA


class TestTaskServiceDeleteTask:
    """Testes de exclusão de tarefas."""

    def test_delete_task_retorna_true(self, task_service: TaskService) -> None:
        """Deve retornar True ao excluir uma tarefa existente."""
        task = task_service.create_task("Para Deletar")
        result = task_service.delete_task(task.id)
        assert result is True

    def test_delete_task_emite_signal_task_deleted(
        self, task_service: TaskService, qtbot: Any
    ) -> None:
        """Deve emitir task_deleted com o ID da tarefa removida."""
        ids_deletados: list[str] = []
        task_service.task_deleted.connect(ids_deletados.append)

        task = task_service.create_task("Deletar Signal")
        task_service.delete_task(task.id)

        assert len(ids_deletados) == 1
        assert ids_deletados[0] == task.id


class TestTaskServiceToggleStatus:
    """Testes de alternância de status."""

    def test_toggle_pendente_para_concluida(self, task_service: TaskService) -> None:
        """PENDENTE → CONCLUIDA deve mover a tarefa para a coluna Concluído."""
        task = task_service.create_task("Toggle", coluna_kanban="A Fazer")
        assert task.status == StatusTarefa.PENDENTE

        result = task_service.toggle_status(task.id)

        assert result.status == StatusTarefa.CONCLUIDA
        assert result.coluna_kanban == "Concluído"

    def test_toggle_concluida_para_pendente(self, task_service: TaskService) -> None:
        """CONCLUIDA → PENDENTE deve mover a tarefa para a coluna A Fazer."""
        task = task_service.create_task("Toggle", coluna_kanban="A Fazer")
        task_service.toggle_status(task.id)  # Marca como concluída

        result = task_service.toggle_status(task.id)  # Reabre

        assert result.status == StatusTarefa.PENDENTE
        assert result.coluna_kanban == "A Fazer"


class TestTaskServiceMoveToColumn:
    """Testes de movimentação de tarefas entre colunas."""

    def test_move_para_coluna_concluido_seta_status_concluida(
        self, task_service: TaskService
    ) -> None:
        """Mover para 'Concluído' deve setar status CONCLUIDA."""
        task = task_service.create_task("Mover")

        result = task_service.move_to_column(task.id, "Concluído", 0)

        assert result.status == StatusTarefa.CONCLUIDA
        assert result.coluna_kanban == "Concluído"

    def test_move_de_concluido_para_outra_coluna_seta_pendente(
        self, task_service: TaskService
    ) -> None:
        """Mover da coluna Concluído para outra deve setar status PENDENTE."""
        task = task_service.create_task("Mover")
        task_service.move_to_column(task.id, "Concluído", 0)

        result = task_service.move_to_column(task.id, "Em Andamento", 0)

        assert result.status == StatusTarefa.PENDENTE
        assert result.coluna_kanban == "Em Andamento"

    def test_move_emite_signal_task_updated(
        self, task_service: TaskService, qtbot: Any
    ) -> None:
        """Deve emitir task_updated ao mover uma tarefa."""
        atualizadas: list[Task] = []
        task_service.task_updated.connect(atualizadas.append)

        task = task_service.create_task("Signal Mover")
        task_service.move_to_column(task.id, "Em Andamento", 0)

        # Filtra apenas a atualização de move (pode haver signal de create também)
        assert any(t.coluna_kanban == "Em Andamento" for t in atualizadas)

    def test_move_id_inexistente_lanca_valor_error(
        self, task_service: TaskService
    ) -> None:
        """ValueError para ID inexistente em move_to_column (linha 140 — DT-028).

        Cobre o branch ``if task is None: raise ValueError`` em
        ``move_to_column``.
        """
        with pytest.raises(ValueError, match="não encontrada"):
            task_service.move_to_column("id-inexistente-xyz", "Em Andamento", 0)


class TestTaskServiceUpdateTask:
    """Testes de atualização de tarefas."""

    def test_update_task_modifica_titulo(self, task_service: TaskService) -> None:
        """Deve atualizar o título da tarefa."""
        task = task_service.create_task("Original")
        result = task_service.update_task(task.id, titulo="Atualizado")
        assert result.titulo == "Atualizado"

    def test_update_task_emite_signal_task_updated(
        self, task_service: TaskService, qtbot: Any
    ) -> None:
        """Deve emitir task_updated ao atualizar uma tarefa."""
        atualizadas: list[Task] = []
        task_service.task_updated.connect(atualizadas.append)

        task = task_service.create_task("Para Atualizar")
        task_service.update_task(task.id, titulo="Novo Título")

        assert any(t.titulo == "Novo Título" for t in atualizadas)

    def test_update_task_id_inexistente_lanca_erro(
        self, task_service: TaskService
    ) -> None:
        """Deve lançar ValueError para ID inexistente."""
        with pytest.raises(ValueError, match="não encontrada"):
            task_service.update_task("id-inexistente", titulo="X")

    def test_update_task_campo_invalido_lanca_erro(
        self, task_service: TaskService
    ) -> None:
        """Deve lançar ValueError para campo não editável."""
        task = task_service.create_task("Tarefa")
        with pytest.raises(ValueError, match="não editáveis"):
            task_service.update_task(task.id, id="outro-id")

    def test_update_task_nao_permite_sobrescrever_criado_em(
        self, task_service: TaskService
    ) -> None:
        """Deve bloquear sobrescrita de criado_em."""
        from datetime import datetime

        task = task_service.create_task("Tarefa")
        with pytest.raises(ValueError, match="não editáveis"):
            task_service.update_task(task.id, criado_em=datetime.now())


class TestTaskServiceGetTaskById:
    """Testes de busca de tarefa por ID."""

    def test_get_task_by_id_retorna_task(self, task_service: TaskService) -> None:
        """Deve retornar a tarefa pelo ID."""
        task = task_service.create_task("Buscar por ID")
        result = task_service.get_task_by_id(task.id)
        assert result is not None
        assert result.id == task.id

    def test_get_task_by_id_inexistente_retorna_none(
        self, task_service: TaskService
    ) -> None:
        """Deve retornar None para ID inexistente."""
        result = task_service.get_task_by_id("id-inexistente")
        assert result is None


class TestTaskServiceSearchTasks:
    """Testes de busca por texto."""

    def test_search_tasks_retorna_resultados(self, task_service: TaskService) -> None:
        """Deve retornar tarefas que correspondem à query."""
        task_service.create_task("Tarefa Alpha")
        task_service.create_task("Tarefa Beta")
        results = task_service.search_tasks("Alpha")
        assert len(results) == 1
        assert results[0].titulo == "Tarefa Alpha"

    def test_search_tasks_case_insensitive(self, task_service: TaskService) -> None:
        """Busca deve ignorar diferença entre maiúsculas e minúsculas."""
        task_service.create_task("Tarefa Importante")
        results = task_service.search_tasks("importante")
        assert len(results) == 1

    def test_search_tasks_sem_resultado_retorna_lista_vazia(
        self, task_service: TaskService
    ) -> None:
        """Busca sem correspondência deve retornar lista vazia."""
        task_service.create_task("Tarefa Existente")
        results = task_service.search_tasks("xyz-inexistente")
        assert results == []

    def test_search_tasks_vazia_retorna_todos(self, task_service: TaskService) -> None:
        """Busca com string vazia deve retornar todas as tarefas."""
        task_service.create_task("Tarefa 1")
        task_service.create_task("Tarefa 2")
        results = task_service.search_tasks("")
        assert len(results) == 2


class TestTaskServiceBulkCreateTasks:
    """Testes de criação em lote de tarefas (DT-034)."""

    def test_bulk_create_persiste_todas_as_tasks(
        self, task_service: TaskService
    ) -> None:
        """bulk_create_tasks deve persistir todas as tasks sem signal por task."""
        from own_board_list.models.task import Task

        tasks = [Task(titulo=f"Bulk {i}") for i in range(3)]
        task_service.bulk_create_tasks(tasks)

        all_tasks = task_service.get_all_tasks()
        titulos = [t.titulo for t in all_tasks]
        for task in tasks:
            assert task.titulo in titulos

    def test_bulk_create_nao_emite_task_created_por_item(
        self, task_service: TaskService, qtbot: Any
    ) -> None:
        """bulk_create_tasks não deve emitir task_created por item (silencioso)."""
        from own_board_list.models.task import Task

        sinais_recebidos: list[object] = []
        task_service.task_created.connect(sinais_recebidos.append)

        tasks = [Task(titulo=f"Silenciosa {i}") for i in range(5)]
        task_service.bulk_create_tasks(tasks)

        assert len(sinais_recebidos) == 0

    def test_bulk_create_lista_vazia_nao_falha(self, task_service: TaskService) -> None:
        """bulk_create_tasks com lista vazia deve retornar sem erro."""
        task_service.bulk_create_tasks([])
        assert task_service.get_all_tasks() == []
