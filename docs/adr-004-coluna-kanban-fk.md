# ADR-004 — Adiamento da substituição de `coluna_kanban` (string) por `coluna_id` (FK)

**Status:** Aceito (decisão de adiar)
**Data:** 2026-04-19
**Autor:** Tech Lead (agente tl-python)
**Relacionado:** DT-013, ADR-001

---

## Contexto

A tabela `tasks` referencia colunas do Kanban pelo **nome** da coluna (campo `coluna_kanban TEXT`) — não por ID. O schema atual:

```sql
CREATE TABLE tasks (
    ...
    coluna_kanban TEXT,           -- "A Fazer" | "Em Andamento" | "Concluído" | ...
    posicao_kanban INTEGER,
    ...
);

CREATE TABLE kanban_columns (
    id TEXT PRIMARY KEY,           -- UUID
    nome TEXT NOT NULL,
    posicao INTEGER,
    criado_em TEXT
);
```

Consequências imediatas dessa modelagem:

1. **Renomear uma coluna quebra a associação** com as tasks existentes — o UPDATE do nome em `kanban_columns` não propaga para `tasks.coluna_kanban`.
2. `ColumnRepository.has_tasks(column_id)` precisa fazer **duas queries** (buscar nome pelo ID, depois contar tasks pelo nome) em vez de um `JOIN` natural.
3. Não há integridade referencial: é possível criar uma task com `coluna_kanban = "Xyz"` mesmo que essa coluna não exista.
4. `ON UPDATE CASCADE` / `ON DELETE CASCADE` não podem ser usados porque não há FK declarada.

A feature de "gerenciar colunas do Kanban" (renomear, criar, remover) está no roadmap como *Should Have* — ainda não implementada na UI. Enquanto apenas as três colunas padrão existem (`A Fazer`, `Em Andamento`, `Concluído`) e nunca são renomeadas, o problema é teórico.

---

## Problema

Substituir `coluna_kanban` (string) por `coluna_id` (FK para `kanban_columns.id`) é a modelagem correta, mas envolve:

1. Migração de dados: gerar UUIDs para as colunas existentes, fazer lookup por nome para popular `tasks.coluna_id`, remover `tasks.coluna_kanban`.
2. Mudança no modelo `Task` (campo `coluna_kanban: str` → `coluna_id: str`).
3. Atualização de todos os pontos que consomem `coluna_kanban`: `TaskService`, `TaskRepository.get_by_column`, widgets de Kanban, fixtures e mocks dos testes.
4. Revalidação da suíte completa (234 testes) após a refatoração.
5. Possível quebra de dados dos usuários existentes (embora poucos, dado que é app desktop pessoal).

O esforço estimado é **G** (6–16 horas) e o benefício, dado o estado atual (colunas nunca renomeadas, sem feature de gerenciamento), é **baixo**.

---

## Alternativas avaliadas

| Abordagem | Prós | Contras | Quando faz sentido |
|-----------|------|---------|-------------------|
| **Adiar a mudança (adotado)** | Zero esforço agora; foca capacidade do time em features entregáveis | Débito técnico registrado em DT-013; `has_tasks()` continua com 2 queries | Até que renomear/gerenciar colunas vire feature |
| Executar a migração completa agora | Modelagem correta; `ON UPDATE CASCADE` resolve renomeações "de graça" | 1 semana de trabalho em um ciclo sem demanda funcional por isso | Quando gerenciamento de colunas entrar no roadmap |
| Híbrido: manter ambos os campos (`coluna_kanban` + `coluna_id`) por um ciclo | Transição gradual | Denormalização com risco de inconsistência; complica writes | Descartado — pior dos dois mundos |
| Trigger SQLite que propaga renomeações | Resolve só o sintoma de renomear | Mantém `has_tasks()` com 2 queries; trigger é estado invisível no app | Descartado — não resolve raiz |

---

## Decisão

