# Plan — Criar card diretamente no Kanban

> **Spec:** [spec.md](spec.md)
> **Fase:** `/plan` → entrada para `/tasks`
> **Autor:** agente `tl-python`
> **Data:** 2026-04-24
> **Status:** Pronto para `/tasks`

---

## Regras desta fase

- **Constitution é lei.** Validado: a feature não envolve rede, não altera stack, respeita layering `models → database → services → ui`, não introduz SQL novo (reusa `TaskRepository.create` via `TaskService.create_task`). Nenhum princípio 🔒 é violado.
- Sem código — apenas contratos e decisões.

---

## Resumo técnico

Adiciona, no rodapé de cada `KanbanColumnWidget`, um controle "+ Adicionar card" que alterna (toggle) para um **novo widget enxuto** `InlineTaskForm` (título + prioridade + data) embutido na coluna. A confirmação delega a `TaskService.create_task`, que já aceita `coluna_kanban` e calcula posição no final — portanto **nenhuma mudança em `services/` nem em `database/`** é necessária. A sincronização com Todo List/Kanban (US-13) se dá pelo signal `task_created` já existente. O mapeamento coluna→status (`COLUNA_CONCLUIDO → CONCLUIDA`) é aplicado pelo próprio `KanbanColumnWidget` no momento de criar, replicando a regra de `move_to_column` para manter consistência com US-09.

## Camadas afetadas

| Camada | Muda? | Natureza da mudança |
|---|---|---|
| `utils/` | não | — |
| `models/` | não | `Task` já cobre todos os campos necessários |
| `database/` | não | `TaskRepository.create` já é suficiente |
| `services/` | sim (pequena) | Novo método `create_task_in_column(titulo, prioridade, data_vencimento, coluna)` que encapsula a regra coluna→status (DRY com `move_to_column`). Evita que a UI conheça a lógica de status |
| `ui/` | sim | Novo `InlineTaskForm` (widget, não diálogo); `KanbanColumnWidget` ganha rodapé com botão "+ Adicionar card" e slot para o form inline; `KanbanWidget._reload_board` preserva estado do form aberto (ver decisão abaixo) |

## Decisões técnicas

### D1 — Novo widget inline vs reutilizar `TaskForm`

- **Alternativas:**
  - A) Reutilizar `TaskForm` como `QDialog` modal abrindo a partir da coluna.
  - B) Reutilizar `TaskForm` convertendo-o em widget embutível com campos ocultáveis.
  - C) **Criar `InlineTaskForm` novo**, enxuto, dedicado ao fluxo Kanban.
- **Escolha:** C.
- **Por quê:** a spec exige formulário **inline** dentro da coluna (não modal), sem descrição, com semântica de "criação em rajada" (permanece aberto após confirmar), múltiplas instâncias simultâneas (uma por coluna) e comportamento específico de `Enter`/`Esc`. Forçar `TaskForm` (hoje `QDialog`) a atender isso acoplaria duas features com requisitos divergentes e aumentaria débito. Reversibilidade alta.
- **Trade-off aceito:** pequena duplicação de UI (campo título + combo prioridade + date edit). Mitigado por manter validação de título centralizada em `Task.__post_init__`.

### D2 — Regra coluna→status: onde mora?

- **Alternativas:**
  - A) UI (`KanbanColumnWidget`) decide status conforme nome da coluna.
  - B) **`TaskService.create_task_in_column` encapsula a regra** (espelho de `move_to_column`).
- **Escolha:** B.
- **Por quê:** manter a regra no service preserva o padrão MVP (UI não conhece enums de status) e deixa US-09 e US-10 compartilhando exatamente a mesma lógica. Evita divergência futura. Reversibilidade alta.

### D3 — Posicionamento do botão "+ Adicionar card"

- **Escolha:** rodapé fixo da coluna (**fora** do `QScrollArea` de cards), abaixo do `_scroll_area`. Quando o `InlineTaskForm` é aberto, o botão é ocultado e o form ocupa seu espaço; ao fechar, o botão reaparece.
- **Por quê:** rodapé fixo mantém o controle sempre visível mesmo em colunas com muitos cards. Evita que o usuário precise rolar até o fim.

