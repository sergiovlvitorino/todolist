"""Testes do repositório de tarefas."""

from __future__ import annotations

from own_board_list.database.task_repository import TaskRepository
from own_board_list.models.task import Prioridade, Task


class TestTaskRepositoryCreate:
    """Testes de criação de tarefas no repositório."""

    def test_create_retorna_task(self, task_repo: TaskRepository) -> None:
        """Deve retornar a mesma tarefa após persistir."""
        task = Task(titulo="Nova Tarefa")
        result = task_repo.create(task)

        assert result.id == task.id
        assert result.titulo == task.titulo

    def test_create_persiste_no_banco(self, task_repo: TaskRepository) -> None:
        """A tarefa criada deve ser encontrada no banco depois."""
        task = Task(titulo="Tarefa Persistida")
        task_repo.create(task)

        found = task_repo.get_by_id(task.id)
        assert found is not None
        assert found.titulo == "Tarefa Persistida"


class TestTaskRepositoryGetById:
    """Testes de busca de tarefa por ID."""

    def test_get_by_id_existente(self, task_repo: TaskRepository) -> None:
        """Deve retornar a tarefa quando o ID existe."""
        task = Task(titulo="Busca por ID")
        task_repo.create(task)

        result = task_repo.get_by_id(task.id)

        assert result is not None
        assert result.id == task.id

    def test_get_by_id_inexistente_retorna_none(
        self, task_repo: TaskRepository
    ) -> None:
        """Deve retornar None quando o ID não existe."""
        result = task_repo.get_by_id("id-inexistente-12345")
        assert result is None


class TestTaskRepositoryGetAll:
    """Testes de listagem de todas as tarefas."""

    def test_get_all_retorna_lista_vazia(self, task_repo: TaskRepository) -> None:
        """Deve retornar lista vazia quando não há tarefas."""
        result = task_repo.get_all()
        assert result == []

    def test_get_all_retorna_todas_as_tarefas(self, task_repo: TaskRepository) -> None:
        """Deve retornar todas as tarefas criadas."""
        task_repo.create(Task(titulo="Tarefa 1"))
        task_repo.create(Task(titulo="Tarefa 2"))
        task_repo.create(Task(titulo="Tarefa 3"))

        result = task_repo.get_all()
        assert len(result) == 3


class TestTaskRepositoryUpdate:
    """Testes de atualização de tarefas."""

    def test_update_modifica_campos(self, task_repo: TaskRepository) -> None:
        """Deve atualizar os campos da tarefa no banco."""
        task = Task(titulo="Original")
        task_repo.create(task)

        task.titulo = "Atualizado"
        task.prioridade = Prioridade.ALTA
        task_repo.update(task)

        found = task_repo.get_by_id(task.id)
        assert found is not None
        assert found.titulo == "Atualizado"
        assert found.prioridade == Prioridade.ALTA

    def test_update_renova_atualizado_em(self, task_repo: TaskRepository) -> None:
        """O campo atualizado_em deve ser renovado antes de chamar update."""
        task = Task(titulo="Tarefa")
        task_repo.create(task)
        timestamp_original = task.atualizado_em

        # A responsabilidade de atualizar o timestamp é do modelo (touch),
        # não do repositório. O repositório apenas persiste o que recebe.
        task.touch()
        task_repo.update(task)

        found = task_repo.get_by_id(task.id)
        assert found is not None
        assert found.atualizado_em >= timestamp_original


class TestTaskRepositoryDelete:
    """Testes de remoção de tarefas."""

    def test_delete_existente_retorna_true(self, task_repo: TaskRepository) -> None:
        """Deve retornar True ao remover uma tarefa existente."""
        task = Task(titulo="Para Deletar")
        task_repo.create(task)

        result = task_repo.delete(task.id)

        assert result is True
        assert task_repo.get_by_id(task.id) is None

    def test_delete_inexistente_retorna_false(self, task_repo: TaskRepository) -> None:
        """Deve retornar False ao tentar remover uma tarefa inexistente."""
        result = task_repo.delete("id-que-nao-existe")
        assert result is False


