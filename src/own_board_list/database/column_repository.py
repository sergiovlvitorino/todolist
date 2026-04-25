"""
Repositório de colunas Kanban no banco de dados SQLite.

Implementa o padrão Repository para a entidade ``KanbanColumn``, encapsulando
o acesso à tabela ``kanban_columns``. Operações disponíveis: criar, listar
ordenadas por posição, atualizar, excluir, reordenar e verificar se uma coluna
possui tarefas associadas (guarda de integridade). Utiliza SQL direto via
``sqlite3`` — sem ORM.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from own_board_list.models.kanban_column import KanbanColumn


class ColumnRepository:
    """Gerencia a persistência de colunas Kanban no banco de dados."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Inicializa com a conexão do banco de dados."""
        self._conn = conn
        self._conn.row_factory = sqlite3.Row

    def _row_to_column(self, row: sqlite3.Row) -> KanbanColumn:
        """Converte uma linha do banco de dados em uma KanbanColumn.

        Datetimes sem timezone (dados legacy/naive) são interpretados como UTC.
        """
        dt = datetime.fromisoformat(row["criado_em"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return KanbanColumn(
            id=row["id"],
            nome=row["nome"],
            posicao=row["posicao"] or 0,
            criado_em=dt,
        )

    def create(self, column: KanbanColumn) -> KanbanColumn:
        """Persiste uma nova coluna no banco de dados."""
        self._conn.execute(
            "INSERT INTO kanban_columns (id, nome, posicao, criado_em)"
            " VALUES (?, ?, ?, ?)",
            (
                column.id,
                column.nome,
                column.posicao,
                column.criado_em.isoformat(),
            ),
        )
        self._conn.commit()
        return column

    def get_all(self) -> list[KanbanColumn]:
        """Retorna todas as colunas ordenadas por posição."""
        cursor = self._conn.execute("SELECT * FROM kanban_columns ORDER BY posicao")
        return [self._row_to_column(row) for row in cursor.fetchall()]

    def update(self, column: KanbanColumn) -> KanbanColumn:
        """Atualiza os dados de uma coluna existente."""
        self._conn.execute(
            "UPDATE kanban_columns SET nome = ?, posicao = ? WHERE id = ?",
            (column.nome, column.posicao, column.id),
        )
        self._conn.commit()
        return column

    def delete(self, column_id: str) -> bool:
        """Remove uma coluna pelo ID. Retorna True se encontrou e removeu."""
        cursor = self._conn.execute(
            "DELETE FROM kanban_columns WHERE id = ?", (column_id,)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def reorder(self, column_ids: list[str]) -> None:
        """Reordena as colunas conforme a lista de IDs fornecida.

        Toda a operação é encapsulada em uma transação: se qualquer UPDATE
        falhar, um rollback completo é realizado e a exceção original é
        relançada, evitando posições parcialmente atualizadas.

        Se já houver uma transação ativa (ex.: chamada dentro de
        ``with DatabaseConnection(...)``) o ``BEGIN`` é omitido e o controle
        da transação fica a cargo do chamador externo.
        """
        # ``sqlite3.Connection`` expõe ``in_transaction`` (Python 3.2+).
        # Proxies de teste podem não implementar o atributo; o fallback
        # conservador é assumir que não há transação ativa e gerenciar aqui.
        owns_transaction = not getattr(self._conn, "in_transaction", False)
        try:
            if owns_transaction:
                self._conn.execute("BEGIN")
            for posicao, column_id in enumerate(column_ids):
                self._conn.execute(
                    "UPDATE kanban_columns SET posicao = ? WHERE id = ?",
                    (posicao, column_id),
                )
            if owns_transaction:
                self._conn.commit()
        except Exception:
            if owns_transaction:
                self._conn.rollback()
            raise

    def has_tasks(self, column_id: str) -> bool:
        """Verifica se uma coluna possui tarefas associadas."""
        # Busca o nome da coluna para verificar via nome nas tasks
        cursor = self._conn.execute(
            "SELECT nome FROM kanban_columns WHERE id = ?", (column_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return False
        nome_coluna: str = row["nome"]
        cursor2 = self._conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE coluna_kanban = ?", (nome_coluna,)
        )
        count_row = cursor2.fetchone()
        count: int = count_row[0] if count_row is not None else 0
        return count > 0
