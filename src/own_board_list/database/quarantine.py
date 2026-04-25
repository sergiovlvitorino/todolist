"""
Gerenciamento de quarentena lateral para registros saneados durante migrations.

Quando a migration v1→v2 encontra dados que violam as novas regras de
integridade (prioridade inválida, status desconhecido, coluna inexistente,
datas ausentes), o registro original é preservado aqui — em um arquivo JSON
diário em ``~/.own-board-list/quarantine_YYYYMMDD.json`` — antes de ser
saneado.

Propósito e limitações:
- Quarentena é **somente para inspeção manual** pelo usuário avançado; não há
  UI dedicada nesta versão (spec §"Fora de escopo").
- O arquivo cresce indefinidamente por dia. Rotação manual ou deleção cabe ao
  usuário. Limpeza automática fica para feature futura.
- Nunca inclui dados de produção além do necessário para diagnóstico; satisfaz
  o princípio de privacidade local da constitution.

Formato do arquivo de quarentena (uma entrada por linha, JSON-L)::

    {"tabela": "tasks", "id_original": "...", "motivo": "status_invalido",
     "payload_original": {...}, "saneamento_aplicado": {...}}

Motivos padronizados:
- ``"prioridade_invalida"``
- ``"status_invalido"``
- ``"coluna_inexistente"``
- ``"data_ausente"``
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from own_board_list.utils.constants import QUARENTENA_DIR


@dataclass
class RegistroQuarentena:
    """Representa um registro saneado durante a migration, preservado para auditoria.

    Atributos:
        tabela: Nome da tabela de origem (``"tasks"`` ou ``"kanban_columns"``).
        id_original: Valor da coluna ``id`` do registro afetado.
        motivo: Código do motivo do saneamento. Valores padronizados:
            ``"prioridade_invalida"``, ``"status_invalido"``,
            ``"coluna_inexistente"``, ``"data_ausente"``.
        payload_original: Dicionário com os valores originais do registro
            (snapshot antes do saneamento).
        saneamento_aplicado: Dicionário com os campos e valores aplicados no
            saneamento (ex.: ``{"prioridade": "Média"}``). ``None`` se o
            registro foi rejeitado por completo sem saneamento.
    """

    tabela: str
    id_original: str
    motivo: str
    payload_original: dict[str, Any]
    saneamento_aplicado: dict[str, Any] | None = None


def caminho_quarentena_atual() -> Path:
    """Retorna o caminho do arquivo de quarentena do dia atual.

    O arquivo tem o formato ``quarantine_YYYYMMDD.json`` e fica em
    ``QUARENTENA_DIR`` (``~/.own-board-list/`` por padrão).
    O diretório é criado automaticamente se não existir.
    """
    QUARENTENA_DIR.mkdir(parents=True, exist_ok=True)
    hoje = date.today().strftime("%Y%m%d")
    return QUARENTENA_DIR / f"quarantine_{hoje}.json"


def registrar_em_quarentena(reg: RegistroQuarentena) -> None:
    """Grava um registro de quarentena em modo append no arquivo diário.

    Cada linha do arquivo é um objeto JSON independente (JSON-L / NDJSON).
    A escrita é append-only: cada chamada acrescenta uma linha ao final.
    Não há lock de arquivo — assume execução single-thread no bootstrap
    da aplicação (DT-041).

    Args:
        reg: Registro de quarentena a ser persistido.

    Raises:
        OSError: Se não for possível escrever no arquivo de quarentena.
    """
    caminho = caminho_quarentena_atual()

    # Serializa o dataclass para dict, adicionando timestamp da gravação.
    payload = asdict(reg)
    payload["registrado_em"] = datetime.now(tz=UTC).isoformat()

    linha = json.dumps(payload, ensure_ascii=False, default=_json_default)

    with caminho.open("a", encoding="utf-8") as f:
        f.write(linha + "\n")


def _json_default(obj: Any) -> Any:
    """Serializa tipos não suportados nativamente pelo json.dumps."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Tipo não serializável: {type(obj)!r}")
