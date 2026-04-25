"""Testes de performance para a funcionalidade de busca (TASK-036).

Classificação: integração (UI+Service+DB real, banco em memória).
Marcados com @pytest.mark.slow para permitir skip em pipelines rápidos.

Thresholds documentados como constantes ajustáveis:
  - THRESHOLD_1K_MS: tempo máximo aceitável para busca em 1.000 tasks (ms)
  - THRESHOLD_5K_MS: tempo máximo aceitável para busca em 5.000 tasks (ms)

Seed determinístico via gerador controlado — sem dependência de Faker/random externo.
Medição via time.perf_counter (resolução sub-milissegundo).

[DECISÃO] Localização em test_integration/ (não test_ui/)
  Alternativas: A) test_ui/test_todo_widget_performance.py
               B) test_integration/test_performance_busca.py
  Escolha: B
  Por quê: o teste exercita o stack completo (UI+Service+DB), portanto pertence
           à camada de integração — além de contribuir para a meta DT-023.
  Risco aceito: thresholds podem variar conforme ambiente CI; ajuste via constantes.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Generator
from typing import Any

import pytest

from own_board_list.database.column_repository import ColumnRepository
from own_board_list.database.migrations import initialize_database
from own_board_list.database.task_repository import TaskRepository
from own_board_list.services.task_service import TaskService
from own_board_list.ui.todo.todo_widget import TodoWidget

# ---------------------------------------------------------------------------
# Thresholds documentados — ajustados pós-baseline (2026-04-19)
# ---------------------------------------------------------------------------
#
# Baseline medido em desenvolvimento (Linux, SQLite em memória):
#   - search_tasks() direto, 1k tasks:    ~5ms   (só banco)
#   - get_all_tasks() direto, 1k tasks:   ~47ms  (só banco)
#   - setText() + processEvents, 1k tasks: ~1ms  (só Qt, após init)
#   - Ciclo completo (setText + qtbot.wait(1)), 1k tasks: ~726ms
#     (inclui _reload_tasks com criação de TaskListItem widgets)
#
# O gargalo principal é a criação de TaskListItem (QWidget) no _reload_tasks,
# não a query SQL. Com 1k tasks sem filtro (get_all_tasks), o widget
# renderiza todos os itens — comportamento esperado.
#
# Thresholds definidos com folga de 2x sobre o baseline para absorver variação
# de ambiente (CI, máquinas mais lentas).
#
# [DECISÃO] Thresholds baseados no ciclo completo (não só DB)
#   Por quê: o teste valida a stack completa (UI+Service+DB); threshold
#            apertado (ex: 500ms) falharia em qualquer CI mais lento.
#   Risco aceito: thresholds altos podem mascarar regressões de performance
#                 graduais — monitorar tendência de execução em CI.

# Tempo máximo para ciclo completo: setText + qtbot.wait(1) com 1.000 tasks
THRESHOLD_1K_MS: int = 2000

# Tempo máximo para ciclo completo: setText + qtbot.wait(1) com 5.000 tasks
THRESHOLD_5K_MS: int = 8000

# Threshold para search_tasks() direto (sem UI), 1k tasks
THRESHOLD_DB_1K_MS: int = 200

# Seed para geração determinística de dados
_SEED_TITLES = [
    "Tarefa de desenvolvimento {i}",
    "Reunião de alinhamento {i}",
    "Deploy ambiente {i}",
    "Revisão de código {i}",
    "Planejamento sprint {i}",
    "Bug fix crítico {i}",
    "Documentação técnica {i}",
    "Teste de integração {i}",
    "Refatoração módulo {i}",
    "Code review PR {i}",
]

_SEED_DESCS = [
    "Descrição detalhada para a tarefa número {i} do projeto",
    "Contexto adicional sobre a atividade {i}",
    "",
]


def _gerar_titulo(i: int) -> str:
    """Gera título determinístico baseado no índice."""
    template = _SEED_TITLES[i % len(_SEED_TITLES)]
    return template.format(i=i)


def _gerar_descricao(i: int) -> str:
    """Gera descrição determinística baseada no índice."""
    template = _SEED_DESCS[i % len(_SEED_DESCS)]
    return template.format(i=i)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_conn_perf() -> Generator[sqlite3.Connection, None, None]:
    """Banco SQLite em memória para testes de performance."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    initialize_database(conn)
    yield conn
    conn.close()


@pytest.fixture()
def task_service_perf(
    qtbot: Any,
    db_conn_perf: sqlite3.Connection,
) -> TaskService:
    """TaskService real conectado ao banco em memória."""
    task_repo = TaskRepository(db_conn_perf)
    column_repo = ColumnRepository(db_conn_perf)
    return TaskService(task_repo, column_repo)