class TestTaskRepositoryGetByColumn:
    """Testes de busca por coluna."""

    def test_get_by_column_ordenado_por_posicao(
        self, task_repo: TaskRepository
    ) -> None:
        """Deve retornar as tarefas ordenadas pela posição na coluna."""
        task_b = Task(titulo="B", coluna_kanban="A Fazer", posicao_kanban=2)
        task_a = Task(titulo="A", coluna_kanban="A Fazer", posicao_kanban=0)
        task_c = Task(titulo="C", coluna_kanban="A Fazer", posicao_kanban=1)
        task_repo.create(task_b)
        task_repo.create(task_a)
        task_repo.create(task_c)

        result = task_repo.get_by_column("A Fazer")

        assert len(result) == 3
        assert result[0].titulo == "A"
        assert result[1].titulo == "C"
        assert result[2].titulo == "B"

    def test_get_by_column_filtra_corretamente(self, task_repo: TaskRepository) -> None:
        """Deve retornar apenas as tarefas da coluna solicitada."""
        task_repo.create(Task(titulo="Fazer", coluna_kanban="A Fazer"))
        task_repo.create(Task(titulo="Andamento", coluna_kanban="Em Andamento"))

        result = task_repo.get_by_column("A Fazer")

        assert len(result) == 1
        assert result[0].titulo == "Fazer"


class TestTaskRepositorySearch:
    """Testes de busca por texto."""

    def test_search_por_titulo(self, task_repo: TaskRepository) -> None:
        """Deve encontrar tarefas pelo título."""
        task_repo.create(Task(titulo="Implementar login"))
        task_repo.create(Task(titulo="Corrigir bug"))

        result = task_repo.search("login")

        assert len(result) == 1
        assert result[0].titulo == "Implementar login"

    def test_search_case_insensitive(self, task_repo: TaskRepository) -> None:
        """A busca deve ser insensível a maiúsculas/minúsculas."""
        task_repo.create(Task(titulo="Implementar LOGIN"))

        result = task_repo.search("login")

        assert len(result) == 1

    def test_search_por_descricao(self, task_repo: TaskRepository) -> None:
        """Deve encontrar tarefas pela descrição."""
        task = Task(titulo="Tarefa X", descricao="Detalhes importantes aqui")
        task_repo.create(task)

        result = task_repo.search("importantes")

        assert len(result) == 1

    def test_search_sem_resultado(self, task_repo: TaskRepository) -> None:
        """Deve retornar lista vazia quando nada é encontrado."""
        task_repo.create(Task(titulo="Alguma Tarefa"))

        result = task_repo.search("inexistente_xyz")

        assert result == []

    def test_search_case_insensitive_unicode_titulo(
        self, task_repo: TaskRepository
    ) -> None:
        """Busca deve ser insensível a maiúsculas/minúsculas com caracteres Unicode."""
        task_repo.create(Task(titulo="REUNIÃO DE EQUIPE"))

        result_lower = task_repo.search("reunião")
        result_upper = task_repo.search("REUNIÃO")
        result_mixed = task_repo.search("Reunião")

        assert len(result_lower) == 1
        assert len(result_upper) == 1
        assert len(result_mixed) == 1

    def test_search_case_insensitive_unicode_descricao(
        self, task_repo: TaskRepository
    ) -> None:
        """Busca na descrição deve ser insensível a maiúsculas com acentos."""
        task_repo.create(Task(titulo="Tarefa Y", descricao="Tomar CAFÉ com o cliente"))

        result = task_repo.search("café")

        assert len(result) == 1
        assert result[0].titulo == "Tarefa Y"

    def test_search_escapa_percentual(self, task_repo: TaskRepository) -> None:
        """Buscar '50%' deve encontrar apenas a task com '50%', não todas."""
        task_repo.create(Task(titulo="Desconto 50%"))
        task_repo.create(Task(titulo="Outra tarefa"))

        result = task_repo.search("50%")

        assert len(result) == 1
        assert result[0].titulo == "Desconto 50%"

    def test_search_escapa_underscore(self, task_repo: TaskRepository) -> None:
        """Buscar 'a_b' deve encontrar apenas a task com 'a_b' literal."""
        task_repo.create(Task(titulo="config a_b aqui"))
        task_repo.create(Task(titulo="axb não deve aparecer"))

        result = task_repo.search("a_b")

        assert len(result) == 1
        assert result[0].titulo == "config a_b aqui"

    def test_search_escapa_backslash(self, task_repo: TaskRepository) -> None:
        """Buscar 'C:\\\\Users' deve encontrar task com barra invertida literal."""
        task_repo.create(Task(titulo="Caminho C:\\Users\\doc"))
        task_repo.create(Task(titulo="Outro caminho"))

        result = task_repo.search("C:\\Users")

        assert len(result) == 1
        assert result[0].titulo == "Caminho C:\\Users\\doc"


