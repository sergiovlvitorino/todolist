"""
Testes de migração — fixtures de bancos legados (TASK-062).

Cobre TC-094..TC-099 do plan.md da spec 011-migrations-policy-schema-constraints.

Nota sobre numeração: TC-093 e TC-094 foram reutilizados em US-10. Os IDs
abaixo seguem a numeração canônica do plan.md da spec 011 (conforme nota em
docs/plano-testes.md §7). A correspondência entre subcasos e IDs do plan é:

    TC-094 — banco v1 válido: migra sem perda, sem quarentena
    TC-095 — tarefa com prioridade nula: saneada para "Média",
              quarentena registrada
    TC-096 — tarefa com status desconhecido: saneada para "Pendente",
              quarentena registrada
    TC-097 — tarefa com coluna_kanban fantasma: realocada para "A Fazer",
              quarentena registrada
    TC-098 — tarefa com criado_em/atualizado_em nulos: preenchidos com UTC,
              quarentena registrada
    TC-099 — banco com schema_version > SCHEMA_VERSION_ATUAL:
              VersaoFuturaError, arquivo intacto
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from own_board_list.database.migrations import (
    VersaoFuturaError,
    _criar_tabela_schema_version,
    get_schema_version,
    initialize_database,
    set_schema_version,
    verificar_versao_futura,
)
from own_board_list.utils.constants import SCHEMA_VERSION_ATUAL

# ---------------------------------------------------------------------------
# Helpers para construir fixtures de banco legado v1
# ---------------------------------------------------------------------------


def _criar_banco_legado_v1(conn: sqlite3.Connection) -> None:
    """Cria o schema v1 (sem constraints CHECK/NOT NULL/FK, sem schema_version).

    Representa um banco pré-DT-040: tabelas existem, mas sem a tabela de
    controle de versão e sem constraints rígidas — exatamente o estado de um
    usuário que nunca passou pela migration v1→v2.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kanban_columns (
            id        TEXT PRIMARY KEY,
            nome      TEXT,
            posicao   INTEGER,
            criado_em TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id              TEXT PRIMARY KEY,
            titulo          TEXT,
            descricao       TEXT,
            prioridade      TEXT,
            data_vencimento TEXT,
            status          TEXT,
            coluna_kanban   TEXT,
            posicao_kanban  INTEGER,
            criado_em       TEXT,
            atualizado_em   TEXT
        )
    """)
    conn.commit()


def _inserir_coluna(
    conn: sqlite3.Connection,
    nome: str = "A Fazer",
    posicao: int = 0,
    criado_em: str | None = None,
) -> str:
    """Insere uma coluna kanban e retorna seu id."""
    col_id = str(uuid.uuid4())
    ts = criado_em if criado_em is not None else datetime.now(tz=UTC).isoformat()
    conn.execute(
        "INSERT INTO kanban_columns (id, nome, posicao, criado_em) VALUES (?, ?, ?, ?)",
        (col_id, nome, posicao, ts),
    )
    return col_id


_SENTINEL = object()  # sentinela para distinguir None explícito de "não informado"


def _inserir_task(
    conn: sqlite3.Connection,
    coluna_id: str,
    titulo: str = "Tarefa legada",
    prioridade: str | None = "Média",
    status: str | None = "Pendente",
    criado_em: object = _SENTINEL,
    atualizado_em: object = _SENTINEL,
) -> str:
    """Insere uma tarefa legada e retorna seu id.

    Quando ``criado_em``/``atualizado_em`` não são passados (sentinela),
    usa o timestamp atual. Quando passados explicitamente como ``None``,
    insere NULL no banco — útil para simular banco legado com datas ausentes.
    """
    task_id = str(uuid.uuid4())
    ts = datetime.now(tz=UTC).isoformat()
    criado_em_val = ts if criado_em is _SENTINEL else criado_em
    atualizado_em_val = ts if atualizado_em is _SENTINEL else atualizado_em
    conn.execute(
        """
        INSERT INTO tasks (
            id, titulo, descricao, prioridade, data_vencimento,
            status, coluna_kanban, posicao_kanban, criado_em, atualizado_em
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            titulo,
            "",
            prioridade,
            None,
            status,
            coluna_id,
            0,
            criado_em_val,
            atualizado_em_val,
        ),
    )
    return task_id