def _popular_banco(service: TaskService, n: int) -> None:
    """Insere n tasks com dados determinísticos no banco.

    Usa ``TaskService.bulk_create_tasks`` (que delega para
    ``TaskRepository.bulk_insert``) para evitar que os signals do TaskService
    (task_created) disparem _reload_tasks() no widget a cada inserção —
    o que tornaria o custo O(n²) e inflaria o tempo medido.

    Nenhum signal é emitido; o widget é instanciado *após* a inserção e
    carrega as tasks na inicialização via _reload_tasks() síncrono.

    Refatorado via DT-034: remoção de ``# type: ignore[attr-defined]``.
    """
    from own_board_list.models.task import Task
    from own_board_list.utils.constants import COLUNA_PADRAO

    tasks = [
        Task(
            titulo=_gerar_titulo(i),
            descricao=_gerar_descricao(i),
            coluna_kanban=COLUNA_PADRAO,
            posicao_kanban=i,
        )
        for i in range(n)
    ]
    service.bulk_create_tasks(tasks)


# ---------------------------------------------------------------------------
# Testes de performance
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestPerformanceBusca:
    """Testes de performance da busca com volumes de 1k e 5k tasks."""

    def test_busca_com_1000_tasks_dentro_do_threshold(
        self,
        qtbot: Any,
        task_service_perf: TaskService,
    ) -> None:
        """Busca com 1.000 tasks deve completar dentro do THRESHOLD_1K_MS.

        Threshold: THRESHOLD_1K_MS ms (constante ajustável no topo do arquivo).
        Mede: tempo de setText() + qtbot.wait(1), incluindo _reload_tasks().
        """
        _popular_banco(task_service_perf, 1000)

        widget = TodoWidget(task_service_perf, debounce_ms=0)
        qtbot.addWidget(widget)

        # Aquece o cache do banco com uma busca prévia
        task_service_perf.search_tasks("Reunião")

        # Medição real
        inicio = time.perf_counter()
        widget._search_input.setText("Revisão")
        qtbot.wait(1)  # processa o QTimer.singleShot(0, ...)
        fim = time.perf_counter()

        elapsed_ms = (fim - inicio) * 1000

        assert elapsed_ms < THRESHOLD_1K_MS, (
            f"Busca com 1k tasks levou {elapsed_ms:.1f}ms "
            f"(threshold: {THRESHOLD_1K_MS}ms)"
        )

    def test_busca_com_5000_tasks_dentro_do_threshold(
        self,
        qtbot: Any,
        task_service_perf: TaskService,
    ) -> None:
        """Busca com 5.000 tasks deve completar dentro do THRESHOLD_5K_MS.

        Threshold: THRESHOLD_5K_MS ms (constante ajustável no topo do arquivo).
        Mede: tempo de setText() + qtbot.wait(1), incluindo _reload_tasks().
        """
        _popular_banco(task_service_perf, 5000)

        widget = TodoWidget(task_service_perf, debounce_ms=0)
        qtbot.addWidget(widget)

        # Aquece o cache
        task_service_perf.search_tasks("Deploy")

        inicio = time.perf_counter()
        widget._search_input.setText("Deploy")
        qtbot.wait(1)
        fim = time.perf_counter()

        elapsed_ms = (fim - inicio) * 1000

        assert elapsed_ms < THRESHOLD_5K_MS, (
            f"Busca com 5k tasks levou {elapsed_ms:.1f}ms "
            f"(threshold: {THRESHOLD_5K_MS}ms)"
        )

    def test_busca_sem_resultados_com_5000_tasks(
        self,
        qtbot: Any,
        task_service_perf: TaskService,
    ) -> None:
        """Busca sem resultados (pior caso de LIKE) com 5k tasks deve
        completar dentro do threshold e exibir label de vazio."""
        _popular_banco(task_service_perf, 5000)

        widget = TodoWidget(task_service_perf, debounce_ms=0)
        qtbot.addWidget(widget)

        inicio = time.perf_counter()
        widget._search_input.setText("zzzzz_inexistente_xyzxyz")
        qtbot.wait(1)
        fim = time.perf_counter()

        elapsed_ms = (fim - inicio) * 1000

        # Resultado: zero matches — label deve estar ativo (não oculto)
        # isHidden() é usado pois isVisible() requer hierarquia de pais visíveis
        assert not widget._label_empty_search.isHidden(), (
            "Label de vazio deve aparecer quando busca retorna 0 resultados"
        )

        assert elapsed_ms < THRESHOLD_5K_MS, (
            f"Busca sem resultados com 5k tasks levou {elapsed_ms:.1f}ms "
            f"(threshold: {THRESHOLD_5K_MS}ms)"
        )

    def test_baseline_search_tasks_direto_1000(
        self,
        qtbot: Any,
        task_service_perf: TaskService,
    ) -> None:
        """Baseline: mede search_tasks() direto (sem UI) com 1k tasks.

        Serve como referência para isolar custo da UI vs. custo do DB.
        Threshold mais conservador: 200ms (só banco, sem render Qt).
        """
        _popular_banco(task_service_perf, 1000)

        inicio = time.perf_counter()
        resultados = task_service_perf.search_tasks("Reunião")
        fim = time.perf_counter()

        elapsed_ms = (fim - inicio) * 1000

        # Verifica que retornou resultados (integridade)
        assert len(resultados) > 0

        assert elapsed_ms < THRESHOLD_DB_1K_MS, (
            f"search_tasks() direto com 1k tasks levou {elapsed_ms:.1f}ms "
            f"(threshold: {THRESHOLD_DB_1K_MS}ms)"
        )