**Adiar** a migração. Manter `coluna_kanban TEXT` como o campo de referência até que uma das condições de gatilho seja atingida.

**Dívida registrada:** DT-013 em `docs/tasks.md`, prioridade **Média**, esforço **G**, parecer PO 2026-04-19 ("aceita para próximo ciclo com ressalva de prioridade no backlog").

**Parecer técnico (Tech Lead):** concordo com o adiamento *desde que* a dívida seja revisitada antes da implementação de qualquer feature de gerenciamento de colunas. Fazer a feature sobre o modelo errado custaria muito mais do que fazer a migração agora.

---

## Gatilhos para revisitar (qualquer um basta)

1. **Feature de gerenciar colunas entra no sprint** (US-12 ou equivalente de `docs/funcionalidades.md`) — renomear/criar/excluir colunas via UI. **Antes** de começar, migrar para FK.
2. **Mais de 5 colunas customizadas** em uso por usuários reais — aumenta a probabilidade de renomeação e de inconsistência.
3. **Primeiro bug reportado** de task "órfã" (apontando para coluna inexistente) — virou problema real.
4. **Necessidade de query relacional** (ex.: "tasks agrupadas por coluna com contagem") que ficaria trivial com JOIN direto em vez do lookup atual.

Sem nenhum desses gatilhos em ~3 ciclos, revisar formalmente no retrospective técnico (a dívida pode ter se tornado dispensável por outras mudanças de roadmap).

---

## Consequências

### Positivas (do adiamento)

- Capacidade preservada para outras dívidas técnicas e features.
- Zero risco de regressão neste ciclo.
- Decisão explícita e documentada — não é mais "ninguém lembrou de fazer", é "decidimos não fazer agora".

### Negativas (assumidas conscientemente)

- `has_tasks()` continua com 2 queries (custo irrisório no volume atual).
- Renomear uma coluna manualmente (via SQL direto ou feature futura) quebra as tasks associadas se não houver cuidado explícito.
- Sem integridade referencial para `coluna_kanban`.
- **Cada ciclo que passa com a dívida aumenta a superfície de código que precisará ser alterada** na eventual migração. Este custo é linear no número de locais que referenciam `coluna_kanban` — atualmente 8 locais (mapeados em DT-013).

### Critério de rollback / reversão

A decisão em si é pouco arriscada (mantém status quo). Caso o adiamento se prove errado (algum gatilho acontecer antes do esperado), o plano de migração está esboçado em DT-013 com critérios de aceite claros. Não há "rollback" — há "executar quando for necessário".

---

## Plano de migração (para quando o gatilho disparar)

Registrado aqui para não precisar redescobrir depois:

1. Adicionar coluna `tasks.coluna_id TEXT` (nullable inicialmente).
2. `UPDATE tasks SET coluna_id = (SELECT id FROM kanban_columns WHERE nome = tasks.coluna_kanban)`.
3. Validar que nenhum `coluna_id IS NULL` (se houver, log + correção caso-a-caso).
4. Recriar a tabela `tasks` com `coluna_id NOT NULL REFERENCES kanban_columns(id) ON UPDATE CASCADE ON DELETE RESTRICT` (SQLite não suporta `ALTER TABLE ADD FOREIGN KEY` — precisa recriar).
5. Remover `coluna_kanban`.
6. Atualizar o índice: `idx_tasks_coluna_kanban` → `idx_tasks_coluna_id`.
7. Adaptar `Task`, repositórios, service, widgets e testes.
8. Adicionar teste específico de renomeação: renomear coluna deve preservar associação.
9. Executar suíte completa + smoke manual.

Estimativa revisada na ocasião: **G** (permanece válida).

---

## Referências

- `docs/tasks.md` §DT-013
- `docs/adr-001-stack.md` §"Banco de Dados"
- SQLite — [ALTER TABLE limitations](https://www.sqlite.org/lang_altertable.html)
