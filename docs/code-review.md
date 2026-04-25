# Code Review - Own Board List MVP

**Revisor:** Tech Lead Python Senior
**Data:** 2026-04-16
**Commit base:** MVP inicial
**Stack:** Python 3.11+, PyQt6, SQLite (stdlib), pytest, pytest-qt

---

## Sumario Executivo

### Notas por Categoria (0-10)

| Categoria | Nota | Comentario |
|---|---|---|
| Corretude | 8 | Logica geral correta, poucos bugs potenciais |
| Type hints | 7 | Bom uso geral, mas hacks com `object` nos eventos PyQt6 e `Any` em excesso |
| PEP 8 / Estilo | 9 | Codigo limpo, docstrings consistentes, imports bem organizados |
| Arquitetura | 8 | Boa separacao de camadas (model/repo/service/ui), signals bem usados |
| Seguranca | 9 | Queries parametrizadas em todo lugar, sem SQL injection |
| Testes | 7 | Boa cobertura da camada de dados e servico, mas zero testes de UI |
| Problemas criticos | 8 | Nenhum bug que impeca o app de funcionar, mas ha riscos |

**Nota geral: 7.7/10** -- MVP solido com boa arquitetura. Precisa de ajustes pontuais antes do release.

---

### Problemas Criticos (bloqueiam funcionalidade)

Nenhum problema critico identificado. O app deve funcionar corretamente no fluxo principal.

### Problemas Importantes (devem ser corrigidos antes do release)

1. **`datetime.now()` sem timezone** -- Todos os timestamps sao naive. Pode causar bugs sutis em fusos horarios diferentes ou ao serializar/deserializar.
2. **`update_task` com `setattr` aceita campos arbitrarios** -- Permite sobrescrever `id`, `criado_em` ou qualquer campo interno via kwargs.
3. **`toggle_status` calcula posicao errada** -- Conta as tarefas na coluna destino *antes* de mover, mas a propria tarefa pode ja estar contada se for re-toggle rapido.
4. **`_get_drop_position` logica de coordenadas complexa e fragil** -- O calculo de `container_y` mapeia coordenadas de forma convoluta e o valor nunca e usado.
5. **`reorder` no `ColumnRepository` nao e atomico** -- Multiplos UPDATEs seguidos de um commit; se falhar no meio, as posicoes ficam inconsistentes.
6. **Relacao task-coluna por nome (string) em vez de FK** -- `coluna_kanban` na tabela `tasks` e texto livre, nao e FK para `kanban_columns.id`. Renomear uma coluna quebra a associacao.
7. **Versao duplicada** -- `__version__` em `__init__.py` e `app.setApplicationVersion("0.1.0")` em `main.py` sao independentes do `pyproject.toml`.
8. **`assert` em codigo de producao** -- `todo_widget.py` usa `assert` para validacao de tipos nos dados do formulario (linhas 202-208). Assertions sao removidas com `python -O`.

### Melhorias (nice-to-have)

1. Extrair `_COR_PRIORIDADE` para modulo compartilhado (duplicado em `task_list_item.py` e `kanban_card_widget.py`).
2. Adicionar `__context_manager__` (`__enter__`/`__exit__`) ao `DatabaseConnection`.
3. Usar `date.today()` do `datetime` modulo com injection para facilitar testes.
4. Adicionar indice na coluna `coluna_kanban` da tabela `tasks` para performance.
5. Testes de UI com `pytest-qt` para os widgets principais.
6. Adicionar logging estruturado.
7. Implementar tratamento de erros na UI (try/except com mensagens ao usuario).

---

## Review por Arquivo

### `pyproject.toml`

**Pontos positivos:**
- Configuracao limpa com hatchling.
- mypy strict habilitado.
- Ruff bem configurado com regras relevantes (E, F, I, UP, B).
- Separacao correta entre dependencias de prod e dev.

**Problemas encontrados:**

Linha 5 -- Falta pin maximo de PyQt6:
```toml
dependencies = ["PyQt6>=6.6.0"]
```
PyQt6 7.x (quando sair) pode introduzir breaking changes. Recomendo `"PyQt6>=6.6.0,<7"`.

