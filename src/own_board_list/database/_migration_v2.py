"""
Migration v1 → v2: saneamento de dados legados e recriação de tabelas
com constraints CHECK/NOT NULL/FOREIGN KEY.

Este módulo é importado por ``database/migrations.py`` apenas quando a
migration v1→v2 precisa ser executada. A separação em módulo próprio mantém
``migrations.py`` focado no motor de controle.

Implementado em:
- TASK-053: saneamento de ``tasks`` (prioridade, status, coluna_kanban, datas)
- TASK-054: saneamento de ``kanban_columns`` (criado_em ausente)
- TASK-055: recriação das tabelas com constraints; troca e reindexação
"""

from __future__ import annotations

import sqlite3


def aplicar_migration_v1_v2(conn: sqlite3.Connection) -> None:
    """Executa todos os passos da migration v1 → v2.

    Deve ser chamada dentro de uma transação ``BEGIN IMMEDIATE`` já aberta
    pelo ``MigrationService``. Qualquer exceção propaga para o chamador que
    fará o ROLLBACK.

    Passos (implementados em TASK-053, TASK-054, TASK-055):
    1. Sanear dados inválidos em ``tasks`` (prioridade, status, coluna_kanban, datas).
    2. Sanear dados inválidos em ``kanban_columns`` (criado_em ausente).
    3. Recriar tabelas com constraints; copiar dados saneados; trocar e reindexar.
    """
    import own_board_list.database._migration_v2_recriar_tabelas as _rt
    import own_board_list.database._migration_v2_sanear_columns as _sc
    import own_board_list.database._migration_v2_sanear_tasks as _st

    _st.sanear_tasks(conn)
    _sc.sanear_kanban_columns(conn)
    _rt.recriar_tabelas_v2(conn)
