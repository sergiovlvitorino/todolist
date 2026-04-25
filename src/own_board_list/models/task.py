"""
Modelo de domínio para tarefas.

Define a dataclass ``Task`` e os enumeradores ``Prioridade`` (Baixa/Média/Alta)
e ``StatusTarefa`` (Pendente/Concluída). Não possui dependências externas além
da stdlib — pode ser instanciado e testado sem banco de dados ou interface
gráfica. A validação básica dos campos ocorre em ``__post_init__``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from own_board_list.models.enums import Prioridade as Prioridade
from own_board_list.models.enums import StatusTarefa as StatusTarefa
from own_board_list.utils.constants import COLUNA_PADRAO, TITULO_MAX_LEN


def parse_datetime(value: str) -> datetime:
    """Faz o parse de uma string ISO 8601 em datetime com timezone UTC.

    Strings sem informação de timezone (dados legacy/naive) são assumidas
    como UTC para manter consistência.
    """
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


@dataclass
class Task:
    """Representa uma tarefa no sistema."""

    titulo: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    descricao: str = ""
    prioridade: Prioridade = Prioridade.MEDIA
    data_vencimento: date | None = None
    status: StatusTarefa = StatusTarefa.PENDENTE
    coluna_kanban: str = field(default_factory=lambda: COLUNA_PADRAO)
    posicao_kanban: int = 0
    criado_em: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    atualizado_em: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def __post_init__(self) -> None:
        """Valida os campos após a inicialização."""
        if not self.titulo or not self.titulo.strip():
            raise ValueError("O título da tarefa não pode ser vazio.")
        if len(self.titulo) > TITULO_MAX_LEN:
            raise ValueError(
                f"O título deve ter no máximo {TITULO_MAX_LEN} caracteres, "
                f"mas tem {len(self.titulo)}."
            )

    def touch(self) -> None:
        """Atualiza o timestamp de modificação para o momento atual (UTC)."""
        self.atualizado_em = datetime.now(tz=UTC)

    def marcar_concluida(self) -> None:
        """Marca a tarefa como concluída e atualiza o timestamp."""
        self.status = StatusTarefa.CONCLUIDA
        self.touch()

    def reabrir(self) -> None:
        """Reabre a tarefa, voltando ao status pendente."""
        self.status = StatusTarefa.PENDENTE
        self.touch()

    def to_dict(self) -> dict[str, Any]:
        """Serializa a tarefa para um dicionário."""
        return {
            "id": self.id,
            "titulo": self.titulo,
            "descricao": self.descricao,
            "prioridade": str(self.prioridade),
            "data_vencimento": (
                self.data_vencimento.isoformat()
                if self.data_vencimento is not None
                else None
            ),
            "status": str(self.status),
            "coluna_kanban": self.coluna_kanban,
            "posicao_kanban": self.posicao_kanban,
            "criado_em": self.criado_em.isoformat(),
            "atualizado_em": self.atualizado_em.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        """Reconstrói uma Task a partir de um dicionário.

        Datetimes sem timezone (dados legacy) são interpretados como UTC.
        """
        data_vencimento: date | None = None
        if data.get("data_vencimento"):
            data_vencimento = date.fromisoformat(data["data_vencimento"])

        return cls(
            id=data["id"],
            titulo=data["titulo"],
            descricao=data.get("descricao", ""),
            prioridade=Prioridade(data.get("prioridade", Prioridade.MEDIA)),
            data_vencimento=data_vencimento,
            status=StatusTarefa(data.get("status", StatusTarefa.PENDENTE)),
            coluna_kanban=data.get("coluna_kanban", COLUNA_PADRAO),
            posicao_kanban=data.get("posicao_kanban", 0),
            criado_em=parse_datetime(data["criado_em"]),
            atualizado_em=parse_datetime(data["atualizado_em"]),
        )
