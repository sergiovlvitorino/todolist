"""Testes de integração — fluxo de busca por texto na Todo List (TASK-035).

Estratégia: banco SQLite em memória REAL + TaskService REAL + TodoWidget REAL.
SEM mocks de repositório. Classificado como integração para contribuir com DT-023.

Cobre: Unicode, acentos/ç, emojis, SQL wildcards (%/_), aspas, só-espaços,
busca vazia, seções vazias com filtro, reaplicação pós-CRUD e busca global vazia.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from datetime import date, timedelta
from typing import Any

import pytest

from own_board_list.database.column_repository import ColumnRepository
from own_board_list.database.migrations import initialize_database
from own_board_list.database.task_repository import TaskRepository
from own_board_list.services.task_service import TaskService
from own_board_list.ui.todo.todo_widget import TodoWidget

# ---------------------------------------------------------------------------
# Fixtures locais — banco em memória exclusivo para testes de integração busca
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_conn_busca() -> Generator[sqlite3.Connection, None, None]:
    """Conexão SQLite em memória com schema completo, exclusiva para busca."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    initialize_database(conn)
    yield conn
    conn.close()


@pytest.fixture()
def task_service_busca(
    qtbot: Any,
    db_conn_busca: sqlite3.Connection,
) -> TaskService:
    """TaskService real conectado ao banco em memória (sem mocks)."""
    task_repo = TaskRepository(db_conn_busca)
    column_repo = ColumnRepository(db_conn_busca)
    return TaskService(task_repo, column_repo)


@pytest.fixture()
def widget_busca(
    qtbot: Any,
    task_service_busca: TaskService,
) -> TodoWidget:
    """TodoWidget real com debounce_ms=0 para testes síncronos."""
    widget = TodoWidget(task_service_busca, debounce_ms=0)
    qtbot.addWidget(widget)
    return widget


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _aplicar_busca(qtbot: Any, widget: TodoWidget, termo: str) -> None:
    """Define o termo no campo de busca e aguarda processamento do debounce.

    Usa setText() em vez de keyClicks() para compatibilidade com ambientes
    headless (XCB) onde keyClicks() em widget não visível causa Abort.
    """
    widget._search_input.setText(termo)
    qtbot.wait(1)


def _contar_items_visiveis(widget: TodoWidget) -> int:
    """Conta TaskListItem visíveis em todos os grupos."""
    from own_board_list.ui.todo.task_list_item import TaskListItem

    total = 0
    for group in (
        widget._group_hoje,
        widget._group_proximas,
        widget._group_sem_data,
        widget._group_concluidas,
    ):
        layout = group.layout()
        if layout is None:
            continue
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and isinstance(item.widget(), TaskListItem):
                total += 1
    return total


# ===========================================================================
# Cenários de integração (classificados explicitamente como integração)
# ===========================================================================


