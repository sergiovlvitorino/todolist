# Changelog

Todas as mudanças relevantes ao usuário deste produto serão documentadas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o
projeto adota [Versionamento Semântico](https://semver.org/lang/pt-BR/).

As entradas são descritas do ponto de vista de quem usa a aplicação — mudanças
puramente internas só aparecem quando afetam estabilidade, performance ou
confiança percebida no produto.

## [Não lançado]

### Adicionado

- **Migração automática do banco de dados ao atualizar.** Ao iniciar o aplicativo
  após uma atualização que evolui o formato interno dos dados, a migração ocorre
  automaticamente, antes da interface abrir. Para a grande maioria dos casos, a
  transição é silenciosa. Quando a migração demora mais de 1,5 segundo (bancos
  muito grandes), um indicador de progresso é exibido brevemente.

- **Backup automático antes de migrar.** Imediatamente antes de qualquer
  alteração no formato de dados, o aplicativo cria uma cópia de segurança do
  arquivo atual em `~/.own-board-list/`, com nome que inclui a data e hora e a
  versão de origem (ex.: `data_backup_v1_20260425_143000.db`). As 3 cópias mais
  recentes são mantidas automaticamente; cópias mais antigas são descartadas.
  Em caso de falha, uma mensagem exibe o caminho exato do backup e instrui o
  usuário sobre como obter ajuda.

- **Quarentena de registros inconsistentes.** Dados pré-existentes que não
  satisfazem as novas regras de integridade (ex.: tarefas sem data de criação,
  com status desconhecido ou apontando para coluna removida) são corrigidos
  automaticamente com valores seguros e o registro original é preservado em um
  arquivo lateral de quarentena (`~/.own-board-list/quarantine_YYYYMMDD.json`).
  Quando isso ocorre, o caminho do arquivo de quarentena é exibido no splash de
  migração para que o usuário possa inspecionar. Nenhum dado é descartado
  silenciosamente.

- **Proteção de integridade no armazenamento.** O banco de dados passou a
  rejeitar ativamente registros inválidos independentemente do ponto de entrada:
  tarefas sem título, com prioridade ou status fora dos valores aceitos, com
  posição negativa, sem data de criação/atualização, ou associadas a uma coluna
  inexistente. Isso fecha a lacuna entre a validação da interface e a camada de
  armazenamento, garantindo que dados introduzidos por qualquer ferramenta
  externa ou regressão futura não causem cards invisíveis ou erros opacos.

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
