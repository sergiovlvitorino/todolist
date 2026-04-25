"""
Migrações e inicialização do esquema do banco de dados.

Contém a função ``initialize_database``, que cria as tabelas ``tasks`` e
``kanban_columns`` (caso ainda não existam) e insere as três colunas padrão
do Kanban ("A Fazer", "Em Andamento", "Concluído") na primeira execução.
Deve ser chamada logo após abrir a conexão, antes de qualquer operação nos
repositórios.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime

from own_board_list.utils.constants import (
    COLUNA_A_FAZER,
    COLUNA_CONCLUIDO,
    COLUNA_EM_ANDAMENTO,
)


def initialize_database(conn: sqlite3.Connection) -> None:
    """Cria as tabelas e insere dados padrão se necessário."""
    cursor = conn.cursor()

    # Cria tabela de colunas Kanban
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kanban_columns (
            id TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            posicao INTEGER DEFAULT 0,
            criado_em TEXT
        )
    """)

    # Cria tabela de tarefas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            titulo TEXT NOT NULL,
            descricao TEXT DEFAULT '',
            prioridade TEXT,
            data_vencimento TEXT,
            status TEXT,
            coluna_kanban TEXT,
            posicao_kanban INTEGER DEFAULT 0,
            criado_em TEXT,
            atualizado_em TEXT
        )
    """)

    # Cria índices para acelerar consultas de filtragem e ordenação
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_coluna_kanban
        ON tasks (coluna_kanban)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_status
        ON tasks (status)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_prioridade
        ON tasks (prioridade)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_data_vencimento
        ON tasks (data_vencimento)
    """)

    # Insere colunas padrão se a tabela estiver vazia
    cursor.execute("SELECT COUNT(*) FROM kanban_columns")
    row = cursor.fetchone()
    count: int = row[0] if row is not None else 0

    if count == 0:
        agora = datetime.now(tz=UTC).isoformat()
        colunas_padrao = [
            (str(uuid.uuid4()), COLUNA_A_FAZER, 0, agora),
            (str(uuid.uuid4()), COLUNA_EM_ANDAMENTO, 1, agora),
            (str(uuid.uuid4()), COLUNA_CONCLUIDO, 2, agora),
        ]
        cursor.executemany(
            "INSERT INTO kanban_columns (id, nome, posicao, criado_em)"
            " VALUES (?, ?, ?, ?)",
            colunas_padrao,
        )

    conn.commit()
