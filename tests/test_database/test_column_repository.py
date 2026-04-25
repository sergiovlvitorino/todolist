"""Testes do repositório de colunas Kanban."""

from __future__ import annotations

import sqlite3

import pytest

from own_board_list.database.column_repository import ColumnRepository
from own_board_list.database.task_repository import TaskRepository
from own_board_list.models.kanban_column import KanbanColumn
from own_board_list.models.task import Task


class TestColumnRepositoryCreate:
    """Testes de criação de colunas."""

    def test_create_retorna_coluna(self, column_repo: ColumnRepository) -> None:
        """Deve retornar a coluna após persistir."""
        coluna = KanbanColumn(nome="Revisão", posicao=3)
        result = column_repo.create(coluna)

        assert result.id == coluna.id
        assert result.nome == "Revisão"

    def test_create_persiste_no_banco(self, column_repo: ColumnRepository) -> None:
        """A coluna criada deve aparecer no get_all."""
        coluna = KanbanColumn(nome="Nova Coluna", posicao=10)
        column_repo.create(coluna)

        all_columns = column_repo.get_all()
        nomes = [c.nome for c in all_columns]
        assert "Nova Coluna" in nomes


class TestColumnRepositoryGetAll:
    """Testes de listagem de colunas."""

    def test_get_all_retorna_colunas_padrao(
        self, column_repo: ColumnRepository
    ) -> None:
        """Deve retornar as 3 colunas padrão criadas pelo initialize_database."""
        result = column_repo.get_all()

        assert len(result) == 3
        nomes = [c.nome for c in result]
        assert "A Fazer" in nomes
        assert "Em Andamento" in nomes
        assert "Concluído" in nomes

    def test_get_all_ordenado_por_posicao(self, column_repo: ColumnRepository) -> None:
        """As colunas devem ser retornadas em ordem de posição."""
        result = column_repo.get_all()

        posicoes = [c.posicao for c in result]
        assert posicoes == sorted(posicoes)


class TestColumnRepositoryUpdate:
    """Testes de atualização de colunas."""

    def test_update_modifica_nome(self, column_repo: ColumnRepository) -> None:
        """Deve atualizar o nome da coluna."""
        colunas = column_repo.get_all()
        coluna = colunas[0]
        nome_original = coluna.nome

        coluna.nome = "Renomeada"
        column_repo.update(coluna)

        atualizadas = column_repo.get_all()
        nomes = [c.nome for c in atualizadas]
        assert "Renomeada" in nomes
        assert nome_original not in nomes


class TestColumnRepositoryDelete:
    """Testes de remoção de colunas."""

    def test_delete_existente_retorna_true(self, column_repo: ColumnRepository) -> None:
        """Deve retornar True ao remover uma coluna existente."""
        coluna = KanbanColumn(nome="Temporária", posicao=99)
        column_repo.create(coluna)

        result = column_repo.delete(coluna.id)

        assert result is True
        colunas = column_repo.get_all()
        ids = [c.id for c in colunas]
        assert coluna.id not in ids

    def test_delete_inexistente_retorna_false(
        self, column_repo: ColumnRepository
    ) -> None:
        """Deve retornar False ao tentar remover uma coluna inexistente."""
        result = column_repo.delete("id-inexistente-99999")
        assert result is False


