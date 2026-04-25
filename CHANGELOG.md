# Changelog

Todas as mudanças relevantes ao usuário deste produto serão documentadas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o
projeto adota [Versionamento Semântico](https://semver.org/lang/pt-BR/).

As entradas são descritas do ponto de vista de quem usa a aplicação — mudanças
puramente internas só aparecem quando afetam estabilidade, performance ou
confiança percebida no produto.

## [Não lançado]

### Adicionado

- **Criação de card diretamente no Kanban.** Cada coluna agora exibe um botão
  "+ Adicionar card" no rodapé. Ao clicar, um formulário inline aparece na própria
  coluna — sem abrir diálogos — com campos de título, prioridade e data de
  vencimento. `Enter` confirma; `Esc` cancela. O card entra no final da coluna e
  fica imediatamente disponível também na aba Todo List. Múltiplas colunas podem
  ter o formulário aberto ao mesmo tempo sem interferência, e rascunhos são
  preservados enquanto você alterna entre colunas. Em caso de falha ao salvar,
  o formulário permanece aberto com os dados intactos e uma mensagem de erro
  descritiva é exibida.

### Corrigido

- **Busca de tarefas agora é case-insensitive para Unicode.** Termos com acento
  funcionam corretamente em qualquer caixa: por exemplo, buscar `reuniao`,
  `Reunião` ou `REUNIÃO` retorna a mesma tarefa. Antes, o SQLite comparava
  apenas o intervalo ASCII (`A`–`Z`) e deixava passar resultados com
  caracteres acentuados.
- **Correção de crash potencial em eventos de mouse no Kanban.** Alguns
  fluxos de `drag-and-drop` de cards podiam receber eventos nulos do Qt e
  derrubar a aplicação. Os handlers agora tratam esses casos com segurança.

### Melhorado

- **Performance de consultas ao banco.** Índices adicionados nas colunas
  mais consultadas (status, coluna Kanban, data de vencimento). Ganho
  perceptível para usuários com volumes maiores de tarefas.
- **Estabilidade geral.** Tratamento consistente de fusos horários usando
  UTC internamente, evitando divergências de data/hora entre sessões.
- **Qualidade de código.** Cobertura de testes automatizados elevada de
  aproximadamente 35% para 94% (234 testes). Impacto direto: maior
  confiança para evoluir o produto sem introduzir regressões.

> Consulte [`docs/tasks.md`](docs/tasks.md) para o catálogo técnico completo,
> incluindo as dívidas já resolvidas e as 13 remanescentes priorizadas para
> os próximos ciclos.

---

## [0.1.0] — 2026-04-16

### Adicionado

- Primeira versão funcional do **Own Board List**.
- **Aba Todo List**: criar, editar, excluir, marcar/desmarcar tarefas como
  concluídas. Agrupamento automático em seções **Hoje**, **Próximas**,
  **Sem data** e **Concluídas**. Atalho `Ctrl+N` para nova tarefa.
  Destaques visuais para tarefas vencidas e concluídas.
- **Aba Kanban**: visualização em colunas padrão (**A Fazer**,
  **Em Andamento**, **Concluído**) com drag-and-drop de cards entre
  colunas, contador por coluna e highlight visual no destino.
- **Sincronização bidirecional** entre as abas em tempo real: alterar na
  Todo List reflete no Kanban, e vice-versa.
- **Persistência local** automática em SQLite (`~/.own-board-list/data.db`),
  sem botão "Salvar" e sem dependência de internet ou autenticação.
