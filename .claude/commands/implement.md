---
description: Fase /implement do fluxo SDD — executa as tasks com dev-python + qa, uma por vez, fechando com testes verdes e commit rastreável.
argument-hint: [NNN-slug | TASK-NNN | DT-NNN]
---

# /implement — Fase SDD: Implementação

Você está iniciando a **fase `/implement`** do fluxo SDD do projeto `own-board-list`.

## Pré-requisitos (gating)

1. Ler **obrigatoriamente** [docs/constitution.md](../../docs/constitution.md).
2. Decidir o alvo:
   - Se `$ARGUMENTS` é `NNN-slug`: executar as tasks pendentes de `docs/specs/NNN-slug/tasks.md` na ordem topológica.
   - Se `$ARGUMENTS` é `TASK-NNN` ou `DT-NNN`: executar somente essa task. Dívidas técnicas catalogadas e bugs triviais podem usar esta forma **sem** passar por `/specify`/`/plan` (escape hatch da constitution).
   - Se `$ARGUMENTS` vazio: continuar a feature mais recente com tasks não fechadas.
3. **RECUSAR** forma `NNN-slug` se não existir `tasks.md`. Instruir a rodar `/tasks` primeiro.

## Tarefa

Para **cada task pendente na ordem**, delegue ao subagente **`dev-python`** a implementação, com **`qa`** como validador ao final de cada task.

Ciclo por task:

1. `dev-python` lê a task + `plan.md` relevante + constitution.
2. `dev-python` implementa o código (incluindo testes), mantendo layering MVP intacto.
3. Rodar gates de qualidade localmente (ver [constitution §Gates](../../docs/constitution.md#-gates-de-qualidade)):
   - `uv run pytest`
   - `uv run ruff check .`
   - `uv run ruff format --check .`
   - `uv run mypy src/`
4. Se algum gate falhar: `dev-python` corrige antes de prosseguir. Não marcar task como concluída com gate vermelho.
5. `qa` valida TC de aceite da task.
6. Commit único referenciando a task:
   ```
   <tipo>(US-NN|TASK-NNN|DT-NNN): <descrição curta>
   ```
7. Marcar task como `[x]` em `docs/specs/NNN-slug/tasks.md` **e** em `docs/tasks.md` (backlog global).
8. Parar e reportar ao usuário antes de seguir para a próxima task (continuar automaticamente se o usuário estiver em auto mode).

## Encerramento da feature

Após a última task, rodar checklist de [encerramento do template de tasks](../../docs/specs/_template/tasks.md):
- Todos os TCs passando
- Gates verdes
- `funcionalidades.md` atualizada
- `CHANGELOG.md` atualizado se mudança perceptível
- ADRs novos merged

## Saída esperada

Por task: resumo 2-linhas (o que foi feito + hash do commit).
Ao final da feature: checklist de encerramento marcado.
