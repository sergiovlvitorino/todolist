# Spec — Política de Migrations e Constraints de Integridade do Schema

> **ID:** Feature técnica/infra (sem US própria) — origem em DT-040 + DT-013 (ver [docs/tasks.md](../../tasks.md))
> **Diretório:** `docs/specs/011-migrations-policy-schema-constraints/`
> **Fase:** `/specify` → entrada para `/plan`
> **Autor:** agente `po`
> **Data:** 2026-04-25

---

## Regras desta fase

- **Proibido mencionar tecnologia** (PyQt, SQLite, signals, tabelas, SQL, nomes de classes/arquivos). Se a spec inclui tecnologia, ela é plano, não spec.
- **Proibido prescrever solução**. Descreva o problema do usuário e o resultado observável.
- Toda ambiguidade deve virar pergunta explícita na seção **Questões em aberto**, não palpite.

---

## Contexto

Hoje o armazenamento local aceita silenciosamente registros incompletos ou semanticamente inválidos: tarefas sem título, com prioridade ou status desconhecidos, sem data de criação, ou apontando para uma coluna do quadro que não existe. A validação ocorre apenas quando uma tarefa é criada pelos fluxos da aplicação; qualquer manipulação fora desses fluxos (importação futura, ferramenta auxiliar, regressão de código) pode introduzir estados que a interface não consegue exibir corretamente — tarefas "órfãs", listas desordenadas ou erros opacos ao abrir o aplicativo.

Além disso, o aplicativo não possui hoje uma política definida para evoluir o formato dos dados armazenados. Toda alteração de regra de integridade aplicada de agora em diante precisa preservar os dados que o usuário já acumulou em uso real, sem exigir que ele saiba migrar manualmente.

Esta feature define o comportamento esperado do sistema quanto a (a) integridade dos dados que entram no armazenamento e (b) evolução do formato do armazenamento entre versões do aplicativo. Cobre as dívidas catalogadas DT-040 (constraints de integridade) e DT-013 (associação de tarefa à coluna por identidade estável em vez de nome).

## User Stories

### Feature.1 — Rejeição de dados inconsistentes na entrada

> Como usuário, quero que o aplicativo recuse silenciosamente qualquer tentativa de salvar uma tarefa em estado inválido, para que eu nunca encontre cards "quebrados", invisíveis ou duplicados ao reabrir a aplicação.

**Critérios de aceite:**
- [ ] Tentativa de salvar uma tarefa **sem título** é rejeitada com mensagem clara, independentemente do ponto de entrada (formulário de nova tarefa, edição, criação direta no quadro, ou qualquer rota futura).
- [ ] Tentativa de salvar uma tarefa com **prioridade fora do conjunto permitido** ("Baixa", "Média", "Alta") é rejeitada com mensagem clara.
- [ ] Tentativa de salvar uma tarefa com **status fora do conjunto permitido** ("Pendente", "Concluída") é rejeitada com mensagem clara.
- [ ] Tentativa de salvar uma tarefa **sem associação a uma coluna existente** do quadro é rejeitada com mensagem clara.
- [ ] Tentativa de salvar uma tarefa com **posição negativa** no quadro é rejeitada com mensagem clara.
- [ ] Tentativa de salvar uma tarefa **sem data de criação ou de atualização** é rejeitada.
- [ ] Tentativa de salvar uma coluna do quadro **sem nome** ou **sem data de criação** é rejeitada.
- [ ] As mesmas regras valem se um registro for inserido por qualquer outro caminho que não a interface — o armazenamento não aceita o estado inválido.

**Cenários negativos / erros:**
- Quando o usuário tenta salvar uma tarefa sem título via formulário, o sistema exibe a mensagem antes de fechar o formulário e mantém os campos preenchidos para correção.
- Quando uma tentativa de inserção inválida ocorre por qualquer caminho não interativo, o erro é registrado de forma rastreável (sem expor dados pessoais do usuário) e a operação não deixa estado parcial.

---

### Feature.2 — Identidade estável da coluna do quadro

> Como usuário, quero poder renomear uma coluna do quadro sem perder a associação com as tarefas que estão nela, para que minha organização sobreviva a ajustes de vocabulário.

**Critérios de aceite:**
- [ ] Após renomear uma coluna, **todas as tarefas que estavam nela continuam aparecendo nela**, sem qualquer ação adicional do usuário.
- [ ] Após renomear uma coluna, a Todo List continua exibindo as tarefas associadas corretamente classificadas.
- [ ] Ao excluir uma coluna que contém tarefas, o sistema impede a exclusão e informa o usuário, **ou** segue o comportamento já definido em US-09 (a regra existente prevalece).
- [ ] Não é possível associar uma tarefa a uma coluna que não exista — em nenhum fluxo, em nenhum momento.

