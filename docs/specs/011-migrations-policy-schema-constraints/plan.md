# Plan — Política de Migrations e Constraints de Integridade do Schema

> **Spec:** [spec.md](spec.md)
> **Fase:** `/plan` → artefato de entrada para `/tasks`
> **Autor:** agente `tl-python`
> **Data:** 2026-04-25

---

## Regras desta fase

- **Constitution é lei.** Esta feature reforça vários princípios 🔒 (privacidade local, layering, gates de qualidade) e nenhum é violado.
- **Sem código** — assinaturas e shapes de dados permitidos; implementação não.
- Decisões reversíveis ficam neste plan; uma decisão estrutural (estratégia de versionamento de schema) sobe para **ADR-005**.

---

## Resumo técnico

Introduzir uma política explícita de versionamento do schema SQLite (tabela `schema_version` + lista ordenada de migrations idempotentes) e aplicar `CHECK` + `NOT NULL` + `FOREIGN KEY` para fechar os buracos hoje permitidos pelo schema. A primeira execução em um banco legado executa **backup → migrations encadeadas → saneamento de dados inválidos (com quarentena lateral) → validação final**. Saneamento usa defaults consistentes com US-01 (`prioridade="Média"`, `status="Pendente"`, realocação para `A Fazer`). O domínio (`models/`) já valida estes invariantes desde DT-038/039/042 — esta feature alinha o **schema** ao **domínio**, com defesa em profundidade.

## Camadas afetadas

| Camada | Muda? | Natureza da mudança |
|---|---|---|
| `utils/` | sim | nova constante `SCHEMA_VERSION_ATUAL`, caminho de quarentena, limiar de progresso (1,5s), retenção de backup (3) |
| `models/` | não | invariantes já cobertos por DT-038/039/042; apenas auditoria de consistência |
| `database/` | sim | reescrita de `migrations.py` em motor versionado; nova tabela `schema_version`; novo módulo `backup.py`; novo módulo `quarantine.py`; constraints SQL |
| `services/` | sim | novo `MigrationService` orquestrando backup → migrations → saneamento → quarentena → log; integração no bootstrap |
| `ui/` | sim | splash com indicador de progresso condicional (> 1,5 s) e exibição de caminho de quarentena/falha |

Layering preservado: `utils → models → database → services → ui`.

## Contratos

```python
# utils/constants.py (adições)
SCHEMA_VERSION_ATUAL: int = 2  # v1 = pré-DT-040; v2 = constraints fechados + FK
LIMIAR_PROGRESSO_MIGRACAO_S: float = 1.5
BACKUPS_RETIDOS: int = 3
QUARENTENA_DIR: Path  # ~/.own-board-list/

# database/migrations.py (refeito)
@dataclass(frozen=True)
class Migration:
    versao_destino: int
    descricao: str
    aplicar: Callable[[sqlite3.Connection], None]

MIGRATIONS: list[Migration]  # ordenadas por versao_destino crescente

def get_schema_version(conn: sqlite3.Connection) -> int: ...
def set_schema_version(conn: sqlite3.Connection, versao: int) -> None: ...
def initialize_database(conn: sqlite3.Connection) -> MigrationReport: ...

# database/backup.py (novo)
def criar_backup(db_path: Path, versao_origem: int) -> Path: ...
def rotacionar_backups(db_path: Path, manter: int = BACKUPS_RETIDOS) -> list[Path]: ...
def listar_backups(db_path: Path) -> list[Path]: ...

# database/quarantine.py (novo)
@dataclass
class RegistroQuarentena:
    tabela: str
    id_original: str
    motivo: str  # "status_invalido" | "coluna_inexistente" | "data_ausente" | ...
    payload_original: dict[str, Any]
    saneamento_aplicado: dict[str, Any] | None  # None se rejeitado por completo

def registrar_em_quarentena(reg: RegistroQuarentena) -> None: ...
def caminho_quarentena_atual() -> Path: ...

# services/migration_service.py (novo)
@dataclass
class MigrationReport:
    versao_origem: int
    versao_destino: int
    backup_path: Path | None
    quarentena_path: Path | None
    duracao_s: float
    registros_saneados: int
    sucesso: bool
    erro: str | None

class MigrationService:
    def executar(self, db_path: Path) -> MigrationReport: ...
    def status_versao(self, db_path: Path) -> int: ...

# ui/splash.py (novo)
class MigrationSplash(QWidget):
    def show_progress(self, mensagem: str) -> None: ...
    def show_quarantine_path(self, caminho: Path) -> None: ...
    def show_error(self, mensagem: str, backup_path: Path | None) -> None: ...
```

## Migração de dados / schema

**Tabela de controle (nova):**
```sql
CREATE TABLE IF NOT EXISTS schema_version (
    versao INTEGER PRIMARY KEY,
    aplicada_em TEXT NOT NULL
);
```

**Migration v1 → v2 (passos idempotentes, executados em transação por migration):**