def _ler_quarentena(tmp_path: Path) -> list[dict]:  # type: ignore[type-arg]
    """Lê e parseia todos os registros do arquivo de quarentena do dia."""
    arquivos = list(tmp_path.glob("quarantine_*.json"))
    if not arquivos:
        return []
    linhas = arquivos[0].read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(linha) for linha in linhas]


# ---------------------------------------------------------------------------
# Fixtures pytest
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn_legado_valido() -> sqlite3.Connection:
    """Banco legado v1 com dados completamente válidos (TC-094).

    Uma coluna 'A Fazer' e duas tarefas com prioridade, status e datas
    preenchidos corretamente. Nenhum saneamento é esperado.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _criar_banco_legado_v1(conn)

    col_id = _inserir_coluna(conn, nome="A Fazer")
    _inserir_task(
        conn,
        coluna_id=col_id,
        titulo="Tarefa 1",
        prioridade="Alta",
        status="Pendente",
    )
    _inserir_task(
        conn,
        coluna_id=col_id,
        titulo="Tarefa 2",
        prioridade="Baixa",
        status="Concluída",
    )
    conn.commit()
    return conn


@pytest.fixture()
def conn_legado_prioridade_nula() -> sqlite3.Connection:
    """Banco legado v1 com uma tarefa com prioridade NULL (TC-095).

    O saneamento deve atribuir 'Média' e registrar na quarentena.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _criar_banco_legado_v1(conn)

    col_id = _inserir_coluna(conn, nome="A Fazer")
    _inserir_task(conn, coluna_id=col_id, titulo="Sem prioridade", prioridade=None)
    conn.commit()
    return conn


@pytest.fixture()
def conn_legado_status_invalido() -> sqlite3.Connection:
    """Banco legado v1 com status desconhecido (TC-096).

    Valor 'Fazendo' não pertence ao conjunto {'Pendente', 'Concluída'}.
    O saneamento deve atribuir 'Pendente' e registrar na quarentena.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _criar_banco_legado_v1(conn)

    col_id = _inserir_coluna(conn, nome="A Fazer")
    _inserir_task(conn, coluna_id=col_id, titulo="Status errado", status="Fazendo")
    conn.commit()
    return conn


@pytest.fixture()
def conn_legado_coluna_fantasma() -> sqlite3.Connection:
    """Banco legado v1 com tarefa apontando para coluna inexistente (TC-097).

    A tarefa referencia um UUID que não existe em kanban_columns.
    O saneamento deve realocar para 'A Fazer' e registrar na quarentena.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _criar_banco_legado_v1(conn)

    _inserir_coluna(conn, nome="A Fazer")  # coluna de destino de realocação
    id_fantasma = str(uuid.uuid4())  # id que não existe em nenhuma coluna
    _inserir_task(conn, coluna_id=id_fantasma, titulo="Tarefa orfã")
    conn.commit()
    return conn


@pytest.fixture()
def conn_legado_datas_nulas() -> sqlite3.Connection:
    """Banco legado v1 com criado_em/atualizado_em NULL (TC-098).

    O saneamento deve preencher ambos com o timestamp UTC da migration e
    registrar na quarentena com observação
    'data desconhecida (migrado em ...)'.
    Usa inserção direta com None explícito para forçar NULL no SQLite.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _criar_banco_legado_v1(conn)

    col_id = _inserir_coluna(conn, nome="A Fazer")
    # None explícito = NULL no banco (sentinela garante que não seja ts)
    _inserir_task(
        conn,
        coluna_id=col_id,
        titulo="Sem datas",
        criado_em=None,  # None explícito → NULL
        atualizado_em=None,  # None explícito → NULL
    )
    conn.commit()

    # Verificar que realmente ficou NULL (sanidade da fixture)
    cursor = conn.execute(
        "SELECT criado_em, atualizado_em FROM tasks WHERE titulo='Sem datas'"
    )
    row = cursor.fetchone()
    assert row["criado_em"] is None, "Fixture: criado_em deveria ser NULL"
    assert row["atualizado_em"] is None, "Fixture: atualizado_em deveria ser NULL"

    return conn


@pytest.fixture()
def conn_versao_futura() -> sqlite3.Connection:
    """Banco com schema_version > SCHEMA_VERSION_ATUAL (TC-099).

    Simula um banco criado por uma versão futura da aplicação.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _criar_tabela_schema_version(conn)
    versao_futura = SCHEMA_VERSION_ATUAL + 10
    set_schema_version(conn, versao_futura)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# TC-094 — Banco legado válido: migra para v2 sem perda, sem quarentena
