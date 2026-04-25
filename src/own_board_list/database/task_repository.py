"""
Repositório de tarefas no banco de dados SQLite.

Implementa o padrão Repository para a entidade ``Task``, isolando toda a lógica
de acesso ao banco da camada de serviço. Operações disponíveis: criar, buscar
por ID, listar todas, atualizar, excluir, listar por coluna Kanban, atualizar
posição no Kanban e buscar por texto (título ou descrição). Utiliza SQL direto
via ``sqlite3`` — sem ORM.
"""

from __future__ import annotations

import sqlite3

from own_board_list.models.task import Prioridade, StatusTarefa, Task, parse_datetime
from own_board_list.utils.constants import COLUNA_PADRAO


def _unicode_upper(value: str | None) -> str | None:
    """Função auxiliar registrada no SQLite para upper-case Unicode correto.

    O SQLite nativo ``UPPER()`` não converte caracteres além do ASCII (ex.: ã→Ã,
    ç→Ç, é→É). Registrar esta função permite usar ``PY_UPPER()`` em queries
    com suporte pleno a Unicode via Python.
    """
    if value is None:
        return None
    return value.upper()


class TaskRepository:
    """Gerencia a persistência de tarefas no banco de dados."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Inicializa com a conexão do banco de dados."""
        self._conn = conn
        self._conn.row_factory = sqlite3.Row
        self._conn.create_function("PY_UPPER", 1, _unicode_upper)

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """Converte uma linha do banco de dados em uma Task."""
        return Task(
            id=row["id"],
            titulo=row["titulo"],
            descricao=row["descricao"] or "",
            prioridade=(
                Prioridade(row["prioridade"]) if row["prioridade"] else Prioridade.MEDIA
            ),
            data_vencimento=(
                parse_datetime(row["data_vencimento"]).date()
                if row["data_vencimento"]
                else None
            ),
            status=(
                StatusTarefa(row["status"]) if row["status"] else StatusTarefa.PENDENTE
            ),
            coluna_kanban=row["coluna_kanban"] or COLUNA_PADRAO,
            posicao_kanban=row["posicao_kanban"] or 0,
            criado_em=parse_datetime(row["criado_em"]),
            atualizado_em=parse_datetime(row["atualizado_em"]),
        )

    def create(self, task: Task) -> Task:
        """Persiste uma nova tarefa no banco de dados."""
        self._conn.execute(
            """
            INSERT INTO tasks (
                id, titulo, descricao, prioridade, data_vencimento,
                status, coluna_kanban, posicao_kanban, criado_em, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.id,
                task.titulo,
                task.descricao,
                str(task.prioridade),
                task.data_vencimento.isoformat() if task.data_vencimento else None,
                str(task.status),
                task.coluna_kanban,
                task.posicao_kanban,
                task.criado_em.isoformat(),
                task.atualizado_em.isoformat(),
            ),
        )
        self._conn.commit()
        return task

    def get_by_id(self, task_id: str) -> Task | None:
        """Busca uma tarefa pelo seu ID."""
        cursor = self._conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_task(row)

    def get_all(self) -> list[Task]:
        """Retorna todas as tarefas."""
        cursor = self._conn.execute("SELECT * FROM tasks ORDER BY criado_em DESC")
        return [self._row_to_task(row) for row in cursor.fetchall()]

    def update(self, task: Task) -> Task:
        """Persiste as alterações de uma tarefa existente no banco de dados."""
        self._conn.execute(
            """
            UPDATE tasks SET
                titulo = ?,
                descricao = ?,
                prioridade = ?,
                data_vencimento = ?,
                status = ?,
                coluna_kanban = ?,
                posicao_kanban = ?,
                atualizado_em = ?
            WHERE id = ?
            """,
            (
                task.titulo,
                task.descricao,
                str(task.prioridade),
                task.data_vencimento.isoformat() if task.data_vencimento else None,
                str(task.status),
                task.coluna_kanban,
                task.posicao_kanban,
                task.atualizado_em.isoformat(),
                task.id,
            ),
        )
        self._conn.commit()
        return task

    def delete(self, task_id: str) -> bool:
        """Remove uma tarefa pelo ID. Retorna True se encontrou e removeu."""
        cursor = self._conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def get_by_column(self, coluna: str) -> list[Task]:
        """Retorna tarefas de uma coluna Kanban, ordenadas por posição."""
        cursor = self._conn.execute(
            "SELECT * FROM tasks WHERE coluna_kanban = ? ORDER BY posicao_kanban",
            (coluna,),
        )
        return [self._row_to_task(row) for row in cursor.fetchall()]

    def update_position(self, task_id: str, coluna: str, posicao: int) -> None:
        """Atualiza a coluna e posição de uma tarefa no Kanban."""
        self._conn.execute(
            "UPDATE tasks SET coluna_kanban = ?, posicao_kanban = ? WHERE id = ?",
            (coluna, posicao, task_id),
        )
        self._conn.commit()

    def bulk_insert(self, tasks: list[Task]) -> None:
        """Persiste uma lista de tarefas em lote dentro de uma única transação.

        Usa ``executemany`` para minimizar o overhead de SQL e envolve toda a
        operação em ``BEGIN``/``COMMIT`` atômico. Se já houver uma transação
        ativa (``conn.in_transaction``), o controle da transação fica a cargo
        do chamador externo.

        Nenhum signal Qt é emitido — método silencioso, adequado para
        importação em massa e seeders de teste.
        """
        if not tasks:
            return

        rows = [
            (
                task.id,
                task.titulo,
                task.descricao,
                str(task.prioridade),
                task.data_vencimento.isoformat() if task.data_vencimento else None,
                str(task.status),
                task.coluna_kanban,
                task.posicao_kanban,
                task.criado_em.isoformat(),
                task.atualizado_em.isoformat(),
            )
            for task in tasks
        ]

        # ``sqlite3.Connection`` expõe ``in_transaction`` (Python 3.2+).
        # Proxies de teste podem não implementar o atributo; o fallback
        # conservador é assumir que não há transação ativa e gerenciar aqui.
        owns_transaction = not getattr(self._conn, "in_transaction", False)
        try:
            if owns_transaction:
                self._conn.execute("BEGIN")
            self._conn.executemany(
                """
                INSERT INTO tasks (
                    id, titulo, descricao, prioridade, data_vencimento,
                    status, coluna_kanban, posicao_kanban, criado_em, atualizado_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            if owns_transaction:
                self._conn.commit()
        except Exception:
            if owns_transaction:
                self._conn.rollback()
            raise

    def search(self, query: str) -> list[Task]:
        """Busca tarefas por título ou descrição (case-insensitive, incluindo Unicode).

        Usa ``PY_UPPER`` — função Python registrada na conexão — para contornar a
        limitação do SQLite nativo que não converte caracteres Unicode em ``UPPER()``.
        Escapa os caracteres especiais de LIKE (``\\``, ``%``, ``_``) para evitar
        que o termo de busca seja interpretado como wildcard.
        """
        escaped = (
            query.upper().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        pattern = f"%{escaped}%"
        cursor = self._conn.execute(
            """
            SELECT * FROM tasks
            WHERE PY_UPPER(titulo) LIKE ? ESCAPE '\\'
               OR PY_UPPER(descricao) LIKE ? ESCAPE '\\'
            ORDER BY criado_em DESC
            """,
            (pattern, pattern),
        )
        return [self._row_to_task(row) for row in cursor.fetchall()]
