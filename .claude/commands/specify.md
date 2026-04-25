---
description: Fase /specify do fluxo SDD — cria ou atualiza a spec (WHAT/WHY) de uma feature. Delega ao agente po.
argument-hint: <descrição em linguagem natural da feature>
---

# /specify — Fase SDD: Especificação

Você está iniciando a **fase `/specify`** do fluxo Spec-Driven Development do projeto `own-board-list`.

## Pré-requisitos

- Ler **obrigatoriamente** [docs/constitution.md](../../docs/constitution.md) antes de qualquer coisa.
- Ler [docs/funcionalidades.md](../../docs/funcionalidades.md) para saber quais US já existem e qual é o próximo número disponível.

## Entrada

Descrição da feature fornecida pelo usuário: **$ARGUMENTS**

## Tarefa

Delegue ao subagente **`po`** (via ferramenta Agent com `subagent_type: po`) a produção da spec seguindo o template [docs/specs/_template/spec.md](../../docs/specs/_template/spec.md).

Instrua o agente `po` a:

1. Identificar se a feature corresponde a uma US existente em `docs/funcionalidades.md` ou é nova.
2. Se for nova, reservar o próximo `US-NN` disponível e adicionar entrada curta em `docs/funcionalidades.md` linkando para o novo diretório de spec.
3. Criar o diretório `docs/specs/NNN-slug/` (NNN zero-padded; `slug` em kebab-case curto).
4. Produzir `docs/specs/NNN-slug/spec.md` respeitando as regras da fase:
   - Zero menção de tecnologia (PyQt, SQLite, nomes de classes).
   - Critérios de aceite observáveis e testáveis.
   - Cenários de erro explícitos.
   - Qualquer ambiguidade vai em "Questões em aberto".
5. **Não** criar `plan.md` ou `tasks.md` (isso é fase seguinte).

## Saída esperada

Ao final, confirmar ao usuário:
- Caminho do `spec.md` criado.
- Lista de questões em aberto (se houver) que bloqueiam `/plan`.
- Próximo passo: rodar `/plan` quando questões estiverem resolvidas.
