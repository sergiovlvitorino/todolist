"""
Migrações e inicialização do esquema do banco de dados.

Implementa o motor de versionamento de schema baseado na tabela
``schema_version`` (ADR-005). As funções públicas ``get_schema_version`` e
``set_schema_version`` controlam a versão registrada no banco. A função
``initialize_database`` é o ponto de entrada idempotente: detecta se o banco
é novo (v0), já está na versão atual ou precisa de migrations.

Tabela de controle::

    CREATE TABLE IF NOT EXISTS schema_version (
        versao      INTEGER PRIMARY KEY,
        aplicada_em TEXT NOT NULL
    );

Banco novo (sem a tabela ``schema_version``) é tratado como versão 0.
Banco cuja versão máxima em ``schema_version`` é igual a ``SCHEMA_VERSION_ATUAL``
está atualizado — nenhuma migration é executada.

Nota sobre PRAGMA foreign_keys
-------------------------------
``PRAGMA foreign_keys = ON`` já está ativado em ``connection.py``
(``DatabaseConnection.get_connection``) para toda conexão aberta pela
aplicação. Conexões brutas usadas em testes devem ativá-lo manualmente se
precisarem de FK enforcement. O schema v2 (após migration v1→v2 via TASK-055)
ativa FK via ``REFERENCES kanban_columns(id) ON DELETE RESTRICT``; bancos novos
criados por esta função usam o schema v1 compatível e são registrados como v2
(sem necessidade de migração — banco novo já nasce limpo).
"""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from own_board_list.utils.constants import (
    COLUNA_A_FAZER,
    COLUNA_CONCLUIDO,
    COLUNA_EM_ANDAMENTO,
    SCHEMA_VERSION_ATUAL,
)

# ---------------------------------------------------------------------------
# Controle de versão do schema
# ---------------------------------------------------------------------------


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Retorna a versão atual do schema registrada no banco.

    Se a tabela ``schema_version`` não existir (banco novo ou pré-ADR-005),
    retorna 0.  Se existir mas estiver vazia, retorna 0 também.
    """
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
    )
    if cursor.fetchone() is None:
        return 0

    cursor = conn.execute("SELECT MAX(versao) FROM schema_version")
    row = cursor.fetchone()
    if row is None or row[0] is None:
        return 0
    return int(row[0])


def set_schema_version(conn: sqlite3.Connection, versao: int) -> None:
    """Registra uma versão de schema como aplicada, com timestamp UTC.

    Deve ser chamada dentro de uma transação ativa (``BEGIN IMMEDIATE``).
    Usa ``INSERT OR REPLACE`` para ser idempotente caso a versão já exista.
    """
    agora = datetime.now(tz=UTC).isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO schema_version (versao, aplicada_em) VALUES (?, ?)",
        (versao, agora),
    )


def _criar_tabela_schema_version(conn: sqlite3.Connection) -> None:
    """Cria a tabela de controle de versão se ainda não existir."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            versao      INTEGER PRIMARY KEY,
            aplicada_em TEXT NOT NULL
        )
    """)


# ---------------------------------------------------------------------------
# Dataclass Migration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Migration:
    """Representa um passo atômico de evolução do schema.

    Atributos:
        versao_destino: Número inteiro da versão após a aplicação desta migration.
        descricao: Texto legível descrevendo o que a migration faz.
        aplicar: Callable que recebe a conexão SQLite e executa as alterações
            necessárias. Deve operar dentro de uma transação já aberta pelo
            chamador (``MigrationService``).
    """

    versao_destino: int
    descricao: str
    aplicar: Callable[[sqlite3.Connection], None]


# ---------------------------------------------------------------------------
# Lista de migrations registradas (ordenadas por versao_destino crescente)
# ---------------------------------------------------------------------------

MIGRATIONS: list[Migration] = []  # populado abaixo após definição dos aplicadores


def _aplicar_v1_v2(conn: sqlite3.Connection) -> None:
    """Executa a migration v1 → v2.

    Importa localmente as funções de saneamento e recriação de tabelas que são
    definidas em módulos específicos (TASK-053, TASK-054, TASK-055) para evitar
    dependências circulares e manter cada task atômica.
    """
    import own_board_list.database._migration_v2 as _v2

    _v2.aplicar_migration_v1_v2(conn)


MIGRATIONS.append(
    Migration(
        versao_destino=2,
        descricao="Saneamento de dados legados + constraints CHECK/NOT NULL/FK",
        aplicar=_aplicar_v1_v2,
    )
)


# ---------------------------------------------------------------------------
# initialize_database — ponto de entrada idempotente
# ---------------------------------------------------------------------------


def initialize_database(conn: sqlite3.Connection) -> None:
    """Cria e/ou atualiza o schema do banco de dados de forma idempotente.

    Comportamento:
    - **Banco realmente novo (sem tabelas de dados):** cria ``schema_version``,
      ``kanban_columns`` e ``tasks`` com o schema compatível v1 (sem FK
      constraint — FK é adicionada pela migration v1→v2 em bancos de produção).
      Registra versão 2. Insere colunas padrão.
    - **Banco legado (tabelas existem, sem ``schema_version``):** detectado como
      v1. Aplica migrations pendentes (v1→v2 em sequência).
    - **Banco na versão atual:** não-op.
    - **Banco com versão inferior registrada:** aplica migrations pendentes.
      Em produção, o ``MigrationService`` garante backup e quarentena antes.
      Em testes isolados (banco ``:memory:``), aplica sem backup.

    [DECISÃO] Banco novo registrado como v2 sem FK REFERENCES
      Alternativas:
        A) Criar schema v2 completo (com FK REFERENCES) em banco novo.
        B) Criar schema v1 (compatível) e registrar como v2.
      Escolha: B — durante esta onda, o código de serviço ainda usa nomes de
      colunas (não IDs) em ``coluna_kanban``. A transição nome→ID faz parte do
      DT-013 e será concluída em tasks futuras. Banco novo em testes usa B para
      manter compatibilidade; banco de produção passa pela migration.

    [DECISÃO] Diferenciar banco legado de banco novo
      Um banco legado tem tabelas ``tasks``/``kanban_columns`` mas não tem a
      tabela ``schema_version``. A detecção é feita ANTES de criar
      ``schema_version``: se as tabelas de dados existem, o banco é legado (v1);
      caso contrário é novo (v0). Isso evita tratar legado como novo e pular
      a migration.
    """
    # Detectar se é banco legado (tabelas existem sem schema_version)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'"
    )
    tabelas_existem = cursor.fetchone() is not None

    _criar_tabela_schema_version(conn)
    versao_atual = get_schema_version(conn)

    if versao_atual == 0 and tabelas_existem:
        # Banco legado sem schema_version → tratar como v1 (pré-ADR-005).
        versao_atual = 1

    if versao_atual == 0:
        # Banco realmente novo — criar schema compatível e registrar como v_atual.
        _criar_schema_v1_compativel(conn)
        set_schema_version(conn, SCHEMA_VERSION_ATUAL)
        conn.commit()
        return

    if versao_atual == SCHEMA_VERSION_ATUAL:
        # Já atualizado — nada a fazer.
        return

    # versao_atual < SCHEMA_VERSION_ATUAL → aplicar migrations pendentes.
    for migration in MIGRATIONS:
        if migration.versao_destino > versao_atual:
            migration.aplicar(conn)
            set_schema_version(conn, migration.versao_destino)
            conn.commit()


# ---------------------------------------------------------------------------
# Criação do schema v1-compatível para bancos novos
# ---------------------------------------------------------------------------


def _criar_schema_v1_compativel(conn: sqlite3.Connection) -> None:
    """Cria tabelas e índices em schema compatível com o código atual.

    Usado para banco novo (``initialize_database`` com v=0). Não inclui
    FK ``REFERENCES`` para manter compatibilidade com o código de serviço
    que ainda usa nomes de colunas em ``coluna_kanban``. As constraints
    CHECK e NOT NULL são incluídas onde não causam incompatibilidade.
    """
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kanban_columns (
            id       TEXT PRIMARY KEY,
            nome     TEXT NOT NULL CHECK(length(trim(nome)) > 0),
            posicao  INTEGER NOT NULL DEFAULT 0 CHECK(posicao >= 0),
            criado_em TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id             TEXT PRIMARY KEY,
            titulo         TEXT NOT NULL CHECK(length(trim(titulo)) > 0),
            descricao      TEXT NOT NULL DEFAULT '',
            prioridade     TEXT NOT NULL DEFAULT 'Média'
                               CHECK(prioridade IN ('Baixa','Média','Alta')),
            data_vencimento TEXT,
            status         TEXT NOT NULL DEFAULT 'Pendente'
                               CHECK(status IN ('Pendente','Concluída')),
            coluna_kanban  TEXT NOT NULL,
            posicao_kanban INTEGER NOT NULL DEFAULT 0 CHECK(posicao_kanban >= 0),
            criado_em      TEXT NOT NULL,
            atualizado_em  TEXT NOT NULL
        )
    """)

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


