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

Invariante de thread (DT-041)
------------------------------
A conexão SQLite é aberta com ``check_same_thread=False`` para suportar o
loop de eventos Qt, que pode despachar chamadas de repositório a partir de
diferentes contextos internos mantendo porém um único thread principal.

**Contrato:** a conexão DEVE ser usada exclusivamente no thread que a criou
(o thread principal da aplicação). Qualquer feature futura que use
``QThread`` ou ``concurrent.futures`` DEVE criar uma ``DatabaseConnection``
própria para cada thread — nunca compartilhar esta instância.

Em modo debug (``python -O`` desativado), ``get_connection()`` afirma
via ``assert`` que o thread atual é o proprietário da conexão. Isso torna
violações detectáveis durante desenvolvimento e testes, sem custo em produção
otimizada (``python -O`` suprime asserts).

Se for necessário usar múltiplas threads com o banco, encapsule o acesso em
um ``threading.Lock`` e crie uma conexão por thread — ou escale para SRE
antes de qualquer mudança arquitetural.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from types import TracebackType
from typing import Literal


def get_default_db_path() -> Path:
    """Retorna o caminho padrão do banco de dados, criando o diretório se necessário."""
    db_dir = Path.home() / ".own-board-list"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "data.db"


class DatabaseConnection:
    """Gerencia a conexão com o banco de dados SQLite.

    Invariante de thread: a conexão é criada e deve ser usada exclusivamente
    pelo thread que instanciou este objeto (normalmente o thread principal Qt).
    Ver docstring do módulo para detalhes (DT-041).
    """

    def __init__(self, db_path: str | Path) -> None:
        """Inicializa com o caminho do banco de dados, sem abrir a conexão."""
        self._db_path = Path(db_path)
        self._connection: sqlite3.Connection | None = None
        # Registra o thread proprietário no momento da construção do objeto.
        # O guard em get_connection() usa este valor para detectar acessos
        # cross-thread durante desenvolvimento (modo debug).
        self._owner_thread_id: int = threading.get_ident()

    def get_connection(self) -> sqlite3.Connection:
        """Retorna a conexão ativa, abrindo uma nova se necessário.

        Em modo debug, afirma que o chamador está no thread proprietário
        (registrado em ``__init__``). A asserção é suprimida com ``python -O``.
        """
        assert threading.get_ident() == self._owner_thread_id, (
            "DatabaseConnection acessada de thread diferente do proprietário. "
            "Crie uma nova DatabaseConnection por thread ou use um Lock explícito. "
            f"(proprietário={self._owner_thread_id}, "
            f"atual={threading.get_ident()})"
        )
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
