# Spec — Criar card diretamente no Kanban

> **ID:** US-10 (origem em [docs/funcionalidades.md §US-10](../../funcionalidades.md))
> **Diretório:** `docs/specs/010-criar-card-kanban/`
> **Fase:** `/specify` → entrada para `/plan`
> **Autor:** agente `po`
> **Data:** 2026-04-24
> **Status:** ✅ Pronto para `/plan`

---

## Contexto

Hoje, para adicionar uma tarefa enquanto o usuário está pensando em termos de fluxo de trabalho (coluna do Kanban), ele precisa trocar para a aba Todo List, criar a tarefa (que entra em "A Fazer" por padrão via US-13) e, se quiser que ela apareça em outra coluna, movê-la pelo Kanban (US-09). Esse vai-e-vem quebra o raciocínio: quando o usuário está olhando para "Em Andamento", ele quer registrar o item diretamente ali. Esta feature permite criar uma tarefa no rodapé de qualquer coluna, sem sair do Kanban, com o novo card já pertencendo àquela coluna.

Depende de: US-08 (quadro e colunas já visíveis), US-13 (sincronização entre abas) e US-01 (modelo de campos de tarefa: título, descrição, data de vencimento, prioridade).

## User Stories

### US-10.1 — Criar card no rodapé de uma coluna do Kanban

> Como usuário, quero criar uma nova tarefa diretamente em uma coluna do Kanban, para que eu não precise trocar de aba nem mover o card depois.

**Critérios de aceite:**
- [ ] Cada coluna do quadro exibe, no seu rodapé, um controle identificável como "+ Adicionar card".
- [ ] Ao acionar o controle de uma coluna, aparece um formulário de criação **inline**, dentro da própria coluna, logo acima ou no lugar do controle "+ Adicionar card".
- [ ] O formulário inline é enxuto e oferece exatamente três campos: **título** (obrigatório), **prioridade** (opcional; valores Baixa, Média, Alta; padrão Média — paridade com US-01) e **data de vencimento** (opcional). O campo de descrição **não** aparece no formulário inline; para preenchê-lo, o usuário abrirá os detalhes do card depois (escopo de US-12).
- [ ] O formulário abre já com o foco no campo de título.
- [ ] O formulário oferece ação explícita "Adicionar" (confirma) e ação explícita "Cancelar" (descarta).
- [ ] Ao confirmar com título válido, o novo card aparece como **último card** da coluna em que o formulário foi aberto, sem recarregar o quadro inteiro.
- [ ] Após confirmar, o formulário inline permanece aberto e limpo, pronto para uma próxima criação naquela mesma coluna (criação em rajada), mantendo o foco no campo de título.
- [ ] Ao cancelar, nenhum card é criado e o formulário é fechado, restaurando o controle "+ Adicionar card".
- [ ] A tarefa criada pelo Kanban também passa a ser visível na aba Todo List (via US-13), com os mesmos campos preenchidos.
- [ ] A coluna em que o card foi criado é a coluna à qual o card pertence — ele **não** cai forçosamente em "A Fazer" quando criado em outra coluna.
- [ ] **A coluna dita o status do card criado** (consistente com US-09): se a coluna mapeia para o status "concluído", o card nasce já marcado como concluído; em qualquer outra coluna, o card nasce como pendente. Esse status é imediatamente refletido na aba Todo List via US-13.
- [ ] O contador de cards da coluna (US-08) é atualizado imediatamente após a criação.

**Cenários negativos / erros:**
- Quando o usuário confirma com o título **vazio** (ou apenas espaços em branco), nenhum card é criado, o formulário permanece aberto, o campo de título recebe destaque de erro e uma mensagem curta indica que o título é obrigatório.
- Quando o usuário informa um título com mais de 200 caracteres (limite da US-01), o sistema impede a confirmação e sinaliza o limite (seja bloqueando a digitação além do limite, seja mostrando mensagem de erro ao tentar confirmar).
- Quando o usuário informa uma data de vencimento em formato inválido, o sistema impede a confirmação e sinaliza o erro no campo de data, sem criar o card.
- Quando o usuário cancela o formulário, qualquer conteúdo digitado é descartado irreversivelmente (sem diálogo de confirmação).
- Quando a criação falha por erro de persistência, o card não aparece na coluna, o formulário permanece aberto com os dados preenchidos e uma mensagem informa a falha.

### US-10.2 — Controlar o formulário inline por teclado

> Como usuário, quero confirmar ou cancelar a criação do card sem usar o mouse, para que o fluxo de registro seja rápido.