Linha 27 -- `testpaths` sem configuracao de `qt_api`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--tb=short"
```
Falta `qt_api = "pyqt6"` para garantir que pytest-qt use o backend correto.

---

### `src/own_board_list/main.py`

**Pontos positivos:**
- Entry point simples e limpo.
- `if __name__ == "__main__"` presente.

**Problemas encontrados:**

Linha 16 -- Versao hardcoded:
```python
app.setApplicationVersion("0.1.0")
```
Deveria usar `__version__` do pacote:
```python
from own_board_list import __version__
app.setApplicationVersion(__version__)
```

---

### `src/own_board_list/models/task.py`

**Pontos positivos:**
- Uso excelente de `StrEnum` para Prioridade e StatusTarefa.
- Validacao no `__post_init__` com mensagens claras.
- Serializacao `to_dict`/`from_dict` bem implementada.
- Dataclass imutabilidade conceitual bem definida.

**Problemas encontrados:**

Linhas 39-40 -- `datetime.now()` sem timezone:
```python
criado_em: datetime = field(default_factory=datetime.now)
atualizado_em: datetime = field(default_factory=datetime.now)
```
Recomendacao: usar `datetime.now(tz=timezone.utc)` ou pelo menos `datetime.now(tz=ZoneInfo("America/Sao_Paulo"))` para consistencia. Timestamps naive sao propensos a bugs.

Linha 44 -- Validacao nao faz `strip()` no titulo armazenado:
```python
if not self.titulo or not self.titulo.strip():
    raise ValueError("O titulo da tarefa nao pode ser vazio.")
```
O titulo `"   texto   "` passa na validacao mas e armazenado com espacos. Considere fazer `self.titulo = self.titulo.strip()` apos a validacao.

**Sugestao de melhoria:** `from_dict` confia cegamente nos dados. Se `data["criado_em"]` estiver ausente, lanca `KeyError` sem mensagem util. Considere validacao defensiva.

---

### `src/own_board_list/models/kanban_column.py`

**Pontos positivos:**
- Modelo simples e coerente.
- Mesma estrutura de validacao da Task.

**Problemas encontrados:**

Linha 18 -- Mesmo problema de `datetime.now()` sem timezone:
```python
criado_em: datetime = field(default_factory=datetime.now)
```

Sem problemas adicionais. Modelo bem implementado.

---

### `src/own_board_list/database/connection.py`

**Pontos positivos:**
- Lazy connection com `get_connection()`.
- `PRAGMA foreign_keys = ON` e `PRAGMA journal_mode = WAL` configurados.
- `row_factory = sqlite3.Row` habilitado.
- Path criado automaticamente com `mkdir(parents=True, exist_ok=True)`.

**Problemas encontrados:**

Linha 29 -- `check_same_thread=False` e perigoso:
```python
self._connection = sqlite3.connect(
    str(self._db_path),
    check_same_thread=False,
)
```
SQLite nao e thread-safe por padrao. Se o app usar threads (ex: QThread para operacoes longas), isso pode causar corrupcao de dados. Para um MVP single-thread e aceitavel, mas deve ser documentado como limitacao.

**Sugestao:** Implementar context manager:
```python
def __enter__(self) -> DatabaseConnection:
    return self

def __exit__(self, *args: object) -> None:
    self.close()
