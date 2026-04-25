"""
Saneamento de colunas Kanban legadas na migration v1 → v2 (TASK-054).

Saneia os campos de ``kanban_columns`` que podem violar as constraints v2:
- ``criado_em`` ausente → timestamp UTC da migration (com observação no log)
- ``nome`` vazio ou nulo → constraint será rejeitada na recriação (não saneia)
- ``posicao`` nula → default 0 (aplicado na recriação pelo DEFAULT)

Cada registro afetado é registrado na quarentena lateral antes do saneamento.

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


def sanear_kanban_columns(conn: sqlite3.Connection) -> int:
    """Saneia dados inválidos na tabela ``kanban_columns`` antes da recriação.

    Realiza UPDATE para preencher ``criado_em`` ausente com o timestamp UTC
    atual da migration. Registra cada linha afetada na quarentena lateral.

    Deve ser chamado dentro de uma transação ativa.

    Returns:
        Número de registros saneados.
    """
    agora = datetime.now(tz=UTC).isoformat()
    data_migracao = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    obs = f"data desconhecida (migrado em {data_migracao})"
    total_saneados = 0

    total_saneados += _sanear_criado_em(conn, agora, obs)

    return total_saneados


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Converte sqlite3.Row em dict para serialização na quarentena."""
    return dict(zip(row.keys(), tuple(row), strict=False))


def _sanear_criado_em(conn: sqlite3.Connection, agora: str, obs: str) -> int:
    """Preenche criado_em ausente em kanban_columns com timestamp UTC da migration."""
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM kanban_columns WHERE criado_em IS NULL")
    rows = cursor.fetchall()

    for row in rows:
        registrar_em_quarentena(
            RegistroQuarentena(
                tabela="kanban_columns",
                id_original=row["id"],
                motivo="data_ausente",
                payload_original=_row_to_dict(row),
                saneamento_aplicado={
                    "criado_em": agora,
                    "observacao": obs,
                },
            )
        )

    if rows:
        conn.execute(
            "UPDATE kanban_columns SET criado_em = ? WHERE criado_em IS NULL",
            (agora,),
        )

    return len(rows)
