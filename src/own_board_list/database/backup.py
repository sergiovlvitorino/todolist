"""
Gerenciamento de backups do banco de dados SQLite antes de migrations.

Fornece três funções públicas:

- ``criar_backup`` — copia o arquivo ``data.db`` atual para um arquivo de
  backup com nome que inclui a versão de origem e o timestamp UTC.
- ``rotacionar_backups`` — mantém apenas os N arquivos de backup mais recentes,
  apagando os excedentes (política FIFO simples).
- ``listar_backups`` — retorna os arquivos de backup existentes ordenados do
  mais antigo para o mais recente.

Formato do nome do arquivo de backup::

    data_backup_vN_YYYYMMDDTHHMMSS.db

Exemplo::

    data_backup_v1_20260425T183000.db

Os backups ficam no mesmo diretório do arquivo principal (``~/.own-board-list/``
em produção).  Não há sincronização remota — princípio de privacidade local
(constitution §"Princípios invioláveis").
"""

from __future__ import annotations

import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

from own_board_list.utils.constants import BACKUPS_RETIDOS

# Padrão de nome de arquivo de backup: data_backup_vN_YYYYMMDDTHHMMSS.db
_BACKUP_PATTERN = re.compile(r"^data_backup_v(\d+)_(\d{8}T\d{6})\.db$")


def criar_backup(db_path: Path, versao_origem: int) -> Path:
    """Cria uma cópia de segurança do banco de dados antes da migration.

    Args:
        db_path: Caminho do arquivo ``.db`` de origem.
        versao_origem: Versão do schema atual (antes da migration).

    Returns:
        Caminho do arquivo de backup criado.

    Raises:
        FileNotFoundError: Se ``db_path`` não existir.
        OSError: Se não for possível copiar o arquivo.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Arquivo de banco de dados não encontrado: {db_path}")

    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%S")
    nome_backup = f"data_backup_v{versao_origem}_{timestamp}.db"
    backup_path = db_path.parent / nome_backup

    shutil.copy2(str(db_path), str(backup_path))
    return backup_path


def listar_backups(db_path: Path) -> list[Path]:
    """Lista backups no diretório de ``db_path``, do mais antigo ao mais recente.

    Considera apenas arquivos com o padrão de nome
    ``data_backup_vN_YYYYMMDDTHHMMSS.db``. A ordenação é lexicográfica
    pelo timestamp, o que coincide com a ordem cronológica dada a estampa
    ISO 8601 sem separadores.

    Args:
        db_path: Caminho do arquivo ``.db`` principal (usado para encontrar
            o diretório de backups).

    Returns:
        Lista de Paths dos arquivos de backup, ordenados do mais antigo ao
        mais recente.
    """
    diretorio = db_path.parent
    backups = [
        f for f in diretorio.iterdir() if f.is_file() and _BACKUP_PATTERN.match(f.name)
    ]
    # Ordenação pelo nome (timestamp lexicográfico = cronológico)
    backups.sort(key=lambda p: p.name)
    return backups


def rotacionar_backups(
    db_path: Path,
    manter: int = BACKUPS_RETIDOS,
) -> list[Path]:
    """Remove backups excedentes, mantendo apenas os ``manter`` mais recentes.

    Usa política FIFO: os arquivos mais antigos são apagados primeiro.

    Args:
        db_path: Caminho do arquivo ``.db`` principal.
        manter: Número máximo de backups a conservar. Padrão: ``BACKUPS_RETIDOS``.

    Returns:
        Lista de Paths dos arquivos removidos (pode ser vazia).

    Raises:
        ValueError: Se ``manter`` < 1.
    """
    if manter < 1:
        raise ValueError(f"'manter' deve ser >= 1, recebeu {manter}.")

    backups = listar_backups(db_path)
    excedentes = backups[: max(0, len(backups) - manter)]

    removidos: list[Path] = []
    for backup in excedentes:
        try:
            backup.unlink()
            removidos.append(backup)
        except OSError:
            # Falha ao remover backup excedente não é crítica; loga e continua.
            pass

    return removidos
