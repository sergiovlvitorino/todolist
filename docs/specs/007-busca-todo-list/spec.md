# Spec — Busca de tarefas por texto na Todo List

> **ID:** US-07 (origem em [docs/funcionalidades.md §US-07](../../funcionalidades.md))
> **Diretório:** `docs/specs/007-busca-todo-list/`
> **Fase:** `/specify` → entrada para `/plan`
> **Autor:** agente `po` (handoff original 2026-04-19; migrado para SDD em 2026-04-24)
> **Status:** ✅ Implementado

---

## Contexto

Usuários acumulam dezenas a milhares de tarefas ao longo do tempo. Percorrer visualmente a Todo List para achar uma tarefa específica vira custo cognitivo crescente, especialmente quando o título foi digitado em outro idioma, com acentos ou em caixa mista. Esta feature adiciona um campo de busca textual na aba Todo List que filtra a lista em tempo real conforme o usuário digita.

## User Stories

### US-07.1 — Buscar tarefa pelo título ou descrição

> Como usuário, quero buscar tarefas pelo título ou descrição, para que eu localize rapidamente uma tarefa específica.

**Critérios de aceite:**
- [x] Campo de busca visível no topo da aba Todo List
- [x] Busca filtra a lista em tempo real enquanto o usuário digita (sem botão "Buscar")
- [x] Busca é case-insensitive e insensível a acentos/diacríticos (ex.: "acao" casa "Ação")
- [x] Busca examina tanto o título quanto a descrição da tarefa
- [x] Resultados aparecem distribuídos nas seções existentes (Hoje, Próximas, Sem data, Concluídas)
- [x] Quando nenhum resultado casa, a lista mostra "Nenhuma tarefa encontrada"
- [x] Um caractere literal `%` ou `_` digitado pelo usuário casa apenas esse caractere (não funciona como curinga)
- [x] Termo composto só por espaços é tratado como busca vazia (mostra todas as tarefas)
- [x] Após qualquer operação CRUD (criar, editar, excluir, concluir) com busca ativa, o filtro é reaplicado automaticamente

**Cenários negativos / erros:**
- Quando o usuário digita um termo muito rápido, a lista não "pisca" a cada tecla: há um breve atraso (debounce) antes de aplicar o filtro.
- Quando a lista está filtrada e o usuário abre o formulário de nova/editar tarefa, ao voltar o termo de busca permanece preenchido e o filtro continua aplicado.

### US-07.2 — Controlar o campo de busca pelo teclado

> Como usuário, quero focar e limpar a busca via teclado, para que eu não precise do mouse.

**Critérios de aceite:**
- [x] Atalho para focar o campo de busca (acelerador global na aba)
- [x] Botão visível para limpar o campo com um clique
- [x] Tecla `Esc` enquanto o campo está focado limpa o termo e devolve o foco para a lista

## Requisitos não-funcionais específicos

- **Performance:** filtrar 10.000 tarefas deve responder em ≤ 200 ms (percebido como instantâneo).
- **Privacidade:** o termo digitado nunca é persistido entre sessões.

## Fora de escopo

- Busca por campos estruturados (prioridade, data, status): ficará em US futura (ver US-06 — Filtros).
- Busca fuzzy / aproximada (distância de Levenshtein): explicitamente descartada.
- Busca no Kanban: esta feature é apenas na Todo List.

## Questões em aberto

Nenhuma — feature encerrada.

## Ligações

- **Catálogo mestre:** [docs/funcionalidades.md §US-07](../../funcionalidades.md)
- **Plan desta feature:** [plan.md](plan.md)
- **Tasks desta feature:** [tasks.md](tasks.md)
- **Testes relacionados:** seção "Busca" de [docs/plano-testes.md](../../plano-testes.md)