### D4 — Preservação do form aberto durante reload do quadro

- **Problema:** `KanbanWidget._reload_board` hoje destrói e recria todos os `KanbanColumnWidget` a cada signal (`task_created`, `task_updated`, `task_deleted`). Isso **descartaria** o rascunho do form aberto — violando US-10.3 ("clicar fora não fecha; formulário só fecha por Adicionar/Cancelar/Esc").
- **Alternativas:**
  - A) Refatorar `_reload_board` para reload incremental (só cards, preservando colunas).
  - B) Reload completo + snapshot/restauração do estado do form (por coluna) antes/depois.
  - C) Reload incremental **apenas de cards** dentro de cada coluna, preservando a coluna e o form.
- **Escolha:** C.
- **Por quê:** menor blast radius; alinha-se com a natureza do signal (criar/editar/deletar um card não muda a lista de colunas). Abre caminho para performance melhor em quadros grandes. Reversibilidade alta.
- **Impacto:** `KanbanColumnWidget` ganha `set_tasks(tasks: list[Task])` que faz diff local (clear + repopula cards, sem mexer no form inline). `KanbanWidget._reload_board` passa a chamar esse método em cada coluna existente quando possível; recria colunas apenas se a lista de colunas mudou (pensando em US-11).

### D5 — Validação de título >200 chars e data inválida

- **Escolha:** `QLineEdit.setMaxLength(TITULO_MAX_LEN)` + `QDateEdit` (que já impede datas inválidas). Título vazio/só-espaços: destaque de erro via stylesheet e label de mensagem inline. Erro de persistência (captura de exceção ao chamar service) idem.

### D6 — Acessibilidade e teclado

- `Enter` no `QLineEdit` de título → `returnPressed` → confirma.
- `Esc` no widget form → instala `eventFilter` ou sobrescreve `keyPressEvent` do `InlineTaskForm`; atalho fica **local** ao widget (não global), evitando interferir em outros atalhos do Kanban.
- Ordem de Tab: título → prioridade → data → Adicionar → Cancelar (via ordem de adição ao layout + `setTabOrder` explícito).
- Foco inicial no título via `QTimer.singleShot(0, self._edit_titulo.setFocus)` ao abrir.

## Contratos

```python
# services/task_service.py (novo método)
class TaskService(QObject):
    def create_task_in_column(
        self,
        titulo: str,
        coluna: str,
        prioridade: Prioridade = Prioridade.MEDIA,
        data_vencimento: date | None = None,
    ) -> Task:
        """Cria tarefa já associada à coluna informada, aplicando a regra
        coluna→status (COLUNA_CONCLUIDO → CONCLUIDA; demais → PENDENTE).
        Emite task_created. Card sempre entra no final da coluna."""
```

```python
# ui/kanban/inline_task_form.py (novo)
class InlineTaskForm(QWidget):
    submitted = pyqtSignal(dict)   # {"titulo": str, "prioridade": Prioridade, "data_vencimento": date|None}
    cancelled = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None: ...
    def reset(self) -> None: ...                 # limpa campos e mantém foco no título
    def show_error(self, mensagem: str) -> None: ...
    def focus_title(self) -> None: ...
```

```python
# ui/kanban/kanban_column_widget.py (mudanças)
class KanbanColumnWidget(QFrame):
    add_card_requested = pyqtSignal(str)                 # column_name
    create_card_submitted = pyqtSignal(str, dict)        # column_name, dados do form

    def set_tasks(self, tasks: list[Task]) -> None: ...  # reload incremental só de cards
    def open_inline_form(self) -> None: ...
    def close_inline_form(self) -> None: ...
    def has_inline_form_open(self) -> bool: ...
```

```python
# ui/kanban/kanban_widget.py (mudanças)
class KanbanWidget(QWidget):
    def _on_create_card_submitted(self, column_name: str, dados: dict) -> None:
        """Chama task_service.create_task_in_column; em caso de erro, chama
        col_widget._inline_form.show_error(...) e mantém form aberto."""

    def _reload_board(self) -> None:
        """Preserva colunas e forms inline abertos; apenas atualiza cards."""
```

## Migração de dados / schema

Nenhuma.

## ADRs novos necessários