```

---

### `src/own_board_list/database/migrations.py`

**Pontos positivos:**
- Schema simples e funcional.
- `CREATE TABLE IF NOT EXISTS` para idempotencia.
- Colunas padrao inseridas condicionalmente.

**Problemas encontrados:**

Linhas 26-37 -- Tabela `tasks` sem FK para `kanban_columns`:
```sql
CREATE TABLE IF NOT EXISTS tasks (
    ...
    coluna_kanban TEXT,
    ...
)
```
O campo `coluna_kanban` armazena o *nome* da coluna, nao o ID. Isso significa que renomear uma coluna no `kanban_columns` nao atualiza as tasks, quebrando a associacao. Deveria ser:
```sql
coluna_kanban_id TEXT REFERENCES kanban_columns(id)
```
**Impacto:** Problema de design que afeta integridade referencial. Em um MVP pode ser aceitavel, mas deve ser corrigido antes de adicionar funcionalidade de renomear colunas.

Linha 46 -- `datetime.now().isoformat()` sem timezone (mesmo problema recorrente).

**Sugestao:** Adicionar sistema de versionamento de schema (ex: tabela `schema_version`) para facilitar futuras migracoes.

---

### `src/own_board_list/database/task_repository.py`

**Pontos positivos:**
- Todas as queries usam parametros `?` (sem SQL injection).
- Metodo `_row_to_task` centraliza a conversao.
- CRUD completo e bem estruturado.
- Metodo `search` com LIKE parametrizado.

**Problemas encontrados:**

Linha 17 -- `row_factory` setado no construtor sobrescreve configuracao:
```python
def __init__(self, conn: sqlite3.Connection) -> None:
    self._conn = conn
    self._conn.row_factory = sqlite3.Row
```
O repositorio modifica o estado da conexao compartilhada. Se outro codigo mudar o `row_factory`, os repositorios quebram. Seria melhor usar cursores com `row_factory` local, mas para MVP e aceitavel.

Linha 82 -- `update` modifica o objeto recebido (side effect):
```python
def update(self, task: Task) -> Task:
    task.atualizado_em = datetime.now()
```
O repositorio modifica diretamente o dominio. Isso deveria ser responsabilidade do servico ou do proprio modelo. Mistura responsabilidades.

Linhas 25-26 -- Linha longa (ultrapassa 88 chars configurados no ruff):
```python
prioridade=Prioridade(row["prioridade"]) if row["prioridade"] else Prioridade.MEDIA,
status=StatusTarefa(row["status"]) if row["status"] else StatusTarefa.PENDENTE,
```

Linhas 127-133 -- `update_position` nao atualiza `atualizado_em`:
```python
def update_position(self, task_id: str, coluna: str, posicao: int) -> None:
    self._conn.execute(
        "UPDATE tasks SET coluna_kanban = ?, posicao_kanban = ? WHERE id = ?",
        (coluna, posicao, task_id),
    )
```
Move a tarefa no Kanban sem registrar quando foi movida. Inconsistente com `update()` que renova o timestamp. Note que `update_position` nao parece ser usado atualmente (o servico usa `update` via `move_to_column`), mas e uma API publica inconsistente.

---

### `src/own_board_list/database/column_repository.py`

**Pontos positivos:**
- Queries parametrizadas.
- `has_tasks` faz join logico correto (busca nome da coluna, depois conta tasks).
- `reorder` funcional.

**Problemas encontrados:**

Linha 17 -- Mesmo problema de `row_factory` no construtor (duplicado com TaskRepository).

Linhas 66-73 -- `reorder` nao e atomico:
```python
def reorder(self, column_ids: list[str]) -> None:
    for posicao, column_id in enumerate(column_ids):
        self._conn.execute(
            "UPDATE kanban_columns SET posicao = ? WHERE id = ?",
            (posicao, column_id),
        )
    self._conn.commit()
```
Se o app crashar entre os UPDATEs e o commit, as posicoes ficam inconsistentes. Deveria usar transacao explicita:
```python
def reorder(self, column_ids: list[str]) -> None:
    cursor = self._conn.cursor()
    try:
        for posicao, column_id in enumerate(column_ids):
            cursor.execute(
                "UPDATE kanban_columns SET posicao = ? WHERE id = ?",
                (posicao, column_id),
            )
        self._conn.commit()
    except Exception:
        self._conn.rollback()
        raise
```
Nota: o SQLite com WAL mode tem auto-rollback em caso de crash, entao o risco real e baixo, mas a pratica correta e usar transacoes explicitas.

Linhas 76-90 -- `has_tasks` faz lookup por nome em vez de ID:
```python
def has_tasks(self, column_id: str) -> bool:
    cursor = self._conn.execute(
        "SELECT nome FROM kanban_columns WHERE id = ?", (column_id,)
    )
    row = cursor.fetchone()
    if row is None:
        return False
    nome_coluna: str = row["nome"]
    cursor2 = self._conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE coluna_kanban = ?", (nome_coluna,)
    )
