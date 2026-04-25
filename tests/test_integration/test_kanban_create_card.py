"""Testes de integração: criação de card no Kanban (UI + Service + DB).

Cobre TC-080, TC-081, TC-089.
Usa banco SQLite :memory: real — sem mocks na camada de persistência.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtWidgets import QApplication

from own_board_list.models.task import Prioridade, StatusTarefa
from own_board_list.services.task_service import TaskService
from own_board_list.ui.kanban.kanban_widget import KanbanWidget
from own_board_list.utils.constants import (
    COLUNA_A_FAZER,
    COLUNA_CONCLUIDO,
    COLUNA_EM_ANDAMENTO,
)

# ---------------------------------------------------------------------------
# TC-080 — create_task_in_column em coluna "Concluído" nasce CONCLUIDA
# ---------------------------------------------------------------------------


class TestCreateTaskInColumnStatus:
    """TC-080 e TC-081 — Regra coluna→status em create_task_in_column."""

    def test_coluna_concluido_status_concluida(
        self, task_service_int: TaskService
    ) -> None:
        """TC-080: task criada em 'Concluído' deve ter status CONCLUIDA."""
        task = task_service_int.create_task_in_column(
            "Task Concluída", coluna=COLUNA_CONCLUIDO
        )

        recuperada = task_service_int.get_task_by_id(task.id)
        assert recuperada is not None
        assert recuperada.status == StatusTarefa.CONCLUIDA
        assert recuperada.coluna_kanban == COLUNA_CONCLUIDO

    def test_coluna_concluido_emite_signal_task_created(
        self, task_service_int: TaskService
    ) -> None:
        """TC-080: create_task_in_column deve emitir task_created exatamente 1 vez."""
        sinais: list[object] = []
        task_service_int.task_created.connect(sinais.append)

        task_service_int.create_task_in_column("X", coluna=COLUNA_CONCLUIDO)

        assert len(sinais) == 1

    def test_coluna_a_fazer_status_pendente(
        self, task_service_int: TaskService
    ) -> None:
        """TC-081: task criada em 'A Fazer' deve ter status PENDENTE."""
        task = task_service_int.create_task_in_column(
            "Task A Fazer", coluna=COLUNA_A_FAZER
        )

        recuperada = task_service_int.get_task_by_id(task.id)
        assert recuperada is not None
        assert recuperada.status == StatusTarefa.PENDENTE
        assert recuperada.coluna_kanban == COLUNA_A_FAZER

    def test_coluna_em_andamento_status_pendente(
        self, task_service_int: TaskService
    ) -> None:
        """TC-081: task criada em 'Em Andamento' deve ter status PENDENTE."""
        task = task_service_int.create_task_in_column(
            "Em Prog", coluna=COLUNA_EM_ANDAMENTO
        )

        recuperada = task_service_int.get_task_by_id(task.id)
        assert recuperada is not None
        assert recuperada.status == StatusTarefa.PENDENTE
        assert recuperada.coluna_kanban == COLUNA_EM_ANDAMENTO

    def test_card_entra_no_final_da_coluna(self, task_service_int: TaskService) -> None:
        """TC-081: cada novo card deve receber posição = len(tasks na coluna)."""
        t0 = task_service_int.create_task_in_column("Primeiro", coluna=COLUNA_A_FAZER)
        t1 = task_service_int.create_task_in_column("Segundo", coluna=COLUNA_A_FAZER)
        t2 = task_service_int.create_task_in_column("Terceiro", coluna=COLUNA_A_FAZER)

        r0 = task_service_int.get_task_by_id(t0.id)
        r1 = task_service_int.get_task_by_id(t1.id)
        r2 = task_service_int.get_task_by_id(t2.id)

        assert r0 is not None
        assert r1 is not None
        assert r2 is not None
        assert r0.posicao_kanban == 0
        assert r1.posicao_kanban == 1
        assert r2.posicao_kanban == 2

    def test_create_task_in_column_com_prioridade(
        self, task_service_int: TaskService
    ) -> None:
        """Prioridade informada deve ser persistida corretamente."""
        task = task_service_int.create_task_in_column(
            "Alta Prio",
            coluna=COLUNA_A_FAZER,
            prioridade=Prioridade.ALTA,
        )

        recuperada = task_service_int.get_task_by_id(task.id)
        assert recuperada is not None
        assert recuperada.prioridade == Prioridade.ALTA


# ---------------------------------------------------------------------------
# TC-089 — Confirmar form cria card no final e sincroniza Todo List
# ---------------------------------------------------------------------------


class TestIntegracaoUIServiceDB:
    """TC-089 — Fluxo completo: form inline → service → DB → UI."""

    def test_criar_card_via_kanban_widget_aparece_na_coluna(
        self, qtbot: Any, task_service_int: TaskService, column_repo_int: Any
    ) -> None:
        """TC-089: criar card via KanbanWidget persiste e reflete na coluna correta."""
        kanban = KanbanWidget(task_service_int, column_repo_int)
        qtbot.addWidget(kanban)

        # Localiza a coluna "Em Andamento" no widget
        col_widget = next(
            (
                w
                for w in kanban._column_widgets
                if w.property("column_name") == COLUNA_EM_ANDAMENTO
            ),
            None,
        )
        assert col_widget is not None, "Coluna 'Em Andamento' deve existir no board"

        cards_antes = len(col_widget._cards)

        # Simula submit do form inline
        dados = {
            "titulo": "Nova Tarefa X",
            "prioridade": Prioridade.MEDIA,
            "data_vencimento": None,
        }
        col_widget.create_card_submitted.emit(COLUNA_EM_ANDAMENTO, dados)
        QApplication.processEvents()

        # O card deve aparecer como último na coluna
        assert len(col_widget._cards) == cards_antes + 1

    def test_card_criado_e_persistido_no_banco(
        self, qtbot: Any, task_service_int: TaskService, column_repo_int: Any
    ) -> None:
        """TC-089: card criado via UI deve ser persistido no banco."""
        kanban = KanbanWidget(task_service_int, column_repo_int)
        qtbot.addWidget(kanban)

        col_widget = next(
            (
                w
                for w in kanban._column_widgets
                if w.property("column_name") == COLUNA_A_FAZER
            ),
            None,
        )
        assert col_widget is not None

        dados = {
            "titulo": "Persistida no banco",
            "prioridade": Prioridade.BAIXA,
            "data_vencimento": None,
        }
        col_widget.create_card_submitted.emit(COLUNA_A_FAZER, dados)
        QApplication.processEvents()

        tasks_no_banco = task_service_int.get_tasks_by_column(COLUNA_A_FAZER)
        titulos = [t.titulo for t in tasks_no_banco]
        assert "Persistida no banco" in titulos

    def test_task_created_emitido_sincroniza_todo_list(
        self, task_service_int: TaskService
    ) -> None:
        """TC-089: task_created deve ser emitido para sincronização do TodoWidget."""
        sinais_criados: list[object] = []
        task_service_int.task_created.connect(sinais_criados.append)

        task_service_int.create_task_in_column("Sync Todo", coluna=COLUNA_EM_ANDAMENTO)

        assert len(sinais_criados) == 1

    def test_ultimo_card_fica_no_final_da_coluna(
        self, qtbot: Any, task_service_int: TaskService, column_repo_int: Any
    ) -> None:
        """TC-089: último card confirmado deve ter maior posicao_kanban na coluna."""
        # Cria dois cards antes
        task_service_int.create_task_in_column("Primeiro", coluna=COLUNA_EM_ANDAMENTO)
        task_service_int.create_task_in_column("Segundo", coluna=COLUNA_EM_ANDAMENTO)

        terceiro = task_service_int.create_task_in_column(
            "Terceiro", coluna=COLUNA_EM_ANDAMENTO
        )

        tasks = task_service_int.get_tasks_by_column(COLUNA_EM_ANDAMENTO)
        posicoes = [t.posicao_kanban for t in tasks]
        # O último card criado deve ter posição = 2 (final da lista)
        r = task_service_int.get_task_by_id(terceiro.id)
        assert r is not None
        assert r.posicao_kanban == max(posicoes)
