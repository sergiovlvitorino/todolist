"""
Enumeradores de domínio do projeto Own Board List.

Módulo isolado para evitar dependência circular entre ``task.py`` e
``constants.py``. Ambos importam daqui sem criar ciclo.
"""

from __future__ import annotations

from enum import StrEnum


class Prioridade(StrEnum):
    """Nível de prioridade de uma tarefa."""

    BAIXA = "Baixa"
    MEDIA = "Média"
    ALTA = "Alta"


class StatusTarefa(StrEnum):
    """Status atual de uma tarefa."""

    PENDENTE = "Pendente"
    CONCLUIDA = "Concluída"