@pytest.mark.integration
class TestFluxoBusca:
    """Integração UI+Service+DB para US-07 (busca por texto)."""

    # -----------------------------------------------------------------------
    # Cenário 1 — Unicode: maiúsculas/minúsculas (Reunião / reuniao)
    # -----------------------------------------------------------------------

    def test_busca_case_insensitive_unicode_reuniao(
        self,
        qtbot: Any,
        task_service_busca: TaskService,
        widget_busca: TodoWidget,
    ) -> None:
        """Buscar 'reuniao' (minúsculo, sem acento) NÃO deve encontrar 'Reunião'
        — o motor usa PY_UPPER que converte corretamente, mas o termo de busca
        'reuniao' e 'Reunião' são strings diferentes após upper().
        Buscar 'Reunião' deve encontrar exatamente a task com esse título."""
        task_service_busca.create_task("Reunião de alinhamento")
        task_service_busca.create_task("Deploy produção")

        # Busca exata com acento — deve encontrar
        _aplicar_busca(qtbot, widget_busca, "Reunião")
        assert widget_busca._search_term == "Reunião"
        resultados = task_service_busca.search_tasks("Reunião")
        assert len(resultados) == 1
        assert resultados[0].titulo == "Reunião de alinhamento"

        # Busca em maiúsculas — deve encontrar (case-insensitive via PY_UPPER)
        resultados_upper = task_service_busca.search_tasks("REUNIÃO")
        assert len(resultados_upper) == 1

    # -----------------------------------------------------------------------
    # Cenário 2 — Acentos e ç: ação/acao
    # -----------------------------------------------------------------------

    def test_busca_com_acento_e_cedilha(
        self,
        qtbot: Any,
        task_service_busca: TaskService,
        widget_busca: TodoWidget,
    ) -> None:
        """Busca por 'ação' deve encontrar task com 'ação'; 'acao' sem acento
        NÃO deve encontrar 'ação' (comportamento correto — sem folding de acentos)."""
        task_service_busca.create_task("Plano de ação Q2")
        task_service_busca.create_task("Revisão de código")

        # Busca exata com acento encontra a task
        resultados_acento = task_service_busca.search_tasks("ação")
        assert any("ação" in t.titulo for t in resultados_acento)

        # Busca sem acento NÃO encontra (sem folding de acentos)
        resultados_sem_acento = task_service_busca.search_tasks("acao")
        assert not any("ação" in t.titulo for t in resultados_sem_acento)

        # Busca por ç em maiúscula (Ç) deve funcionar via PY_UPPER
        resultados_cedilha_upper = task_service_busca.search_tasks("AÇÃO")
        assert any("ação" in t.titulo for t in resultados_cedilha_upper)

    # -----------------------------------------------------------------------
    # Cenário 3 — Emojis no título e na busca
    # -----------------------------------------------------------------------

    def test_busca_com_emoji_no_titulo(
        self,
        qtbot: Any,
        task_service_busca: TaskService,
        widget_busca: TodoWidget,
    ) -> None:
        """Tasks com emojis no título devem ser encontradas ao buscar pelo emoji."""
        task_service_busca.create_task("🚀 Release v2.0")
        task_service_busca.create_task("Tarefa sem emoji")

        resultados = task_service_busca.search_tasks("🚀")
        assert len(resultados) == 1
        assert "🚀" in resultados[0].titulo

        # A task sem emoji não aparece
        resultados_sem_emoji = task_service_busca.search_tasks("sem emoji")
        assert len(resultados_sem_emoji) == 1
        assert "sem emoji" in resultados_sem_emoji[0].titulo

    # -----------------------------------------------------------------------
    # Cenário 4 — SQL wildcard %: não deve vazar para LIKE
    # -----------------------------------------------------------------------

    def test_busca_com_percentual_escapado(
        self,
        qtbot: Any,
        task_service_busca: TaskService,
        widget_busca: TodoWidget,
    ) -> None:
        """Buscar '50%' deve encontrar exatamente a task com '50%' no título,
        sem retornar todas as tasks (regressão de TASK-029 — escape de %)."""
        task_service_busca.create_task("Meta: 50% concluída")
        task_service_busca.create_task("Outra tarefa qualquer")
        task_service_busca.create_task("Mais uma tarefa")

        resultados = task_service_busca.search_tasks("50%")
        assert len(resultados) == 1
        assert "50%" in resultados[0].titulo

    # -----------------------------------------------------------------------
    # Cenário 5 — SQL wildcard _: não deve fazer match de qualquer char
    # -----------------------------------------------------------------------

    def test_busca_com_underscore_escapado(
        self,
        qtbot: Any,
        task_service_busca: TaskService,
        widget_busca: TodoWidget,
    ) -> None:
        """Buscar 'a_b' deve encontrar exatamente a task com 'a_b', sem
        retornar tasks como 'acb', 'adb' (regressão de TASK-029 — escape de _)."""
        task_service_busca.create_task("config a_b produção")
        task_service_busca.create_task("config acb test")
        task_service_busca.create_task("config adb homolog")

        resultados = task_service_busca.search_tasks("a_b")
        assert len(resultados) == 1
        assert "a_b" in resultados[0].titulo

    # -----------------------------------------------------------------------
    # Cenário 6 — Aspas simples e duplas não quebram a query SQL
    # -----------------------------------------------------------------------

    def test_busca_com_aspas_simples_nao_quebra_sql(
        self,
        qtbot: Any,
        task_service_busca: TaskService,
        widget_busca: TodoWidget,
    ) -> None:
        """Buscar termos com aspas simples (') não deve causar erro SQL."""
        task_service_busca.create_task("O'Brien review")
        task_service_busca.create_task("Tarefa normal")

        # Não deve lançar exceção
        resultados = task_service_busca.search_tasks("O'Brien")
        assert len(resultados) == 1
        assert "O'Brien" in resultados[0].titulo

    def test_busca_com_aspas_duplas_nao_quebra_sql(
        self,
        qtbot: Any,
        task_service_busca: TaskService,
        widget_busca: TodoWidget,
    ) -> None:
        """Buscar termos com aspas duplas não deve causar erro SQL."""
        task_service_busca.create_task('Tarefa "urgente" hoje')
        task_service_busca.create_task("Outra task")

        resultados = task_service_busca.search_tasks('"urgente"')
        assert len(resultados) == 1
        assert '"urgente"' in resultados[0].titulo

    # -----------------------------------------------------------------------
    # Cenário 7 — Só-espaços: não ativa filtro, exibe todas as tasks
    # -----------------------------------------------------------------------

    def test_busca_so_espacos_nao_ativa_filtro(
        self,
        qtbot: Any,
        task_service_busca: TaskService,
        widget_busca: TodoWidget,
    ) -> None:
        """Digitar apenas espaços no campo de busca não deve ativar filtro.
        _search_term deve ser '' (via strip) e todas as tasks devem aparecer."""
        task_service_busca.create_task("Alpha")
        task_service_busca.create_task("Beta")
        task_service_busca.create_task("Gamma")

        _aplicar_busca(qtbot, widget_busca, "   ")
        qtbot.wait(1)

        assert widget_busca._search_term == ""
        assert widget_busca._label_empty_search.isHidden()
        assert _contar_items_visiveis(widget_busca) == 3

    # -----------------------------------------------------------------------
    # Cenário 8 — Campo vazio: exibe todas as tasks sem label de vazio
    # -----------------------------------------------------------------------

    def test_busca_vazia_exibe_todas_as_tasks(
        self,
        qtbot: Any,
        task_service_busca: TaskService,
        widget_busca: TodoWidget,
    ) -> None:
        """Com campo de busca vazio, todas as tasks devem ser exibidas e
        o label 'Nenhuma tarefa encontrada' não deve aparecer."""
        task_service_busca.create_task("Task 1")
        task_service_busca.create_task("Task 2")

        # Campo já está vazio no início — verifica estado inicial
        assert widget_busca._search_term == ""
        assert widget_busca._label_empty_search.isHidden()
        assert _contar_items_visiveis(widget_busca) == 2

    # -----------------------------------------------------------------------
    # Cenário 9 — Seções vazias: com filtro ativo, seções sem resultado
    #            devem exibir "Nenhuma tarefa" (comportamento dos grupos)
    # -----------------------------------------------------------------------

    def test_secoes_vazias_com_filtro_ativo(
        self,
        qtbot: Any,
        task_service_busca: TaskService,
        widget_busca: TodoWidget,
    ) -> None:
        """Com filtro ativo que retorna tasks só em 'Sem data', os outros grupos
        devem exibir 'Nenhuma tarefa' (label dos grupos individuais)."""
        from PyQt6.QtWidgets import QLabel

        task_service_busca.create_task("Reunião semanal")  # sem data

        _aplicar_busca(qtbot, widget_busca, "Reunião")
        qtbot.wait(1)

        # Grupos 'Hoje', 'Próximas' e 'Concluídas' devem ter o label "Nenhuma tarefa"
        for group in (
            widget_busca._group_hoje,
            widget_busca._group_proximas,
            widget_busca._group_concluidas,
        ):
            layout = group.layout()
            assert layout is not None
            assert layout.count() == 1
            item = layout.itemAt(0)
            assert item is not None
            label = item.widget()
            assert isinstance(label, QLabel)
            assert label.text() == "Nenhuma tarefa"

        # Grupo 'Sem data' deve ter o item encontrado
        assert _contar_items_visiveis(widget_busca) == 1

    # -----------------------------------------------------------------------
    # Cenário 10 — Reaplicação pós-create: nova task aparece se bate com filtro
    # -----------------------------------------------------------------------

    def test_reaplica_filtro_apos_create(
        self,
        qtbot: Any,
        task_service_busca: TaskService,
        widget_busca: TodoWidget,
    ) -> None:
        """Com filtro ativo, criar uma nova task que bate com o filtro deve
        fazê-la aparecer imediatamente na lista (via signal task_created)."""
        task_service_busca.create_task("Tarefa existente")

        _aplicar_busca(qtbot, widget_busca, "nova")
        qtbot.wait(1)
        assert _contar_items_visiveis(widget_busca) == 0

        # Cria nova task que bate com o filtro
        task_service_busca.create_task("nova tarefa importante")

        # O signal task_created dispara _reload_tasks que usa self._search_term
        assert _contar_items_visiveis(widget_busca) == 1

    # -----------------------------------------------------------------------
    # Cenário 11 — Reaplicação pós-update e pós-delete
    # -----------------------------------------------------------------------

    def test_reaplica_filtro_apos_update(
        self,
        qtbot: Any,
        task_service_busca: TaskService,
        widget_busca: TodoWidget,
    ) -> None:
        """Com filtro ativo, atualizar um título para bater com o filtro deve
        fazê-la aparecer, e vice-versa."""
        task = task_service_busca.create_task("Título original")

        _aplicar_busca(qtbot, widget_busca, "atualizado")
        qtbot.wait(1)
        assert _contar_items_visiveis(widget_busca) == 0

        # Atualiza para bater com o filtro
        task_service_busca.update_task(task.id, titulo="Título atualizado")

        assert _contar_items_visiveis(widget_busca) == 1

        # Atualiza para não bater mais
        task_service_busca.update_task(task.id, titulo="Título diferente")

        assert _contar_items_visiveis(widget_busca) == 0

    def test_reaplica_filtro_apos_delete(
        self,
        qtbot: Any,
        task_service_busca: TaskService,
        widget_busca: TodoWidget,
    ) -> None:
        """Com filtro ativo, deletar uma task que batia com o filtro deve
        removê-la da lista e exibir label de vazio se for a última."""
        task = task_service_busca.create_task("Tarefa para deletar")

        _aplicar_busca(qtbot, widget_busca, "deletar")
        qtbot.wait(1)
        assert _contar_items_visiveis(widget_busca) == 1
        assert widget_busca._label_empty_search.isHidden()

        # Deleta a task
        task_service_busca.delete_task(task.id)

        assert _contar_items_visiveis(widget_busca) == 0
        # isHidden() funciona sem hierarquia visível (isVisible() requer pais visíveis)
        assert not widget_busca._label_empty_search.isHidden()

    # -----------------------------------------------------------------------
    # Cenário 12 — Busca global vazia: nenhuma task bate, label aparece
    # -----------------------------------------------------------------------

    def test_busca_global_sem_resultados_exibe_label_vazio(
        self,
        qtbot: Any,
        task_service_busca: TaskService,
        widget_busca: TodoWidget,
    ) -> None:
        """Com 3 tasks no banco, buscar 'zzzz' deve exibir o label
        'Nenhuma tarefa encontrada' e nenhum item nas seções."""
        task_service_busca.create_task("Task Alpha")
        task_service_busca.create_task("Task Beta")
        task_service_busca.create_task("Task Gamma")

        _aplicar_busca(qtbot, widget_busca, "zzzz")
        qtbot.wait(1)

        # Label deve estar ativo (não oculto) quando busca retorna zero resultados
        assert not widget_busca._label_empty_search.isHidden()
        assert _contar_items_visiveis(widget_busca) == 0

        # Limpar o campo deve ocultar o label e mostrar todas as tasks
        widget_busca._search_input.clear()
        qtbot.wait(1)

        assert widget_busca._label_empty_search.isHidden()
        assert _contar_items_visiveis(widget_busca) == 3

    # -----------------------------------------------------------------------
    # Cenário adicional — Distribuição por seções com filtro ativo
    # -----------------------------------------------------------------------

    def test_filtro_distribui_tasks_por_secoes_corretas(
        self,
        qtbot: Any,
        task_service_busca: TaskService,
        widget_busca: TodoWidget,
    ) -> None:
        """Tasks filtradas devem ser distribuídas nas seções corretas
        (Hoje, Próximas, Sem data, Concluídas) igual ao comportamento sem filtro."""
        from own_board_list.ui.todo.task_list_item import TaskListItem

        hoje = date.today()
        amanha = hoje + timedelta(days=1)

        task_service_busca.create_task("Busca hoje", data_vencimento=hoje)
        task_service_busca.create_task("Busca próxima", data_vencimento=amanha)
        task_service_busca.create_task("Busca sem data")
        task_concluida = task_service_busca.create_task("Busca concluída")
        task_service_busca.toggle_status(task_concluida.id)

        _aplicar_busca(qtbot, widget_busca, "Busca")
        qtbot.wait(1)

        def _primeiro_widget(group: Any) -> Any:
            layout = group.layout()
            if layout is None:
                return None
            item = layout.itemAt(0)
            return item.widget() if item else None

        assert isinstance(_primeiro_widget(widget_busca._group_hoje), TaskListItem)
        assert isinstance(_primeiro_widget(widget_busca._group_proximas), TaskListItem)
        assert isinstance(_primeiro_widget(widget_busca._group_sem_data), TaskListItem)
        assert isinstance(
            _primeiro_widget(widget_busca._group_concluidas), TaskListItem
        )
