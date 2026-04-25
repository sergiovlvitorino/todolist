"""Benchmark de performance para MigrationService com banco de 10 000 tarefas.

TC-107 — Migração de 10 000 tarefas conclui em ≤ 3 s (pytest.mark.slow).

Mede o tempo total de execução do ``MigrationService.executar`` sobre um banco
legado (v1) com 10 000 tarefas pré-populadas. O threshold de 3 s é o critério
de aceite documentado no plan.md e no docs/plano-testes.md.

Estratégia:
- Banco em arquivo temporário (não em memória) para simular condições reais de I/O.
- Schema legado v1 construído manualmente (sem ``schema_version``, sem constraints
  CHECK/NOT NULL/FK), exigindo a migration v1→v2 completa.
- Inserção via ``executemany`` para minimizar o overhead de setup.
- ``MigrationService.executar`` é chamado uma única vez; o tempo medido inclui
  backup, saneamento, recriação de tabelas, validação de integridade e rotação
  de backups.
"""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from own_board_list.services.migration_service import MigrationService

# ---------------------------------------------------------------------------
# Threshold documentado — TC-107
#
# A spec (Feature.3) exige migração silenciosa (<1,5 s) ou com indicador de
# progresso até o limite razoável. O plan.md registra risco explícito de banco
# grande (>10k tarefas) e define como mitigação a medição em benchmark.
# O threshold de 3 s inclui folga sobre o limiar de progresso (1,5 s) para
# absorver variação de hardware em CI (2x baseline máximo esperado).
# ---------------------------------------------------------------------------

THRESHOLD_MIGRACAO_10K_S: float = 3.0
N_TAREFAS: int = 10_000

# Valores de referência para as 3 colunas padrão inseridas no banco legado
_COLUNA_A_FAZER_ID = str(uuid.UUID(int=1))
_COLUNA_EM_ANDAMENTO_ID = str(uuid.UUID(int=2))
_COLUNA_CONCLUIDO_ID = str(uuid.UUID(int=3))
_COLUNAS_IDS = [_COLUNA_A_FAZER_ID, _COLUNA_EM_ANDAMENTO_ID, _COLUNA_CONCLUIDO_ID]


def _criar_schema_legado_v1(conn: sqlite3.Connection) -> None:
    """Cria schema v1 (sem schema_version, sem constraints CHECK/FK/NOT NULL).

    Representa o estado de um banco real antes da DT-040/DT-013:
    tabelas simples, sem ``schema_version``, sem REFERENCES, sem CHECK.
    """
    conn.executescript("""
        CREATE TABLE kanban_columns (
            id        TEXT PRIMARY KEY,
            nome      TEXT,
            posicao   INTEGER DEFAULT 0,
            criado_em TEXT
        );

        CREATE TABLE tasks (
            id              TEXT PRIMARY KEY,
            titulo          TEXT,
            descricao       TEXT DEFAULT '',
            prioridade      TEXT DEFAULT 'Média',
            data_vencimento TEXT,
            status          TEXT DEFAULT 'Pendente',
            coluna_kanban   TEXT,
            posicao_kanban  INTEGER DEFAULT 0,
            criado_em       TEXT,
            atualizado_em   TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_coluna_kanban
            ON tasks (coluna_kanban);
        CREATE INDEX IF NOT EXISTS idx_tasks_status
            ON tasks (status);
        CREATE INDEX IF NOT EXISTS idx_tasks_prioridade
            ON tasks (prioridade);
    """)


def _popular_colunas_legado(conn: sqlite3.Connection) -> None:
    """Insere as 3 colunas padrão no banco legado."""
    agora = datetime.now(tz=UTC).isoformat()
    conn.executemany(
        "INSERT INTO kanban_columns (id, nome, posicao, criado_em) VALUES (?, ?, ?, ?)",
        [
            (_COLUNA_A_FAZER_ID, "A Fazer", 0, agora),
            (_COLUNA_EM_ANDAMENTO_ID, "Em Andamento", 1, agora),
            (_COLUNA_CONCLUIDO_ID, "Concluído", 2, agora),
        ],
    )


