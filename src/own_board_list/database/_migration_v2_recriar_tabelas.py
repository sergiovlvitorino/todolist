"""
Recriação das tabelas com constraints CHECK/NOT NULL/FK na migration v1 → v2.

Implementado em TASK-055. Este stub é substituído pela implementação real.
"""

from __future__ import annotations

import sqlite3


def recriar_tabelas_v2(conn: sqlite3.Connection) -> None:
    """Recria ``tasks`` e ``kanban_columns`` com constraints v2.

    Padrão SQLite: CREATE TABLE *_new → INSERT INTO *_new SELECT ... →
    DROP TABLE → RENAME TABLE.

    Implementado em TASK-055.
    """
    # Stub — implementação em TASK-055
    pass
