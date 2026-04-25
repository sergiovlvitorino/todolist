"""
Constantes centralizadas do projeto Own Board List.

Consolida nomes de colunas Kanban padrão, limites de campos, mapeamento de
cores por prioridade e parâmetros de política de migrations em um único local,
evitando strings mágicas espalhadas pelo código-fonte e violação do princípio
DRY.
"""

from __future__ import annotations

from pathlib import Path

from own_board_list.models.enums import Prioridade

# ---------------------------------------------------------------------------
# Nomes das colunas Kanban padrão
# ---------------------------------------------------------------------------

#: Coluna de entrada — tarefas ainda não iniciadas.
COLUNA_A_FAZER = "A Fazer"

#: Coluna de trabalho em curso.
COLUNA_EM_ANDAMENTO = "Em Andamento"

#: Coluna de itens finalizados.
COLUNA_CONCLUIDO = "Concluído"

#: Coluna padrão atribuída a novas tarefas.
COLUNA_PADRAO = COLUNA_A_FAZER

# ---------------------------------------------------------------------------
# Limites de campos
# ---------------------------------------------------------------------------

#: Comprimento máximo permitido para o título de uma tarefa.
TITULO_MAX_LEN = 200

#: Comprimento máximo permitido para a descrição de uma tarefa.
DESCRICAO_MAX_LEN = 5000

#: Comprimento máximo permitido para o nome de uma coluna Kanban.
NOME_COLUNA_MAX_LEN = 100

# ---------------------------------------------------------------------------
# Mapeamento de prioridade para cor HTML (usado nos widgets de UI)
# ---------------------------------------------------------------------------

#: Cores HTML por nível de prioridade.
COR_PRIORIDADE: dict[Prioridade, str] = {
    Prioridade.ALTA: "#d32f2f",
    Prioridade.MEDIA: "#f57c00",
    Prioridade.BAIXA: "#388e3c",
}

# ---------------------------------------------------------------------------
# Política de migrations e versionamento de schema (ADR-005)
# ---------------------------------------------------------------------------

#: Versão atual do schema SQLite suportada por esta build da aplicação.
#: v1 = schema pré-DT-040 (sem CHECK/NOT NULL/FK).
#: v2 = schema com constraints fechados + FK por id de coluna (DT-013/DT-040).
SCHEMA_VERSION_ATUAL: int = 2

#: Limiar em segundos a partir do qual a migração exibe indicador de progresso
#: no splash. Abaixo deste valor a transição é silenciosa.
LIMIAR_PROGRESSO_MIGRACAO_S: float = 1.5

#: Número máximo de arquivos de backup retidos por rotação FIFO simples.
BACKUPS_RETIDOS: int = 3

#: Diretório base para arquivos auxiliares da aplicação (backups, quarentena).
QUARENTENA_DIR: Path = Path.home() / ".own-board-list"