**Cenários negativos / erros:**
- Se, por algum estado pré-existente no armazenamento do usuário, houver tarefas apontando para colunas que já não existem, o sistema deve, na primeira execução após a atualização, sanar a inconsistência de forma documentada e previsível (ver Feature.3 — migração de dados existentes).

---

### Feature.3 — Atualização do formato de dados sem perda

> Como usuário que já uso o aplicativo, quero atualizar para uma nova versão sem perder minhas tarefas e sem precisar entender de banco de dados, para que a evolução do produto seja transparente.

**Critérios de aceite:**
- [ ] Ao iniciar uma versão do aplicativo cujo formato de dados evoluiu em relação à versão anterior, a atualização do formato é **automática**, **silenciosa quando bem-sucedida** e **executada antes da interface ficar disponível**.
- [ ] Antes de qualquer alteração no formato de dados, o sistema cria uma **cópia de segurança** do arquivo de dados atual em local previsível, com nome que inclua a data/hora e a versão de origem. A cópia permanece após a atualização para permitir recuperação manual. O sistema mantém **as 3 cópias mais recentes** (rotação simples); cópias mais antigas são descartadas automaticamente. Política de retenção configurável fica fora de escopo nesta entrega.
- [ ] Se a atualização for bem-sucedida, o usuário **não percebe nada além de uma indicação de progresso curta** quando a duração ultrapassar **1,5 segundo**. Abaixo desse limiar, a transição é silenciosa (splash sem indicador). O caminho do arquivo de quarentena (quando existir registros saneados) é exibido no splash de migração.
- [ ] Se a atualização **falhar**, o aplicativo exibe uma mensagem clara explicando: (a) que a atualização não pôde ser concluída, (b) onde está a cópia de segurança, (c) como obter ajuda. O aplicativo **não** abre em estado parcial.
- [ ] Após uma atualização bem-sucedida, **nenhuma tarefa criada na versão anterior é perdida** e todas continuam acessíveis com os mesmos atributos visíveis ao usuário (título, descrição, prioridade, vencimento, status, coluna).
- [ ] O sistema sabe identificar a versão do formato de dados em uso e **recusa-se a abrir** um arquivo de dados de versão **mais nova** do que a aplicação suporta, preservando o arquivo intacto.
- [ ] O sistema é capaz de aplicar **múltiplas atualizações de formato em sequência** quando o usuário pula versões (ex.: instala a versão 5 sem ter passado pela 3 ou 4).

**Cenários negativos / erros:**
- Quando o usuário inicia o aplicativo pela **primeira vez** (não há arquivo de dados anterior), nenhuma migração ocorre — o aplicativo simplesmente cria o armazenamento já no formato atual e abre normalmente.
- Quando dados pré-existentes contêm valores que **não satisfazem** as novas regras de integridade, a atualização aplica a estratégia de saneamento definida abaixo (item "Estratégias de saneamento de dados legados"). Em todos os casos, o evento é registrado em log de auditoria e o registro original é preservado em arquivo lateral de quarentena.
- Quando a atualização é interrompida por queda de energia ou fechamento forçado do aplicativo, ao reabrir o sistema detecta o estado intermediário e (a) retoma de onde parou ou (b) restaura a partir da cópia de segurança e tenta novamente. O usuário não fica com dados parcialmente migrados.

**Estratégias de saneamento de dados legados (decisões):**
- **Prioridade ausente ou desconhecida:** atribuir o padrão **"Média"** (consistente com US-01). Sem quarentena.
- **Status ausente ou desconhecido:** atribuir o padrão **"Pendente"** (estado seguro; o usuário pode marcar como concluída depois).
- **Tarefa apontando para coluna inexistente:** **realocar para a coluna padrão "A Fazer"** (sempre presente). Não bloqueia a migração; o evento é registrado no log de auditoria e o registro original é copiado para o arquivo lateral de quarentena.
- **`criado_em`/`atualizado_em` ausentes:** atribuir o instante UTC do momento da migração (`datetime.utcnow()`), com observação no log: "data desconhecida (migrado em YYYY-MM-DD)".

---

### Feature.4 — Recuperação diante de armazenamento corrompido

> Como usuário, quero que o aplicativo não me deixe na mão se o arquivo de dados estiver corrompido, para que eu nunca perca acesso ao produto sem orientação.