Nenhum. Justificativa:
- Não altera stack, padrão de persistência nem layering.
- Não introduz nova dependência.
- Reutiliza padrões já firmados (signals Qt, Repository, layering MVP, regra coluna→status de US-09).
- Decisões tomadas são reversíveis e locais à feature — ficam aqui, não carecem de ADR global.

## Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Reload completo destruir rascunho do form inline | alta sem ação | alto (viola US-10.3) | Refatorar `_reload_board` para reload incremental (D4); TC dedicado |
| Múltiplos forms abertos gerarem vazamento de signals ao recriar coluna | baixa | médio | `set_tasks` em vez de recriar coluna; `deleteLater` com rigor; TC com N forms abertos |
| Atalho `Esc` fechar janela inteira em vez do form | média | médio | `keyPressEvent` local + `event.accept()`; não instalar como shortcut global |
| Divergência entre regra coluna→status de `create_task_in_column` e `move_to_column` | baixa | alto | Service centraliza regra; TC comparando caminhos (criar em "Concluído" vs mover para "Concluído") |
| Performance em quadros com 10k tarefas ao reload incremental | baixa | médio | Reload por coluna afetada (usar `task_created.coluna_kanban` para atualizar só uma); mensurar em TC slow |
| Usuário digitar >200 chars via paste | média | baixo | `setMaxLength(TITULO_MAX_LEN)` trunca naturalmente |

## Plano de testes

(Elaborado em par com `qa`; detalhamento final e numeração de TCs no `tasks.md`.)

- [ ] TC — Abrir form inline pelo botão "+ Adicionar card" em uma coluna (UI)
- [ ] TC — Foco inicial vai para campo título ao abrir (UI)
- [ ] TC — Confirmar com título válido cria card no final da coluna correta (integração UI+Service+DB)
- [ ] TC — Após confirmar, form permanece aberto e limpo, com foco no título (UI)
- [ ] TC — Cancelar fecha form e descarta rascunho; botão "+ Adicionar card" reaparece (UI)
- [ ] TC — `Enter` no título confirma; `Esc` cancela (UI)
- [ ] TC — Ordem de Tab: título → prioridade → data → Adicionar → Cancelar (UI)
- [ ] TC — Título vazio/só-espaços: exibe erro inline, não cria card, form permanece (UI)
- [ ] TC — Título com >200 caracteres é impedido (UI)
- [ ] TC — Data inválida impede confirmação (UI)
- [ ] TC — Criar em "Concluído" nasce com `status=CONCLUIDA` (integração Service)
- [ ] TC — Criar em "A Fazer"/"Em Andamento" nasce com `status=PENDENTE` (integração Service)
- [ ] TC — Contador da coluna incrementa imediatamente após criação (UI)
- [ ] TC — Card criado no Kanban aparece na Todo List (via signal `task_created`) (integração UI+Service)
- [ ] TC — Dois forms abertos simultaneamente em colunas diferentes não interferem (UI)
- [ ] TC — Clicar fora do form não o fecha (UI)
- [ ] TC — Criação em coluna A não fecha form aberto em coluna B (UI) — reload incremental preservando form
- [ ] TC — Falha de persistência mantém form aberto com dados e exibe erro (unit+UI com mock de service)
- [ ] TC — `TaskService.create_task_in_column` em "Concluído" dispara `task_created` com status correto (unit)
- [ ] TC — Benchmark: criação com 10k tarefas pré-existentes ≤ 200ms (slow, marcado `pytest.mark.slow`)

## Dependências

- **Tasks bloqueantes no backlog global:** nenhuma conhecida. Decisão D4 (reload incremental) pode ser extraída para TASK própria caso se revele mais extensa que o esperado durante `/tasks`.
- **Features:** depende de US-08 (colunas visíveis), US-13 (signals de sincronização), US-01 (modelo de campos). Interage com US-09 (mesma regra coluna→status).

## Ligações

- **Constitution:** [../../constitution.md](../../constitution.md)
- **ADRs relevantes:** [ADR-001](../../adr-001-stack.md) (padrão MVP com Qt signals)
- **Backlog global:** [docs/tasks.md](../../tasks.md)
- **Plano de testes:** [docs/plano-testes.md](../../plano-testes.md)
