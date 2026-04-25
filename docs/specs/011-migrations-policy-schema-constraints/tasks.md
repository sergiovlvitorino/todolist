# Tasks — Política de Migrations e Constraints de Integridade do Schema

> **Plan:** [plan.md](plan.md)
> **Fase:** `/tasks` → artefato de entrada para `/implement`
> **Autores:** agentes `tl-python` + `qa`
> **Data:** 2026-04-25

---

## Regras desta fase

- Cada task é **atômica**: P (≤ 2 h) ou M (2–6 h). Tasks G são proibidas.
- Numeração `TASK-NNN` é global e contínua (continua a sequência de [docs/tasks.md](../../tasks.md)). Última usada: TASK-046.
- Toda task aterra em ≥ 1 TC (mapeados no `plan.md`, registrados em [docs/plano-testes.md](../../plano-testes.md)).
- Ordem respeita topologia (dependências explícitas).

---

## Estimativas

- **P:** até 2 h
- **M:** 2–6 h
- **G:** proibida — quebrar até caber em M

---

## Decomposição

| # | ID | Descrição | Camada | Esforço | Depende | TC aceite |
|---|---|---|---|---|---|---|
| 1 | TASK-047 | ADR-005 — Estratégia de versionamento de schema SQLite (`docs/adr-005-schema-versioning.md`) | docs | P | — | — (gate de spec) | ✅ |
| 2 | TASK-048 | Adicionar constantes em `utils/constants.py` (`SCHEMA_VERSION_ATUAL=2`, `LIMIAR_PROGRESSO_MIGRACAO_S=1.5`, `BACKUPS_RETIDOS=3`, `QUARENTENA_DIR`) | utils | P | TASK-047 | TC-093 | ✅ |
| 3 | TASK-049 | Criar tabela `schema_version` e funções `get_schema_version`/`set_schema_version` em `database/migrations.py`; ativar `PRAGMA foreign_keys=ON` em `connection.py` | database | P | TASK-048 | TC-093, TC-094 | ✅ |
| 4 | TASK-050 | Criar módulo `database/backup.py` (`criar_backup`, `rotacionar_backups`, `listar_backups`) | database | P | TASK-048 | TC-101 | ✅ |
| 5 | TASK-051 | Criar módulo `database/quarantine.py` (`RegistroQuarentena`, `registrar_em_quarentena`, escrita append-only em JSON diário) | database | P | TASK-048 | TC-095..TC-098 | ✅ |
| 6 | TASK-052 | Definir `Migration` (dataclass) e refatorar `initialize_database` para motor versionado iterando `MIGRATIONS` em ordem; bootstrap idempotente do banco novo (v0→v2 direto) | database | M | TASK-049 | TC-093, TC-094 | ✅ |
| 7 | TASK-053 | Implementar migration v1→v2 — saneamento de `tasks` (prioridade, status, coluna_kanban, datas) com escrita em quarentena | database | M | TASK-051, TASK-052 | TC-095, TC-096, TC-097, TC-098 | ✅ |
| 8 | TASK-054 | Implementar migration v1→v2 — saneamento de `kanban_columns` (criado_em ausente) com escrita em quarentena | database | P | TASK-051, TASK-052 | TC-098 | ✅ |
| 9 | TASK-055 | Implementar migration v1→v2 — recriação de `tasks_new` e `kanban_columns_new` com `CHECK`, `NOT NULL`, `FK ON DELETE RESTRICT`; copiar dados saneados; trocar tabelas; recriar índices | database | M | TASK-053, TASK-054 | TC-102, TC-103 | ✅ |
| 10 | TASK-056 | Validação final pós-migration: `PRAGMA integrity_check`, `PRAGMA foreign_key_check`; falha → rollback + restauração do backup | database | P | TASK-055 | TC-100, TC-103 | ✅ |
| 11 | TASK-057 | Detecção de versão futura: `versao_origem > SCHEMA_VERSION_ATUAL` falha com erro claro e arquivo intacto | database | P | TASK-052 | TC-099 | ✅ |
| 12 | TASK-058 | Criar `services/migration_service.py` com `MigrationService.executar` orquestrando backup → migrations → validação → rotação → `MigrationReport` | services | M | TASK-050, TASK-056, TASK-057 | TC-094, TC-100 | ✅ |
| 13 | TASK-059 | Integrar `MigrationService` no bootstrap da aplicação antes de instanciar a UI | services | P | TASK-058 | TC-094 | ✅ |
| 14 | TASK-060 | Criar `ui/splash.py` (`MigrationSplash`) com indicador condicional (> 1,5 s), exibição de quarentena e modo de erro com caminho do backup | ui | M | TASK-058 | TC-104, TC-105, TC-106 | ✅ |
| 15 | TASK-061 | Auditoria de consistência domínio×schema: revisar mensagens de erro de `Task`/`KanbanColumn` para alinhar com `IntegrityError` do schema | models | P | TASK-055 | TC-108 | ✅ |
| 16 | TASK-062 | Testes de migração — fixtures de bancos legados (válido, prioridade nula, status nulo, coluna fantasma, datas nulas, versão futura) | testes | M | TASK-058 | TC-094..TC-099 |
| 17 | TASK-063 | Testes de constraints SQL diretas (insert cru com violação) e `foreign_key_check` | testes | P | TASK-055 | TC-102, TC-103 |
| 18 | TASK-064 | Testes de backup/quarentena (rotação 3, escrita append-only, payload preservado) | testes | P | TASK-050, TASK-051 | TC-101, TC-095..TC-098 |
| 19 | TASK-065 | Testes de UI do splash (progresso > 1,5 s, exibição de quarentena, erro com caminho do backup) | testes | P | TASK-060 | TC-104, TC-105, TC-106 | ✅ |
| 20 | TASK-066 | Benchmark `pytest.mark.slow`: migração de 10 000 tarefas conclui em ≤ 3 s | testes | P | TASK-058 | TC-107 |
| 21 | TASK-067 | Atualizar `docs/plano-testes.md` (adicionar TC-093..TC-108) e `docs/funcionalidades.md`/`CHANGELOG.md` (DT-040 + DT-013 fechadas) | docs | P | TASK-066 | — |

