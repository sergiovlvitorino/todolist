"""
Recriação das tabelas com constraints CHECK/NOT NULL/FK na migration v1 → v2
(TASK-055).

SQLite não suporta ALTER TABLE ADD CONSTRAINT. O padrão idiomático é:
1. Criar tabela nova com o schema desejado (``*_new``).
2. Copiar dados da tabela original com ``INSERT INTO *_new SELECT ...``.
3. Apagar a tabela original com ``DROP TABLE``.
4. Renomear ``*_new`` para o nome original com ``ALTER TABLE ... RENAME TO``.
5. Recriar índices.

Deve ser chamado APÓS os saneamentos (TASK-053 e TASK-054), dentro de uma
transação ``BEGIN IMMEDIATE`` já aberta pelo ``MigrationService``.

Schema v2:
- ``kanban_columns``: ``nome`` NOT NULL CHECK(trim > 0), ``posicao`` NOT NULL
  CHECK(>= 0), ``criado_em`` NOT NULL.
- ``tasks``: ``titulo`` NOT NULL CHECK(trim > 0), ``prioridade`` NOT NULL
  CHECK(∈ {'Baixa','Média','Alta'}), ``status`` NOT NULL CHECK(∈
  {'Pendente','Concluída'}), ``coluna_kanban`` NOT NULL REFERENCES
  kanban_columns(id) ON DELETE RESTRICT, ``posicao_kanban`` NOT NULL
  CHECK(>= 0), ``criado_em`` NOT NULL, ``atualizado_em`` NOT NULL.
"""

from __future__ import annotations

import sqlite3


def recriar_tabelas_v2(conn: sqlite3.Connection) -> None:
    """Recria ``kanban_columns`` e ``tasks`` com o schema v2.

    Ordem: kanban_columns primeiro (tasks referencia kanban_columns via FK).

    Deve ser chamado dentro de uma transação ativa.

    Raises:
        sqlite3.IntegrityError: Se os dados não satisfazem as constraints v2
            após o saneamento (indica saneamento incompleto ou dado irrecuperável).
    """
    _recriar_kanban_columns(conn)
    _recriar_tasks(conn)
    _recriar_indices(conn)


def _recriar_kanban_columns(conn: sqlite3.Connection) -> None:
    """Recria ``kanban_columns`` com NOT NULL e CHECK constraints."""
    conn.execute("""
        CREATE TABLE kanban_columns_new (
            id        TEXT PRIMARY KEY,
            nome      TEXT NOT NULL CHECK(length(trim(nome)) > 0),
            posicao   INTEGER NOT NULL DEFAULT 0 CHECK(posicao >= 0),
            criado_em TEXT NOT NULL
        )
    """)

    conn.execute("""
        INSERT INTO kanban_columns_new (id, nome, posicao, criado_em)
        SELECT
            id,
            nome,
            COALESCE(posicao, 0),
            criado_em
        FROM kanban_columns
    """)

    conn.execute("DROP TABLE kanban_columns")
    conn.execute("ALTER TABLE kanban_columns_new RENAME TO kanban_columns")


def _recriar_tasks(conn: sqlite3.Connection) -> None:
    """Recria ``tasks`` com NOT NULL, CHECK e FK REFERENCES constraints."""
    conn.execute("""
        CREATE TABLE tasks_new (
            id              TEXT PRIMARY KEY,
            titulo          TEXT NOT NULL CHECK(length(trim(titulo)) > 0),
            descricao       TEXT NOT NULL DEFAULT '',
            prioridade      TEXT NOT NULL CHECK(prioridade IN ('Baixa','Média','Alta')),
            data_vencimento TEXT,
            status          TEXT NOT NULL CHECK(status IN ('Pendente','Concluída')),
            coluna_kanban   TEXT NOT NULL
                                REFERENCES kanban_columns(id) ON DELETE RESTRICT,
            posicao_kanban  INTEGER NOT NULL DEFAULT 0 CHECK(posicao_kanban >= 0),
            criado_em       TEXT NOT NULL,
            atualizado_em   TEXT NOT NULL
        )
    """)

    conn.execute("""
        INSERT INTO tasks_new (
            id, titulo, descricao, prioridade, data_vencimento,
            status, coluna_kanban, posicao_kanban, criado_em, atualizado_em
        )
        SELECT
            id,
            titulo,
            COALESCE(descricao, ''),
            prioridade,
            data_vencimento,
            status,
            coluna_kanban,
            COALESCE(posicao_kanban, 0),
            criado_em,
            atualizado_em
        FROM tasks
    """)

    conn.execute("DROP TABLE tasks")
    conn.execute("ALTER TABLE tasks_new RENAME TO tasks")


def _recriar_indices(conn: sqlite3.Connection) -> None:
    """Recria os índices da tabela ``tasks`` após a troca de tabelas."""
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_coluna_kanban
        ON tasks (coluna_kanban)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_status
        ON tasks (status)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_prioridade
        ON tasks (prioridade)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_data_vencimento
        ON tasks (data_vencimento)
    """)
