"""TC-102 e TC-103 — Constraints SQL diretas e PRAGMA foreign_key_check.

Testa o schema v2 real (resultante da migration v1→v2 via ``initialize_database``
sobre um banco legado) via INSERTs crus, verificando:

- TC-102a: NOT NULL violado em ``titulo``, ``status``, ``prioridade``,
  ``criado_em``, ``atualizado_em`` (tasks) e ``nome``, ``criado_em`` (kanban_columns)
- TC-102b: CHECK violado em ``status`` (valor fora do enum)
- TC-102c: CHECK violado em ``prioridade`` (valor fora do enum)
- TC-102d: CHECK violado em ``posicao_kanban`` (negativo)
- TC-102e: CHECK violado em ``length(trim(titulo)) > 0`` (titulo = espaços)
- TC-102f: FK violada — ``coluna_kanban`` aponta para ID inexistente
- TC-103: ``PRAGMA foreign_key_check`` retorna resultado vazio após banco
  inicializado corretamente em todos os cenários acima

Relação com TC-108 (``tests/test_models/test_domain_schema_consistency.py``):
TC-108 usa DDL inline idêntico ao schema v2 para validar defesa em profundidade
domínio × schema. TC-102/TC-103 complementam TC-108 ao usar o schema produzido
pela migration real (``initialize_database`` sobre banco legado v1), garantindo
que a migration efetivamente aplica as constraints e que o ``PRAGMA
foreign_key_check`` retorna limpo após cada cenário.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime

import pytest

from own_board_list.database.migrations import initialize_database

# ---------------------------------------------------------------------------
# Constantes de teste
# ---------------------------------------------------------------------------

_TS = datetime.now(tz=UTC).isoformat()

_SQL_KANBAN_V1 = """
    CREATE TABLE IF NOT EXISTS kanban_columns (
        id        TEXT PRIMARY KEY,
        nome      TEXT,
        posicao   INTEGER DEFAULT 0,
        criado_em TEXT
    )
"""

_SQL_TASKS_V1 = """
    CREATE TABLE IF NOT EXISTS tasks (
        id              TEXT PRIMARY KEY,
        titulo          TEXT,
        descricao       TEXT DEFAULT '',
        prioridade      TEXT,
        data_vencimento TEXT,
        status          TEXT,
        coluna_kanban   TEXT,
        posicao_kanban  INTEGER DEFAULT 0,
        criado_em       TEXT,
        atualizado_em   TEXT
    )
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn_v2_via_migration() -> sqlite3.Connection:
    """Banco em memória migrado de v1 → v2 via ``initialize_database``.

    Cria um banco legado (schema v1 sem constraints, com dados válidos),
    então executa ``initialize_database`` para realizar a migration v1→v2.
    O resultado é o schema v2 com CHECK/NOT NULL/FK reais — idêntico ao
    schema de produção pós-migration.

    A coluna padrão "A Fazer" é inserida no banco legado para que a migration
    não precise alocar tarefa fantasma. Ao final, ativa ``PRAGMA foreign_keys=ON``
    explicitamente (necessário para FK enforcement em conexão bruta).
    """
    conn = sqlite3.connect(":memory:")

    # Criar schema v1 sem constraints
    conn.execute(_SQL_KANBAN_V1)
    conn.execute(_SQL_TASKS_V1)

    # Inserir coluna padrão "A Fazer" — necessária para FK de tasks
    col_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO kanban_columns (id, nome, posicao, criado_em) VALUES (?,?,?,?)",
        (col_id, "A Fazer", 0, _TS),
    )
    conn.commit()

    # Executar migration v1→v2 (schema_version não existe → detectado como legado v1)
    initialize_database(conn)

    # Ativar FK enforcement (obrigatório por conexão no SQLite)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()

    return conn


@pytest.fixture()
def col_id_valido(conn_v2_via_migration: sqlite3.Connection) -> str:
    """Retorna o ID da primeira coluna existente no banco migrado."""
    cursor = conn_v2_via_migration.execute("SELECT id FROM kanban_columns LIMIT 1")
    row = cursor.fetchone()
    assert row is not None, "Banco migrado deve conter ao menos uma coluna"
    return str(row[0])


