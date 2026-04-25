# CLAUDE.md — Own Board List

Este arquivo orienta agentes e contribuidores ao operar neste repositório. Leia-o antes de qualquer edição.

## Leitura obrigatória

1. **[docs/constitution.md](docs/constitution.md)** — princípios invioláveis (🔒), padrões fortes (⚖️) e gates de qualidade (✅). **Nada neste projeto é decidido sem passar por aqui.**
2. **[README.md](README.md)** — visão do produto, stack, como rodar.
3. **[docs/funcionalidades.md](docs/funcionalidades.md)** — catálogo mestre de user stories (US-01..US-NN).

## Fluxo Spec-Driven Development

Toda feature não-trivial segue quatro fases, cada uma com um slash command e um agente responsável:

```
/specify  →  docs/specs/NNN-slug/spec.md   (agente: po)          WHAT e WHY — zero tecnologia
/plan     →  docs/specs/NNN-slug/plan.md   (agente: tl-python)   HOW — camadas, contratos, ADRs novos
/tasks    →  docs/specs/NNN-slug/tasks.md  (tl-python + qa)      Decomposição atômica + TCs
/implement →  código + testes + commit      (dev-python + qa)     Uma task por vez, gates verdes
```

**Gating**: `/plan` exige `spec.md`; `/tasks` exige `plan.md`; `/implement` exige `tasks.md`. Slash commands em `.claude/commands/` implementam essa ordem.

**Escape hatch** (apenas para trabalho trivial): dívidas técnicas catalogadas (`DT-NNN`) e bugs óbvios pulam `/specify` e `/plan` e vão direto para `/implement` com commit `fix(DT-NN):`. Features novas **nunca** pulam fases.

**Exemplo completo migrado**: [docs/specs/007-busca-todo-list/](docs/specs/007-busca-todo-list/) mostra o trio `spec.md` + `plan.md` + `tasks.md` para US-07 (Busca de tarefas por texto).

## Mapa de artefatos

| Pergunta | Arquivo |
|---|---|
| Quais são os princípios invioláveis do projeto? | [docs/constitution.md](docs/constitution.md) |
| Quais user stories existem? | [docs/funcionalidades.md](docs/funcionalidades.md) |
| Por que a stack é esta? | [docs/adr-001-stack.md](docs/adr-001-stack.md) |
| Qual o backlog técnico global e o catálogo de DTs? | [docs/tasks.md](docs/tasks.md) |
| Plano de testes e TCs | [docs/plano-testes.md](docs/plano-testes.md) |
| Uma feature específica em andamento | `docs/specs/NNN-slug/` |
| Templates para novas features | [docs/specs/_template/](docs/specs/_template/) |
| Mudanças perceptíveis ao usuário | [CHANGELOG.md](CHANGELOG.md) |

## Convenções

- **Linguagem dos artefatos**: português brasileiro.
- **Numeração** (preservada): `US-NN`, `ADR-NNN`, `TASK-NNN`, `DT-NNN`, `TC-NNN`.
- **Diretório de spec por feature**: `docs/specs/NNN-slug/` onde `NNN` é o número zero-padded da US principal entregue.
- **Commits**: `<tipo>(US-NN|TASK-NNN|DT-NNN): <descrição>` — todo commit referencia ao menos um identificador rastreável. Tipos: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.
- **Gates de qualidade** (rodar antes de marcar task como concluída):
  ```bash
  uv run pytest
  uv run ruff check .
  uv run ruff format --check .
  uv run mypy src/
  ```

## Agentes

Os agentes envolvidos no fluxo SDD (definições em `~/.claude/agents/`):

| Agente | Fase SDD | Função |
|---|---|---|
| `po` | `/specify` | Escreve `spec.md` (WHAT/WHY, zero tecnologia) |
| `tl-python` | `/plan`, `/tasks` | Escreve `plan.md`, abre ADRs, decompõe em tasks |
| `qa` | `/plan`, `/tasks`, `/implement` | Mapeia TCs, valida cada task no encerramento |
| `dev-python` | `/implement` | Implementa task por task, uma por vez, com gates verdes |
| `sre` | sob demanda | Infra/observabilidade/CI quando aplicável |

Cada agente tem uma seção "Fluxo Spec-Driven Development" no seu prompt que define obrigações e restrições. Quando em dúvida, esse prompt + a constitution ganham de qualquer palpite.