# ---------------------------------------------------------------------------


class TestTC094BancoLegadoValido:
    """TC-094: banco v1 com dados válidos migra para v2 preservando os registros."""

    def test_apos_migracao_versao_e_v2(
        self, conn_legado_valido: sqlite3.Connection
    ) -> None:
        """Após initialize_database, schema_version deve ser SCHEMA_VERSION_ATUAL."""
        initialize_database(conn_legado_valido)
        versao = get_schema_version(conn_legado_valido)
        assert versao == SCHEMA_VERSION_ATUAL

    def test_tarefas_preservadas_apos_migracao(
        self, conn_legado_valido: sqlite3.Connection
    ) -> None:
        """Todas as tarefas do banco v1 válido devem continuar presentes."""
        cursor = conn_legado_valido.execute("SELECT COUNT(*) FROM tasks")
        count_antes = cursor.fetchone()[0]

        initialize_database(conn_legado_valido)

        cursor = conn_legado_valido.execute("SELECT COUNT(*) FROM tasks")
        count_depois = cursor.fetchone()[0]
        assert count_depois == count_antes

    def test_colunas_preservadas_apos_migracao(
        self, conn_legado_valido: sqlite3.Connection
    ) -> None:
        """Todas as colunas Kanban do banco v1 válido devem continuar presentes."""
        cursor = conn_legado_valido.execute("SELECT COUNT(*) FROM kanban_columns")
        count_antes = cursor.fetchone()[0]

        initialize_database(conn_legado_valido)

        cursor = conn_legado_valido.execute("SELECT COUNT(*) FROM kanban_columns")
        count_depois = cursor.fetchone()[0]
        assert count_depois == count_antes

    def test_titulos_preservados_apos_migracao(
        self, conn_legado_valido: sqlite3.Connection
    ) -> None:
        """Os títulos originais das tarefas devem ser mantidos sem alteração."""
        cursor = conn_legado_valido.execute("SELECT titulo FROM tasks ORDER BY titulo")
        titulos_antes = [r[0] for r in cursor.fetchall()]

        initialize_database(conn_legado_valido)

        cursor = conn_legado_valido.execute("SELECT titulo FROM tasks ORDER BY titulo")
        titulos_depois = [r[0] for r in cursor.fetchall()]
        assert titulos_depois == titulos_antes

    def test_prioridades_validas_preservadas(
        self, conn_legado_valido: sqlite3.Connection
    ) -> None:
        """Prioridades já válidas não devem ser alteradas pela migration."""
        cursor = conn_legado_valido.execute(
            "SELECT id, prioridade FROM tasks ORDER BY id"
        )
        prioridades_antes = {r[0]: r[1] for r in cursor.fetchall()}

        initialize_database(conn_legado_valido)

        cursor = conn_legado_valido.execute(
            "SELECT id, prioridade FROM tasks ORDER BY id"
        )
        prioridades_depois = {r[0]: r[1] for r in cursor.fetchall()}
        assert prioridades_depois == prioridades_antes


# ---------------------------------------------------------------------------
# TC-095 — Prioridade nula: saneada para "Média", quarentena registrada
# ---------------------------------------------------------------------------