```
Consequencia direta da falta de FK. Duas queries onde uma bastaria.

---

### `src/own_board_list/services/task_service.py`

**Pontos positivos:**
- Boa orquestracao entre repositorios e signals Qt.
- Logica de negocio centralizada (toggle_status, move_to_column).
- Sincronizacao automatica status/coluna kanban.
- Signals bem definidos para desacoplamento UI.

**Problemas encontrados:**

Linhas 64-74 -- `update_task` com `setattr` irrestrito:
```python
def update_task(self, task_id: str, **kwargs: Any) -> Task:
    task = self._task_repo.get_by_id(task_id)
    if task is None:
        raise ValueError(f"Tarefa com ID '{task_id}' nao encontrada.")

    for key, value in kwargs.items():
        if hasattr(task, key):
            setattr(task, key, value)
        else:
            raise ValueError(f"Campo invalido: '{key}'")
```
**Problema de seguranca logica:** Permite sobrescrever `id`, `criado_em`, `atualizado_em`, `status` via kwargs sem validacao. Um chamador pode fazer `update_task(id, id="outro-id")` e corromper dados.

**Sugestao de correcao:**
```python
_CAMPOS_EDITAVEIS = frozenset({
    "titulo", "descricao", "prioridade", "data_vencimento",
    "coluna_kanban", "posicao_kanban",
})

def update_task(self, task_id: str, **kwargs: Any) -> Task:
    campos_invalidos = set(kwargs) - self._CAMPOS_EDITAVEIS
    if campos_invalidos:
        raise ValueError(f"Campos nao editaveis: {campos_invalidos}")
    ...
```

Linhas 23-26 -- Signals tipados como `object` e `list`:
```python
task_created = pyqtSignal(object)   # Task
task_updated = pyqtSignal(object)   # Task
task_deleted = pyqtSignal(str)      # task_id
tasks_reloaded = pyqtSignal(list)   # list[Task]
```
`pyqtSignal(object)` perde type safety. Infelizmente e uma limitacao do PyQt6 -- nao suporta tipos genericos em signals. O comentario ajuda, mas considere criar wrappers tipados.

Linhas 97-106 -- `toggle_status` tem bug potencial de posicao:
```python
if task.status == StatusTarefa.PENDENTE:
    task.marcar_concluida()
    task.coluna_kanban = COLUNA_CONCLUIDO
    tasks_concluidas = self._task_repo.get_by_column(COLUNA_CONCLUIDO)
    task.posicao_kanban = len(tasks_concluidas)
```
Se a tarefa *ja esta* na coluna "Concluido" (caso teoricamente impossivel mas defensivamente relevante), `len(tasks_concluidas)` inclui a propria tarefa, resultando em posicao duplicada. O mesmo vale para o bloco `else`. Na pratica, como `update` e chamado depois e o banco e atualizado, funciona, mas a logica e fragil.

---

### `src/own_board_list/ui/main_window.py`

**Pontos positivos:**
- Inicializacao limpa e bem organizada.
- `closeEvent` fecha a conexao com o banco.
- Menu com atalho Ctrl+Q.

**Problemas encontrados:**

Linhas 73-76 -- `closeEvent` com type: ignore:
```python
def closeEvent(self, event: object) -> None:  # type: ignore[override]
    self._db_connection.close()
    super().closeEvent(event)  # type: ignore[arg-type]
```
Workaround necessario para PyQt6 stubs. Funciona, mas o `# type: ignore[override]` mascara erros reais. Alternativa mais segura:
```python
def closeEvent(self, event: QCloseEvent | None) -> None:  # type: ignore[override]
    self._db_connection.close()
    if event is not None:
        super().closeEvent(event)
```

