"""Testes de backup e quarentena do banco de dados.

Cobre:
- TC-101: rotacionar_backups mantém apenas as 3 mais recentes; criar_backup
  rejeita arquivo inexistente; listar_backups ordenado por nome (mtime simulado)
- TC-095: registrar_em_quarentena com motivo ``prioridade_invalida``; linha em
  quarentena com payload preservado
- TC-096: registrar_em_quarentena com motivo ``status_invalido``; payload original
  preservado fielmente
- TC-097: registrar_em_quarentena com motivo ``coluna_inexistente``; payload
  preservado, saneamento indicado
- TC-098: registrar_em_quarentena com motivo ``data_ausente``; payload preservado
- Edge cases: diretório de quarentena criado automaticamente; arquivos de dias
  diferentes são separados; múltiplas chamadas no mesmo dia são append-only;
  estrutura RegistroQuarentena correta
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from own_board_list.database.backup import (
    criar_backup,
    listar_backups,
    rotacionar_backups,
)
from own_board_list.database.quarantine import (
    RegistroQuarentena,
    caminho_quarentena_atual,
    registrar_em_quarentena,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_file(tmp_path: Path) -> Path:
    """Cria um arquivo .db temporário simulando o banco de dados."""
    db = tmp_path / "data.db"
    db.write_bytes(b"SQLite format 3\x00" + b"\x00" * 84)
    return db


@pytest.fixture
def quarentena_dir(tmp_path: Path) -> Path:
    """Diretório temporário para arquivos de quarentena."""
    return tmp_path / "quarantine"


# ---------------------------------------------------------------------------
# TC-101 — Backup: criação, listagem e rotação
# ---------------------------------------------------------------------------


class TestCriarBackup:
    """TC-101 (parcial) — criar_backup cria arquivo com nome correto."""

    def test_criar_backup_retorna_path_existente(self, db_file: Path) -> None:
        """Backup criado deve existir no sistema de arquivos."""
        backup_path = criar_backup(db_file, versao_origem=1)

        assert backup_path.exists()
        assert backup_path.parent == db_file.parent

    def test_criar_backup_nome_inclui_versao_e_timestamp(self, db_file: Path) -> None:
        """Nome do backup deve seguir padrão data_backup_vN_YYYYMMDDTHHMMSS.db."""
        backup_path = criar_backup(db_file, versao_origem=1)
        nome = backup_path.name

        assert nome.startswith("data_backup_v1_")
        assert nome.endswith(".db")
        # timestamp: 8 dígitos + T + 6 dígitos
        partes = nome.removeprefix("data_backup_v1_").removesuffix(".db")
        assert len(partes) == 15  # YYYYMMDDTHHMMSS
        assert "T" in partes

    def test_criar_backup_versao_diferente_no_nome(self, db_file: Path) -> None:
        """Versão informada deve aparecer no nome do arquivo."""
        backup_path = criar_backup(db_file, versao_origem=2)

        assert "v2" in backup_path.name

    def test_criar_backup_conteudo_identico_ao_original(self, db_file: Path) -> None:
        """Conteúdo do backup deve ser byte-a-byte igual ao original."""
        conteudo_original = db_file.read_bytes()
        backup_path = criar_backup(db_file, versao_origem=1)

        assert backup_path.read_bytes() == conteudo_original

    def test_criar_backup_arquivo_inexistente_levanta_file_not_found(
        self, tmp_path: Path
    ) -> None:
        """TC-101 — criar_backup deve rejeitar arquivo inexistente."""
        inexistente = tmp_path / "nao_existe.db"

        with pytest.raises(FileNotFoundError, match="nao_existe.db"):
            criar_backup(inexistente, versao_origem=1)


class TestListarBackups:
    """TC-101 (parcial) — listar_backups retorna lista ordenada por nome."""

    def test_listar_backups_vazio_sem_arquivos(self, db_file: Path) -> None:
        """Sem backups no diretório, lista deve ser vazia."""
        resultado = listar_backups(db_file)

        assert resultado == []

    def test_listar_backups_ignora_arquivos_fora_do_padrao(self, db_file: Path) -> None:
        """Arquivos com nomes fora do padrão não devem ser incluídos."""
        (db_file.parent / "outro_arquivo.db").write_bytes(b"x")
        (db_file.parent / "data.db.bak").write_bytes(b"x")
        (db_file.parent / "data_backup_sem_versao.db").write_bytes(b"x")

        resultado = listar_backups(db_file)

        assert resultado == []

    def test_listar_backups_ordena_por_nome_cronologico(self, db_file: Path) -> None:
        """TC-101 — lista ordenada do mais antigo ao mais recente."""
        dir_ = db_file.parent
        # Cria arquivos com nomes que já contêm timestamps em ordem
        nomes = [
            "data_backup_v1_20260101T100000.db",
            "data_backup_v1_20260102T100000.db",
            "data_backup_v1_20260103T100000.db",
        ]
        for nome in nomes:
            (dir_ / nome).write_bytes(b"backup")

        resultado = listar_backups(db_file)

        assert [p.name for p in resultado] == nomes

    def test_listar_backups_ordem_independe_de_criacao_no_fs(
        self, db_file: Path
    ) -> None:
        """Ordenação é lexicográfica pelo nome, não por mtime do sistema de arquivos."""
        dir_ = db_file.parent
        # Cria em ordem invertida para garantir que não é por mtime
        nomes_invertidos = [
            "data_backup_v1_20260103T100000.db",
            "data_backup_v1_20260101T100000.db",
            "data_backup_v1_20260102T100000.db",
        ]
        for nome in nomes_invertidos:
            (dir_ / nome).write_bytes(b"backup")

        resultado = listar_backups(db_file)

        assert resultado[0].name == "data_backup_v1_20260101T100000.db"
        assert resultado[1].name == "data_backup_v1_20260102T100000.db"
        assert resultado[2].name == "data_backup_v1_20260103T100000.db"


class TestRotacionarBackups:
    """TC-101 — rotacionar_backups mantém apenas as 3 últimas cópias."""

    def _criar_backups_nomeados(self, diretorio: Path, nomes: list[str]) -> list[Path]:
        paths = []
        for nome in nomes:
            p = diretorio / nome
            p.write_bytes(b"backup")
            paths.append(p)
        return paths

    def test_rotacao_com_exatamente_3_nao_remove_nada(self, db_file: Path) -> None:
        """Com exatamente 3 backups, rotação não remove nenhum."""
        nomes = [
            "data_backup_v1_20260101T100000.db",
            "data_backup_v1_20260102T100000.db",
            "data_backup_v1_20260103T100000.db",
        ]
        self._criar_backups_nomeados(db_file.parent, nomes)

        removidos = rotacionar_backups(db_file, manter=3)

        assert removidos == []
        assert len(listar_backups(db_file)) == 3

    def test_rotacao_com_4_remove_o_mais_antigo(self, db_file: Path) -> None:
        """TC-101 — com 4 backups, o mais antigo deve ser removido."""
        nomes = [
            "data_backup_v1_20260101T100000.db",
            "data_backup_v1_20260102T100000.db",
            "data_backup_v1_20260103T100000.db",
            "data_backup_v1_20260104T100000.db",
        ]
        self._criar_backups_nomeados(db_file.parent, nomes)

        removidos = rotacionar_backups(db_file, manter=3)

        assert len(removidos) == 1
        assert removidos[0].name == "data_backup_v1_20260101T100000.db"
        restantes = [p.name for p in listar_backups(db_file)]
        assert "data_backup_v1_20260101T100000.db" not in restantes
        assert len(restantes) == 3

    def test_rotacao_com_5_remove_os_2_mais_antigos(self, db_file: Path) -> None:
        """TC-101 — com 5 backups, os 2 mais antigos devem ser removidos."""
        nomes = [
            "data_backup_v1_20260101T100000.db",
            "data_backup_v1_20260102T100000.db",
            "data_backup_v1_20260103T100000.db",
            "data_backup_v1_20260104T100000.db",
            "data_backup_v1_20260105T100000.db",
        ]
        self._criar_backups_nomeados(db_file.parent, nomes)

        removidos = rotacionar_backups(db_file, manter=3)

        assert len(removidos) == 2
        nomes_removidos = {p.name for p in removidos}
        assert "data_backup_v1_20260101T100000.db" in nomes_removidos
        assert "data_backup_v1_20260102T100000.db" in nomes_removidos
        assert len(listar_backups(db_file)) == 3

    def test_rotacao_com_menos_que_3_nao_remove_nada(self, db_file: Path) -> None:
        """Com menos backups que o limite, nenhum é removido."""
        nomes = [
            "data_backup_v1_20260101T100000.db",
            "data_backup_v1_20260102T100000.db",
        ]
        self._criar_backups_nomeados(db_file.parent, nomes)

        removidos = rotacionar_backups(db_file, manter=3)

        assert removidos == []
        assert len(listar_backups(db_file)) == 2

    def test_rotacao_com_diretorio_sem_backups_nao_falha(self, db_file: Path) -> None:
        """Rotação em diretório sem backups retorna lista vazia sem exceção."""
        removidos = rotacionar_backups(db_file, manter=3)

        assert removidos == []

    def test_rotacao_manter_menor_que_1_levanta_value_error(
        self, db_file: Path
    ) -> None:
        """Valor de manter < 1 deve levantar ValueError."""
        with pytest.raises(ValueError, match="manter"):
            rotacionar_backups(db_file, manter=0)

    def test_rotacao_fluxo_completo_backup_mais_rotacao(self, db_file: Path) -> None:
        """TC-101 — backup criado + rotação mantém exatamente 3 backups."""
        # Simula 3 backups anteriores
        dir_ = db_file.parent
        for i in range(1, 4):
            nome = f"data_backup_v1_20260101T10000{i}.db"
            (dir_ / nome).write_bytes(b"old backup")

        # Cria o backup novo
        novo_backup = criar_backup(db_file, versao_origem=1)
        assert novo_backup.exists()

        # Rotaciona mantendo 3
        removidos = rotacionar_backups(db_file, manter=3)

        # Deve restar exatamente 3 (o mais antigo dos 3 antigos é removido)
        assert len(removidos) == 1
        backups_restantes = listar_backups(db_file)
        assert len(backups_restantes) == 3
        # O mais novo (criado agora) deve estar entre os restantes
        assert novo_backup in backups_restantes


# ---------------------------------------------------------------------------
# TC-095..TC-098 — Quarentena: escrita append-only, payload preservado
# ---------------------------------------------------------------------------


def _ler_linhas_quarentena(caminho: Path) -> list[dict[str, Any]]:
    """Lê todas as linhas JSON do arquivo de quarentena."""
    linhas = []
    with caminho.open("r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha:
                linhas.append(json.loads(linha))
    return linhas


class TestCaminhoQuarentena:
    """Testes de caminho_quarentena_atual."""

    def test_cria_diretorio_automaticamente(self, quarentena_dir: Path) -> None:
        """Edge case — diretório de quarentena deve ser criado se não existir."""
        assert not quarentena_dir.exists()

        with patch("own_board_list.database.quarantine.QUARENTENA_DIR", quarentena_dir):
            caminho = caminho_quarentena_atual()

        assert quarentena_dir.exists()
        assert caminho.parent == quarentena_dir

    def test_nome_arquivo_contem_data_atual(self, quarentena_dir: Path) -> None:
        """Nome do arquivo deve conter a data de hoje no formato YYYYMMDD."""
        hoje = date.today().strftime("%Y%m%d")

        with patch("own_board_list.database.quarantine.QUARENTENA_DIR", quarentena_dir):
            caminho = caminho_quarentena_atual()

        assert caminho.name == f"quarantine_{hoje}.json"

    def test_dias_diferentes_geram_arquivos_distintos(
        self, quarentena_dir: Path
    ) -> None:
        """Edge case — dias diferentes produzem arquivos separados."""
        with patch("own_board_list.database.quarantine.QUARENTENA_DIR", quarentena_dir):
            with patch("own_board_list.database.quarantine.date") as mock_date:
                mock_date.today.return_value = date(2026, 4, 25)
                caminho_dia1 = caminho_quarentena_atual()

            with patch("own_board_list.database.quarantine.date") as mock_date:
                mock_date.today.return_value = date(2026, 4, 26)
                caminho_dia2 = caminho_quarentena_atual()

        assert caminho_dia1 != caminho_dia2
        assert caminho_dia1.name == "quarantine_20260425.json"
        assert caminho_dia2.name == "quarantine_20260426.json"


class TestRegistrarEmQuarentena:
    """TC-095..TC-098 — registrar_em_quarentena, payload e append-only."""

    def _registro(
        self,
        motivo: str = "prioridade_invalida",
        tabela: str = "tasks",
        id_original: str = "task-001",
        payload: dict[str, Any] | None = None,
        saneamento: dict[str, Any] | None = None,
    ) -> RegistroQuarentena:
        if payload is None:
            payload = {"titulo": "Tarefa legada", "prioridade": None}
        return RegistroQuarentena(
            tabela=tabela,
            id_original=id_original,
            motivo=motivo,
            payload_original=payload,
            saneamento_aplicado=saneamento,
        )

    def test_tc095_prioridade_invalida_arquivo_criado(
        self, quarentena_dir: Path
    ) -> None:
        """TC-095 — prioridade nula/inválida gera linha em arquivo diário."""
        payload = {
            "id": "task-abc",
            "titulo": "Tarefa legada",
            "prioridade": None,
            "status": "Pendente",
        }
        reg = RegistroQuarentena(
            tabela="tasks",
            id_original="task-abc",
            motivo="prioridade_invalida",
            payload_original=payload,
            saneamento_aplicado={"prioridade": "Média"},
        )

        with patch("own_board_list.database.quarantine.QUARENTENA_DIR", quarentena_dir):
            registrar_em_quarentena(reg)
            caminho = caminho_quarentena_atual()

        assert caminho.exists()
        linhas = _ler_linhas_quarentena(caminho)
        assert len(linhas) == 1
        assert linhas[0]["motivo"] == "prioridade_invalida"

    def test_tc095_payload_original_preservado_fielmente(
        self, quarentena_dir: Path
    ) -> None:
        """TC-095 — payload_original deve ser gravado sem alteração."""
        payload = {
            "id": "task-abc",
            "titulo": "Tarefa com prioridade nula",
            "prioridade": None,
            "status": "Pendente",
            "coluna_kanban": "col-1",
        }
        reg = RegistroQuarentena(
            tabela="tasks",
            id_original="task-abc",
            motivo="prioridade_invalida",
            payload_original=payload,
            saneamento_aplicado={"prioridade": "Média"},
        )

        with patch("own_board_list.database.quarantine.QUARENTENA_DIR", quarentena_dir):
            registrar_em_quarentena(reg)
            caminho = caminho_quarentena_atual()

        linhas = _ler_linhas_quarentena(caminho)
        assert linhas[0]["payload_original"] == payload
        assert linhas[0]["saneamento_aplicado"] == {"prioridade": "Média"}

    def test_tc096_status_invalido_motivo_correto(self, quarentena_dir: Path) -> None:
        """TC-096 — status desconhecido gera linha com motivo status_invalido."""
        payload = {
            "id": "task-xyz",
            "titulo": "Tarefa com status custom",
            "status": "Bloqueado",
            "prioridade": "Alta",
        }
        reg = RegistroQuarentena(
            tabela="tasks",
            id_original="task-xyz",
            motivo="status_invalido",
            payload_original=payload,
            saneamento_aplicado={"status": "Pendente"},
        )

        with patch("own_board_list.database.quarantine.QUARENTENA_DIR", quarentena_dir):
            registrar_em_quarentena(reg)
            caminho = caminho_quarentena_atual()

        linhas = _ler_linhas_quarentena(caminho)
        assert len(linhas) == 1
        assert linhas[0]["motivo"] == "status_invalido"
        assert linhas[0]["payload_original"]["status"] == "Bloqueado"
        assert linhas[0]["saneamento_aplicado"] == {"status": "Pendente"}

    def test_tc097_coluna_inexistente_payload_preservado(
        self, quarentena_dir: Path
    ) -> None:
        """TC-097 — tarefa apontando coluna inexistente gera linha em quarentena."""
        payload = {
            "id": "task-col",
            "titulo": "Tarefa órfã",
            "coluna_kanban": "col-fantasma-999",
            "prioridade": "Média",
            "status": "Pendente",
        }
        reg = RegistroQuarentena(
            tabela="tasks",
            id_original="task-col",
            motivo="coluna_inexistente",
            payload_original=payload,
            saneamento_aplicado={"coluna_kanban": "col-a-fazer-id"},
        )

        with patch("own_board_list.database.quarantine.QUARENTENA_DIR", quarentena_dir):
            registrar_em_quarentena(reg)
            caminho = caminho_quarentena_atual()

        linhas = _ler_linhas_quarentena(caminho)
        assert len(linhas) == 1
        assert linhas[0]["motivo"] == "coluna_inexistente"
        assert linhas[0]["payload_original"]["coluna_kanban"] == "col-fantasma-999"
        assert linhas[0]["saneamento_aplicado"]["coluna_kanban"] == "col-a-fazer-id"

    def test_tc098_data_ausente_payload_preservado(self, quarentena_dir: Path) -> None:
        """TC-098 — criado_em nulo gera linha em quarentena com motivo data_ausente."""
        payload = {
            "id": "task-sem-data",
            "titulo": "Tarefa sem data",
            "criado_em": None,
            "atualizado_em": None,
        }
        reg = RegistroQuarentena(
            tabela="tasks",
            id_original="task-sem-data",
            motivo="data_ausente",
            payload_original=payload,
            saneamento_aplicado={
                "criado_em": "2026-04-25T00:00:00+00:00",
                "atualizado_em": "2026-04-25T00:00:00+00:00",
                "observacao": "data desconhecida (migrado em 2026-04-25)",
            },
        )

        with patch("own_board_list.database.quarantine.QUARENTENA_DIR", quarentena_dir):
            registrar_em_quarentena(reg)
            caminho = caminho_quarentena_atual()

        linhas = _ler_linhas_quarentena(caminho)
        assert len(linhas) == 1
        assert linhas[0]["motivo"] == "data_ausente"
        assert linhas[0]["payload_original"]["criado_em"] is None
        assert "observacao" in linhas[0]["saneamento_aplicado"]

    def test_append_only_multiplas_chamadas_no_mesmo_dia(
        self, quarentena_dir: Path
    ) -> None:
        """Edge case — múltiplas chamadas no mesmo dia acrescentam linhas."""
        registros = [
            RegistroQuarentena(
                tabela="tasks",
                id_original=f"task-{i}",
                motivo="prioridade_invalida",
                payload_original={"id": f"task-{i}", "prioridade": None},
                saneamento_aplicado={"prioridade": "Média"},
            )
            for i in range(3)
        ]

        with patch("own_board_list.database.quarantine.QUARENTENA_DIR", quarentena_dir):
            for reg in registros:
                registrar_em_quarentena(reg)
            caminho = caminho_quarentena_atual()

        linhas = _ler_linhas_quarentena(caminho)
        assert len(linhas) == 3
        ids = [linha["id_original"] for linha in linhas]
        assert "task-0" in ids
        assert "task-1" in ids
        assert "task-2" in ids

    def test_append_only_nao_sobrescreve_conteudo_anterior(
        self, quarentena_dir: Path
    ) -> None:
        """Escrita append-only: segunda chamada não apaga a primeira linha."""
        reg1 = RegistroQuarentena(
            tabela="tasks",
            id_original="task-first",
            motivo="status_invalido",
            payload_original={"id": "task-first", "status": "Bloqueado"},
            saneamento_aplicado={"status": "Pendente"},
        )
        reg2 = RegistroQuarentena(
            tabela="tasks",
            id_original="task-second",
            motivo="coluna_inexistente",
            payload_original={"id": "task-second", "coluna_kanban": "x"},
            saneamento_aplicado={"coluna_kanban": "col-padrao"},
        )

        with patch("own_board_list.database.quarantine.QUARENTENA_DIR", quarentena_dir):
            registrar_em_quarentena(reg1)
            registrar_em_quarentena(reg2)
            caminho = caminho_quarentena_atual()

        linhas = _ler_linhas_quarentena(caminho)
        assert len(linhas) == 2
        assert linhas[0]["id_original"] == "task-first"
        assert linhas[1]["id_original"] == "task-second"

    def test_linha_contem_timestamp_registrado_em(self, quarentena_dir: Path) -> None:
        """Cada linha deve conter o campo registrado_em com timestamp UTC."""
        reg = RegistroQuarentena(
            tabela="tasks",
            id_original="task-ts",
            motivo="prioridade_invalida",
            payload_original={"id": "task-ts"},
        )

        with patch("own_board_list.database.quarantine.QUARENTENA_DIR", quarentena_dir):
            registrar_em_quarentena(reg)
            caminho = caminho_quarentena_atual()

        linhas = _ler_linhas_quarentena(caminho)
        assert "registrado_em" in linhas[0]
        # Deve ser ISO 8601 parseável
        ts = datetime.fromisoformat(linhas[0]["registrado_em"])
        assert ts.tzinfo is not None  # timezone-aware

    def test_saneamento_none_serializado_como_null(self, quarentena_dir: Path) -> None:
        """saneamento_aplicado=None deve aparecer como null no JSON."""
        reg = RegistroQuarentena(
            tabela="tasks",
            id_original="task-null",
            motivo="status_invalido",
            payload_original={"id": "task-null"},
            saneamento_aplicado=None,
        )

        with patch("own_board_list.database.quarantine.QUARENTENA_DIR", quarentena_dir):
            registrar_em_quarentena(reg)
            caminho = caminho_quarentena_atual()

        linhas = _ler_linhas_quarentena(caminho)
        assert linhas[0]["saneamento_aplicado"] is None

    def test_estrutura_registro_quarentena_campos_corretos(self) -> None:
        """Edge case — RegistroQuarentena deve ter todos os campos esperados."""
        reg = RegistroQuarentena(
            tabela="tasks",
            id_original="task-001",
            motivo="coluna_inexistente",
            payload_original={"id": "task-001", "coluna_kanban": "col-xyz"},
            saneamento_aplicado={"coluna_kanban": "col-a-fazer"},
        )

        assert reg.tabela == "tasks"
        assert reg.id_original == "task-001"
        assert reg.motivo == "coluna_inexistente"
        assert reg.payload_original == {"id": "task-001", "coluna_kanban": "col-xyz"}
        assert reg.saneamento_aplicado == {"coluna_kanban": "col-a-fazer"}

    def test_cada_linha_e_json_valido_e_independente(
        self, quarentena_dir: Path
    ) -> None:
        """Cada linha do arquivo deve ser um JSON independente e válido (JSON-L)."""
        registros = [
            RegistroQuarentena(
                tabela="tasks",
                id_original=f"task-{i}",
                motivo="data_ausente",
                payload_original={"id": f"task-{i}", "criado_em": None},
            )
            for i in range(5)
        ]

        with patch("own_board_list.database.quarantine.QUARENTENA_DIR", quarentena_dir):
            for reg in registros:
                registrar_em_quarentena(reg)
            caminho = caminho_quarentena_atual()

        # Cada linha deve ser parseável individualmente
        with caminho.open("r", encoding="utf-8") as f:
            linhas_brutas = f.readlines()

        assert len(linhas_brutas) == 5
        for linha_bruta in linhas_brutas:
            obj = json.loads(linha_bruta.strip())
            assert "tabela" in obj
            assert "id_original" in obj
            assert "motivo" in obj
            assert "payload_original" in obj
            assert "saneamento_aplicado" in obj
            assert "registrado_em" in obj
