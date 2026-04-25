"""
Saneamento de tarefas legadas na migration v1 → v2 (TASK-053).

Saneia os campos de ``tasks`` que podem violar as constraints v2:
- ``prioridade`` ausente ou fora do conjunto permitido → "Média"
- ``status`` ausente ou fora do conjunto permitido → "Pendente"
- ``coluna_kanban`` apontando para coluna inexistente → realocada para "A Fazer"
- ``criado_em`` ou ``atualizado_em`` ausentes → timestamp UTC da migration

Cada registro afetado é registrado na quarentena lateral antes do saneamento,
preservando o payload original para inspeção manual.

Deve ser chamado dentro de uma transação ``BEGIN IMMEDIATE`` já aberta pelo
``MigrationService``.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from own_board_list.database.quarantine import (
    RegistroQuarentena,
    registrar_em_quarentena,
)

_PRIORIDADES_VALIDAS = frozenset({"Baixa", "Média", "Alta"})
_STATUS_VALIDOS = frozenset({"Pendente", "Concluída"})


def sanear_tasks(conn: sqlite3.Connection) -> int:
    """Saneia dados inválidos na tabela ``tasks`` antes da recriação com constraints.

    Realiza os UPDATEs de saneamento e registra cada linha afetada na
    quarentena lateral. Deve ser chamado dentro de uma transação ativa.

    Returns:
        Número total de registros saneados (linhas afetadas em todos os UPDATEs).
    """
    agora = datetime.now(tz=UTC).isoformat()
    data_migracao = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    obs_data = f"data desconhecida (migrado em {data_migracao})"
    total_saneados = 0

    # ------------------------------------------------------------------
    # 1. Saneamento de prioridade
    # ------------------------------------------------------------------
    total_saneados += _sanear_prioridade(conn, agora)

    # ------------------------------------------------------------------
    # 2. Saneamento de status
    # ------------------------------------------------------------------
    total_saneados += _sanear_status(conn, agora)

    # ------------------------------------------------------------------
    # 3. Saneamento de coluna_kanban (coluna inexistente)
    # ------------------------------------------------------------------
    total_saneados += _sanear_coluna_kanban(conn, agora)

    # ------------------------------------------------------------------
    # 4. Saneamento de datas ausentes
    # ------------------------------------------------------------------
    total_saneados += _sanear_datas(conn, agora, obs_data)

    return total_saneados


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Converte sqlite3.Row em dict para serialização na quarentena."""
    return dict(zip(row.keys(), tuple(row), strict=False))


def _sanear_prioridade(conn: sqlite3.Connection, agora: str) -> int:
    """Saneia prioridades ausentes ou inválidas → 'Média'."""
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM tasks WHERE prioridade IS NULL OR prioridade NOT IN (?, ?, ?)",
        ("Baixa", "Média", "Alta"),
    )
    rows = cursor.fetchall()

    for row in rows:
        registrar_em_quarentena(
            RegistroQuarentena(
                tabela="tasks",
                id_original=row["id"],
                motivo="prioridade_invalida",
                payload_original=_row_to_dict(row),
                saneamento_aplicado={"prioridade": "Média"},
            )
        )

    if rows:
        conn.execute(
            "UPDATE tasks SET prioridade = 'Média'"
            " WHERE prioridade IS NULL OR prioridade NOT IN ('Baixa','Média','Alta')"
        )

    return len(rows)


def _sanear_status(conn: sqlite3.Connection, agora: str) -> int:
    """Saneia status ausentes ou inválidos → 'Pendente'."""
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM tasks WHERE status IS NULL OR status NOT IN (?, ?)",
        ("Pendente", "Concluída"),
    )
    rows = cursor.fetchall()

    for row in rows:
        registrar_em_quarentena(
            RegistroQuarentena(
                tabela="tasks",
                id_original=row["id"],
                motivo="status_invalido",
                payload_original=_row_to_dict(row),
                saneamento_aplicado={"status": "Pendente"},
            )
        )

    if rows:
        conn.execute(
            "UPDATE tasks SET status = 'Pendente'"
            " WHERE status IS NULL OR status NOT IN ('Pendente','Concluída')"
        )

    return len(rows)


def _sanear_coluna_kanban(conn: sqlite3.Connection, agora: str) -> int:
    """Realoca tarefas cujo coluna_kanban não existe em kanban_columns."""
    conn.row_factory = sqlite3.Row

    # Encontrar o id da coluna "A Fazer" (coluna padrão de realocação)
    cursor = conn.execute(
        "SELECT id FROM kanban_columns WHERE nome = 'A Fazer' LIMIT 1"
    )
    row_a_fazer = cursor.fetchone()
    if row_a_fazer is None:
        # Coluna "A Fazer" não existe — não é possível realocar.
        # Isso não deveria ocorrer em banco legado válido; logar e seguir.
        return 0

    id_a_fazer: str = row_a_fazer["id"]

    # Tarefas cujo coluna_kanban não aparece em kanban_columns.id
    cursor = conn.execute("""
        SELECT t.* FROM tasks t
        WHERE t.coluna_kanban NOT IN (SELECT id FROM kanban_columns)
    """)
    rows = cursor.fetchall()

    for row in rows:
        registrar_em_quarentena(
            RegistroQuarentena(
                tabela="tasks",
                id_original=row["id"],
                motivo="coluna_inexistente",
                payload_original=_row_to_dict(row),
                saneamento_aplicado={"coluna_kanban": id_a_fazer},
            )
        )

    if rows:
        conn.execute(
            "UPDATE tasks SET coluna_kanban = ?"
            " WHERE coluna_kanban NOT IN (SELECT id FROM kanban_columns)",
            (id_a_fazer,),
        )

    return len(rows)


def _sanear_datas(conn: sqlite3.Connection, agora: str, obs: str) -> int:
    """Preenche criado_em/atualizado_em ausentes com timestamp UTC da migration."""
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM tasks WHERE criado_em IS NULL OR atualizado_em IS NULL"
    )
    rows = cursor.fetchall()

    for row in rows:
        registrar_em_quarentena(
            RegistroQuarentena(
                tabela="tasks",
                id_original=row["id"],
                motivo="data_ausente",
                payload_original=_row_to_dict(row),
                saneamento_aplicado={
                    "criado_em": agora,
                    "atualizado_em": agora,
                    "observacao": obs,
                },
            )
        )

    if rows:
        conn.execute(
            "UPDATE tasks"
            " SET criado_em = COALESCE(criado_em, ?),"
            "     atualizado_em = COALESCE(atualizado_em, ?)"
            " WHERE criado_em IS NULL OR atualizado_em IS NULL",
            (agora, agora),
        )

    return len(rows)