Linha 65 -- `TodoWidget` e `KanbanWidget` nao sincronizam entre si diretamente:
A sincronizacao acontece via signals do `TaskService`, o que e correto. Porem, quando o usuario troca de aba, o widget nao faz reload explicito. Se a aba Kanban estiver aberta e o usuario criar uma tarefa na aba Todo, o signal `task_created` dispara e ambos fazem reload. Isso esta correto.

---

### `src/own_board_list/ui/dialogs/confirm_dialog.py`

**Pontos positivos:**
- Funcao simples e reutilizavel.
- Default no "Nao" (seguro).

Sem problemas encontrados. Implementacao limpa.

---

### `src/own_board_list/ui/todo/task_list_item.py`

**Pontos positivos:**
- Signals bem definidos para cada acao.
- Indicacao visual de prioridade e vencimento.
- Texto riscado para tarefas concluidas.

**Problemas encontrados:**

Linha 91 -- Slot `_on_status_toggled` ignora o parametro `checked`:
```python
def _on_status_toggled(self) -> None:
    self.status_toggled.emit(self._task.id)
```
O signal `QCheckBox.toggled` envia `bool`, mas o slot nao o recebe. Funciona porque o servico faz toggle baseado no estado atual do banco, nao no valor do checkbox. Mas semanticamente deveria receber o parametro para consistencia:
```python
def _on_status_toggled(self, checked: bool) -> None:
    self.status_toggled.emit(self._task.id)
```

---

### `src/own_board_list/ui/todo/task_form.py`

**Pontos positivos:**
- Formulario completo com validacao client-side.
- Contador de caracteres.
- Checkbox para habilitar/desabilitar data.
- Botao Salvar desabilitado quando titulo vazio.

**Problemas encontrados:**

Linhas 100-109 -- Multiplas chamadas a `button()` que podem retornar `None`:
```python
self._button_box.button(
    QDialogButtonBox.StandardButton.Save
).setText("Salvar")
self._button_box.button(
    QDialogButtonBox.StandardButton.Cancel
).setText("Cancelar")
self._button_box.button(
    QDialogButtonBox.StandardButton.Save
).setEnabled(False)
```
`button()` pode retornar `None` se o botao nao existir. Embora neste caso os botoes foram criados logo acima, mypy strict reclamaria. Deveria ter null check:
```python
save_btn = self._button_box.button(QDialogButtonBox.StandardButton.Save)
if save_btn is not None:
    save_btn.setText("Salvar")
    save_btn.setEnabled(False)
```

Linha 171 -- Signal emitido com `dict[str, object]` mas declarado como `pyqtSignal(dict)`:
```python
task_saved = pyqtSignal(dict)  # dados do formulario
```
Funciona em runtime, mas o tipo interno nao e verificavel.

---

### `src/own_board_list/ui/todo/todo_widget.py`

**Pontos positivos:**
- Separacao em grupos (Hoje, Proximas, Sem data, Concluidas) e excelente UX.
- Auto-reload via signals.
- Atalho Ctrl+N para nova tarefa.

**Problemas encontrados:**

Linhas 202-208 -- `assert` em codigo de producao:
```python
titulo = dados["titulo"]
assert isinstance(titulo, str)
descricao = dados.get("descricao", "")
assert isinstance(descricao, str)
prioridade = dados.get("prioridade", Prioridade.MEDIA)
assert isinstance(prioridade, Prioridade)
data_venc = dados.get("data_vencimento")
assert data_venc is None or isinstance(data_venc, date)
```
**Problema:** `assert` e removido com `python -O`. Se os tipos estiverem errados, o codigo continuaria sem erro visivel, potencialmente causando bugs silenciosos. Use `if not isinstance(...): raise TypeError(...)` ou valide no servico.

Linhas 172-177 -- Busca linear por tarefa para edicao:
```python
def _on_edit_task(self, task_id: str) -> None:
    task = self._task_service.get_all_tasks()
    task_to_edit: Task | None = None
    for t in task:
        if t.id == task_id:
            task_to_edit = t
            break
```
Carrega *todas* as tarefas para encontrar uma. O `TaskRepository` ja tem `get_by_id()`. Deveria expor esse metodo no servico:
```python
def _on_edit_task(self, task_id: str) -> None:
    task_to_edit = self._task_service.get_task_by_id(task_id)
```