**Critérios de aceite:**
- [ ] Ao iniciar e detectar que o arquivo de dados **não pode ser lido** (corrompido, truncado, formato irreconhecível), o aplicativo **não trava nem abre vazio silenciosamente**.
- [ ] O usuário recebe uma mensagem clara que: identifica o problema, indica o caminho do arquivo problemático, indica se existem cópias de segurança recentes (ver Feature.3) e oferece pelo menos uma ação de recuperação (ex.: iniciar com arquivo novo preservando o anterior em quarentena).
- [ ] Nenhum dado é descartado automaticamente sem confirmação do usuário ou sem ser preservado em quarentena.
- [ ] A quarentena nesta entrega é **apenas um arquivo lateral** em `~/.own-board-list/quarantine_YYYYMMDD.json`. O caminho é registrado no log e exibido no splash quando aplicável. **Não há UI de quarentena nesta versão** — interface gráfica de gestão de quarentena fica fora de escopo.

**Cenários negativos / erros:**
- Se o arquivo de dados está ausente mas existe uma cópia de segurança recente, o aplicativo informa o usuário e oferece restaurar a partir dela.

---

## Requisitos não-funcionais específicos

- **Atomicidade:** uma atualização de formato de dados é tudo-ou-nada do ponto de vista do usuário. O aplicativo nunca abre em estado intermediário.
- **Defesa em profundidade:** as regras de integridade descritas em Feature.1 valem **tanto** na camada que recebe a entrada do usuário **quanto** na camada de armazenamento. Falha em qualquer uma delas é defeito.
- **Privacidade:** cópias de segurança ficam no diretório local do aplicativo, nunca saem da máquina, e seguem a política geral de privacidade do produto (ver constitution).
- **Observabilidade mínima:** atualizações de formato e falhas de integridade são registradas com versão de origem, versão de destino e resultado, sem incluir conteúdo de tarefas do usuário.

## Fora de escopo

- **Migração reversa** (downgrade) entre versões — explicitamente não suportada nesta entrega.
- **Exportação/importação** de dados em formatos externos (CSV, JSON, etc.) — pertence a outras US (ex.: US-15 se aplicável).
- **Edição manual de cópias de segurança** pelo usuário dentro do aplicativo — fora de escopo; o usuário acessa via sistema de arquivos.
- **Sincronização entre dispositivos** — princípio inviolável da constitution: aplicação 100% offline.
- **Ferramenta de inspeção/diagnóstico** do arquivo de dados embutida no aplicativo — fora de escopo.
- **Interface gráfica para gestão de quarentena** — nesta entrega a quarentena é apenas um arquivo lateral em `~/.own-board-list/quarantine_YYYYMMDD.json`. UI dedicada fica para feature futura.
- **Política de retenção configurável de backups** — esta entrega adota rotação fixa (3 últimas). Configuração pelo usuário fica fora de escopo.
- **Renomeação de coluna do quadro (Feature.2 ampliada)** — o suporte de identidade estável da coluna (FK por `id`) é coberto aqui (DT-013), mas o fluxo de UI de renomeação pertence a **US-11** e não compõe esta DT. Esta feature técnica trata exclusivamente de integridade do schema.

## Questões em aberto

> Resolvidas em 2026-04-25 (modo auto). Decisões incorporadas nos critérios de aceite e em "Fora de escopo".

- [x] **Prioridade ausente em legacy** → assumir padrão **"Média"** (consistente com US-01). Sem quarentena.
- [x] **Status ausente em legacy** → assumir padrão **"Pendente"** (estado seguro; usuário marca como concluída depois).
- [x] **Tarefa apontando para coluna inexistente** → **realocar para "A Fazer"** (sempre presente). Logar em arquivo de auditoria; não bloquear a migração.
- [x] **`criado_em`/`atualizado_em` ausentes** → usar `datetime.utcnow()` no momento da migração com observação no log "data desconhecida (migrado em YYYY-MM-DD)".
- [x] **Gerações de backup** → manter as **3 últimas** (rotação simples). Retenção configurável fica fora de escopo nesta entrega.
- [x] **Limiar de progresso** → exibir indicador de progresso apenas se a migração ultrapassar **1,5 segundo**. Abaixo, splash silencioso.
- [x] **Acesso à quarentena** → **apenas arquivo lateral** em `~/.own-board-list/quarantine_YYYYMMDD.json`. Sem UI v1 (fora de escopo). Caminho exibido no splash de migração e logado no console.
- [x] **Renomeação de coluna** → fora de escopo desta DT (cobre **US-11**). Esta DT trata apenas de integridade do schema.

## Ligações

- **Catálogo de DTs:** [docs/tasks.md §DT-013](../../tasks.md), [docs/tasks.md §DT-040](../../tasks.md)
- **Constitution:** [docs/constitution.md](../../constitution.md) — princípios de privacidade, layering e gates de qualidade
- **ADR de stack:** [docs/adr-001-stack.md](../../adr-001-stack.md)
- **Plano desta feature:** a ser criado em `/plan` (deve incluir ADR novo de política de versionamento de schema)
- **Testes relacionados:** novos TCs a serem adicionados em [docs/plano-testes.md](../../plano-testes.md) durante `/tasks`
