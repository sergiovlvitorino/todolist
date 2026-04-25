"""TC-108 — Defesa em profundidade: domínio×schema.

Garante que as validações do domínio (Task.__post_init__ e
KanbanColumn.__post_init__) e as constraints SQL do schema (v2, TASK-055)
rejeitam exatamente o mesmo conjunto de estados inválidos.

Estrutura dos testes:
1. Validação de domínio puro (sem banco) — ValueError levantado no domínio.
2. Validação via schema SQL direto (INSERT cru em banco :memory:) —
   sqlite3.IntegrityError levantado pelo banco.

Isso confirma que a defesa em profundidade está ativa: nenhuma violação
passa silenciosamente por nenhuma das duas camadas.
"""

from __future__ import annotations

import sqlite3

import pytest

from own_board_list.models.enums import Prioridade, StatusTarefa
from own_board_list.models.kanban_column import KanbanColumn
from own_board_list.models.task import Task

# ---------------------------------------------------------------------------
# Fixture: banco em memória com schema v2
# ---------------------------------------------------------------------------

_SQL_KANBAN_COLUMNS = """
    CREATE TABLE kanban_columns (
        id        TEXT PRIMARY KEY,
        nome      TEXT NOT NULL CHECK(length(trim(nome)) > 0),
        posicao   INTEGER NOT NULL DEFAULT 0 CHECK(posicao >= 0),
        criado_em TEXT NOT NULL
    )
"""

_SQL_TASKS = """
    CREATE TABLE tasks (
        id              TEXT PRIMARY KEY,
        titulo          TEXT NOT NULL CHECK(length(trim(titulo)) > 0),
        descricao       TEXT NOT NULL DEFAULT '',
        prioridade      TEXT NOT NULL
            CHECK(prioridade IN ('Baixa','Média','Alta')),
        data_vencimento TEXT,
        status          TEXT NOT NULL
            CHECK(status IN ('Pendente','Concluída')),
        coluna_kanban   TEXT NOT NULL
            REFERENCES kanban_columns(id) ON DELETE RESTRICT,
        posicao_kanban  INTEGER NOT NULL DEFAULT 0
            CHECK(posicao_kanban >= 0),
        criado_em       TEXT NOT NULL,
        atualizado_em   TEXT NOT NULL
    )
"""

_TS = "2026-01-01T00:00:00+00:00"
_COL_ID = "col-padrao"

_INSERT_TASK = "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?)"
_INSERT_COL = "INSERT INTO kanban_columns VALUES (?,?,?,?)"


@pytest.fixture()
def conn_v2() -> sqlite3.Connection:
    """Conexão SQLite em memória com schema v2 (constraints ativas).

    Cria as tabelas com CHECK/NOT NULL/FK idênticos aos da migration v1→v2,
    com PRAGMA foreign_keys=ON. Insere uma coluna padrão para suportar
    testes de FK de tasks.
    """
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(_SQL_KANBAN_COLUMNS)
    conn.execute(_SQL_TASKS)
    conn.execute(_INSERT_COL, (_COL_ID, "A Fazer", 0, _TS))
    conn.commit()
    return conn


def _task_row(
    row_id: str,
    titulo: str = "Tarefa Válida",
    prioridade: str = "Média",
    status: str = "Pendente",
    coluna_kanban: str = _COL_ID,
    posicao_kanban: int = 0,
) -> tuple[str | int | None, ...]:
    """Monta uma linha para INSERT em tasks, parametrizando o campo variante."""
    return (
        row_id,
        titulo,
        "",
        prioridade,
        None,
        status,
        coluna_kanban,
        posicao_kanban,
        _TS,
        _TS,
    )


# ---------------------------------------------------------------------------
# TC-108a — Task.titulo vazio
# ---------------------------------------------------------------------------


class TestTituloVazio:
    """Título vazio/espaços deve ser rejeitado no domínio e no schema."""

    def test_dominio_rejeita_titulo_vazio(self) -> None:
        """Domínio levanta ValueError para titulo=''."""
        with pytest.raises(ValueError, match="título"):
            Task(titulo="")

    def test_dominio_rejeita_titulo_so_espacos(self) -> None:
        """Domínio levanta ValueError para titulo com apenas espaços."""
        with pytest.raises(ValueError, match="título"):
            Task(titulo="   ")

    def test_schema_rejeita_titulo_vazio(self, conn_v2: sqlite3.Connection) -> None:
        """Schema levanta IntegrityError para titulo='' via INSERT cru."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2.execute(_INSERT_TASK, _task_row("t-001", titulo=""))

    def test_schema_rejeita_titulo_so_espacos(
        self, conn_v2: sqlite3.Connection
    ) -> None:
        """Schema levanta IntegrityError para titulo apenas espaços (trim)."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2.execute(_INSERT_TASK, _task_row("t-002", titulo="   "))


# ---------------------------------------------------------------------------
# TC-108b — Task.prioridade inválida
# ---------------------------------------------------------------------------


class TestPrioridadeInvalida:
    """Prioridade fora do conjunto permitido deve ser rejeitada em ambas as camadas."""

    def test_dominio_rejeita_prioridade_invalida(self) -> None:
        """Domínio (StrEnum) levanta ValueError para prioridade desconhecida."""
        with pytest.raises(ValueError, match="Prioridade"):
            Prioridade("Urgente")

    def test_schema_rejeita_prioridade_invalida(
        self, conn_v2: sqlite3.Connection
    ) -> None:
        """Schema levanta IntegrityError para prioridade fora do CHECK IN."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2.execute(_INSERT_TASK, _task_row("t-003", prioridade="Urgente"))

    def test_schema_rejeita_prioridade_null(self, conn_v2: sqlite3.Connection) -> None:
        """Schema levanta IntegrityError para prioridade=NULL (NOT NULL)."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2.execute(
                "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?)",
                ("t-004", "Tarefa", "", None, None, "Pendente", _COL_ID, 0, _TS, _TS),
            )