def _nova_task_row(
    col_id: str,
    row_id: str | None = None,
    titulo: str | None = "Tarefa Válida",
    descricao: str = "",
    prioridade: str | None = "Média",
    status: str | None = "Pendente",
    posicao_kanban: int = 0,
) -> tuple[str | int | None, ...]:
    """Monta uma linha completa para INSERT em tasks no schema v2.

    Nota: campos ``criado_em`` e ``atualizado_em`` são sempre preenchidos
    com ``_TS`` nesta função auxiliar. Para testar NOT NULL explicitamente
    nesses campos, use ``_nova_task_row_com_datas`` que aceita None diretamente.
    """
    return (
        row_id or str(uuid.uuid4()),
        titulo,
        descricao,
        prioridade,
        None,
        status,
        col_id,
        posicao_kanban,
        _TS,
        _TS,
    )


def _nova_task_row_com_datas(
    col_id: str,
    criado_em: str | None,
    atualizado_em: str | None,
    row_id: str | None = None,
    titulo: str = "Tarefa Válida",
    prioridade: str = "Média",
    status: str = "Pendente",
) -> tuple[str | int | None, ...]:
    """Variante de _nova_task_row que aceita criado_em/atualizado_em como None.

    Usada especificamente para testar NOT NULL constraint dessas colunas.
    """
    return (
        row_id or str(uuid.uuid4()),
        titulo,
        "",
        prioridade,
        None,
        status,
        col_id,
        0,
        criado_em,
        atualizado_em,
    )


_INSERT_TASK = (
    "INSERT INTO tasks "
    "(id, titulo, descricao, prioridade, data_vencimento, status, "
    "coluna_kanban, posicao_kanban, criado_em, atualizado_em) "
    "VALUES (?,?,?,?,?,?,?,?,?,?)"
)

_INSERT_COL = (
    "INSERT INTO kanban_columns (id, nome, posicao, criado_em) VALUES (?,?,?,?)"
)


# ---------------------------------------------------------------------------
# TC-102a — NOT NULL em tasks
# ---------------------------------------------------------------------------