---

### `src/own_board_list/ui/kanban/kanban_card_widget.py`

**Pontos positivos:**
- Drag and drop implementado corretamente com QMimeData.
- Limiar de arrasto (`_DRAG_THRESHOLD`) evita cliques acidentais.
- Estilo visual com hover.

**Problemas encontrados:**

Linhas 84-91 e 93-107 -- Import dentro de metodo:
```python
def mousePressEvent(self, event: object) -> None:
    from PyQt6.QtCore import QEvent
    from PyQt6.QtGui import QMouseEvent
```
Imports dentro de metodos sao desnecessarios aqui. `QMouseEvent` e `QDragEnterEvent` podem ser importados no topo do arquivo. O import de `QEvent` na linha 86 nem e usado.

Linhas 84, 93 -- `event: object` com `type: ignore[override]`:
```python
def mousePressEvent(self, event: object) -> None:  # type: ignore[override]
def mouseMoveEvent(self, event: object) -> None:  # type: ignore[override]
```
Workaround comum para stubs PyQt6. Funciona, mas uma alternativa e tipar diretamente:
```python
def mousePressEvent(self, event: QMouseEvent | None) -> None:  # type: ignore[override]
```

Linha 86 -- Import nao utilizado:
```python
from PyQt6.QtCore import QEvent
```
`QEvent` e importado mas nunca usado em `mousePressEvent`.

---

### `src/own_board_list/ui/kanban/kanban_column_widget.py`

**Pontos positivos:**
- Visual feedback no drag (highlight na coluna).
- Scroll area para cards.
- Contagem automatica de cards.

**Problemas encontrados:**

Linhas 118-130 -- `_get_drop_position` com logica morta:
```python
def _get_drop_position(self, y: int) -> int:
    container_y = self._cards_container.mapFromParent(
        self._scroll_area.mapFromParent(
            self.mapFromGlobal(self.mapToGlobal(self._scroll_area.pos()))
        )
    ).y()

    for i, card in enumerate(self._cards):
        card_center_y = card.y() + card.height() // 2
        if y < card_center_y:
            return i
    return len(self._cards)
```
A variavel `container_y` (linhas 119-124) e calculada mas **nunca usada**. O `y` recebido como parametro nao e ajustado com `container_y`. Isso significa que a posicao de drop pode estar incorreta dependendo do scroll. O calculo de coordenadas `mapFromGlobal(mapToGlobal(...))` e um round-trip que resulta na mesma coordenada.

**Sugestao de correcao:**
```python
def _get_drop_position(self, y: int) -> int:
    """Calcula a posicao de insercao baseada na coordenada Y do drop."""
    for i, card in enumerate(self._cards):
        card_center_y = card.y() + card.height() // 2
        if y < card_center_y:
            return i
    return len(self._cards)
```
Remover o calculo morto ou usa-lo para ajustar `y`.

Linhas 132-150 -- Mesmo padrao de `event: object` + imports internos dos outros widgets. Consistente mas verboso.

---

### `src/own_board_list/ui/kanban/kanban_widget.py`

**Pontos positivos:**
- Reload completo do board via signals.
- Separacao limpa entre widget e servico.

**Problemas encontrados:**

Linha 92 -- `addStretch()` acumula a cada reload:
```python
def _reload_board(self) -> None:
    self._clear_board()
    ...
    self._board_layout.addStretch()
```
`_clear_board()` remove os widgets de coluna, mas nao remove o stretch item adicionado previamente. A cada reload, um novo stretch e adicionado ao layout. Apos N reloads, ha N stretch items acumulados.

**Sugestao de correcao:**
```python
def _clear_board(self) -> None:
    """Remove todas as colunas e spacers do quadro."""
    for col_widget in self._column_widgets:
        self._board_layout.removeWidget(col_widget)
        col_widget.deleteLater()
    self._column_widgets.clear()
    # Remove todos os stretch items
    while self._board_layout.count() > 0:
        item = self._board_layout.takeAt(0)
        # Stretch items nao tem widget, entao so precisamos remove-los
```
Ou melhor, gerenciar o stretch como membro da classe.