**Totais:** 21 tasks (13 P + 8 M) ≈ 42–74 h.

## Ordem topológica de execução

```
TASK-047
  ↓
TASK-048
  ├─→ TASK-049 ──→ TASK-052 ──┐
  ├─→ TASK-050 ───────────────┤
  └─→ TASK-051 ──→ TASK-053 ──┤
                  TASK-054 ──┤
                              ├─→ TASK-055 ──→ TASK-056 ──┐
                              │                  TASK-057 ┤
                              │                            ├─→ TASK-058 ──┐
                              │                            │              ├─→ TASK-059
                              │                            │              ├─→ TASK-060 ──→ TASK-065
                              │                            │              ├─→ TASK-062
                              │                            │              └─→ TASK-066
                              ├─→ TASK-061
                              └─→ TASK-063
                  TASK-050+051 ──→ TASK-064
                                                                              TASK-067 (último)
```

Paralelizável: TASK-049/050/051 após TASK-048; TASK-053/054 após TASK-051+052; TASK-061/063/064 independentes uma vez liberadas suas deps.

## Plano de rollback

A entrega é **irreversível em produção** sob a perspectiva do schema (não há downgrade — explícito na spec). Mitigação:

- **Backup automático** pré-migração permite recuperação manual (usuário substitui `data.db` pelo backup) se a versão nova for revertida.
- **Reversão de código:** reverter na ordem inversa (TASK-067 → TASK-047). Como cada migration é registrada em `schema_version`, a versão antiga do app **não** consegue abrir o arquivo migrado (vai para o caminho TC-099) — usuário precisa restaurar do backup. Isso é o comportamento esperado e documentado.
- **Risco de dados perdidos:** zero, desde que os testes TC-094..TC-108 estejam verdes antes do release. Falhas detectadas em produção exigem hotfix de migration nova (v2→v3 corretiva), nunca downgrade.

## Checklist de encerramento da feature

- [ ] Todos os TCs (TC-093..TC-108) verdes
- [ ] Gates de qualidade verdes (`pytest`, `ruff check`, `ruff format --check`, `mypy src/`)
- [ ] ADR-005 merged
- [ ] DT-040 e DT-013 marcadas como concluídas em `docs/tasks.md`
- [ ] `funcionalidades.md` atualizado (impacto em US-09/US-11)
- [ ] `CHANGELOG.md` com nota de migração automática para usuários existentes (mensagem clara sobre backup)

## Ligações

- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)
- **Backlog global:** [../../tasks.md](../../tasks.md)
- **Plano de testes:** [../../plano-testes.md](../../plano-testes.md)