class TestNotNullTasks:
    """TC-102a: campos NOT NULL de tasks rejeitam NULL via INSERT cru."""

    def test_titulo_null_levanta_integrity_error(
        self, conn_v2_via_migration: sqlite3.Connection, col_id_valido: str
    ) -> None:
        """titulo=NULL deve violar NOT NULL constraint."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2_via_migration.execute(
                _INSERT_TASK,
                _nova_task_row(col_id_valido, titulo=None),
            )

    def test_prioridade_null_levanta_integrity_error(
        self, conn_v2_via_migration: sqlite3.Connection, col_id_valido: str
    ) -> None:
        """prioridade=NULL deve violar NOT NULL constraint."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2_via_migration.execute(
                _INSERT_TASK,
                _nova_task_row(col_id_valido, prioridade=None),
            )

    def test_status_null_levanta_integrity_error(
        self, conn_v2_via_migration: sqlite3.Connection, col_id_valido: str
    ) -> None:
        """status=NULL deve violar NOT NULL constraint."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2_via_migration.execute(
                _INSERT_TASK,
                _nova_task_row(col_id_valido, status=None),
            )

    def test_criado_em_null_levanta_integrity_error(
        self, conn_v2_via_migration: sqlite3.Connection, col_id_valido: str
    ) -> None:
        """criado_em=NULL deve violar NOT NULL constraint."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2_via_migration.execute(
                _INSERT_TASK,
                _nova_task_row_com_datas(
                    col_id_valido, criado_em=None, atualizado_em=_TS
                ),
            )

    def test_atualizado_em_null_levanta_integrity_error(
        self, conn_v2_via_migration: sqlite3.Connection, col_id_valido: str
    ) -> None:
        """atualizado_em=NULL deve violar NOT NULL constraint."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2_via_migration.execute(
                _INSERT_TASK,
                _nova_task_row_com_datas(
                    col_id_valido, criado_em=_TS, atualizado_em=None
                ),
            )


# ---------------------------------------------------------------------------
# TC-102a — NOT NULL em kanban_columns
# ---------------------------------------------------------------------------


class TestNotNullKanbanColumns:
    """TC-102a: campos NOT NULL de kanban_columns rejeitam NULL via INSERT cru."""

    def test_nome_null_levanta_integrity_error(
        self, conn_v2_via_migration: sqlite3.Connection
    ) -> None:
        """nome=NULL deve violar NOT NULL constraint em kanban_columns."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2_via_migration.execute(
                _INSERT_COL,
                (str(uuid.uuid4()), None, 0, _TS),
            )

    def test_criado_em_null_levanta_integrity_error(
        self, conn_v2_via_migration: sqlite3.Connection
    ) -> None:
        """criado_em=NULL deve violar NOT NULL constraint em kanban_columns."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2_via_migration.execute(
                _INSERT_COL,
                (str(uuid.uuid4()), "Nova Coluna", 0, None),
            )


# ---------------------------------------------------------------------------
# TC-102b — CHECK status (enum)
# ---------------------------------------------------------------------------


class TestCheckStatusEnum:
    """TC-102b: status fora do conjunto permitido é rejeitado pelo schema v2."""

    @pytest.mark.parametrize(
        "status_invalido",
        ["Arquivada", "Em Andamento", "em_andamento", "pendente", "", "null"],
    )
    def test_status_invalido_levanta_integrity_error(
        self,
        conn_v2_via_migration: sqlite3.Connection,
        col_id_valido: str,
        status_invalido: str,
    ) -> None:
        """Status fora de {'Pendente','Concluída'} deve violar CHECK."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2_via_migration.execute(
                _INSERT_TASK,
                _nova_task_row(col_id_valido, status=status_invalido),
            )

    def test_status_pendente_aceito(
        self, conn_v2_via_migration: sqlite3.Connection, col_id_valido: str
    ) -> None:
        """Status 'Pendente' deve ser aceito (smoke positivo)."""
        conn_v2_via_migration.execute(
            _INSERT_TASK,
            _nova_task_row(col_id_valido, status="Pendente"),
        )
        conn_v2_via_migration.commit()

    def test_status_concluida_aceito(
        self, conn_v2_via_migration: sqlite3.Connection, col_id_valido: str
    ) -> None:
        """Status 'Concluída' deve ser aceito (smoke positivo)."""
        conn_v2_via_migration.execute(
            _INSERT_TASK,
            _nova_task_row(col_id_valido, status="Concluída"),
        )
        conn_v2_via_migration.commit()


# ---------------------------------------------------------------------------
# TC-102c — CHECK prioridade (enum)
# ---------------------------------------------------------------------------


