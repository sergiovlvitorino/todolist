# Funcionalidades — Gestor de Tarefas Desktop

> **Versão:** 1.0 — Escopo inicial (usuário único, local, sem autenticação)
> **Elaborado por:** Agente PO
> **Data:** 2026-04-16

---

## Visão Geral do Produto

Software desktop para gestão pessoal de tarefas, com duas visões complementares: uma lista de tarefas (Todo List) para acompanhamento linear e um quadro Kanban para visualização do fluxo de trabalho. Os dados são armazenados localmente, sem necessidade de internet ou autenticação.

---

## Aba 1 — Todo List

### US-01 — Criar tarefa

> Como usuário, quero criar uma nova tarefa informando título, descrição e data de vencimento, para que eu possa registrar o que precisa ser feito.

**Critérios de aceite:**
- Campo título obrigatório (máx. 200 caracteres)
- Campo descrição opcional (texto livre)
- Campo data de vencimento opcional (seletor de data)
- Campo prioridade opcional: Baixa, Média, Alta (padrão: Média)
- Ao salvar, a tarefa aparece no topo da lista
- Atalho de teclado para abrir formulário de criação (ex: `Ctrl+N`)

---

### US-02 — Visualizar lista de tarefas

> Como usuário, quero ver todas as minhas tarefas em uma lista organizada, para que eu tenha visibilidade do que precisa ser feito.

**Critérios de aceite:**
- Exibe título, prioridade, data de vencimento e status (pendente/concluída) de cada tarefa
- Tarefas vencidas são destacadas visualmente (ex: data em vermelho)
- Tarefas concluídas são exibidas com estilo riscado/esmaecido
- Lista separada em seções: "Hoje", "Próximas", "Sem data", "Concluídas"

---

### US-03 — Marcar tarefa como concluída

> Como usuário, quero marcar uma tarefa como concluída com um clique, para que eu possa acompanhar meu progresso sem precisar deletar o histórico.

**Critérios de aceite:**
- Checkbox visível ao lado de cada tarefa
- Ao marcar, a tarefa é movida para a seção "Concluídas"
- É possível desmarcar (reabrir) uma tarefa concluída
- Ação reversível sem confirmação

---

### US-04 — Editar tarefa

> Como usuário, quero editar os dados de uma tarefa existente, para que eu possa corrigir informações ou atualizar detalhes.

**Critérios de aceite:**
- Duplo clique ou botão de edição abre o formulário preenchido
- Todos os campos são editáveis
- Alterações são salvas ao confirmar
- Cancelar descarta as alterações sem modificar a tarefa

---

### US-05 — Excluir tarefa

> Como usuário, quero excluir uma tarefa, para que eu possa remover itens irrelevantes da minha lista.

**Critérios de aceite:**
- Botão de exclusão disponível em cada tarefa
- Confirmação obrigatória antes de excluir ("Tem certeza?")
- Exclusão é permanente (não vai para lixeira)

---

### US-06 — Filtrar e ordenar tarefas

> Como usuário, quero filtrar e ordenar minha lista de tarefas, para que eu encontre rapidamente o que preciso.

**Critérios de aceite:**
- Filtros disponíveis: status (pendentes / concluídas / todas), prioridade, data de vencimento
- Ordenação por: data de criação, data de vencimento, prioridade, título (A–Z)
- Filtros e ordenação são persistidos durante a sessão
- Botão "Limpar filtros" visível quando algum filtro está ativo

---

### US-07 — Buscar tarefa por texto

> Como usuário, quero buscar tarefas pelo título ou descrição, para que eu localize rapidamente uma tarefa específica.

**Critérios de aceite:**
- Campo de busca no topo da aba
- Busca em tempo real (filtra ao digitar)
- Busca case-insensitive
- Exibe mensagem "Nenhuma tarefa encontrada" quando não há resultados

---

## Aba 2 — Board Kanban

### US-08 — Visualizar quadro Kanban

> Como usuário, quero visualizar minhas tarefas em um quadro Kanban com colunas, para que eu tenha uma visão clara do fluxo de trabalho.

**Critérios de aceite:**
- Colunas padrão: **A Fazer**, **Em Andamento**, **Concluído**
- Cada coluna exibe título, contador de cards e lista de cards
- Cards exibem: título, prioridade (cor) e data de vencimento
- Scroll horizontal automático quando há muitas colunas

---

### US-09 — Mover card entre colunas

> Como usuário, quero mover um card de uma coluna para outra via drag-and-drop, para que eu possa atualizar o status da tarefa de forma visual e intuitiva.

**Critérios de aceite:**
- Drag-and-drop funcional entre todas as colunas
- Botão contextual "Mover para →" como alternativa ao drag-and-drop
- Ao mover para "Concluído", a tarefa é marcada como concluída automaticamente
- Ao mover de "Concluído" para outra coluna, o status é revertido para pendente

> **Nota técnica (DT-040/DT-013, 2026-04-25):** a exclusão de coluna que contenha
> cards continua bloqueada (aviso ao usuário), agora reforçada também em nível de
> banco de dados (`FOREIGN KEY … ON DELETE RESTRICT`). Tarefas que, em bancos
> pré-existentes, apontassem para colunas inexistentes são automaticamente
> realocadas para a coluna "A Fazer" na primeira migração, com registro em
> quarentena.

---

### US-10 — Criar card diretamente no Kanban

> Como usuário, quero criar uma nova tarefa diretamente em uma coluna do Kanban, para que eu não precise trocar de aba.