# ---------------------------------------------------------------------------
# Validação pós-migration (TASK-056)
# ---------------------------------------------------------------------------


def validar_integridade_pos_migration(conn: sqlite3.Connection) -> None:
    """Executa PRAGMA integrity_check e foreign_key_check após a migration.

    Deve ser chamada com FK enforcement ativo (``PRAGMA foreign_keys = ON``).
    Levanta ``RuntimeError`` se qualquer inconsistência for detectada, para que
    o ``MigrationService`` possa fazer rollback e restaurar o backup.

    Args:
        conn: Conexão SQLite com FK ativa e fora de transação (PRAGMAs de
            verificação não funcionam dentro de transação ativa).

    Raises:
        RuntimeError: Se ``integrity_check`` retornar algo diferente de ``"ok"``
            ou se ``foreign_key_check`` retornar linhas.
    """
    # PRAGMA integrity_check retorna uma linha com "ok" se não há problemas.
    cursor = conn.execute("PRAGMA integrity_check")
    resultado = cursor.fetchone()
    if resultado is None or resultado[0] != "ok":
        falhas = [row[0] for row in conn.execute("PRAGMA integrity_check").fetchall()]
        raise RuntimeError(f"PRAGMA integrity_check falhou após migration: {falhas}")

    # PRAGMA foreign_key_check retorna linhas para cada violação de FK.
    cursor = conn.execute("PRAGMA foreign_key_check")
    violacoes = cursor.fetchall()
    if violacoes:
        detalhes = [
            f"tabela={row[0]} rowid={row[1]} fk_tabela={row[2]} fk_idx={row[3]}"
            for row in violacoes
        ]
        raise RuntimeError(
            f"PRAGMA foreign_key_check detectou violações após migration: {detalhes}"
        )