class TestCheckPrioridadeEnum:
    """TC-102c: prioridade fora do conjunto permitido é rejeitada pelo schema v2."""

    @pytest.mark.parametrize(
        "prioridade_invalida",
        ["Urgente", "Crítica", "baixa", "ALTA", "", "nenhuma"],
    )
    def test_prioridade_invalida_levanta_integrity_error(
        self,
        conn_v2_via_migration: sqlite3.Connection,
        col_id_valido: str,
        prioridade_invalida: str,
    ) -> None:
        """Prioridade fora de {'Baixa','Média','Alta'} deve violar CHECK."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2_via_migration.execute(
                _INSERT_TASK,
                _nova_task_row(col_id_valido, prioridade=prioridade_invalida),
            )

    @pytest.mark.parametrize("prioridade_valida", ["Baixa", "Média", "Alta"])
    def test_prioridade_valida_aceita(
        self,
        conn_v2_via_migration: sqlite3.Connection,
        col_id_valido: str,
        prioridade_valida: str,
    ) -> None:
        """Prioridades do enum devem ser aceitas (smoke positivo)."""
        conn_v2_via_migration.execute(
            _INSERT_TASK,
            _nova_task_row(col_id_valido, prioridade=prioridade_valida),
        )
        conn_v2_via_migration.commit()


# ---------------------------------------------------------------------------
# TC-102d — CHECK posicao_kanban >= 0
# ---------------------------------------------------------------------------


class TestCheckPosicaoKanban:
    """TC-102d: posicao_kanban negativo é rejeitado pelo schema v2."""

    def test_posicao_negativa_levanta_integrity_error(
        self, conn_v2_via_migration: sqlite3.Connection, col_id_valido: str
    ) -> None:
        """posicao_kanban < 0 deve violar CHECK(posicao_kanban >= 0)."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2_via_migration.execute(
                _INSERT_TASK,
                _nova_task_row(col_id_valido, posicao_kanban=-1),
            )

    def test_posicao_zero_aceita(
        self, conn_v2_via_migration: sqlite3.Connection, col_id_valido: str
    ) -> None:
        """posicao_kanban=0 deve ser aceito (valor mínimo válido)."""
        conn_v2_via_migration.execute(
            _INSERT_TASK,
            _nova_task_row(col_id_valido, posicao_kanban=0),
        )
        conn_v2_via_migration.commit()

    def test_posicao_coluna_negativa_levanta_integrity_error(
        self, conn_v2_via_migration: sqlite3.Connection
    ) -> None:
        """posicao < 0 em kanban_columns deve violar CHECK(posicao >= 0)."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2_via_migration.execute(
                _INSERT_COL,
                (str(uuid.uuid4()), "Coluna Inválida", -1, _TS),
            )


# ---------------------------------------------------------------------------
# TC-102e — CHECK length(trim(titulo)) > 0
# ---------------------------------------------------------------------------


class TestCheckTituloNaoVazio:
    """TC-102e: titulo vazio ou apenas espaços é rejeitado pelo schema v2."""

    def test_titulo_vazio_levanta_integrity_error(
        self, conn_v2_via_migration: sqlite3.Connection, col_id_valido: str
    ) -> None:
        """titulo='' deve violar CHECK(length(trim(titulo)) > 0)."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2_via_migration.execute(
                _INSERT_TASK,
                _nova_task_row(col_id_valido, titulo=""),
            )

    def test_titulo_so_espacos_levanta_integrity_error(
        self, conn_v2_via_migration: sqlite3.Connection, col_id_valido: str
    ) -> None:
        """titulo com apenas espaços deve violar CHECK(length(trim(titulo)) > 0)."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2_via_migration.execute(
                _INSERT_TASK,
                _nova_task_row(col_id_valido, titulo="   "),
            )

    def test_titulo_valido_aceito(
        self, conn_v2_via_migration: sqlite3.Connection, col_id_valido: str
    ) -> None:
        """titulo não-vazio deve ser aceito."""
        conn_v2_via_migration.execute(
            _INSERT_TASK,
            _nova_task_row(col_id_valido, titulo="Título com conteúdo"),
        )
        conn_v2_via_migration.commit()


# ---------------------------------------------------------------------------
# TC-102f — FK violation: coluna_kanban inexistente
# ---------------------------------------------------------------------------


class TestForeignKeyViolation:
    """TC-102f: task apontando para coluna inexistente é rejeitada pela FK."""

    def test_coluna_inexistente_levanta_integrity_error(
        self, conn_v2_via_migration: sqlite3.Connection
    ) -> None:
        """coluna_kanban com ID que não existe em kanban_columns deve violar FK."""
        id_fantasma = "coluna-que-nao-existe-" + str(uuid.uuid4())
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2_via_migration.execute(
                _INSERT_TASK,
                _nova_task_row(id_fantasma),
            )

    def test_task_valida_com_coluna_existente_aceita(
        self, conn_v2_via_migration: sqlite3.Connection, col_id_valido: str
    ) -> None:
        """task completamente válida com coluna existente deve ser aceita."""
        conn_v2_via_migration.execute(
            _INSERT_TASK,
            _nova_task_row(col_id_valido, titulo="Task válida completa"),
        )
        conn_v2_via_migration.commit()
        cursor = conn_v2_via_migration.execute(
            "SELECT titulo FROM tasks WHERE titulo='Task válida completa'"
        )
        assert cursor.fetchone() is not None


# ---------------------------------------------------------------------------
# TC-103 — PRAGMA foreign_key_check retorna vazio
# ---------------------------------------------------------------------------


class TestPragmaForeignKeyCheck:
    """TC-103: ``PRAGMA foreign_key_check`` retorna resultado vazio após banco v2.

    Garante que após a migration v1→v2, o banco não contém nenhuma violação
    de FK — seja no schema inicial, após inserts válidos, ou após rollback de
    inserts inválidos.
    """

    def test_foreign_key_check_limpo_em_banco_recém_migrado(
        self, conn_v2_via_migration: sqlite3.Connection
    ) -> None:
        """Banco recém-migrado sem dados extras deve ter foreign_key_check limpo."""
        cursor = conn_v2_via_migration.execute("PRAGMA foreign_key_check")
        violacoes = cursor.fetchall()
        assert violacoes == [], (
            f"PRAGMA foreign_key_check deve retornar vazio, mas retornou: {violacoes}"
        )

    def test_foreign_key_check_limpo_após_insert_válido(
        self, conn_v2_via_migration: sqlite3.Connection, col_id_valido: str
    ) -> None:
        """Após insert de task válida, foreign_key_check deve permanecer limpo."""
        conn_v2_via_migration.execute(
            _INSERT_TASK,
            _nova_task_row(col_id_valido, titulo="Task para FK check"),
        )
        conn_v2_via_migration.commit()

        cursor = conn_v2_via_migration.execute("PRAGMA foreign_key_check")
        violacoes = cursor.fetchall()
        assert violacoes == [], (
            f"Após insert válido, foreign_key_check deve retornar vazio: {violacoes}"
        )

    def test_foreign_key_check_limpo_após_tentativa_de_violação_rejeitada(
        self, conn_v2_via_migration: sqlite3.Connection
    ) -> None:
        """Após tentativa rejeitada de FK violation, banco deve permanecer íntegro."""
        id_fantasma = "id-fantasma-" + str(uuid.uuid4())

        # Tentativa de insert inválido — deve ser rejeitada
        try:
            conn_v2_via_migration.execute(
                _INSERT_TASK,
                _nova_task_row(id_fantasma),
            )
        except sqlite3.IntegrityError:
            pass  # esperado — FK violation rejeitada corretamente

        # Banco deve permanecer íntegro
        cursor = conn_v2_via_migration.execute("PRAGMA foreign_key_check")
        violacoes = cursor.fetchall()
        assert violacoes == [], (
            "Após tentativa rejeitada, foreign_key_check deve retornar vazio: "
            f"{violacoes}"
        )

    def test_foreign_key_check_tabela_tasks_especifica(
        self, conn_v2_via_migration: sqlite3.Connection, col_id_valido: str
    ) -> None:
        """``PRAGMA foreign_key_check(tasks)`` deve retornar vazio com dados válidos."""
        conn_v2_via_migration.execute(
            _INSERT_TASK,
            _nova_task_row(col_id_valido, titulo="Task para FK check específico"),
        )
        conn_v2_via_migration.commit()

        cursor = conn_v2_via_migration.execute("PRAGMA foreign_key_check(tasks)")
        violacoes = cursor.fetchall()
        assert violacoes == [], (
            f"PRAGMA foreign_key_check(tasks) deve retornar vazio: {violacoes}"
        )

    def test_foreign_key_check_detecta_violação_injetada_manualmente(
        self, conn_v2_via_migration: sqlite3.Connection
    ) -> None:
        """Confirma que o PRAGMA detecta FK violations quando FK enforcement está OFF.

        Injeta uma task órfã via FK OFF, reativa FK ON, e verifica que
        ``foreign_key_check`` reporta a violação — provando que o PRAGMA
        funciona como detector.
        """
        # Desativar temporariamente para injetar dado inválido
        conn_v2_via_migration.execute("PRAGMA foreign_keys = OFF")

        id_orfao = str(uuid.uuid4())
        id_coluna_fantasma = "coluna-fantasma-" + str(uuid.uuid4())

        conn_v2_via_migration.execute(
            _INSERT_TASK,
            _nova_task_row(
                id_coluna_fantasma,
                row_id=id_orfao,
                titulo="Task órfã",
            ),
        )
        conn_v2_via_migration.commit()

        # Reativar FK e verificar que violação é detectada
        conn_v2_via_migration.execute("PRAGMA foreign_keys = ON")

        cursor = conn_v2_via_migration.execute("PRAGMA foreign_key_check")
        violacoes = cursor.fetchall()
        assert len(violacoes) >= 1, (
            "PRAGMA foreign_key_check deve detectar a task órfã injetada manualmente"
        )
