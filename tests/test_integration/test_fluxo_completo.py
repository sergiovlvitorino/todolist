"""
Testes de integração: fluxos end-to-end completos.

Cobrem o ciclo de vida completo de tarefas: criar → editar → mover entre
colunas Kanban → concluir → deletar, usando repositório + serviço + banco
SQLite real (em memória), sem mocks na camada de persistência.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from own_board_list.models.task import Prioridade, StatusTarefa, Task
from own_board_list.services.task_service import TaskService
from own_board_list.utils.constants import (
    COLUNA_A_FAZER,
    COLUNA_CONCLUIDO,
    COLUNA_EM_ANDAMENTO,
)


class TestFluxoCriarEditarDeletar:
    """Fluxo: criar → editar → deletar uma tarefa."""

    def test_criar_tarefa_persiste_e_recupera(
        self, task_service_int: TaskService
    ) -> None:
        """Tarefa criada deve ser recuperável pelo ID."""
        task = task_service_int.create_task(
            titulo="Tarefa de Integração",
            descricao="Descrição completa",
            prioridade=Prioridade.ALTA,
        )

        recuperada = task_service_int.get_task_by_id(task.id)

        assert recuperada is not None
        assert recuperada.titulo == "Tarefa de Integração"
        assert recuperada.descricao == "Descrição completa"
        assert recuperada.prioridade == Prioridade.ALTA
        assert recuperada.status == StatusTarefa.PENDENTE
        assert recuperada.coluna_kanban == COLUNA_A_FAZER

    def test_editar_tarefa_persiste_alteracao(
        self, task_service_int: TaskService
    ) -> None:
        """Alteração editada deve ser persistida no banco."""
        task = task_service_int.create_task("Original")

        task_service_int.update_task(
            task.id,
            titulo="Título Editado",
            descricao="Nova descrição",
            prioridade=Prioridade.BAIXA,
        )

        recuperada = task_service_int.get_task_by_id(task.id)
        assert recuperada is not None
        assert recuperada.titulo == "Título Editado"
        assert recuperada.descricao == "Nova descrição"
        assert recuperada.prioridade == Prioridade.BAIXA

    def test_deletar_tarefa_remove_do_banco(
        self, task_service_int: TaskService
    ) -> None:
        """Tarefa deletada não deve ser encontrada no banco."""
        task = task_service_int.create_task("Para Deletar")
        task_id = task.id

        result = task_service_int.delete_task(task_id)

        assert result is True
        assert task_service_int.get_task_by_id(task_id) is None

    def test_fluxo_completo_criar_editar_deletar(
        self, task_service_int: TaskService
    ) -> None:
        """Fluxo sequencial: criar → editar → deletar."""
        # Criar
        task = task_service_int.create_task(
            "Fluxo Completo",
            prioridade=Prioridade.MEDIA,
        )
        assert task_service_int.get_task_by_id(task.id) is not None

        # Editar
        task_service_int.update_task(
            task.id, titulo="Fluxo Atualizado", prioridade=Prioridade.ALTA
        )
        editada = task_service_int.get_task_by_id(task.id)
        assert editada is not None
        assert editada.titulo == "Fluxo Atualizado"

        # Deletar
        task_service_int.delete_task(task.id)
        assert task_service_int.get_task_by_id(task.id) is None


class TestFluxoMovimentoKanban:
    """Fluxo: mover tarefas entre colunas do Kanban."""

    def test_mover_para_em_andamento(self, task_service_int: TaskService) -> None:
        """Task deve mover de 'A Fazer' para 'Em Andamento' com persistência."""
        task = task_service_int.create_task("Iniciar")
        assert task.coluna_kanban == COLUNA_A_FAZER

        task_service_int.move_to_column(task.id, COLUNA_EM_ANDAMENTO, 0)

        recuperada = task_service_int.get_task_by_id(task.id)
        assert recuperada is not None
        assert recuperada.coluna_kanban == COLUNA_EM_ANDAMENTO
        assert recuperada.status == StatusTarefa.PENDENTE

    def test_mover_para_concluido_altera_status(
        self, task_service_int: TaskService
    ) -> None:
        """Mover para 'Concluído' deve setar status CONCLUIDA."""
        task = task_service_int.create_task("Para Concluir")

        task_service_int.move_to_column(task.id, COLUNA_CONCLUIDO, 0)

        recuperada = task_service_int.get_task_by_id(task.id)
        assert recuperada is not None
        assert recuperada.status == StatusTarefa.CONCLUIDA
        assert recuperada.coluna_kanban == COLUNA_CONCLUIDO

    def test_fluxo_completo_kanban_criar_mover_mover_concluir(
        self, task_service_int: TaskService
    ) -> None:
        """Fluxo: A Fazer → Em Andamento → Concluído com persistência em cada etapa."""
        # Criar em A Fazer
        task = task_service_int.create_task("Pipeline Completo")
        assert task_service_int.get_task_by_id(task.id).coluna_kanban == COLUNA_A_FAZER  # type: ignore[union-attr]

        # Mover para Em Andamento
        task_service_int.move_to_column(task.id, COLUNA_EM_ANDAMENTO, 0)
        em_andamento = task_service_int.get_task_by_id(task.id)
        assert em_andamento is not None
        assert em_andamento.coluna_kanban == COLUNA_EM_ANDAMENTO
        assert em_andamento.status == StatusTarefa.PENDENTE

        # Concluir
        task_service_int.move_to_column(task.id, COLUNA_CONCLUIDO, 0)
        concluida = task_service_int.get_task_by_id(task.id)
        assert concluida is not None
        assert concluida.coluna_kanban == COLUNA_CONCLUIDO
        assert concluida.status == StatusTarefa.CONCLUIDA

    def test_mover_de_concluido_retorna_para_pendente(
        self, task_service_int: TaskService
    ) -> None:
        """Mover de 'Concluído' de volta para outra coluna deve setar PENDENTE."""
        task = task_service_int.create_task("Reabrir")
        task_service_int.move_to_column(task.id, COLUNA_CONCLUIDO, 0)

        task_service_int.move_to_column(task.id, COLUNA_A_FAZER, 0)

        recuperada = task_service_int.get_task_by_id(task.id)
        assert recuperada is not None
        assert recuperada.status == StatusTarefa.PENDENTE
        assert recuperada.coluna_kanban == COLUNA_A_FAZER

    def test_posicao_kanban_persiste_ao_mover(
        self, task_service_int: TaskService
    ) -> None:
        """A posição Kanban deve ser persistida corretamente ao mover."""
        task_a = task_service_int.create_task("Task A")
        task_b = task_service_int.create_task("Task B")

        task_service_int.move_to_column(task_a.id, COLUNA_EM_ANDAMENTO, 0)
        task_service_int.move_to_column(task_b.id, COLUNA_EM_ANDAMENTO, 1)

        tasks_em_andamento = task_service_int.get_tasks_by_column(COLUNA_EM_ANDAMENTO)
        assert len(tasks_em_andamento) == 2
        assert tasks_em_andamento[0].posicao_kanban == 0
        assert tasks_em_andamento[1].posicao_kanban == 1


class TestFluxoToggleStatus:
    """Fluxo: alternar status das tarefas."""

    def test_toggle_pendente_para_concluida_e_move_coluna(
        self, task_service_int: TaskService
    ) -> None:
        """Toggle de PENDENTE deve mover para coluna Concluído."""
        task = task_service_int.create_task("Toggle Int")

        result = task_service_int.toggle_status(task.id)

        assert result.status == StatusTarefa.CONCLUIDA
        assert result.coluna_kanban == COLUNA_CONCLUIDO

        recuperada = task_service_int.get_task_by_id(task.id)
        assert recuperada is not None
        assert recuperada.status == StatusTarefa.CONCLUIDA

    def test_toggle_duplo_retorna_ao_estado_original(
        self, task_service_int: TaskService
    ) -> None:
        """Dois toggles consecutivos devem retornar ao estado original."""
        task = task_service_int.create_task("Double Toggle")

        task_service_int.toggle_status(task.id)
        task_service_int.toggle_status(task.id)

        recuperada = task_service_int.get_task_by_id(task.id)
        assert recuperada is not None
        assert recuperada.status == StatusTarefa.PENDENTE
        assert recuperada.coluna_kanban == COLUNA_A_FAZER

    def test_toggle_id_inexistente_lanca_erro(
        self, task_service_int: TaskService
    ) -> None:
        """Toggle em ID inexistente deve lançar ValueError."""
        with pytest.raises(ValueError, match="não encontrada"):
            task_service_int.toggle_status("id-que-nao-existe")


class TestFluxoSignals:
    """Testes de integração verificando os signals Qt em conjunto."""

    def test_signals_sequencia_criar_mover_deletar(
        self, task_service_int: TaskService, qtbot: Any
    ) -> None:
        """Deve emitir signals corretos na sequência criar → mover → deletar."""
        criadas: list[Task] = []
        atualizadas: list[Task] = []
        deletadas: list[str] = []

        task_service_int.task_created.connect(criadas.append)
        task_service_int.task_updated.connect(atualizadas.append)
        task_service_int.task_deleted.connect(deletadas.append)

        task = task_service_int.create_task("Signal Int")
        task_service_int.move_to_column(task.id, COLUNA_EM_ANDAMENTO, 0)
        task_service_int.delete_task(task.id)

        assert len(criadas) == 1
        assert criadas[0].titulo == "Signal Int"
        assert len(atualizadas) >= 1
        assert len(deletadas) == 1
        assert deletadas[0] == task.id


class TestFluxoBusca:
    """Testes de integração com busca de tarefas."""

    def test_busca_retorna_apenas_tasks_correspondentes(
        self, task_service_int: TaskService
    ) -> None:
        """Busca deve filtrar corretamente entre várias tarefas."""
        task_service_int.create_task("Implementar autenticação")
        task_service_int.create_task("Corrigir bug no relatório")
        task_service_int.create_task("Deploy em produção")

        resultado = task_service_int.search_tasks("autenticação")

        assert len(resultado) == 1
        assert resultado[0].titulo == "Implementar autenticação"

    def test_busca_case_insensitive_retorna_correto(
        self, task_service_int: TaskService
    ) -> None:
        """Busca deve ser case insensitive para caracteres ASCII.

        Nota: SQLite LIKE não é case-insensitive para caracteres Unicode
        acentuados (limitação do SQLite). O teste usa apenas ASCII.
        """
        task_service_int.create_task("Tarefa IMPORTANTE")

        resultado = task_service_int.search_tasks("importante")
        assert len(resultado) == 1

    def test_busca_em_descricao(self, task_service_int: TaskService) -> None:
        """Busca deve encontrar pela descrição também."""
        task_service_int.create_task(
            "Tarefa Qualquer",
            descricao="Precisa de autenticação OAuth2",
        )

        resultado = task_service_int.search_tasks("OAuth2")
        assert len(resultado) == 1

    def test_listar_tasks_por_coluna(self, task_service_int: TaskService) -> None:
        """get_tasks_by_column deve retornar apenas tasks da coluna correta."""
        task_service_int.create_task("A Fazer 1")
        task_service_int.create_task("A Fazer 2")
        task_3 = task_service_int.create_task("Em Andamento 1")
        task_service_int.move_to_column(task_3.id, COLUNA_EM_ANDAMENTO, 0)

        tasks_a_fazer = task_service_int.get_tasks_by_column(COLUNA_A_FAZER)
        tasks_em_andamento = task_service_int.get_tasks_by_column(COLUNA_EM_ANDAMENTO)

        assert len(tasks_a_fazer) == 2
        assert len(tasks_em_andamento) == 1


class TestFluxoEdgeCases:
    """Testes de borda no fluxo de integração."""

    def test_criar_multiplas_tasks_na_mesma_coluna(
        self, task_service_int: TaskService
    ) -> None:
        """Múltiplas tasks na mesma coluna devem ter posições diferentes."""
        task_service_int.create_task("Task 1")
        task_service_int.create_task("Task 2")
        task_service_int.create_task("Task 3")

        tasks = task_service_int.get_tasks_by_column(COLUNA_A_FAZER)
        posicoes = [t.posicao_kanban for t in tasks]

        # Não deve haver colisão de posições
        assert len(set(posicoes)) == 3

    def test_update_campo_invalido_nao_altera_banco(
        self, task_service_int: TaskService
    ) -> None:
        """Tentativa de update com campo inválido não deve alterar o banco."""
        task = task_service_int.create_task("Segura no Banco")

        with pytest.raises(ValueError):
            task_service_int.update_task(task.id, campo_inexistente="valor")

        recuperada = task_service_int.get_task_by_id(task.id)
        assert recuperada is not None
        assert recuperada.titulo == "Segura no Banco"

    def test_delete_inexistente_retorna_false(
        self, task_service_int: TaskService
    ) -> None:
        """Deletar ID inexistente deve retornar False sem alterar o banco."""
        task = task_service_int.create_task("Permanece")

        result = task_service_int.delete_task("id-que-nao-existe")

        assert result is False
        assert task_service_int.get_task_by_id(task.id) is not None

    def test_get_all_tasks_retorna_lista_completa(
        self, task_service_int: TaskService
    ) -> None:
        """get_all_tasks deve retornar todas as tarefas do banco."""
        for i in range(5):
            task_service_int.create_task(f"Tarefa {i}")

        todas = task_service_int.get_all_tasks()
        assert len(todas) == 5

    def test_data_vencimento_persiste_e_recupera(
        self, task_service_int: TaskService
    ) -> None:
        """A data de vencimento deve ser persistida e recuperada corretamente."""
        data = date(2026, 12, 31)
        task = task_service_int.create_task("Com Data", data_vencimento=data)

        recuperada = task_service_int.get_task_by_id(task.id)
        assert recuperada is not None
        assert recuperada.data_vencimento == data
