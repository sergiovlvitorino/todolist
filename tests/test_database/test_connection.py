"""Testes unitários de DatabaseConnection e get_default_db_path."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from own_board_list.database.connection import DatabaseConnection, get_default_db_path


class TestGetDefaultDbPath:
    """Testes da função get_default_db_path."""

    def test_retorna_path_dentro_do_home(self, tmp_path: Path) -> None:
        """O caminho padrão deve estar dentro de ~/.own-board-list/."""
        patch_target = "own_board_list.database.connection.Path.home"
        with patch(patch_target, return_value=tmp_path):
            result = get_default_db_path()

        assert result == tmp_path / ".own-board-list" / "data.db"

    def test_cria_diretorio_se_nao_existir(self, tmp_path: Path) -> None:
        """Deve criar o diretório pai se ele não existir."""
        patch_target = "own_board_list.database.connection.Path.home"
        with patch(patch_target, return_value=tmp_path):
            result = get_default_db_path()

        assert result.parent.exists()
        assert result.parent.is_dir()

    def test_nao_falha_se_diretorio_ja_existe(self, tmp_path: Path) -> None:
        """Deve funcionar sem erros quando o diretório já existe."""
        patch_target = "own_board_list.database.connection.Path.home"
        with patch(patch_target, return_value=tmp_path):
            get_default_db_path()
            # Segunda chamada não deve levantar erro
            result = get_default_db_path()

        assert result is not None


class TestDatabaseConnectionOpen:
    """Testes de abertura e obtenção de conexão."""

    def test_get_connection_retorna_connection(self, tmp_path: Path) -> None:
        """get_connection deve retornar um sqlite3.Connection."""
        db = DatabaseConnection(tmp_path / "test.db")
        conn = db.get_connection()

        assert isinstance(conn, sqlite3.Connection)
        db.close()

    def test_get_connection_abre_arquivo(self, tmp_path: Path) -> None:
        """Deve criar o arquivo de banco de dados no caminho informado."""
        db_path = tmp_path / "test.db"
        db = DatabaseConnection(db_path)
        db.get_connection()

        assert db_path.exists()
        db.close()

    def test_get_connection_mesma_instancia(self, tmp_path: Path) -> None:
        """Chamadas repetidas devem retornar a mesma conexão (singleton)."""
        db = DatabaseConnection(tmp_path / "test.db")
        conn1 = db.get_connection()
        conn2 = db.get_connection()

        assert conn1 is conn2
        db.close()

    def test_get_connection_configura_row_factory(self, tmp_path: Path) -> None:
        """A conexão deve ter row_factory = sqlite3.Row configurado."""
        db = DatabaseConnection(tmp_path / "test.db")
        conn = db.get_connection()

        assert conn.row_factory is sqlite3.Row
        db.close()

    def test_aceita_string_como_caminho(self, tmp_path: Path) -> None:
        """Deve aceitar caminho como string além de Path."""
        db_path = str(tmp_path / "test_str.db")
        db = DatabaseConnection(db_path)
        conn = db.get_connection()

        assert conn is not None
        db.close()


class TestDatabaseConnectionClose:
    """Testes de fechamento da conexão."""

    def test_close_fecha_conexao(self, tmp_path: Path) -> None:
        """Após close, a conexão interna deve ser None."""
        db = DatabaseConnection(tmp_path / "test.db")
        db.get_connection()
        db.close()

        # Após fechar, nova chamada deve abrir nova conexão sem erros
        conn = db.get_connection()
        assert conn is not None
        db.close()

    def test_close_sem_conexao_aberta_nao_levanta(self, tmp_path: Path) -> None:
        """Chamar close sem conexão aberta não deve levantar exceção."""
        db = DatabaseConnection(tmp_path / "test.db")
        db.close()  # Não deve levantar

    def test_reabrir_apos_close(self, tmp_path: Path) -> None:
        """Deve ser possível reabrir a conexão após fechar."""
        db = DatabaseConnection(tmp_path / "test.db")
        conn1 = db.get_connection()
        db.close()
        conn2 = db.get_connection()

        assert conn1 is not conn2
        db.close()


class TestDatabaseConnectionContextManager:
    """Testes do protocolo de context manager para transações."""

    def test_context_manager_commit_em_sucesso(self, tmp_path: Path) -> None:
        """Deve fazer commit quando o bloco with termina sem exceção."""
        db = DatabaseConnection(tmp_path / "test.db")
        conn = db.get_connection()
        conn.execute("CREATE TABLE t (v INTEGER)")

        with db:
            conn.execute("INSERT INTO t VALUES (1)")

        row = conn.execute("SELECT v FROM t").fetchone()
        assert row is not None
        assert row[0] == 1
        db.close()

    def test_context_manager_rollback_em_excecao(self, tmp_path: Path) -> None:
        """Deve fazer rollback quando uma exceção é levantada no bloco with."""
        db = DatabaseConnection(tmp_path / "test.db")
        conn = db.get_connection()
        conn.execute("CREATE TABLE t (v INTEGER)")
        conn.commit()

        with pytest.raises(RuntimeError):
            with db:
                conn.execute("INSERT INTO t VALUES (42)")
                raise RuntimeError("falha simulada")

        row = conn.execute("SELECT COUNT(*) FROM t").fetchone()
        assert row is not None
        assert row[0] == 0
        db.close()

    def test_context_manager_nao_suprime_excecao(self, tmp_path: Path) -> None:
        """A exceção deve se propagar após o rollback."""
        db = DatabaseConnection(tmp_path / "test.db")
        db.get_connection()

        with pytest.raises(ValueError, match="erro esperado"):
            with db:
                raise ValueError("erro esperado")

        db.close()


class TestDatabaseConnectionTransactionNesting:
    """Testes de aninhamento de transações (DT-029).

    Garante que ``ColumnRepository.reorder()`` executado dentro de um bloco
    ``with DatabaseConnection(...)`` não emita um segundo ``BEGIN`` — o que
    levantaria ``sqlite3.OperationalError: cannot start a transaction within
    a transaction``. A implementação usa ``conn.in_transaction`` para detectar
    se já há transação ativa antes de emitir ``BEGIN`` explícito.
    """

    def test_reorder_dentro_de_with_database_connection_nao_falha(
        self, tmp_path: Path
    ) -> None:
        """Chamar reorder() dentro de ``with DatabaseConnection`` deve funcionar.

        [DECISÃO] ColumnRepository.reorder() verifica ``in_transaction``
          Alternativas: A) só o context manager gerencia transação |
                        B) repositórios detectam transação ativa via in_transaction
          Escolha: B
          Por quê: preserva rollback autônomo de reorder() em uso fora do context
                   manager, sem BEGIN aninhado quando usado dentro dele.
        """
        from own_board_list.database.column_repository import ColumnRepository
        from own_board_list.database.migrations import initialize_database

        db = DatabaseConnection(tmp_path / "test_nesting.db")
        conn = db.get_connection()
        initialize_database(conn)

        repo = ColumnRepository(conn)
        colunas = repo.get_all()
        ids_invertidos = [c.id for c in reversed(colunas)]

        # Não deve levantar OperationalError: cannot start a transaction within...
        with db:
            repo.reorder(ids_invertidos)

        reordenadas = repo.get_all()
        assert reordenadas[0].posicao == 0
        assert reordenadas[-1].posicao == len(reordenadas) - 1
        db.close()


class TestDatabaseConnectionThreadGuard:
    """Testes do invariante de thread em DatabaseConnection (DT-041).

    [DECISÃO] Manter check_same_thread=False com assert de thread proprietário
      Alternativas: A) voltar a check_same_thread=True |
                    B) manter False + threading.Lock |
                    C) manter False + assert em modo debug
      Escolha: C
      Por quê: a app é single-thread; voltar a True exigiria refatoração do
               loop Qt; Lock seria overhead desnecessário. O assert detecta
               violações durante desenvolvimento (modo debug) sem custo em
               produção otimizada.
    """

    def test_get_connection_no_mesmo_thread_funciona(self, tmp_path: Path) -> None:
        """Acesso no thread proprietário deve funcionar sem erro."""
        db = DatabaseConnection(tmp_path / "test_thread.db")
        conn = db.get_connection()
        assert isinstance(conn, sqlite3.Connection)
        db.close()

    def test_owner_thread_registrado_na_construcao(self, tmp_path: Path) -> None:
        """O ID do thread proprietário deve ser o thread que criou o objeto."""
        db = DatabaseConnection(tmp_path / "test_thread_owner.db")
        assert db._owner_thread_id == threading.get_ident()
        db.close()

    def test_get_connection_de_outro_thread_levanta_assertion_error(
        self, tmp_path: Path
    ) -> None:
        """Acesso de thread diferente do proprietário deve levantar AssertionError
        em modo debug (sem python -O)."""
        db = DatabaseConnection(tmp_path / "test_thread_cross.db")
        # Abre a conexão no thread principal (proprietário)
        db.get_connection()

        erros: list[BaseException] = []

        def acesso_cruzado() -> None:
            try:
                db.get_connection()
            except AssertionError as exc:
                erros.append(exc)

        t = threading.Thread(target=acesso_cruzado)
        t.start()
        t.join()

        # Em modo debug (__debug__ == True), o assert deve ter sido disparado.
        if __debug__:
            assert len(erros) == 1
            assert "proprietário" in str(erros[0]) or "owner" in str(erros[0]).lower()
        else:
            # Com python -O, asserts são suprimidos — sem erros esperados.
            assert len(erros) == 0

        db.close()


class TestDatabaseConnectionPragmas:
    """Testes das configurações de pragmas."""

    def test_foreign_keys_habilitado(self, tmp_path: Path) -> None:
        """PRAGMA foreign_keys deve estar habilitado."""
        db = DatabaseConnection(tmp_path / "test.db")
        conn = db.get_connection()
        cursor = conn.execute("PRAGMA foreign_keys")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 1
        db.close()

    def test_wal_mode_habilitado(self, tmp_path: Path) -> None:
        """PRAGMA journal_mode deve ser WAL."""
        db = DatabaseConnection(tmp_path / "test.db")
        conn = db.get_connection()
        cursor = conn.execute("PRAGMA journal_mode")
        row = cursor.fetchone()
        assert row is not None
        assert row[0].lower() == "wal"
        db.close()