**Critérios de aceite:**
- Botão "+ Adicionar card" no rodapé de cada coluna
- Formulário inline com título obrigatório e campos opcionais
- Card criado aparece no final da coluna selecionada
- A tarefa criada também aparece na aba Todo List

**Status:** implementada (2026-04-24) — TASK-037 a TASK-046 concluídas, gates verdes, 346 testes passando.

**Spec detalhada:** [docs/specs/010-criar-card-kanban/spec.md](specs/010-criar-card-kanban/spec.md)

---

### US-11 — Gerenciar colunas do Kanban

> Como usuário, quero criar, renomear e excluir colunas no quadro Kanban, para que eu possa adaptar o fluxo de trabalho às minhas necessidades.

**Critérios de aceite:**
- Botão "+" para adicionar nova coluna (nome obrigatório)
- Duplo clique no título da coluna permite renomear
- Opção de excluir coluna disponível no menu da coluna
- Não é possível excluir coluna que contém cards (exibe aviso)
- Colunas podem ser reordenadas via drag-and-drop
- Mínimo de 1 coluna no quadro

> **Nota técnica (DT-013, 2026-04-25):** a identidade de cada coluna agora é
> armazenada por `id` (UUID estável) em vez de nome. Isso torna possível, em
> versão futura, renomear uma coluna sem perder a associação com suas tarefas.
> O fluxo de UI de renomeação pertence a esta US-11 e será entregue em ciclo
> subsequente; a infra de banco que viabiliza o recurso foi incluída no ciclo
> atual (feature 011).

---

### US-12 — Visualizar detalhes do card

> Como usuário, quero clicar em um card para ver e editar todos os seus detalhes, para que eu possa acessar informações completas sem sair do Kanban.

**Critérios de aceite:**
- Clique no card abre painel lateral ou modal com todos os campos
- Campos editáveis diretamente no painel
- Exibe data de criação e última modificação
- Alterações são salvas ao fechar o painel

---

## Funcionalidades Transversais

### US-13 — Sincronização entre abas

> Como usuário, quero que as tarefas criadas ou modificadas em qualquer aba reflitam automaticamente na outra, para que os dados estejam sempre consistentes.

**Critérios de aceite:**
- Tarefa criada na Todo List aparece na coluna "A Fazer" do Kanban
- Tarefa criada no Kanban aparece na Todo List
- Status atualizado no Kanban reflete na Todo List e vice-versa
- Não há duplicatas ou inconsistências entre as abas

---

### US-14 — Persistência local de dados

> Como usuário, quero que minhas tarefas sejam salvas automaticamente, para que eu não perca dados ao fechar o aplicativo.

**Critérios de aceite:**
- Dados salvos automaticamente a cada alteração (sem botão "Salvar")
- Dados persistem após fechar e reabrir o aplicativo
- Armazenamento local em arquivo (SQLite ou JSON)
- Caminho do arquivo de dados visível nas configurações

---

### US-15 — Exportar dados

> Como usuário, quero exportar minhas tarefas para um arquivo, para que eu possa fazer backup ou migrar os dados.

**Critérios de aceite:**
- Exportação disponível no menu principal
- Formatos suportados: JSON e CSV
- Arquivo exportado contém todos os campos de todas as tarefas
- Nome do arquivo sugerido inclui data de exportação

---

### US-16 — Preferências de interface

> Como usuário, quero configurar preferências básicas da interface, para que eu adapte o aplicativo ao meu gosto.

**Critérios de aceite:**
- Alternância entre tema claro e escuro
- Preferência persistida entre sessões
- Configurações acessíveis via menu ou ícone dedicado

---

## Requisitos Não Funcionais

| # | Requisito | Detalhamento |
|---|-----------|--------------|
| RNF-01 | **Performance** | Interface responsiva; operações de CRUD em < 200ms |
| RNF-02 | **Armazenamento** | Dados locais; máx. 10.000 tarefas sem degradação perceptível |
| RNF-03 | **Portabilidade** | Executável único (ou instalador simples); sem dependências externas visíveis ao usuário |
| RNF-04 | **Compatibilidade** | Windows 10+, macOS 12+ e Linux (Ubuntu 22.04+) |
| RNF-05 | **Acessibilidade** | Navegação completa por teclado; suporte a zoom da interface |
| RNF-06 | **Resiliência** | Backup automático do arquivo de dados antes de operações destrutivas |

---

## Fora de Escopo (v1.0)

- Autenticação e múltiplos usuários
- Sincronização com nuvem ou entre dispositivos
- Colaboração em tempo real
- Notificações e lembretes por push/e-mail
- Subtarefas e hierarquia de tarefas
- Etiquetas/tags
- Recorrência de tarefas
- Integração com calendários externos (Google Calendar, Outlook)
- Relatórios e dashboards de produtividade
- Importação de dados de outros apps (Trello, Notion, etc.)

---

## Priorização Sugerida (MoSCoW)

### Must Have (MVP)
- US-01, US-02, US-03, US-04, US-05 — CRUD básico da Todo List
- US-08, US-09 — Visualização e movimentação no Kanban
- US-13 — Sincronização entre abas
- US-14 — Persistência local

### Should Have
- US-06, US-07 — Filtros e busca
- US-10 — Criar card no Kanban
- US-11 — Gerenciar colunas
- US-12 — Detalhes do card

### Could Have
- US-15 — Exportar dados
- US-16 — Preferências de interface (tema escuro)

### Won't Have (v1.0)
- Todos os itens listados em "Fora de Escopo"
