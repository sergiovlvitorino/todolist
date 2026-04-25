"""
Modelo de domínio para colunas do Kanban.

Define a dataclass ``KanbanColumn``, que representa uma coluna no quadro Kanban
(ex.: "A Fazer", "Em Andamento", "Concluído"). A classe é imutável do ponto de
vista de negócio — alterações de nome ou posição devem passar pelo
``ColumnRepository``. Não possui dependências externas além da stdlib.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from own_board_list.utils.constants import NOME_COLUNA_MAX_LEN


@dataclass
class KanbanColumn:
    """Representa uma coluna no quadro Kanban."""

    nome: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    posicao: int = 0
    criado_em: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def __post_init__(self) -> None:
        """Valida os campos após a inicialização."""
        if not self.nome or not self.nome.strip():
            raise ValueError("O nome da coluna não pode ser vazio.")
        if len(self.nome) > NOME_COLUNA_MAX_LEN:
            raise ValueError(
                f"O nome da coluna deve ter no máximo "
                f"{NOME_COLUNA_MAX_LEN} caracteres, "
                f"mas tem {len(self.nome)}."
            )

    def to_dict(self) -> dict[str, Any]:
        """Serializa a coluna para um dicionário."""
        return {
            "id": self.id,
            "nome": self.nome,
            "posicao": self.posicao,
            "criado_em": self.criado_em.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KanbanColumn:
        """Reconstrói uma KanbanColumn a partir de um dicionário.

        Datetimes sem timezone (dados legacy/naive) são interpretados como UTC.
        """
        dt = datetime.fromisoformat(data["criado_em"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return cls(
            id=data["id"],
            nome=data["nome"],
            posicao=data.get("posicao", 0),
            criado_em=dt,
        )
