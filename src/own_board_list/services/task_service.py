"""
Serviço de negócio para gerenciamento de tarefas.

``TaskService`` herda de ``QObject`` e atua como ponto central de orquestração:
recebe comandos da UI, delega persistência aos repositórios e emite signals Qt
(``task_created``, ``task_updated``, ``task_deleted``, ``tasks_reloaded``) para
manter as abas Todo List e Kanban sincronizadas sem acoplamento direto entre
elas. Encapsula também as regras de negócio de transição de status — como mover
automaticamente uma tarefa para a coluna "Concluído" ao marcá-la como concluída.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from own_board_list.database.column_repository import ColumnRepository
from own_board_list.database.task_repository import TaskRepository
from own_board_list.models.task import Prioridade, StatusTarefa, Task
from own_board_list.utils.constants import COLUNA_CONCLUIDO, COLUNA_PADRAO


class TaskService(QObject):
    """Orquestra as operações sobre tarefas e emite signals Qt para a UI."""

    task_created = pyqtSignal(object)  # Task
    task_updated = pyqtSignal(object)  # Task
    task_deleted = pyqtSignal(str)  # task_id
    tasks_reloaded = pyqtSignal(list)  # list[Task]

    def __init__(
        self,
        task_repo: TaskRepository,
        column_repo: ColumnRepository,
        parent: QObject | None = None,
    ) -> None:
        """Inicializa o serviço com os repositórios necessários."""
        super().__init__(parent)
        self._task_repo = task_repo
        self._column_repo = column_repo

    def _validar_coluna_existe(self, coluna: str) -> None:
        """Levanta ValueError se a coluna informada não existe no banco.

        Precursor de DT-013 (FK real entre tasks e kanban_columns). Esta guarda
        mínima evita tarefas órfãs invisíveis no Kanban enquanto a FK não é
        implementada.
        """
        nomes_existentes = {c.nome for c in self._column_repo.get_all()}
        if coluna not in nomes_existentes:
            raise ValueError(
                f"A coluna '{coluna}' não existe. "
                f"Colunas disponíveis: {sorted(nomes_existentes)}."
            )

    def create_task(
        self,
        titulo: str,
        descricao: str = "",
        prioridade: Prioridade = Prioridade.MEDIA,
        data_vencimento: date | None = None,
        coluna_kanban: str = COLUNA_PADRAO,
    ) -> Task:
        """Cria e persiste uma nova tarefa, emitindo o signal task_created."""
        self._validar_coluna_existe(coluna_kanban)

        # Calcula a próxima posição na coluna
        tasks_na_coluna = self._task_repo.get_by_column(coluna_kanban)
        posicao = len(tasks_na_coluna)

        task = Task(
            titulo=titulo,
            descricao=descricao,
            prioridade=prioridade,
            data_vencimento=data_vencimento,
            coluna_kanban=coluna_kanban,
            posicao_kanban=posicao,
        )
        self._task_repo.create(task)
        self.task_created.emit(task)
        return task

    # Campos que podem ser modificados via update_task
    _CAMPOS_EDITAVEIS: frozenset[str] = frozenset(
        {
            "titulo",
            "descricao",
            "prioridade",
            "data_vencimento",
            "coluna_kanban",
            "posicao_kanban",
        }
    )

    def update_task(self, task_id: str, **kwargs: Any) -> Task:
        """Atualiza campos de uma tarefa existente e emite task_updated."""
        campos_invalidos = set(kwargs) - self._CAMPOS_EDITAVEIS
        if campos_invalidos:
            raise ValueError(f"Campos não editáveis: {campos_invalidos}")

        if "coluna_kanban" in kwargs:
            self._validar_coluna_existe(kwargs["coluna_kanban"])

        task = self._task_repo.get_by_id(task_id)
        if task is None:
            raise ValueError(f"Tarefa com ID '{task_id}' não encontrada.")

        for key, value in kwargs.items():
            setattr(task, key, value)

        task.touch()
        self._task_repo.update(task)
        self.task_updated.emit(task)
        return task

    def delete_task(self, task_id: str) -> bool:
        """Remove uma tarefa e emite task_deleted. Retorna True se removeu."""
        removed = self._task_repo.delete(task_id)
        if removed:
            self.task_deleted.emit(task_id)
        return removed

    def toggle_status(self, task_id: str) -> Task:
        """Alterna o status da tarefa entre PENDENTE e CONCLUIDA.

        - PENDENTE → CONCLUIDA: move para a coluna "Concluído"
        - CONCLUIDA → PENDENTE: move para a coluna "A Fazer"
        """
        task = self._task_repo.get_by_id(task_id)
        if task is None:
            raise ValueError(f"Tarefa com ID '{task_id}' não encontrada.")

        if task.status == StatusTarefa.PENDENTE:
            task.marcar_concluida()
            task.coluna_kanban = COLUNA_CONCLUIDO
            tasks_concluidas = self._task_repo.get_by_column(COLUNA_CONCLUIDO)
            task.posicao_kanban = len(tasks_concluidas)
        else:
            task.reabrir()
            task.coluna_kanban = COLUNA_PADRAO
            tasks_a_fazer = self._task_repo.get_by_column(COLUNA_PADRAO)
            task.posicao_kanban = len(tasks_a_fazer)

        self._task_repo.update(task)
        self.task_updated.emit(task)
        return task

    def move_to_column(self, task_id: str, coluna: str, posicao: int) -> Task:
        """Move uma tarefa para outra coluna Kanban.

        Ajusta automaticamente o status conforme a coluna destino:
        - Coluna "Concluído" → seta status CONCLUIDA
        - Saindo de "Concluído" para outra coluna → seta status PENDENTE
        """
        self._validar_coluna_existe(coluna)

        task = self._task_repo.get_by_id(task_id)
        if task is None:
            raise ValueError(f"Tarefa com ID '{task_id}' não encontrada.")

        task.coluna_kanban = coluna
        task.posicao_kanban = posicao

        if coluna == COLUNA_CONCLUIDO:
            task.marcar_concluida()
        elif task.status == StatusTarefa.CONCLUIDA:
            task.reabrir()

        self._task_repo.update(task)
        self.task_updated.emit(task)
        return task

    def get_task_by_id(self, task_id: str) -> Task | None:
        """Retorna uma tarefa pelo ID, ou None se não encontrada."""
        return self._task_repo.get_by_id(task_id)

    def get_all_tasks(self) -> list[Task]:
        """Retorna todas as tarefas."""
        return self._task_repo.get_all()

    def get_tasks_by_column(self, coluna: str) -> list[Task]:
        """Retorna as tarefas de uma coluna específica."""
        return self._task_repo.get_by_column(coluna)

    def bulk_create_tasks(self, tasks: list[Task]) -> None:
        """Persiste uma lista de tarefas em lote sem emitir signal por tarefa.

        Delega para ``TaskRepository.bulk_insert`` que usa ``executemany`` em
        uma única transação — eficiente para importação em massa e seeders de
        teste. Nenhum signal ``task_created`` é emitido individualmente;
        o chamador é responsável por notificar a UI se necessário (ex.: chamando
        ``tasks_reloaded.emit`` ou recarregando manualmente).

        [DECISÃO] Método silencioso (sem signal por task)
          Alternativas: A) emitir signal agregador tasks_bulk_created |
                        B) sem signal (silencioso)
          Escolha: B
          Por quê: o caso de uso principal é seeder de teste e importação;
                   a UI que precisar reagir deve recarregar explicitamente.
          Documentado: DT-034.
        """
        self._task_repo.bulk_insert(tasks)

    def create_task_in_column(
        self,
        titulo: str,
        coluna: str,
        prioridade: Prioridade = Prioridade.MEDIA,
        data_vencimento: date | None = None,
    ) -> Task:
        """Cria tarefa já associada à coluna informada, aplicando a regra coluna→status.

        Regra: coluna "Concluído" → status CONCLUIDA; demais → PENDENTE.
        Card sempre entra no final da coluna (posição = len(tasks_na_coluna)).
        Emite task_created.
        """
        self._validar_coluna_existe(coluna)

        tasks_na_coluna = self._task_repo.get_by_column(coluna)
        posicao = len(tasks_na_coluna)

        task = Task(
            titulo=titulo,
            prioridade=prioridade,
            data_vencimento=data_vencimento,
            coluna_kanban=coluna,
            posicao_kanban=posicao,
        )

        if coluna == COLUNA_CONCLUIDO:
            task.marcar_concluida()

        self._task_repo.create(task)
        self.task_created.emit(task)
        return task

    def search_tasks(self, query: str) -> list[Task]:
        """Pesquisa tarefas por texto no título ou descrição."""
        return self._task_repo.search(query)