1. **Saneamento de dados** (`tasks` legados):
   - `UPDATE tasks SET prioridade='Média' WHERE prioridade IS NULL OR prioridade NOT IN ('Baixa','Média','Alta');` → registrar cada linha afetada na quarentena.
   - `UPDATE tasks SET status='Pendente' WHERE status IS NULL OR status NOT IN ('Pendente','Concluída');` → quarentena.
   - `UPDATE tasks SET coluna_kanban=<id_a_fazer> WHERE coluna_kanban NOT IN (SELECT id FROM kanban_columns);` → quarentena com motivo `coluna_inexistente`.
   - `UPDATE tasks SET criado_em=<utc_agora>, atualizado_em=COALESCE(atualizado_em,<utc_agora>) WHERE criado_em IS NULL;` → quarentena com observação "data desconhecida (migrado em YYYY-MM-DD)".
   - `UPDATE kanban_columns SET criado_em=<utc_agora> WHERE criado_em IS NULL;` → quarentena análoga.

2. **Recriação das tabelas com constraints** (padrão SQLite: `CREATE TABLE *_new` → `INSERT INTO *_new SELECT ...` → `DROP` → `RENAME`):

```sql
CREATE TABLE kanban_columns_new (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL CHECK(length(trim(nome)) > 0),
    posicao INTEGER NOT NULL DEFAULT 0 CHECK(posicao >= 0),
    criado_em TEXT NOT NULL
);

CREATE TABLE tasks_new (
    id TEXT PRIMARY KEY,
    titulo TEXT NOT NULL CHECK(length(trim(titulo)) > 0),
    descricao TEXT NOT NULL DEFAULT '',
    prioridade TEXT NOT NULL CHECK(prioridade IN ('Baixa','Média','Alta')),
    data_vencimento TEXT,
    status TEXT NOT NULL CHECK(status IN ('Pendente','Concluída')),
    coluna_kanban TEXT NOT NULL REFERENCES kanban_columns(id) ON DELETE RESTRICT,
    posicao_kanban INTEGER NOT NULL DEFAULT 0 CHECK(posicao_kanban >= 0),
    criado_em TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);
```
   `PRAGMA foreign_keys = ON` no `connection.py` (precisa estar ativo por conexão).

3. **Reindexação:** recriar índices de `coluna_kanban`, `status`, `prioridade`, `data_vencimento`.

4. **Validação final:** `PRAGMA foreign_key_check;` e `PRAGMA integrity_check;` retornam OK; senão, `MigrationService.executar` falha com rollback.

5. **Atomicidade:** cada migration roda em `BEGIN IMMEDIATE ... COMMIT`. Falha → `ROLLBACK` + restauração do backup.

**Ordem de aplicação (orquestração `MigrationService.executar`):**

```
1. Detectar versao_origem (ou 1 se ausente, ou 0 = banco novo)
2. Se versao_origem == SCHEMA_VERSION_ATUAL → return (no-op)
3. Se versao_origem > SCHEMA_VERSION_ATUAL → falhar (arquivo de versão futura)
4. criar_backup(db_path, versao_origem) → backup_path
5. Para cada Migration com versao_destino > versao_origem (em ordem):
     a. BEGIN IMMEDIATE
     b. saneamento (com escrita incremental no quarantine.json)
     c. recriação de tabelas com constraints
     d. set_schema_version(...)
     e. COMMIT (ou ROLLBACK + restaurar backup)
6. PRAGMA integrity_check; PRAGMA foreign_key_check
7. rotacionar_backups (mantém 3)
8. Emitir MigrationReport
```

**Atomicidade entre migrations:** se v1→v2→v3 e v3 falhar, o estado fica em v2 (não v1). Como migrations são monotônicas crescentes e idempotentes, na próxima execução só v3 é tentada novamente. O backup pré-v1 ainda está disponível para recuperação manual.

**Reforço de validação no domínio:** já existe pós-DT-038/039/042. Auditar:
- `Task.__post_init__`: titulo não-vazio, prioridade ∈ enum, status ∈ enum, posicao_kanban ≥ 0, descricao com limite (DT-038).
- `KanbanColumn.__post_init__`: nome com limite, posicao ≥ 0.
- `TaskService.create_task`: já valida coluna existente (DT-042).

Resultado da auditoria: nenhum gap funcional. Apenas alinhar mensagens de erro entre domínio e schema (mesma redação para mesma violação).

## ADRs novos necessários

- [x] **ADR-005 — Estratégia de versionamento de schema SQLite** — necessário porque define padrão estrutural global que vale para toda evolução futura de schema do produto. Conteúdo: tabela `schema_version` + lista ordenada de `Migration` idempotentes + atomicidade por migration + backup com rotação fixa + quarentena lateral. Alternativas avaliadas: (a) **Alembic** — pesado para SQLite local single-user, traz dependência grande; rejeitado. (b) **`PRAGMA user_version`** — simples mas opaco para auditoria; rejeitado por falta de trilha (`aplicada_em`). (c) **Tabela `schema_version` própria** — escolhido: leve, auditável, sem dependência extra, idiomático.

Outras decisões (FK, defaults de saneamento, retenção de backup) são reversíveis e ficam neste `plan.md`.

## Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Banco grande do usuário (>10k tarefas) torna migração lenta (>5 s) | Média | Médio | Splash com progresso > 1,5 s; `executemany`; `INSERT INTO ... SELECT` em vez de loop Python; medir em benchmark (TC novo) |
| Falha no meio da migração (queda de energia, kill -9) | Baixa | Alto | Cada migration em `BEGIN IMMEDIATE` (rollback automático); backup pré-migração; ao reabrir, detectar `schema_version` parcial e restaurar do backup automaticamente |
| Recriação de tabela perde dados por erro no `INSERT INTO ... SELECT` (mismatch de colunas) | Média | Crítico | Validação final com `integrity_check` + `foreign_key_check`; testes de migração com fixtures de bancos legados em vários estados |
| Saneamento agressivo apaga intenção do usuário (ex.: status custom desconhecido) | Baixa | Médio | Toda saneamento gera linha em quarentena com payload original; usuário pode inspecionar arquivo |
| `PRAGMA foreign_keys = ON` quebra fluxo existente que confiava em FK soft (DT-042) | Baixa | Médio | Auditar `TaskService` e `column_repository`: hoje exclusão de coluna com tarefas é bloqueada em service (DT-042); FK `ON DELETE RESTRICT` reforça |
| Quarentena cresce indefinidamente | Baixa | Baixo | Arquivo por dia (`quarantine_YYYYMMDD.json`); usuário pode apagar manualmente; documentar |
| Concorrência: duas instâncias do app abrem simultaneamente | Muito baixa | Alto | Já mitigado por DT-041 (lock de conexão single-thread); migration roda no bootstrap antes da UI |

## Plano de testes

> Convocado o agente `qa` (pair) para mapear TCs. Numeração começa em TC-093 (último confirmado em US-10 foi TC-092).

- [ ] **TC-093** — Banco novo (sem arquivo): `initialize_database` cria schema v2 direto, sem backup, sem quarentena (unit/integração)
- [ ] **TC-094** — Banco v1 com dados válidos: migra para v2 sem perda; nenhum registro em quarentena (integração)
- [ ] **TC-095** — Banco v1 com `prioridade=NULL`: saneada para "Média"; linha em quarentena com motivo (integração)
- [ ] **TC-096** — Banco v1 com `status` desconhecido: saneada para "Pendente"; linha em quarentena (integração)
- [ ] **TC-097** — Banco v1 com tarefa apontando para coluna inexistente: realocada para "A Fazer"; linha em quarentena (integração)
- [ ] **TC-098** — Banco v1 com `criado_em=NULL`: preenchido com UTC atual; linha em quarentena com observação (integração)
- [ ] **TC-099** — `schema_version` futura (ex.: v99): `MigrationService.executar` falha com erro claro; arquivo intacto (integração)
- [ ] **TC-100** — Falha no meio da migration: rollback automático; backup permanece; segunda tentativa retoma (integração; usar `sqlite3` com erro injetado)
- [ ] **TC-101** — Rotação de backup mantém apenas as 3 mais recentes (unit)
- [ ] **TC-102** — Constraints SQL ativas: `INSERT` direto com `titulo=''` falha; `INSERT` com `prioridade='Urgente'` falha; `INSERT` com `coluna_kanban` inexistente falha (integração via cursor cru)
- [ ] **TC-103** — `PRAGMA foreign_key_check` retorna vazio após migração em todos os cenários acima (integração)
- [ ] **TC-104** — Splash exibe indicador apenas se duração > 1,5 s; abaixo, fica silencioso (UI; usar `QTest` + mock de duração)
- [ ] **TC-105** — Splash exibe caminho do arquivo de quarentena quando aplicável (UI)
- [ ] **TC-106** — Falha total da migração: app não abre em estado parcial; mensagem com caminho do backup (UI)
- [ ] **TC-107** — Benchmark: migração de 10k tarefas conclui em ≤ 3 s em hardware de referência (`pytest.mark.slow`)
- [ ] **TC-108** — Defesa em profundidade: violar invariante via repositório direto resulta em `IntegrityError` (integração)

Cada task da fase `/tasks` aterra em pelo menos um destes TCs.

## Dependências

- Tasks bloqueantes no backlog global: nenhuma (DT-038/039/041/042 já fechadas).
- DT cobertas: **DT-040** (constraints) e **DT-013** (FK por id em vez de nome).
- Features afetadas no futuro: **US-09** (excluir coluna — agora reforçado por FK `RESTRICT`), **US-11** (renomear coluna — passa a ser viável pois nome não é mais identidade).

## Ligações

- **Constitution:** [../../constitution.md](../../constitution.md)
- **ADR de stack:** [../../adr-001-stack.md](../../adr-001-stack.md)
- **ADR coluna FK (cruza):** [../../adr-004-coluna-kanban-fk.md](../../adr-004-coluna-kanban-fk.md)
- **ADR novo:** ADR-005 — Estratégia de versionamento de schema SQLite (a criar em `/implement` ou junto da TASK fundadora)
- **Backlog global:** [../../tasks.md](../../tasks.md)
- **Plano de testes:** [../../plano-testes.md](../../plano-testes.md)