# ---------------------------------------------------------------------------
# TC-108c — Task.status inválido
# ---------------------------------------------------------------------------


class TestStatusInvalido:
    """Status fora do conjunto permitido deve ser rejeitado em ambas as camadas."""

    def test_dominio_rejeita_status_invalido(self) -> None:
        """Domínio (StrEnum) levanta ValueError para status desconhecido."""
        with pytest.raises(ValueError, match="StatusTarefa"):
            StatusTarefa("Arquivada")

    def test_schema_rejeita_status_invalido(self, conn_v2: sqlite3.Connection) -> None:
        """Schema levanta IntegrityError para status fora do CHECK IN."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2.execute(_INSERT_TASK, _task_row("t-005", status="Arquivada"))

    def test_schema_rejeita_status_null(self, conn_v2: sqlite3.Connection) -> None:
        """Schema levanta IntegrityError para status=NULL (NOT NULL)."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2.execute(
                "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?)",
                ("t-006", "Tarefa", "", "Média", None, None, _COL_ID, 0, _TS, _TS),
            )


# ---------------------------------------------------------------------------
# TC-108d — Task.posicao_kanban negativa
# ---------------------------------------------------------------------------


class TestPosicaoKanbanNegativa:
    """Posição Kanban negativa deve ser rejeitada em ambas as camadas."""

    def test_dominio_rejeita_posicao_negativa(self) -> None:
        """Domínio levanta ValueError para posicao_kanban < 0."""
        with pytest.raises(ValueError, match="posição Kanban"):
            Task(titulo="Tarefa", posicao_kanban=-1)

    def test_schema_rejeita_posicao_negativa(self, conn_v2: sqlite3.Connection) -> None:
        """Schema levanta IntegrityError para posicao_kanban < 0 via INSERT cru."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2.execute(_INSERT_TASK, _task_row("t-007", posicao_kanban=-1))


# ---------------------------------------------------------------------------
# TC-108e — KanbanColumn.nome vazio
# ---------------------------------------------------------------------------


class TestNomeColunaVazio:
    """Nome de coluna vazio/espaços deve ser rejeitado em ambas as camadas."""

    def test_dominio_rejeita_nome_vazio(self) -> None:
        """Domínio levanta ValueError para nome=''."""
        with pytest.raises(ValueError, match="nome da coluna"):
            KanbanColumn(nome="")

    def test_dominio_rejeita_nome_so_espacos(self) -> None:
        """Domínio levanta ValueError para nome com apenas espaços."""
        with pytest.raises(ValueError, match="nome da coluna"):
            KanbanColumn(nome="   ")

    def test_schema_rejeita_nome_vazio(self, conn_v2: sqlite3.Connection) -> None:
        """Schema levanta IntegrityError para nome='' via INSERT cru."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2.execute(_INSERT_COL, ("col-vazia", "", 0, _TS))

    def test_schema_rejeita_nome_so_espacos(self, conn_v2: sqlite3.Connection) -> None:
        """Schema levanta IntegrityError para nome apenas espaços (trim)."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2.execute(_INSERT_COL, ("col-espacos", "   ", 0, _TS))


# ---------------------------------------------------------------------------
# TC-108f — KanbanColumn.posicao negativa
# ---------------------------------------------------------------------------


class TestPosicaoColunaInvalida:
    """Posição de coluna negativa deve ser rejeitada em ambas as camadas."""

    def test_dominio_rejeita_posicao_negativa(self) -> None:
        """Domínio levanta ValueError para posicao < 0."""
        with pytest.raises(ValueError, match="posição da coluna"):
            KanbanColumn(nome="Col Válida", posicao=-1)

    def test_schema_rejeita_posicao_negativa(self, conn_v2: sqlite3.Connection) -> None:
        """Schema levanta IntegrityError para posicao < 0 via INSERT cru."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2.execute(_INSERT_COL, ("col-neg", "Col Válida", -1, _TS))


# ---------------------------------------------------------------------------
# TC-108g — Task sem coluna válida (FK violation)
# ---------------------------------------------------------------------------


class TestColunaKanbanFK:
    """Task apontando para coluna inexistente deve ser rejeitada pelo schema."""

    def test_schema_rejeita_coluna_inexistente(
        self, conn_v2: sqlite3.Connection
    ) -> None:
        """Schema levanta IntegrityError para coluna_kanban com ID inexistente."""
        with pytest.raises(sqlite3.IntegrityError):
            conn_v2.execute(
                _INSERT_TASK,
                _task_row("t-008", coluna_kanban="coluna-que-nao-existe"),
            )

    def test_schema_aceita_task_valida(self, conn_v2: sqlite3.Connection) -> None:
        """Schema aceita task completamente válida (smoke test positivo)."""
        conn_v2.execute(_INSERT_TASK, _task_row("t-ok", titulo="Tarefa OK"))
        conn_v2.commit()
        cursor = conn_v2.execute("SELECT id FROM tasks WHERE id='t-ok'")
        assert cursor.fetchone() is not None
