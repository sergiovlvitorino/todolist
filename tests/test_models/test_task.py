"""Testes do modelo Task."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from own_board_list.models.task import Prioridade, StatusTarefa, Task
from own_board_list.utils.constants import DESCRICAO_MAX_LEN


class TestTaskCreation:
    """Testes de criação e validação da Task."""

    def test_criacao_valida(self) -> None:
        """Deve criar uma tarefa com campos padrão corretamente."""
        task = Task(titulo="Minha Tarefa")

        assert task.titulo == "Minha Tarefa"
        assert task.descricao == ""
        assert task.prioridade == Prioridade.MEDIA
        assert task.data_vencimento is None
        assert task.status == StatusTarefa.PENDENTE
        assert task.coluna_kanban == "A Fazer"
        assert task.posicao_kanban == 0
        assert task.id != ""
        assert isinstance(task.criado_em, datetime)
        assert isinstance(task.atualizado_em, datetime)

    def test_titulo_vazio_lanca_value_error(self) -> None:
        """Deve lançar ValueError quando o título é uma string vazia."""
        with pytest.raises(ValueError, match="título.*vazio"):
            Task(titulo="")

    def test_titulo_apenas_espacos_lanca_value_error(self) -> None:
        """Deve lançar ValueError quando o título contém apenas espaços."""
        with pytest.raises(ValueError, match="título.*vazio"):
            Task(titulo="   ")

    def test_titulo_acima_de_200_chars_lanca_value_error(self) -> None:
        """Deve lançar ValueError quando o título excede 200 caracteres."""
        titulo_longo = "A" * 201
        with pytest.raises(ValueError, match="200"):
            Task(titulo=titulo_longo)

    def test_titulo_com_exatamente_200_chars_e_valido(self) -> None:
        """Deve aceitar título com exatamente 200 caracteres."""
        titulo = "A" * 200
        task = Task(titulo=titulo)
        assert len(task.titulo) == 200

    def test_descricao_acima_de_5000_chars_lanca_value_error(self) -> None:
        """Deve lançar ValueError quando a descrição excede 5000 caracteres."""
        descricao_longa = "X" * (DESCRICAO_MAX_LEN + 1)
        with pytest.raises(ValueError, match="descrição"):
            Task(titulo="Título OK", descricao=descricao_longa)

    def test_descricao_com_exatamente_5000_chars_e_valida(self) -> None:
        """Deve aceitar descrição com exatamente 5000 caracteres (limite)."""
        descricao = "Y" * DESCRICAO_MAX_LEN
        task = Task(titulo="Título OK", descricao=descricao)
        assert len(task.descricao) == DESCRICAO_MAX_LEN

    def test_descricao_com_4999_chars_e_valida(self) -> None:
        """Deve aceitar descrição com limite-1 caracteres."""
        descricao = "Z" * (DESCRICAO_MAX_LEN - 1)
        task = Task(titulo="Título OK", descricao=descricao)
        assert len(task.descricao) == DESCRICAO_MAX_LEN - 1

    def test_posicao_kanban_negativa_lanca_value_error(self) -> None:
        """Deve lançar ValueError quando posicao_kanban é negativa."""
        with pytest.raises(ValueError, match="posição Kanban"):
            Task(titulo="Título OK", posicao_kanban=-1)

    def test_posicao_kanban_zero_e_valida(self) -> None:
        """Deve aceitar posicao_kanban igual a zero."""
        task = Task(titulo="Título OK", posicao_kanban=0)
        assert task.posicao_kanban == 0

    def test_posicao_kanban_positiva_e_valida(self) -> None:
        """Deve aceitar posicao_kanban maior que zero."""
        task = Task(titulo="Título OK", posicao_kanban=10)
        assert task.posicao_kanban == 10

    def test_criacao_com_todos_os_campos(self) -> None:
        """Deve criar uma tarefa com todos os campos preenchidos."""
        vencimento = date(2025, 12, 31)
        task = Task(
            titulo="Tarefa Completa",
            descricao="Uma descrição",
            prioridade=Prioridade.ALTA,
            data_vencimento=vencimento,
            status=StatusTarefa.PENDENTE,
            coluna_kanban="Em Andamento",
            posicao_kanban=2,
        )

        assert task.titulo == "Tarefa Completa"
        assert task.descricao == "Uma descrição"
        assert task.prioridade == Prioridade.ALTA
        assert task.data_vencimento == vencimento
        assert task.coluna_kanban == "Em Andamento"
        assert task.posicao_kanban == 2


class TestTaskStatus:
    """Testes das transições de status da Task."""

    def test_marcar_concluida(self) -> None:
        """Deve mudar o status para CONCLUIDA e atualizar timestamp."""
        task = Task(titulo="Tarefa")
        antes = task.atualizado_em

        task.marcar_concluida()

        assert task.status == StatusTarefa.CONCLUIDA
        assert task.atualizado_em >= antes

    def test_reabrir(self) -> None:
        """Deve voltar o status para PENDENTE."""
        task = Task(titulo="Tarefa")
        task.marcar_concluida()

        task.reabrir()

        assert task.status == StatusTarefa.PENDENTE

    def test_ids_unicos(self) -> None:
        """Cada tarefa deve ter um ID único (UUID)."""
        task1 = Task(titulo="Tarefa 1")
        task2 = Task(titulo="Tarefa 2")
        assert task1.id != task2.id


class TestTaskSerialization:
    """Testes de serialização/desserialização da Task."""

    def test_to_dict_sem_data_vencimento(self) -> None:
        """Deve serializar corretamente sem data de vencimento."""
        task = Task(titulo="Tarefa")
        d = task.to_dict()

        assert d["titulo"] == "Tarefa"
        assert d["data_vencimento"] is None
        assert isinstance(d["criado_em"], str)
        assert isinstance(d["atualizado_em"], str)

    def test_to_dict_com_data_vencimento(self) -> None:
        """Deve serializar a data de vencimento como ISO string."""
        vencimento = date(2025, 6, 15)
        task = Task(titulo="Tarefa", data_vencimento=vencimento)
        d = task.to_dict()

        assert d["data_vencimento"] == "2025-06-15"

    def test_from_dict_round_trip_sem_data(self) -> None:
        """Deve reconstruir a tarefa idêntica a partir do dicionário."""
        task = Task(titulo="Round Trip", descricao="Teste", prioridade=Prioridade.ALTA)
        d = task.to_dict()
        reconstruida = Task.from_dict(d)

        assert reconstruida.id == task.id
        assert reconstruida.titulo == task.titulo
        assert reconstruida.descricao == task.descricao
        assert reconstruida.prioridade == task.prioridade
        assert reconstruida.data_vencimento is None
        assert reconstruida.status == task.status

    def test_from_dict_round_trip_com_data(self) -> None:
        """Deve reconstruir a tarefa com data de vencimento corretamente."""
        vencimento = date(2025, 3, 20)
        task = Task(titulo="Com Data", data_vencimento=vencimento)
        d = task.to_dict()
        reconstruida = Task.from_dict(d)

        assert reconstruida.data_vencimento == vencimento
