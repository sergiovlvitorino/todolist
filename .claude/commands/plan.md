---
description: Fase /plan do fluxo SDD — produz o plano técnico (HOW) a partir da spec. Delega ao tl-python.
argument-hint: [NNN-slug | <vazio para feature mais recente>]
---

# /plan — Fase SDD: Planejamento técnico

Você está iniciando a **fase `/plan`** do fluxo SDD do projeto `own-board-list`.

## Pré-requisitos (gating)

1. Ler **obrigatoriamente** [docs/constitution.md](../../docs/constitution.md).
2. Identificar a feature:
   - Se `$ARGUMENTS` foi dado (ex.: `007-busca-todo-list`), usar esse diretório.
   - Senão, usar o `docs/specs/NNN-slug/` com `spec.md` modificado mais recentemente.
3. **RECUSAR** se não existir `docs/specs/NNN-slug/spec.md` para a feature. Instruir o usuário a rodar `/specify` primeiro.
4. **RECUSAR** se a spec contém "Questões em aberto" não resolvidas — listar as pendências e pedir resolução antes de prosseguir.

## Tarefa

Delegue ao subagente **`tl-python`** a produção do plano, com `qa` como reviewer para o bloco "Plano de testes".

Instrua o `tl-python` a:

1. Ler `spec.md` da feature e `docs/constitution.md` na íntegra.
2. Produzir `docs/specs/NNN-slug/plan.md` seguindo o template [docs/specs/_template/plan.md](../../docs/specs/_template/plan.md).
3. Validar que cada decisão respeita os 🔒 princípios invioláveis da constitution. Se alguma decisão **precisa** violar um princípio 🔒, parar e pedir aprovação explícita do usuário + justificativa para ADR novo.
4. Se a feature exige decisão irreversível ou de escopo global, criar ADR novo em `docs/adr-NNN-*.md` (próximo número disponível) e referenciar no `plan.md`.
5. Invocar o subagente `qa` (em paralelo ou ao final) para mapear TCs a serem criados/ampliados; consolidar no bloco "Plano de testes" do `plan.md`.
6. **Não** criar `tasks.md` (isso é fase seguinte).

## Saída esperada

- Caminho do `plan.md` criado.
- Lista de ADRs novos (se houver).
- Riscos principais identificados.
- Próximo passo: rodar `/tasks`.