class TestTC095PrioridadeNula:
    """TC-095: tarefa com prioridade NULL é saneada para 'Média'."""

    def test_prioridade_nula_saneada_para_media(
        self,
        conn_legado_prioridade_nula: sqlite3.Connection,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Após migração, prioridade NULL deve se tornar 'Média'."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)

        initialize_database(conn_legado_prioridade_nula)

        cursor = conn_legado_prioridade_nula.execute(
            "SELECT prioridade FROM tasks WHERE titulo = 'Sem prioridade'"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "Média"

    def test_quarentena_registrada_para_prioridade_nula(
        self,
        conn_legado_prioridade_nula: sqlite3.Connection,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Registro de quarentena com motivo 'prioridade_invalida' deve existir."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)
        initialize_database(conn_legado_prioridade_nula)

        registros = _ler_quarentena(tmp_path)
        assert registros, "Arquivo de quarentena não foi criado"
        motivos = [r["motivo"] for r in registros]
        assert "prioridade_invalida" in motivos

    def test_saneamento_aplicado_registrado_na_quarentena(
        self,
        conn_legado_prioridade_nula: sqlite3.Connection,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """O campo 'saneamento_aplicado' deve indicar a nova prioridade."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)
        initialize_database(conn_legado_prioridade_nula)

        registros = _ler_quarentena(tmp_path)
        reg = next(r for r in registros if r["motivo"] == "prioridade_invalida")

        assert reg["saneamento_aplicado"] == {"prioridade": "Média"}
        assert reg["payload_original"]["prioridade"] is None

    def test_versao_banco_e_v2_apos_sanear_prioridade(
        self,
        conn_legado_prioridade_nula: sqlite3.Connection,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Schema deve estar em SCHEMA_VERSION_ATUAL após sanear prioridade nula."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)
        initialize_database(conn_legado_prioridade_nula)
        assert get_schema_version(conn_legado_prioridade_nula) == SCHEMA_VERSION_ATUAL


# ---------------------------------------------------------------------------
# TC-096 — Status desconhecido: saneado para "Pendente", quarentena registrada
# ---------------------------------------------------------------------------


class TestTC096StatusInvalido:
    """TC-096: tarefa com status fora do conjunto permitido é saneada."""

    def test_status_invalido_saneado_para_pendente(
        self,
        conn_legado_status_invalido: sqlite3.Connection,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Após migração, status desconhecido deve se tornar 'Pendente'."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)
        initialize_database(conn_legado_status_invalido)

        cursor = conn_legado_status_invalido.execute(
            "SELECT status FROM tasks WHERE titulo = 'Status errado'"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "Pendente"

    def test_quarentena_registrada_para_status_invalido(
        self,
        conn_legado_status_invalido: sqlite3.Connection,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Registro de quarentena com motivo 'status_invalido' deve existir."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)
        initialize_database(conn_legado_status_invalido)

        registros = _ler_quarentena(tmp_path)
        assert registros, "Arquivo de quarentena não foi criado"
        motivos = [r["motivo"] for r in registros]
        assert "status_invalido" in motivos

    def test_payload_original_preservado_na_quarentena(
        self,
        conn_legado_status_invalido: sqlite3.Connection,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """O payload original deve conter o status inválido antes do saneamento."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)
        initialize_database(conn_legado_status_invalido)

        registros = _ler_quarentena(tmp_path)
        reg = next(r for r in registros if r["motivo"] == "status_invalido")

        assert reg["payload_original"]["status"] == "Fazendo"
        assert reg["saneamento_aplicado"] == {"status": "Pendente"}

    def test_versao_banco_e_v2_apos_sanear_status(
        self,
        conn_legado_status_invalido: sqlite3.Connection,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Schema deve estar em SCHEMA_VERSION_ATUAL após sanear status inválido."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)
        initialize_database(conn_legado_status_invalido)
        assert get_schema_version(conn_legado_status_invalido) == SCHEMA_VERSION_ATUAL


# ---------------------------------------------------------------------------
# TC-097 — Coluna fantasma: tarefa realocada para "A Fazer", quarentena
# ---------------------------------------------------------------------------


class TestTC097ColunaFantasma:
    """TC-097: tarefa apontando para coluna inexistente é realocada para 'A Fazer'."""

    def test_tarefa_realocada_para_a_fazer(
        self,
        conn_legado_coluna_fantasma: sqlite3.Connection,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Após migração, tarefa órfã deve apontar para a coluna 'A Fazer'."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)
        initialize_database(conn_legado_coluna_fantasma)

        # Encontrar o id da coluna 'A Fazer'
        cursor = conn_legado_coluna_fantasma.execute(
            "SELECT id FROM kanban_columns WHERE nome = 'A Fazer' LIMIT 1"
        )
        id_a_fazer = cursor.fetchone()[0]

        cursor = conn_legado_coluna_fantasma.execute(
            "SELECT coluna_kanban FROM tasks WHERE titulo = 'Tarefa orfã'"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == id_a_fazer

    def test_quarentena_registrada_para_coluna_inexistente(
        self,
        conn_legado_coluna_fantasma: sqlite3.Connection,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Registro de quarentena com motivo 'coluna_inexistente' deve existir."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)
        initialize_database(conn_legado_coluna_fantasma)

        registros = _ler_quarentena(tmp_path)
        assert registros, "Arquivo de quarentena não foi criado"
        motivos = [r["motivo"] for r in registros]
        assert "coluna_inexistente" in motivos

    def test_payload_original_preserva_coluna_fantasma(
        self,
        conn_legado_coluna_fantasma: sqlite3.Connection,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """O payload original deve conter o id da coluna fantasma."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)

        # Capturar o id da coluna fantasma ANTES da migração
        cursor = conn_legado_coluna_fantasma.execute(
            "SELECT coluna_kanban FROM tasks WHERE titulo = 'Tarefa orfã'"
        )
        coluna_fantasma_id = cursor.fetchone()[0]

        initialize_database(conn_legado_coluna_fantasma)

        registros = _ler_quarentena(tmp_path)
        reg = next(r for r in registros if r["motivo"] == "coluna_inexistente")

        assert reg["payload_original"]["coluna_kanban"] == coluna_fantasma_id

    def test_saneamento_aplicado_indica_id_a_fazer(
        self,
        conn_legado_coluna_fantasma: sqlite3.Connection,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """O saneamento_aplicado deve indicar o id da coluna 'A Fazer'."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)
        initialize_database(conn_legado_coluna_fantasma)

        cursor = conn_legado_coluna_fantasma.execute(
            "SELECT id FROM kanban_columns WHERE nome = 'A Fazer' LIMIT 1"
        )
        id_a_fazer = cursor.fetchone()[0]

        registros = _ler_quarentena(tmp_path)
        reg = next(r for r in registros if r["motivo"] == "coluna_inexistente")

        assert reg["saneamento_aplicado"] == {"coluna_kanban": id_a_fazer}

    def test_versao_banco_e_v2_apos_realocar(
        self,
        conn_legado_coluna_fantasma: sqlite3.Connection,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Schema deve estar em SCHEMA_VERSION_ATUAL após realocar tarefa órfã."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)
        initialize_database(conn_legado_coluna_fantasma)
        assert get_schema_version(conn_legado_coluna_fantasma) == SCHEMA_VERSION_ATUAL


# ---------------------------------------------------------------------------
# TC-098 — Datas nulas: preenchidas com UTC atual, quarentena com observação
# ---------------------------------------------------------------------------


class TestTC098DatasNulas:
    """TC-098: criado_em/atualizado_em NULL são preenchidos com UTC da migration."""

    def test_criado_em_preenchido_apos_migracao(
        self,
        conn_legado_datas_nulas: sqlite3.Connection,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Após migração, criado_em deve ser um timestamp ISO não nulo."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)
        initialize_database(conn_legado_datas_nulas)

        cursor = conn_legado_datas_nulas.execute(
            "SELECT criado_em, atualizado_em FROM tasks WHERE titulo = 'Sem datas'"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] is not None, "criado_em deve estar preenchido"
        assert row[1] is not None, "atualizado_em deve estar preenchido"

    def test_datas_preenchidas_sao_iso_valido(
        self,
        conn_legado_datas_nulas: sqlite3.Connection,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Os timestamps preenchidos devem ser strings ISO parseable."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)

        # Capturar janela temporal com margem de 1 segundo
        inicio = datetime.now(tz=UTC) - timedelta(seconds=1)
        initialize_database(conn_legado_datas_nulas)
        fim = datetime.now(tz=UTC) + timedelta(seconds=1)

        cursor = conn_legado_datas_nulas.execute(
            "SELECT criado_em FROM tasks WHERE titulo = 'Sem datas'"
        )
        criado_em_str = cursor.fetchone()[0]

        # Deve ser parseável como datetime ISO
        criado_em_dt = datetime.fromisoformat(criado_em_str)
        assert inicio <= criado_em_dt <= fim, (
            f"Timestamp ({criado_em_dt}) deve estar no intervalo da migration"
        )

    def test_quarentena_registrada_para_datas_nulas(
        self,
        conn_legado_datas_nulas: sqlite3.Connection,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Registro de quarentena com motivo 'data_ausente' deve ser gravado."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)
        initialize_database(conn_legado_datas_nulas)

        registros = _ler_quarentena(tmp_path)
        assert registros, "Arquivo de quarentena não foi criado"
        motivos = [r["motivo"] for r in registros]
        assert "data_ausente" in motivos

    def test_observacao_na_quarentena_menciona_data_migracao(
        self,
        conn_legado_datas_nulas: sqlite3.Connection,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """O saneamento_aplicado deve conter observação sobre a data."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)
        initialize_database(conn_legado_datas_nulas)

        registros = _ler_quarentena(tmp_path)
        reg = next(r for r in registros if r["motivo"] == "data_ausente")

        observacao = reg["saneamento_aplicado"].get("observacao", "")
        assert "data desconhecida" in observacao
        assert "migrado em" in observacao

    def test_payload_original_tem_datas_nulas(
        self,
        conn_legado_datas_nulas: sqlite3.Connection,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """O payload_original deve mostrar criado_em/atualizado_em nulos."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)
        initialize_database(conn_legado_datas_nulas)

        registros = _ler_quarentena(tmp_path)
        reg = next(r for r in registros if r["motivo"] == "data_ausente")

        assert reg["payload_original"]["criado_em"] is None
        assert reg["payload_original"]["atualizado_em"] is None

    def test_versao_banco_e_v2_apos_sanear_datas(
        self,
        conn_legado_datas_nulas: sqlite3.Connection,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Schema deve estar em SCHEMA_VERSION_ATUAL após sanear datas nulas."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)
        initialize_database(conn_legado_datas_nulas)
        assert get_schema_version(conn_legado_datas_nulas) == SCHEMA_VERSION_ATUAL


# ---------------------------------------------------------------------------
# TC-099 — Versão futura: VersaoFuturaError, arquivo intacto
# ---------------------------------------------------------------------------


class TestTC099VersaoFutura:
    """TC-099: banco com schema_version > SCHEMA_VERSION_ATUAL gera erro claro."""

    def test_verificar_versao_futura_levanta_erro(
        self, conn_versao_futura: sqlite3.Connection
    ) -> None:
        """verificar_versao_futura deve levantar VersaoFuturaError."""
        with pytest.raises(VersaoFuturaError):
            verificar_versao_futura(conn_versao_futura)

    def test_mensagem_erro_menciona_versoes(
        self, conn_versao_futura: sqlite3.Connection
    ) -> None:
        """A mensagem do erro deve mencionar a versão do banco e da aplicação."""
        with pytest.raises(VersaoFuturaError) as exc_info:
            verificar_versao_futura(conn_versao_futura)

        mensagem = str(exc_info.value)
        versao_futura = SCHEMA_VERSION_ATUAL + 10
        assert str(versao_futura) in mensagem
        assert str(SCHEMA_VERSION_ATUAL) in mensagem

    def test_versao_futura_atributos_corretos(
        self, conn_versao_futura: sqlite3.Connection
    ) -> None:
        """VersaoFuturaError deve expor versao_banco e versao_app corretamente."""
        versao_futura = SCHEMA_VERSION_ATUAL + 10
        with pytest.raises(VersaoFuturaError) as exc_info:
            verificar_versao_futura(conn_versao_futura)

        err = exc_info.value
        assert err.versao_banco == versao_futura
        assert err.versao_app == SCHEMA_VERSION_ATUAL

    def test_migration_service_falha_graciosamente_com_versao_futura(
        self,
        tmp_path: Path,
    ) -> None:
        """MigrationService.executar deve retornar sucesso=False para versão futura.

        Usa arquivo físico para que MigrationService possa abrir via Path.
        O arquivo não deve ser alterado após a falha.
        """
        from own_board_list.services.migration_service import MigrationService

        db_path = tmp_path / "data.db"

        # Criar banco com versão futura via arquivo físico
        conn = sqlite3.connect(str(db_path))
        _criar_tabela_schema_version(conn)
        set_schema_version(conn, SCHEMA_VERSION_ATUAL + 10)
        conn.commit()
        conn.close()

        # Capturar tamanho do arquivo antes
        tamanho_antes = db_path.stat().st_size

        service = MigrationService()
        report = service.executar(db_path)

        # A migration deve falhar com sucesso=False
        assert report.sucesso is False
        assert report.erro is not None
        assert len(report.erro) > 0

        # O arquivo deve permanecer intacto (mesmo tamanho)
        tamanho_depois = db_path.stat().st_size
        assert tamanho_depois == tamanho_antes

    def test_versao_banco_nao_alterada_apos_falha_versao_futura(
        self,
        tmp_path: Path,
    ) -> None:
        """O schema_version não deve ser alterado após falha por versão futura."""
        from own_board_list.services.migration_service import MigrationService

        db_path = tmp_path / "data.db"
        versao_futura = SCHEMA_VERSION_ATUAL + 10

        conn = sqlite3.connect(str(db_path))
        _criar_tabela_schema_version(conn)
        set_schema_version(conn, versao_futura)
        conn.commit()
        conn.close()

        service = MigrationService()
        service.executar(db_path)

        # Verificar que a versão não foi modificada
        conn_verificacao = sqlite3.connect(str(db_path))
        versao_atual = get_schema_version(conn_verificacao)
        conn_verificacao.close()

        assert versao_atual == versao_futura


# ---------------------------------------------------------------------------
# Testes adicionais de borda
# ---------------------------------------------------------------------------


class TestCenariosBorda:
    """Cenários de borda complementares aos TCs principais."""

    def test_banco_multiplas_irregularidades_todas_saneadas(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Banco com prioridade nula E status inválido: ambos são saneados."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        _criar_banco_legado_v1(conn)

        col_id = _inserir_coluna(conn, nome="A Fazer")
        # Uma tarefa com prioridade nula E status inválido ao mesmo tempo
        conn.execute(
            """
            INSERT INTO tasks (
                id, titulo, descricao, prioridade, data_vencimento,
                status, coluna_kanban, posicao_kanban, criado_em, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                "Tarefa problematica",
                "",
                None,  # prioridade nula
                None,
                "Fazendo",  # status inválido
                col_id,
                0,
                datetime.now(tz=UTC).isoformat(),
                datetime.now(tz=UTC).isoformat(),
            ),
        )
        conn.commit()

        initialize_database(conn)

        cursor = conn.execute(
            "SELECT prioridade, status FROM tasks WHERE titulo = 'Tarefa problematica'"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "Média"
        assert row[1] == "Pendente"

    def test_banco_legado_sem_nenhuma_tarefa_migra_ok(self) -> None:
        """Banco v1 vazio (sem tarefas) deve migrar sem erros."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        _criar_banco_legado_v1(conn)

        # Inserir apenas a coluna obrigatória, sem tarefas
        _inserir_coluna(conn, nome="A Fazer")
        conn.commit()

        # Não deve levantar exceção
        initialize_database(conn)
        assert get_schema_version(conn) == SCHEMA_VERSION_ATUAL

    def test_initialize_database_idempotente_em_banco_v2(self) -> None:
        """Chamar initialize_database duas vezes em banco v2 não causa erro."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row

        initialize_database(conn)
        versao_apos_primeira = get_schema_version(conn)

        # Segunda chamada deve ser no-op
        initialize_database(conn)
        versao_apos_segunda = get_schema_version(conn)

        assert versao_apos_primeira == versao_apos_segunda == SCHEMA_VERSION_ATUAL

    def test_prioridade_fora_do_conjunto_saneada(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Prioridade com valor fora do enum é saneada para 'Média'."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        _criar_banco_legado_v1(conn)

        col_id = _inserir_coluna(conn, nome="A Fazer")
        _inserir_task(
            conn,
            coluna_id=col_id,
            titulo="Urgente task",
            prioridade="Urgente",
        )
        conn.commit()

        initialize_database(conn)

        cursor = conn.execute(
            "SELECT prioridade FROM tasks WHERE titulo = 'Urgente task'"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "Média"

    def test_status_nulo_saneado_para_pendente(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Status NULL (não apenas valor inválido) é saneado para 'Pendente'."""
        import own_board_list.database.quarantine as quarantine_mod

        monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path)

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        _criar_banco_legado_v1(conn)

        col_id = _inserir_coluna(conn, nome="A Fazer")
        _inserir_task(conn, coluna_id=col_id, titulo="Status nulo", status=None)
        conn.commit()

        initialize_database(conn)

        cursor = conn.execute("SELECT status FROM tasks WHERE titulo = 'Status nulo'")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "Pendente"