class TestTaskRepositoryUpdatePosition:
    """Testes de atualização de posição no Kanban."""

    def test_update_position(self, task_repo: TaskRepository) -> None:
        """Deve atualizar a coluna e posição da tarefa."""
        task = Task(titulo="Mover", coluna_kanban="A Fazer", posicao_kanban=0)
        task_repo.create(task)

        task_repo.update_position(task.id, "Em Andamento", 1)

        found = task_repo.get_by_id(task.id)
        assert found is not None
        assert found.coluna_kanban == "Em Andamento"
        assert found.posicao_kanban == 1


class TestTaskRepositoryBulkInsert:
    """Testes de inserção em lote (DT-034).

    Garante que bulk_insert persiste corretamente via executemany,
    sem emitir signals Qt, e com comportamento correto nos edge cases.
    """

    def test_bulk_insert_persiste_todas_as_tasks(
        self, task_repo: TaskRepository
    ) -> None:
        """bulk_insert deve persistir todas as tasks fornecidas."""
        tasks = [Task(titulo=f"Task bulk {i}") for i in range(5)]
        task_repo.bulk_insert(tasks)

        all_tasks = task_repo.get_all()
        titulos = [t.titulo for t in all_tasks]
        for task in tasks:
            assert task.titulo in titulos

    def test_bulk_insert_lista_vazia_nao_falha(self, task_repo: TaskRepository) -> None:
        """bulk_insert com lista vazia deve retornar sem erro."""
        task_repo.bulk_insert([])  # não deve lançar

        assert task_repo.get_all() == []

    def test_bulk_insert_em_lote_e_atomico(self, task_repo: TaskRepository) -> None:
        """bulk_insert deve ser atômico: ou todas as tasks são inseridas ou nenhuma."""
        tasks_validas = [Task(titulo=f"Válida {i}") for i in range(3)]
        task_repo.bulk_insert(tasks_validas)
        assert len(task_repo.get_all()) == 3

    def test_bulk_insert_com_todas_as_colunas(self, task_repo: TaskRepository) -> None:
        """bulk_insert deve preservar todos os campos da Task."""
        from datetime import date

        from own_board_list.models.task import Prioridade

        task = Task(
            titulo="Task completa",
            descricao="Descrição detalhada",
            prioridade=Prioridade.ALTA,
            data_vencimento=date(2025, 12, 31),
            coluna_kanban="Em Andamento",
            posicao_kanban=7,
        )
        task_repo.bulk_insert([task])

        found = task_repo.get_by_id(task.id)
        assert found is not None
        assert found.titulo == "Task completa"
        assert found.descricao == "Descrição detalhada"
        assert found.prioridade == Prioridade.ALTA
        assert found.data_vencimento == date(2025, 12, 31)
        assert found.coluna_kanban == "Em Andamento"
        assert found.posicao_kanban == 7