---

### `tests/conftest.py`

**Pontos positivos:**
- Banco em memoria para testes (rapido e isolado).
- Fixtures bem estruturadas com Generator type hint.
- Schema inicializado automaticamente.

**Problemas encontrados:**

Linha 41 -- `qtbot: object` perde tipagem:
```python
def task_service(
    qtbot: object,
    task_repo: TaskRepository,
    column_repo: ColumnRepository,
) -> TaskService:
```
O tipo correto e `pytestqt.qtbot.QtBot`, mas como e uma dependencia de teste, `object` e aceitavel. O `qtbot` e necessario aqui apenas para inicializar o event loop do Qt.

---

### `tests/test_models/test_task.py`

**Pontos positivos:**
- Cobertura excelente do modelo: criacao, validacao, status, serializacao.
- Testes de borda (200 chars, titulo vazio, apenas espacos).
- Nomes descritivos em portugues.
- Organizacao por classes tematicas.

**Problemas encontrados:**

Nenhum problema significativo. Testes bem escritos e completos.

**Sugestao:** Adicionar teste para `from_dict` com dados incompletos/invalidos (campo ausente, tipo errado).

---

### `tests/test_database/test_task_repository.py`

**Pontos positivos:**
- Cobertura completa do CRUD.
- Testes de busca (por coluna, por texto, case-insensitive).
- Testes de update_position.

**Problemas encontrados:**

Nenhum problema significativo. Boa cobertura.

**Sugestao:** Adicionar teste de `search` com caracteres especiais SQL (ex: `%`, `_`, `'`).

---

### `tests/test_database/test_column_repository.py`

**Pontos positivos:**
- Cobertura de CRUD, reorder e has_tasks.
- Teste de integracao column_repo + task_repo para `has_tasks`.

Sem problemas encontrados.

---

### `tests/test_services/test_task_service.py`

**Pontos positivos:**
- Testes de signals Qt com `qtbot`.
- Testes de regras de negocio (toggle status muda coluna).
- Testes de move_to_column com sincronizacao de status.

**Problemas encontrados:**

Ausencia de testes para:
- `update_task` (nenhum teste)
- `search_tasks` (nenhum teste)
- `get_all_tasks` (nenhum teste)
- Cenarios de erro (task nao encontrada, campo invalido)

**Sugestao:** Adicionar pelo menos:
```python
class TestTaskServiceUpdateTask:
    def test_update_task_modifica_titulo(self, task_service):
        task = task_service.create_task("Original")
        result = task_service.update_task(task.id, titulo="Atualizado")
        assert result.titulo == "Atualizado"

    def test_update_task_id_inexistente_lanca_erro(self, task_service):
        with pytest.raises(ValueError, match="nao encontrada"):
            task_service.update_task("inexistente", titulo="X")

    def test_update_task_campo_invalido_lanca_erro(self, task_service):
        task = task_service.create_task("Tarefa")
        with pytest.raises(ValueError, match="Campo invalido"):
            task_service.update_task(task.id, campo_fake="X")
```

---

## Problemas de Arquitetura

### 1. Relacao task-coluna por nome (string) em vez de foreign key

**Arquivos afetados:** `migrations.py`, `task_repository.py`, `column_repository.py`, `task_service.py`

A tabela `tasks` usa `coluna_kanban TEXT` para referenciar a coluna, enquanto `kanban_columns` tem `id TEXT PRIMARY KEY`. Isso significa:
- Renomear uma coluna nao propaga para as tasks.
- `has_tasks` precisa fazer 2 queries (busca nome, depois conta).
- Nao ha integridade referencial no banco.

**Impacto:** Medio. Para o MVP sem funcionalidade de renomear colunas, funciona. Mas e uma divida tecnica que deve ser resolvida antes de adicionar essa funcionalidade.