class TestColumnRepositoryReorder:
    """Testes de reordenação de colunas."""

    def test_reorder_atualiza_posicoes(self, column_repo: ColumnRepository) -> None:
        """Deve atualizar as posições conforme a nova ordem de IDs."""
        colunas = column_repo.get_all()
        # Inverte a ordem
        ids_invertidos = [c.id for c in reversed(colunas)]
        column_repo.reorder(ids_invertidos)

        reordenadas = column_repo.get_all()
        for i, coluna in enumerate(reordenadas):
            assert coluna.posicao == i

    def test_reorder_verifica_ordem_correta(
        self, column_repo: ColumnRepository
    ) -> None:
        """A primeira coluna na lista deve ter posição 0."""
        colunas = column_repo.get_all()
        ids = [c.id for c in colunas]
        # Reordena mantendo a mesma ordem
        column_repo.reorder(ids)

        reordenadas = column_repo.get_all()
        assert reordenadas[0].posicao == 0
        assert reordenadas[1].posicao == 1
        assert reordenadas[2].posicao == 2

    def test_reorder_rollback_em_erro_parcial(
        self,
        db_conn: sqlite3.Connection,
    ) -> None:
        """Erro no meio do loop de UPDATEs deve fazer rollback completo.

        Cenário: 3 colunas (padrão do banco em memória), falha simulada no
        segundo UPDATE do loop de reorder(). Nenhuma posição deve ter sido
        alterada após a exceção (rollback). A exceção original deve ser
        relançada ao chamador.

        Estratégia: ConnectionProxy envolve a conexão SQLite real e
        intercepta chamadas a execute(). Na 3ª chamada (segundo UPDATE),
        lança OperationalError antes de executar o SQL, forçando o caminho
        de exceção e rollback do método reorder().
        """

        class ConnectionProxy:
            """Proxy que delega para a conexão real e injeta falha pontual."""

            def __init__(self, real_conn: sqlite3.Connection) -> None:
                self._real = real_conn
                self._call_count = 0

            def execute(self, sql: str, *args: object) -> object:
                self._call_count += 1
                # Sequência de chamadas em reorder():
                #   1ª: BEGIN
                #   2ª: UPDATE posicao=0 (primeiro ID)
                #   3ª: UPDATE posicao=1 (segundo ID) ← falha aqui
                if self._call_count == 3:
                    raise sqlite3.OperationalError("Falha simulada no segundo UPDATE")
                return self._real.execute(sql, *args)

            def commit(self) -> None:
                self._real.commit()

            def rollback(self) -> None:
                self._real.rollback()

            # Repassa row_factory para que ColumnRepository consiga
            # definir a propriedade sem AttributeError
            @property
            def row_factory(self) -> object:
                return self._real.row_factory

            @row_factory.setter
            def row_factory(self, value: object) -> None:
                self._real.row_factory = value  # type: ignore[assignment]

        proxy = ConnectionProxy(db_conn)
        repo_com_proxy = ColumnRepository(proxy)  # type: ignore[arg-type]

        # Lê as colunas diretamente pelo repo real para registrar estado original
        repo_real = ColumnRepository(db_conn)
        colunas = repo_real.get_all()
        posicoes_originais = {c.id: c.posicao for c in colunas}
        ids_nova_ordem = [c.id for c in reversed(colunas)]

        # A exceção deve ser relançada ao chamador
        with pytest.raises(sqlite3.OperationalError, match="Falha simulada"):
            repo_com_proxy.reorder(ids_nova_ordem)

        # Nenhuma posição deve ter sido alterada (rollback ocorreu)
        colunas_apos = repo_real.get_all()
        posicoes_apos = {c.id: c.posicao for c in colunas_apos}
        assert posicoes_apos == posicoes_originais


class TestColumnRepositoryHasTasks:
    """Testes de verificação de tarefas numa coluna."""

    def test_has_tasks_retorna_false_quando_vazio(
        self, column_repo: ColumnRepository
    ) -> None:
        """Deve retornar False quando a coluna não tem tarefas."""
        colunas = column_repo.get_all()
        coluna_a_fazer = next(c for c in colunas if c.nome == "A Fazer")

        result = column_repo.has_tasks(coluna_a_fazer.id)
        assert result is False

    def test_has_tasks_retorna_true_quando_ha_tasks(
        self,
        column_repo: ColumnRepository,
        task_repo: TaskRepository,
    ) -> None:
        """Deve retornar True quando a coluna tem ao menos uma tarefa."""
        colunas = column_repo.get_all()
        coluna_a_fazer = next(c for c in colunas if c.nome == "A Fazer")

        task_repo.create(Task(titulo="Tarefa na coluna", coluna_kanban="A Fazer"))

        result = column_repo.has_tasks(coluna_a_fazer.id)
        assert result is True

    def test_has_tasks_retorna_false_para_id_inexistente(
        self, column_repo: ColumnRepository
    ) -> None:
        """Deve retornar False quando o ID da coluna não existe (linha 117 — DT-027).

        Cobre o branch ``if row is None: return False`` em ``has_tasks``.
        """
        result = column_repo.has_tasks("id-que-nao-existe-no-banco")
        assert result is False


class TestColumnRepositoryRowToColumn:
    """Testes de conversão de linha do banco para KanbanColumn."""

    def test_row_to_column_normaliza_datetime_naive_para_utc(
        self, db_conn: sqlite3.Connection, column_repo: ColumnRepository
    ) -> None:
        """Datetime naive deve ser normalizado para UTC (linha 34 — DT-027).

        Insere diretamente no banco um ``criado_em`` sem offset de timezone
        (simulando dados legacy) e verifica que ``get_all()`` retorna o
        ``KanbanColumn`` com ``tzinfo=UTC`` após a normalização.
        """
        from datetime import UTC, datetime

        from own_board_list.models.kanban_column import KanbanColumn

        coluna = KanbanColumn(nome="Coluna Legacy", posicao=99)
        # Grava com datetime naive (sem timezone) para simular dados legados
        naive_iso = datetime(2024, 1, 15, 10, 30, 0).isoformat()  # sem tzinfo
        db_conn.execute(
            "INSERT INTO kanban_columns (id, nome, posicao, criado_em)"
            " VALUES (?, ?, ?, ?)",
            (coluna.id, coluna.nome, coluna.posicao, naive_iso),
        )
        db_conn.commit()

        # Busca via repositório — deve normalizar para UTC
        colunas = column_repo.get_all()
        coluna_legacy = next((c for c in colunas if c.nome == "Coluna Legacy"), None)
        assert coluna_legacy is not None
        assert coluna_legacy.criado_em.tzinfo == UTC