**Critérios de aceite:**
- [ ] Com o formulário inline aberto e o foco em qualquer um dos seus campos, pressionar `Enter` no campo de título tem o mesmo efeito de "Adicionar" (quando o título é válido).
- [ ] Pressionar `Esc` com o formulário aberto tem o mesmo efeito de "Cancelar" e fecha o formulário.
- [ ] É possível alternar entre os campos do formulário usando `Tab` / `Shift+Tab` na ordem lógica (título → prioridade → data → Adicionar → Cancelar).
- [ ] Quando o formulário é aberto, nenhum atalho global do Kanban (ex.: mover card) dispara em resposta ao que for digitado no título.
- [ ] Não existe, nesta feature, atalho global para **abrir** o formulário de uma coluna: a abertura se dá exclusivamente pelo clique (ou acionamento via teclado no controle focado) do botão "+ Adicionar card" da coluna desejada.

**Cenários negativos / erros:**
- Quando o usuário pressiona `Enter` com o título vazio, o comportamento é o mesmo do cenário de título vazio de US-10.1 (erro inline, sem criar card).

### US-10.3 — Usar múltiplas colunas ao mesmo tempo sem interferência

> Como usuário, quero poder abrir o formulário de criação em várias colunas simultaneamente ou trocar de coluna durante a digitação, para que eu não perca contexto.

**Critérios de aceite:**
- [ ] É permitido ter o formulário inline aberto em **mais de uma coluna ao mesmo tempo**; cada formulário mantém seus próprios dados digitados independentemente.
- [ ] Abrir o formulário em uma coluna B não fecha nem limpa um formulário já aberto na coluna A.
- [ ] Cancelar o formulário em uma coluna não afeta o formulário aberto em outras colunas.
- [ ] Confirmar o formulário em uma coluna cria o card apenas naquela coluna; os formulários abertos em outras colunas continuam intactos.
- [ ] Clicar fora de um formulário inline (em outro card, em outra coluna, ou em área vazia do quadro) **não** fecha o formulário nem descarta o conteúdo digitado — o formulário só é fechado por "Adicionar", "Cancelar" ou `Esc`.

**Regra de descarte do rascunho:**
- O conteúdo digitado no formulário inline é um **rascunho volátil**, sem persistência. Ele é descartado sempre que o formulário se encerra, incluindo: ação "Cancelar", tecla `Esc`, perda de foco da janela para fora do Kanban ou fechamento do aplicativo. Ao reabrir o aplicativo ou reativar o Kanban, o formulário não reaparece e nada do que foi digitado é recuperado.

## Requisitos não-funcionais específicos

- **Performance:** abrir o formulário inline e confirmar a criação devem ser percebidos como instantâneos (≤ 200 ms, em linha com RNF-01), inclusive em quadros com 10.000 tarefas distribuídas.
- **Acessibilidade:** todo o fluxo (abrir, preencher, confirmar, cancelar) é operável apenas por teclado (RNF-05).

## Fora de escopo

- Criar card via drag-and-drop de texto externo (arrastar e soltar): não coberto.
- Criar múltiplos cards de uma vez coletando uma lista (bulk import): não coberto.
- Criação de card em posição específica dentro da coluna (ex.: no topo, ou entre dois cards existentes): nesta feature, o novo card **sempre** entra no final da coluna.
- Templates ou valores padrão configuráveis para o formulário inline (ex.: "todo card criado em 'Em Andamento' já vem com prioridade Alta"): não coberto.
- Edição de campos avançados não previstos na US-01 (etiquetas, checklists, anexos): fora de escopo do MVP.
- Qualquer alteração no comportamento de criação pela Todo List (US-01).
- **Edição do campo descrição no momento da criação pelo Kanban:** o formulário inline é intencionalmente enxuto e não expõe descrição. O preenchimento/edição de descrição é feito depois, pela tela de detalhes do card (escopo de US-12).
- **Persistência de rascunhos** do formulário inline entre sessões ou reaberturas do Kanban: não coberto (rascunho é sempre volátil).
- **Atalho de teclado global** para abrir o formulário na coluna focada (análogo ao `Ctrl+N` da Todo List): não coberto nesta US; registrado como possível evolução futura.
- **Comportamento da exclusão de uma coluna que contém formulário inline aberto** (via US-11): não é decidido aqui; é **dependência futura** a ser definida quando US-11 (gerenciar colunas) for especificada.
- **Limite visual/layout do formulário inline** quando há muito conteúdo: tratado na fase `/plan` como decisão de UX/implementação, não como requisito de produto.

## Dependências futuras

- **US-11 (gerenciar colunas):** quando for especificada, deverá definir o que acontece ao excluir uma coluna que tenha um formulário inline aberto (descartar silenciosamente vs. bloquear exclusão). Até lá, assume-se que US-11 não está disponível e esse cenário não ocorre.

## Ligações

- **Catálogo mestre:** [docs/funcionalidades.md §US-10](../../funcionalidades.md)
- **Dependências de produto:** US-01 (campos de tarefa), US-08 (quadro Kanban), US-13 (sincronização entre abas).
- **Relacionadas:** US-09 (mover cards), US-11 (gerenciar colunas), US-12 (detalhes do card).
- **Testes relacionados:** TCs a serem mapeados em [docs/plano-testes.md](../../plano-testes.md) durante `/plan` e `/tasks`.
