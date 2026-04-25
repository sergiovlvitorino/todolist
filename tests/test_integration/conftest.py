"""Fixtures para os testes de integração.

As fixtures db_conn_integration, task_repo_int, column_repo_int e
task_service_int são definidas no conftest.py raiz (DT-026 — unificação
de fixtures). Este arquivo é mantido por compatibilidade de namespace e
define apenas fixtures exclusivas desta camada (ex.: db_file).
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def db_file(tmp_path: Path) -> Generator[Path, None, None]:
    """Banco SQLite em arquivo temporário para testes de persistência."""
    db_path = tmp_path / "test_integration.db"
    yield db_path
    if db_path.exists():
        db_path.unlink()
