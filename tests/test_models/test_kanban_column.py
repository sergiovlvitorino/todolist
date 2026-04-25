"""Testes unitários do modelo KanbanColumn."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from own_board_list.models.kanban_column import KanbanColumn
from own_board_list.utils.constants import NOME_COLUNA_MAX_LEN


class TestKanbanColumnCreate:
    """Testes de criação de KanbanColumn."""

    def test_criacao_valida(self) -> None:
        """Deve criar uma coluna com os campos padrão corretos."""
        col = KanbanColumn(nome="Revisão")

        assert col.nome == "Revisão"
        assert col.posicao == 0
        assert col.id != ""
        assert col.criado_em.tzinfo is not None

    def test_criacao_com_posicao(self) -> None:
        """Deve criar uma coluna com posição personalizada."""
        col = KanbanColumn(nome="Em Teste", posicao=2)

        assert col.posicao == 2

    def test_criacao_com_id_personalizado(self) -> None:
        """Deve aceitar um ID fornecido explicitamente."""
        col = KanbanColumn(nome="Col", id="meu-id-fixo")

        assert col.id == "meu-id-fixo"

    def test_ids_unicos_entre_instancias(self) -> None:
        """Cada instância deve ter um ID único gerado automaticamente."""
        col1 = KanbanColumn(nome="Col 1")
        col2 = KanbanColumn(nome="Col 2")

        assert col1.id != col2.id


class TestKanbanColumnValidacao:
    """Testes de validação do KanbanColumn."""

    def test_nome_vazio_levanta_value_error(self) -> None:
        """Deve levantar ValueError quando o nome é vazio."""
        with pytest.raises(ValueError, match="nome da coluna não pode ser vazio"):
            KanbanColumn(nome="")

    def test_nome_apenas_espacos_levanta_value_error(self) -> None:
        """Deve levantar ValueError quando o nome contém apenas espaços."""
        with pytest.raises(ValueError, match="nome da coluna não pode ser vazio"):
            KanbanColumn(nome="   ")

    def test_mensagem_nome_vazio_menciona_espacos(self) -> None:
        """Mensagem de erro deve mencionar que espaços também são inválidos."""
        with pytest.raises(ValueError, match="espaços"):
            KanbanColumn(nome="")

    def test_nome_acima_de_100_chars_levanta_value_error(self) -> None:
        """Deve levantar ValueError quando o nome excede 100 caracteres."""
        nome_longo = "A" * (NOME_COLUNA_MAX_LEN + 1)
        with pytest.raises(ValueError, match="nome da coluna"):
            KanbanColumn(nome=nome_longo)

    def test_nome_com_exatamente_100_chars_e_valido(self) -> None:
        """Deve aceitar nome com exatamente 100 caracteres (limite)."""
        nome = "B" * NOME_COLUNA_MAX_LEN
        col = KanbanColumn(nome=nome)
        assert len(col.nome) == NOME_COLUNA_MAX_LEN

    def test_nome_com_99_chars_e_valido(self) -> None:
        """Deve aceitar nome com limite-1 caracteres."""
        nome = "C" * (NOME_COLUNA_MAX_LEN - 1)
        col = KanbanColumn(nome=nome)
        assert len(col.nome) == NOME_COLUNA_MAX_LEN - 1

    def test_posicao_negativa_levanta_value_error(self) -> None:
        """Deve levantar ValueError quando posicao é negativa."""
        with pytest.raises(ValueError, match="posição da coluna"):
            KanbanColumn(nome="Col Válida", posicao=-1)

    def test_posicao_zero_e_valida(self) -> None:
        """Deve aceitar posicao igual a zero."""
        col = KanbanColumn(nome="Col Válida", posicao=0)
        assert col.posicao == 0

    def test_posicao_positiva_e_valida(self) -> None:
        """Deve aceitar posicao maior que zero."""
        col = KanbanColumn(nome="Col Válida", posicao=5)
        assert col.posicao == 5


class TestKanbanColumnToDict:
    """Testes da serialização to_dict."""

    def test_to_dict_contem_todas_as_chaves(self) -> None:
        """O dicionário deve conter todas as chaves esperadas."""
        col = KanbanColumn(nome="A Fazer", posicao=0)
        d = col.to_dict()

        assert set(d.keys()) == {"id", "nome", "posicao", "criado_em"}

    def test_to_dict_valores_corretos(self) -> None:
        """Os valores do dicionário devem refletir os campos da instância."""
        col = KanbanColumn(nome="Em Andamento", posicao=1, id="abc-123")
        d = col.to_dict()

        assert d["id"] == "abc-123"
        assert d["nome"] == "Em Andamento"
        assert d["posicao"] == 1
        assert isinstance(d["criado_em"], str)

    def test_to_dict_criado_em_e_iso_string(self) -> None:
        """criado_em deve ser uma string ISO 8601 válida."""
        col = KanbanColumn(nome="Col")
        d = col.to_dict()

        # Não deve levantar exceção
        parsed = datetime.fromisoformat(d["criado_em"])
        assert parsed is not None


class TestKanbanColumnFromDict:
    """Testes da desserialização from_dict."""

    def test_from_dict_reconstroi_coluna(self) -> None:
        """Deve reconstruir uma KanbanColumn a partir de um dicionário válido."""
        agora = datetime.now(tz=UTC).isoformat()
        d = {"id": "xpto-99", "nome": "Concluído", "posicao": 2, "criado_em": agora}

        col = KanbanColumn.from_dict(d)

        assert col.id == "xpto-99"
        assert col.nome == "Concluído"
        assert col.posicao == 2

    def test_from_dict_posicao_padrao_zero(self) -> None:
        """Posição deve ser 0 quando ausente no dicionário."""
        agora = datetime.now(tz=UTC).isoformat()
        d = {"id": "abc", "nome": "Col", "criado_em": agora}

        col = KanbanColumn.from_dict(d)

        assert col.posicao == 0

    def test_from_dict_datetime_naive_recebe_utc(self) -> None:
        """Datetime sem timezone (legacy) deve ser tratado como UTC."""
        naive_iso = "2024-01-15T10:30:00"
        d = {"id": "abc", "nome": "Col", "posicao": 0, "criado_em": naive_iso}

        col = KanbanColumn.from_dict(d)

        assert col.criado_em.tzinfo is not None
        assert col.criado_em.tzinfo == UTC


class TestKanbanColumnRoundTrip:
    """Testes de round-trip de serialização."""

    def test_round_trip_to_dict_from_dict(self) -> None:
        """Deve reconstruir uma coluna idêntica após to_dict -> from_dict."""
        original = KanbanColumn(nome="Sprint 1", posicao=3, id="round-trip-id")
        d = original.to_dict()
        reconstruida = KanbanColumn.from_dict(d)

        assert reconstruida.id == original.id
        assert reconstruida.nome == original.nome
        assert reconstruida.posicao == original.posicao
        # Compara sem timezone para evitar diferença de representação naive vs aware
        assert reconstruida.criado_em.replace(tzinfo=None) == (
            original.criado_em.replace(tzinfo=None)
        )
