"""
Serviço de orquestração de migrations do banco de dados.

``MigrationService`` é o ponto central de controle para a evolução do schema
SQLite. Ele implementa a sequência completa definida no ADR-005:

1. Detectar versão atual do banco (``schema_version``).
2. Verificar se é versão futura (falhar imediatamente, arquivo intacto).
3. Se há migrations pendentes: criar backup pré-migração.
4. Para cada migration pendente (em ordem crescente de ``versao_destino``):
   a. ``BEGIN IMMEDIATE``
   b. Executar o callable ``Migration.aplicar``
   c. Registrar nova versão em ``schema_version``
   d. ``COMMIT`` (ou ``ROLLBACK`` + restaurar backup em falha)
5. Executar ``PRAGMA integrity_check`` e ``PRAGMA foreign_key_check``.
6. Em caso de sucesso: rotacionar backups (manter 3).
7. Emitir ``MigrationReport``.

Camada: services → database. Não depende de UI (sem PyQt6 neste módulo).
O serviço é instanciado no bootstrap da aplicação antes de criar a UI.
"""

from __future__ import annotations

import shutil
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from own_board_list.database.backup import criar_backup, rotacionar_backups
from own_board_list.database.migrations import (
    MIGRATIONS,
    _criar_tabela_schema_version,
    get_schema_version,
    set_schema_version,
    validar_integridade_pos_migration,
    verificar_versao_futura,
)
from own_board_list.utils.constants import BACKUPS_RETIDOS


@dataclass
class MigrationReport:
    """Resultado da execução do processo de migration.

    Atributos:
        versao_origem: Versão do schema antes da execução (0 = banco novo).
        versao_destino: Versão do schema após a execução.
        backup_path: Caminho do backup criado antes da migration, ou ``None``
            se nenhum backup foi necessário (banco já atualizado ou novo).
        quarentena_path: Caminho do arquivo de quarentena do dia, ou ``None``
            se nenhum registro foi saneado.
        duracao_s: Tempo total de execução em segundos.
        registros_saneados: Número de registros afetados pelo saneamento.
        sucesso: ``True`` se a migration concluiu sem erros.
        erro: Mensagem de erro em caso de falha, ou ``None`` em sucesso.
    """

    versao_origem: int
    versao_destino: int
    backup_path: Path | None = None
    quarentena_path: Path | None = None
    duracao_s: float = 0.0
    registros_saneados: int = 0
    sucesso: bool = True
    erro: str | None = None


class MigrationService:
    """Orquestra a execução de migrations do schema SQLite.

    Instanciar e chamar ``executar(db_path)`` no bootstrap da aplicação,
    antes de criar repositórios ou a interface gráfica.
    """

    def executar(self, db_path: Path) -> MigrationReport:
        """Executa o processo completo de migration para o banco em ``db_path``.

        Sequência (ADR-005):
        1. Abrir conexão e verificar versão futura.
        2. Se sem migrations pendentes → retornar report de no-op.
        3. Criar backup pré-migration.
        4. Para cada migration pendente: BEGIN IMMEDIATE → aplicar → COMMIT.
        5. Validar integridade.
        6. Rotacionar backups.

        Args:
            db_path: Caminho absoluto para o arquivo ``data.db``.

        Returns:
            ``MigrationReport`` com resultado detalhado.

        Note:
            Em caso de falha, o backup pré-migration é mantido e o banco
            é restaurado a partir dele. O ``MigrationReport.sucesso`` será
            ``False`` e ``erro`` conterá a mensagem.
        """
        inicio = time.perf_counter()
        backup_path: Path | None = None

        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")

        try:
            # 1. Criar tabela de controle se não existir e verificar versão futura.
            _criar_tabela_schema_version(conn)
            verificar_versao_futura(conn)

            versao_origem = get_schema_version(conn)

            # Detectar banco legado (tabelas existem sem schema_version).
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'"
            )
            tabelas_existem = cursor.fetchone() is not None
            if versao_origem == 0 and tabelas_existem:
                versao_origem = 1

            # 2. Verificar se há migrations pendentes.
            migrations_pendentes = [
                m for m in MIGRATIONS if m.versao_destino > versao_origem
            ]

            if not migrations_pendentes:
                duracao = time.perf_counter() - inicio
                return MigrationReport(
                    versao_origem=versao_origem,
                    versao_destino=versao_origem,
                    duracao_s=duracao,
                    sucesso=True,
                )

            # 3. Criar backup pré-migration.
            backup_path = criar_backup(db_path, versao_origem)

            # 4. Aplicar migrations pendentes em sequência.
            versao_atual = versao_origem
            for migration in migrations_pendentes:
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    migration.aplicar(conn)
                    set_schema_version(conn, migration.versao_destino)
                    conn.commit()
                    versao_atual = migration.versao_destino
                except Exception as exc:
                    conn.rollback()
                    conn.close()
                    # Restaurar backup.
                    if backup_path and backup_path.exists():
                        shutil.copy2(str(backup_path), str(db_path))
                    duracao = time.perf_counter() - inicio
                    return MigrationReport(
                        versao_origem=versao_origem,
                        versao_destino=versao_atual,
                        backup_path=backup_path,
                        duracao_s=duracao,
                        sucesso=False,
                        erro=(
                            f"Falha na migration v{versao_atual}→"
                            f"v{migration.versao_destino}: {exc}"
                        ),
                    )

            # 5. Validar integridade pós-migration.
            try:
                validar_integridade_pos_migration(conn)
            except RuntimeError as exc:
                conn.close()
                if backup_path and backup_path.exists():
                    shutil.copy2(str(backup_path), str(db_path))
                duracao = time.perf_counter() - inicio
                return MigrationReport(
                    versao_origem=versao_origem,
                    versao_destino=versao_atual,
                    backup_path=backup_path,
                    duracao_s=duracao,
                    sucesso=False,
                    erro=f"Falha na validação de integridade: {exc}",
                )

            # 6. Rotacionar backups.
            rotacionar_backups(db_path, manter=BACKUPS_RETIDOS)

            conn.close()

            # Determinar caminho de quarentena do dia (se existir).
            from own_board_list.database.quarantine import caminho_quarentena_atual

            quarentena_path = caminho_quarentena_atual()
            quarentena_path_final: Path | None = (
                quarentena_path if quarentena_path.exists() else None
            )

            duracao = time.perf_counter() - inicio
            return MigrationReport(
                versao_origem=versao_origem,
                versao_destino=versao_atual,
                backup_path=backup_path,
                quarentena_path=quarentena_path_final,
                duracao_s=duracao,
                sucesso=True,
            )

        except Exception as exc:
            conn.close()
            duracao = time.perf_counter() - inicio
            return MigrationReport(
                versao_origem=0,
                versao_destino=0,
                backup_path=backup_path,
                duracao_s=duracao,
                sucesso=False,
                erro=str(exc),
            )

    def status_versao(self, db_path: Path) -> int:
        """Retorna a versão atual do schema sem executar migrations.

        Abre uma conexão temporária somente-leitura para consultar
        ``schema_version``. Retorna 0 se o banco não existe ou não tem
        a tabela de controle.

        Args:
            db_path: Caminho para o arquivo ``data.db``.

        Returns:
            Versão inteira do schema, ou 0 se indeterminada.
        """
        if not db_path.exists():
            return 0
        conn = sqlite3.connect(str(db_path))
        try:
            versao = get_schema_version(conn)
        except Exception:
            versao = 0
        finally:
            conn.close()
        return versao