### 2. Responsabilidade de atualizar timestamps

**Arquivos afetados:** `task.py`, `task_repository.py`, `task_service.py`

O `atualizado_em` e modificado em tres lugares:
- `Task.marcar_concluida()` e `Task.reabrir()` (modelo)
- `TaskRepository.update()` (repositorio)
- Via `setattr` em `TaskService.update_task()` (servico)

Isso cria inconsistencia: quem e o responsavel? O repositorio sempre sobrescreve no `update()`, mas o modelo tambem atualiza nos metodos de dominio. Recomendacao: definir que **apenas o repositorio** renova `atualizado_em`, ou **apenas o modelo** via um metodo dedicado.

### 3. Duplicacao de constantes de cor

**Arquivos afetados:** `task_list_item.py`, `kanban_card_widget.py`

O dicionario `_COR_PRIORIDADE` esta duplicado em dois arquivos:
```python
_COR_PRIORIDADE = {
    Prioridade.ALTA: "#d32f2f",
    Prioridade.MEDIA: "#f57c00",
    Prioridade.BAIXA: "#388e3c",
}
```
Deveria ser extraido para um modulo compartilhado (ex: `ui/constants.py` ou `ui/theme.py`).

### 4. Ausencia de tratamento de erros na UI

**Arquivos afetados:** Todos os widgets

Nenhum widget tem try/except ao redor das chamadas ao servico. Se o banco corromper ou o servico lancar uma excecao, o app crasha sem mensagem ao usuario. Recomendacao: adicionar tratamento de erros com `QMessageBox.critical()`.

### 5. Reload completo a cada mudanca

**Arquivos afetados:** `todo_widget.py`, `kanban_widget.py`

Ambos os widgets fazem reload completo (recriam todos os widgets filhos) a cada signal do servico. Para um MVP com poucas tarefas, isso e aceitavel. Para escalar, seria necessario update parcial (adicionar/remover/atualizar apenas o item afetado).

---

## Acoes Necessarias Antes do Merge

### Prioridade Alta (devem ser corrigidos)

1. **Remover `assert` do codigo de producao** em `todo_widget.py` (linhas 202-208). Substituir por validacao explicita com `isinstance` + `raise TypeError`.

2. **Restringir campos editaveis em `update_task`** no `task_service.py`. Adicionar whitelist de campos permitidos para evitar sobrescrita acidental de `id`, `criado_em`, etc.

3. **Remover variavel nao usada `container_y`** em `kanban_column_widget.py` (linhas 119-124). Codigo morto que confunde.

4. **Corrigir acumulo de stretch items** em `kanban_widget.py` (linha 92). O `_clear_board()` precisa limpar tambem os spacers.

5. **Remover import nao usado `QEvent`** em `kanban_card_widget.py` (linha 86).

6. **Adicionar `qt_api = "pyqt6"`** no `pyproject.toml` na secao `[tool.pytest.ini_options]`.

### Prioridade Media (deveriam ser corrigidos)

7. **Adicionar testes para `update_task`, `search_tasks` e cenarios de erro** no `test_task_service.py`.

8. **Expor `get_task_by_id` no `TaskService`** e usar em `todo_widget.py` em vez de busca linear.

9. **Centralizar versao** -- usar `__version__` do pacote em `main.py`.

10. **Mover imports de dentro dos metodos para o topo** em `kanban_card_widget.py` e `kanban_column_widget.py`.

11. **Adicionar null checks nos botoes do `QDialogButtonBox`** em `task_form.py` (linhas 101-109).

### Prioridade Baixa (nice-to-have)

12. Extrair `_COR_PRIORIDADE` para modulo compartilhado.
13. Adicionar `datetime.now(tz=timezone.utc)` em todo o projeto.
14. Adicionar context manager ao `DatabaseConnection`.
15. Documentar limitacao de `check_same_thread=False`.
16. Adicionar testes de UI com pytest-qt.
17. Adicionar tratamento de erros com `QMessageBox` nos widgets.
18. Adicionar indice em `tasks.coluna_kanban` no schema.
