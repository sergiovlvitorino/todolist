"""
Gerenciamento de conexão com o banco de dados SQLite.

Fornece ``DatabaseConnection``, que encapsula o ciclo de vida de uma conexão
``sqlite3.Connection`` (abertura lazy, configuração de pragmas WAL e
foreign keys, fechamento explícito). A função auxiliar ``get_default_db_path``
resolve o caminho padrão do arquivo de dados em ``~/.own-board-list/data.db``,
criando o diretório se necessário.

A classe implementa o protocolo de context manager (``__enter__`` /
``__exit__``) para transações atômicas:

    with db_connection:
        repo_a.update(...)
        repo_b.update(...)
    # commit automático; rollback em caso de exceção
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from types import TracebackType
from typing import Literal


def get_default_db_path() -> Path:
    """Retorna o caminho padrão do banco de dados, criando o diretório se necessário."""
    db_dir = Path.home() / ".own-board-list"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "data.db"


class DatabaseConnection:
    """Gerencia a conexão com o banco de dados SQLite."""

    def __init__(self, db_path: str | Path) -> None:
        """Inicializa com o caminho do banco de dados, sem abrir a conexão."""
        self._db_path = Path(db_path)
        self._connection: sqlite3.Connection | None = None

    def get_connection(self) -> sqlite3.Connection:
        """Retorna a conexão ativa, abrindo uma nova se necessário."""
        if self._connection is None:
            self._connection = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
            )
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA journal_mode = WAL")
        return self._connection

    def close(self) -> None:
        """Fecha a conexão com o banco de dados."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> DatabaseConnection:
        """Inicia uma transação explícita e retorna a própria instância.

        Emite ``BEGIN`` diretamente via ``execute`` para que ``conn.in_transaction``
        reflita imediatamente o estado da transação. Repositórios que também
        precisam emitir ``BEGIN`` (ex.: ``ColumnRepository.reorder``) devem
        verificar ``conn.in_transaction`` antes de abrir uma transação aninhada
        — SQLite não suporta ``BEGIN`` dentro de ``BEGIN``.
        """
        self.get_connection().execute("BEGIN")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[False]:
        """Finaliza a transação: commit em sucesso, rollback em exceção.

        Retorna False para não suprimir nenhuma exceção levantada no bloco.
        """
        conn = self.get_connection()
        if exc_type is None:
            conn.commit()
        else:
            conn.rollback()
        return False