def _popular_tarefas_legado(conn: sqlite3.Connection, n: int) -> None:
    """Insere n tarefas no banco legado usando executemany (sem overhead O(n²)).

    Distribui as tarefas pelas 3 colunas de forma round-robin. Todos os campos
    têm valores válidos — o objetivo é medir o custo da migration, não do
    saneamento. Um subconjunto (1/10) tem prioridade nula para exercitar o
    saneamento sem dominar o tempo de execução.
    """
    agora = datetime.now(tz=UTC).isoformat()
    prioridades = ["Baixa", "Média", "Alta"]

    tarefas = []
    for i in range(n):
        coluna_id = _COLUNAS_IDS[i % len(_COLUNAS_IDS)]
        # 10% com prioridade nula para exercitar saneamento
        prioridade = None if i % 10 == 0 else prioridades[i % len(prioridades)]
        tarefas.append(
            (
                str(uuid.uuid4()),
                f"Tarefa de benchmark {i:05d}",
                "",
                prioridade,
                None,
                "Pendente",
                coluna_id,
                i // len(_COLUNAS_IDS),
                agora,
                agora,
            )
        )

    conn.executemany(
        """
        INSERT INTO tasks
            (id, titulo, descricao, prioridade, data_vencimento,
             status, coluna_kanban, posicao_kanban, criado_em, atualizado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        tarefas,
    )
    conn.commit()


@pytest.fixture(autouse=True)
def _isolar_quarentena(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[None, None, None]:
    # 10% das tarefas têm prioridade=NULL → migration grava ~1000 registros em
    # quarentena por teste. Sem isolamento, o caminho global QUARENTENA_DIR
    # (~/.own-board-list/) acumula MBs de dados de teste no diretório real do
    # usuário (DT-043).
    from own_board_list.database import quarantine as quarantine_mod

    monkeypatch.setattr(quarantine_mod, "QUARENTENA_DIR", tmp_path / "quarentena")
    yield


@pytest.fixture()
def db_legado_10k(tmp_path: Path) -> Generator[Path, None, None]:
    """Banco legado v1 em arquivo temporário com 10 000 tarefas pré-populadas.

    Usa arquivo real (não :memory:) para incluir o custo real de I/O no benchmark.
    O arquivo é removido ao fim do teste pelo ``tmp_path`` do pytest.
    """
    db_path = tmp_path / "legado_10k.db"
    conn = sqlite3.connect(str(db_path))
    try:
        _criar_schema_legado_v1(conn)
        _popular_colunas_legado(conn)
        _popular_tarefas_legado(conn, N_TAREFAS)
    finally:
        conn.close()
    yield db_path


# ---------------------------------------------------------------------------
# TC-107 — Benchmark: migração de 10k tarefas conclui em ≤ 3 s
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestBenchmarkMigracao10k:
    """TC-107 — MigrationService.executar com 10 000 tarefas ≤ 3 s.

    [DECISÃO] Medir MigrationService completo (não só a migration interna)
      Alternativas:
        A) Medir apenas ``_aplicar_v1_v2`` sem backup/rotação → ignora overhead real.
        B) Medir ``MigrationService.executar`` completo (backup + migration +
           validação + rotação) → representa o custo total percebido pelo bootstrap.
      Escolha: B
      Por quê: o threshold de 3 s é o limite de experiência do usuário; a spec
               define o limiar de progresso em 1,5 s para o processo completo.
               Medir apenas a migration subestimaria o custo real e invalidaria
               o critério de aceite.
      Risco aceito: variação de I/O em CI pode causar flakiness ocasional em
                    ambientes com disco lento. Threshold de 3 s tem folga 2x
                    sobre o limiar de progresso (1,5 s) para mitigar esse risco.
    """

    def test_migracao_10k_tarefas_dentro_do_threshold(
        self,
        db_legado_10k: Path,
    ) -> None:
        """TC-107: MigrationService.executar em banco v1 com 10k tarefas ≤ 3 s.

        Verifica que:
        1. A migração conclui com sucesso (``report.sucesso == True``).
        2. A versão de destino é 2 (schema atualizado).
        3. O tempo total de execução não ultrapassa ``THRESHOLD_MIGRACAO_10K_S``.
        4. Todas as 10 000 tarefas estão presentes após a migration.
        """
        service = MigrationService()

        report = service.executar(db_legado_10k)

        # Validar sucesso antes de checar tempo (falha de migration != falha de perf)
        assert report.sucesso, (
            f"Migration falhou antes da medição de tempo: {report.erro}"
        )
        assert report.versao_destino == 2, (
            f"Versão de destino esperada: 2, obtida: {report.versao_destino}"
        )

        assert report.duracao_s <= THRESHOLD_MIGRACAO_10K_S, (
            f"Migração de {N_TAREFAS} tarefas levou {report.duracao_s:.2f} s "
            f"(threshold: {THRESHOLD_MIGRACAO_10K_S} s). "
            f"Versão origem: {report.versao_origem} → {report.versao_destino}. "
            f"Registros saneados: {report.registros_saneados}."
        )

        # Verificar integridade dos dados pós-migration
        conn = sqlite3.connect(str(db_legado_10k))
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM tasks")
            row = cursor.fetchone()
            total_tarefas = row[0] if row is not None else 0
        finally:
            conn.close()

        assert total_tarefas == N_TAREFAS, (
            f"Perda de dados na migration: esperadas {N_TAREFAS} tarefas, "
            f"encontradas {total_tarefas}."
        )

    def test_migracao_10k_registra_versao_destino(
        self,
        db_legado_10k: Path,
    ) -> None:
        """TC-107 (complementar): schema_version registrada como 2 após migration."""
        from own_board_list.database.migrations import get_schema_version

        service = MigrationService()
        report = service.executar(db_legado_10k)

        assert report.sucesso, f"Migration falhou: {report.erro}"

        conn = sqlite3.connect(str(db_legado_10k))
        try:
            versao = get_schema_version(conn)
        finally:
            conn.close()

        assert versao == 2, f"schema_version esperada: 2, encontrada: {versao}"

    def test_migracao_10k_relatorio_contem_duracao(
        self,
        db_legado_10k: Path,
    ) -> None:
        """TC-107 (complementar): MigrationReport.duracao_s > 0 e coerente."""
        service = MigrationService()
        report = service.executar(db_legado_10k)

        assert report.sucesso, f"Migration falhou: {report.erro}"
        assert report.duracao_s > 0, "duracao_s deve ser positiva"
        # Limite superior generoso (30 s) para detectar regressão grave
        assert report.duracao_s < 30.0, (
            f"duracao_s={report.duracao_s:.2f} s excede limite de sanidade (30 s)"
        )
