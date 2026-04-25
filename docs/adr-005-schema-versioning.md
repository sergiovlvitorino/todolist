# ADR-005 — Estratégia de Versionamento de Schema SQLite

> **Status:** Aceito
> **Data:** 2026-04-25
> **Autores:** agente `tl-python`
> **Contexto:** DT-040 (constraints de integridade) + DT-013 (FK por id estável)

---

## Contexto

O banco SQLite do Own Board List não possuía nenhuma política explícita para
evoluir seu schema ao longo das versões da aplicação. Qualquer mudança
estrutural exigiria que o usuário descartasse o banco ou migrasse manualmente,
o que é inaceitável para um produto desktop local. Além disso, o schema atual
não impõe `CHECK`, `NOT NULL` nem `FOREIGN KEY` nas colunas críticas,
permitindo que dados inválidos entrem via qualquer caminho não coberto pela
validação de domínio.

Esta ADR define o padrão de versionamento a ser adotado daqui em diante.

---

## Decisão

### 1. Tabela de controle `schema_version`

Adotar uma tabela dedicada para registrar as migrations já aplicadas:

```sql
CREATE TABLE IF NOT EXISTS schema_version (
    versao   INTEGER PRIMARY KEY,
    aplicada_em TEXT NOT NULL
);
```

- `versao` é o número inteiro destino da migration (ex.: 2 para v1→v2).
- `aplicada_em` é o timestamp ISO 8601 UTC do momento da aplicação.
- A versão mais alta presente na tabela é a versão atual do schema.
- Banco novo (sem a tabela) é tratado como versão 0.

### 2. Dataclass `Migration` e lista `MIGRATIONS`

Cada passo de evolução é representado por:

```python
@dataclass(frozen=True)
class Migration:
    versao_destino: int
    descricao: str
    aplicar: Callable[[sqlite3.Connection], None]
```

A lista `MIGRATIONS` em `database/migrations.py` é ordenada crescentemente por
`versao_destino`. O motor itera apenas as migrations com
`versao_destino > versao_atual`, garantindo idempotência.

### 3. Atomicidade por migration

Cada migration roda em `BEGIN IMMEDIATE … COMMIT`. Falha → `ROLLBACK` automático
do SQLite + restauração do backup pré-migração feita pelo `MigrationService`.
Migrations já aplicadas não são repetidas (idempotência via `schema_version`).

### 4. Backup pré-migração com rotação fixa

Antes de iniciar qualquer migration, o `MigrationService` cria uma cópia do
arquivo `.db` com o nome `data_backup_vN_YYYYMMDDTHHMMSS.db` no mesmo
diretório. Após migração bem-sucedida, o sistema mantém apenas as 3 cópias mais
recentes (rotação FIFO simples). A retenção configurável fica fora de escopo
nesta versão.

### 5. Quarentena lateral

Registros com valores inválidos que são saneados (e não rejeitados) durante a
migration v1→v2 são gravados em `~/.own-board-list/quarantine_YYYYMMDD.json`
em modo append. O arquivo é somente para inspeção manual; não há UI dedicada
nesta entrega.

### 6. Versão futura

Se `versao_atual > SCHEMA_VERSION_ATUAL` (constante da aplicação), o
`MigrationService` aborta com erro claro e preserva o arquivo intacto. O
usuário é orientado a restaurar o backup ou usar a versão correta da aplicação.

---

## Alternativas avaliadas

| Alternativa | Motivo de rejeição |
|---|---|
| **Alembic** | Dependência externa pesada; projetado para uso com ORM e servidores; não idiomático para SQLite local single-user sem dependências extras. |
| **`PRAGMA user_version`** | Simples, mas opaco para auditoria: não registra quando cada migration foi aplicada nem permite trilha de histórico. |
| **Tabela `schema_version` própria** ✅ | Leve, auditável, sem dependência extra, idiomático para SQLite. Trilha completa via `aplicada_em`. |

---

## Consequências

### Positivas
- Evolução de schema transparente para o usuário.
- Cada passo de migration é rastreável e auditável.
- Backup automático garante recuperação manual em caso de falha.
- Quarentena preserva dados que não satisfazem as novas regras, sem descarte silencioso.
- Defesa em profundidade: `CHECK`/`NOT NULL`/`FK` no schema + validação no domínio (`models/`).

### Negativas / Trade-offs
- Downgrade de schema não é suportado (explícito na spec). Usuário que reverter o binário precisa restaurar o backup manualmente.
- Quarentena cresce indefinidamente (arquivo por dia). Usuário pode apagar manualmente; limpeza automática fica para feature futura.
- Recriação de tabelas com constraints (padrão SQLite) é verbosa — mitigada por testes de regressão TC-102/TC-103.

---

## Versões do schema

| Versão | Descrição | Data |
|---|---|---|
| 0 | Banco novo (sem tabela `schema_version`) | — |
| 1 | Schema original pré-DT-040 (sem `CHECK`/`NOT NULL`/`FK`) | pré-2026-04-25 |
| 2 | Schema com `CHECK`, `NOT NULL`, `FOREIGN KEY ON DELETE RESTRICT`, tabela `schema_version` | 2026-04-25 |

---

## Ligações

- **Spec:** [docs/specs/011-migrations-policy-schema-constraints/spec.md](specs/011-migrations-policy-schema-constraints/spec.md)
- **Plan:** [docs/specs/011-migrations-policy-schema-constraints/plan.md](specs/011-migrations-policy-schema-constraints/plan.md)
- **Constitution:** [docs/constitution.md](constitution.md) — princípios de privacidade local, layering, gates de qualidade
- **ADR-001:** [docs/adr-001-stack.md](adr-001-stack.md) — stack fixo (sqlite3 da stdlib, sem ORM)
- **ADR-004:** [docs/adr-004-coluna-kanban-fk.md](adr-004-coluna-kanban-fk.md) — FK por id da coluna (DT-013)
