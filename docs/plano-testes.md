# Plano de Testes — Own Board List

**Projeto:** Own Board List — Gestor de Tarefas Desktop
**Versão:** 1.0
**Data:** 2026-04-16
**Autor:** Agente QA
**Stack:** Python 3.11+, PyQt6, SQLite (stdlib), pytest, pytest-qt, pytest-cov

---

## Sumário

1. [Pirâmide de Testes](#1-pirâmide-de-testes)
2. [Casos de Teste por Módulo](#2-casos-de-teste-por-módulo)
   - 2.1 [models/task.py](#21-modelstaskpy)
   - 2.2 [models/kanban_column.py](#22-modelskanban_columnpy)
   - 2.3 [database/task_repository.py](#23-databasetask_repositorypy)
   - 2.4 [database/column_repository.py](#24-databasecolumn_repositorypy)
   - 2.5 [services/task_service.py](#25-servicestask_servicepy)
   - 2.6 [Sincronização entre Abas](#26-sincronização-entre-abas)
   - 2.7 [Filtros e Busca](#27-filtros-e-busca)
   - 2.8 [ui/TodoWidget](#28-uitodowidget)
   - 2.9 [ui/KanbanWidget](#29-uikanbanwidget)
3. [Fixtures Recomendadas (conftest.py)](#3-fixtures-recomendadas-conftestpy)
4. [Cobertura Mínima Esperada](#4-cobertura-mínima-esperada)
5. [Checklist de Release (Smoke Tests Manuais)](#5-checklist-de-release-smoke-tests-manuais)
6. [Riscos de Qualidade Identificados](#6-riscos-de-qualidade-identificados)

---

## 1. Pirâmide de Testes

```
              /\
             /  \
            / E2E\          ~5% — fluxos completos (pytest-qt + simulação real)
           /------\
          /   UI   \        ~20% — componentes Qt isolados (qtbot)
         /----------\
        / Integração \      ~30% — services + DB :memory: (sem UI)
       /--------------\
      /   Unitários    \    ~45% — models + utils (sem Qt, sem DB)
     /------------------\
```

### Nível 1 — Testes Unitários

**Alvo:** `models/`, `utils/constants.py`
**Características:**
- Sem dependências externas (nem Qt, nem SQLite)
- Execução extremamente rápida (< 1ms por teste)
- Isolamento total — sem fixtures de banco
- Cobrem validações de domínio, conversões e comportamento das dataclasses

**Comando:** `pytest tests/test_models/ -v`

### Nível 2 — Testes de Integração

**Alvo:** `database/` (repositories) + `services/`
**Características:**
- SQLite `:memory:` — banco criado e destruído a cada teste
- `QApplication` necessária para `TaskService` (herda `QObject`), mas sem janelas abertas
- Testam queries SQL, transações, validações de negócio e emissão de signals
- Velocidade média (~10–50ms por teste)

**Comando:** `pytest tests/test_database/ tests/test_services/ -v`

### Nível 3 — Testes de UI/Componente

**Alvo:** `ui/todo/`, `ui/kanban/`, `ui/dialogs/`
**Características:**
- `qtbot` do pytest-qt para instanciar widgets sem um display físico (usa offscreen plugin)
- Testam renderização inicial, cliques em botões, preenchimento de formulários
- Verificam que signals dos widgets são emitidos corretamente
- Não testam integração com banco — usam mocks ou fixtures de service

**Comando:** `pytest tests/test_ui/ -v`

### Nível 4 — Testes E2E

**Alvo:** fluxos completos de usuário end-to-end
**Características:**
- `MainWindow` completa instanciada com `qtbot`
- Banco SQLite `:memory:` real (sem mocks)
- Simulam interações de usuário: cliques, digitação, drag-and-drop
- Lentos (~100–500ms por teste), poucos em número
- Cobrem os cenários de maior risco de regressão

**Comando:** `pytest tests/test_ui/ -k "e2e" -v`

**Variável de ambiente necessária para CI (sem display):**
```bash
QT_QPA_PLATFORM=offscreen pytest
```

---

## 2. Casos de Teste por Módulo

### 2.1 `models/task.py`

**Arquivo de teste:** `tests/test_models/test_task.py`
**Tipo predominante:** Unitário (sem fixtures de banco ou Qt)

---

#### TC-001 — Criação válida de Task com campos obrigatórios

| Campo | Valor |
|-------|-------|
| **Tipo** | Unitário |
| **Pré-condições** | Nenhuma |
| **Passos** | Instanciar `Task(titulo="Estudar Python")` |
| **Resultado esperado** | Objeto criado sem exceção; `id` preenchido (UUID não vazio); `status == StatusTarefa.PENDENTE`; `prioridade == Prioridade.MEDIA`; `data_vencimento is None`; `coluna_kanban == "A Fazer"`; `posicao_kanban == 0`; `criado_em` e `atualizado_em` do tipo `datetime` |

```python
def test_task_criacao_valida_campos_obrigatorios():
    task = Task(titulo="Estudar Python")

    assert task.id != ""
    assert task.titulo == "Estudar Python"
    assert task.status == StatusTarefa.PENDENTE
    assert task.prioridade == Prioridade.MEDIA
    assert task.data_vencimento is None
    assert task.coluna_kanban == "A Fazer"
    assert task.posicao_kanban == 0
    assert isinstance(task.criado_em, datetime)
    assert isinstance(task.atualizado_em, datetime)
```

---

#### TC-002 — Título vazio levanta ValueError

| Campo | Valor |
|-------|-------|
| **Tipo** | Unitário |
| **Pré-condições** | Nenhuma |
| **Passos** | Instanciar `Task(titulo="")` |
| **Resultado esperado** | `ValueError` é levantado com mensagem contendo "título" ou "obrigatório" |

```python
def test_task_titulo_vazio_levanta_erro():
    with pytest.raises(ValueError, match=r"título|obrigatório"):
        Task(titulo="")
```

---

#### TC-003 — Título apenas com espaços levanta ValueError

| Campo | Valor |
|-------|-------|
| **Tipo** | Unitário |
| **Pré-condições** | Nenhuma |
| **Passos** | Instanciar `Task(titulo="   ")` |
| **Resultado esperado** | `ValueError` é levantado (título em branco após strip) |

```python
def test_task_titulo_apenas_espacos_levanta_erro():
    with pytest.raises(ValueError):
        Task(titulo="   ")
```

---

#### TC-004 — Título com exatamente 200 caracteres é válido

| Campo | Valor |
|-------|-------|
| **Tipo** | Unitário |
| **Pré-condições** | Nenhuma |
| **Passos** | Instanciar `Task(titulo="A" * 200)` |
| **Resultado esperado** | Objeto criado sem exceção |

```python
def test_task_titulo_limite_exato_200_chars():
    task = Task(titulo="A" * 200)
    assert len(task.titulo) == 200
```

---

#### TC-005 — Título com 201 caracteres levanta ValueError

| Campo | Valor |
|-------|-------|
| **Tipo** | Unitário |
| **Pré-condições** | Nenhuma |
| **Passos** | Instanciar `Task(titulo="A" * 201)` |
| **Resultado esperado** | `ValueError` com menção ao limite de 200 caracteres |

```python
def test_task_titulo_acima_200_chars_levanta_erro():
    with pytest.raises(ValueError, match=r"200|máximo|limite"):
        Task(titulo="A" * 201)
```

---

#### TC-006 — Conversão to_dict com data_vencimento None

| Campo | Valor |
|-------|-------|
| **Tipo** | Unitário |
| **Pré-condições** | Nenhuma |
| **Passos** | Criar task sem data; chamar `task.to_dict()` |
| **Resultado esperado** | Dicionário retornado; `d["data_vencimento"] is None`; todos os campos-chave presentes |

```python
def test_task_to_dict_sem_data_vencimento():
    task = Task(titulo="Tarefa sem data")
    d = task.to_dict()

    assert d["data_vencimento"] is None
    assert d["titulo"] == "Tarefa sem data"
    assert "id" in d
    assert "status" in d
    assert "prioridade" in d
    assert "criado_em" in d
    assert "atualizado_em" in d
```

---

#### TC-007 — Conversão to_dict com data_vencimento preenchida

| Campo | Valor |
|-------|-------|
| **Tipo** | Unitário |
| **Pré-condições** | Nenhuma |
| **Passos** | Criar task com `data_vencimento=date(2026, 12, 31)`; chamar `to_dict()` |
| **Resultado esperado** | `d["data_vencimento"]` é string ISO `"2026-12-31"` (ou objeto `date` — consistente com `from_dict`) |

```python
def test_task_to_dict_com_data_vencimento():
    from datetime import date
    task = Task(titulo="Com data", data_vencimento=date(2026, 12, 31))
    d = task.to_dict()

    # Aceita tanto string ISO quanto objeto date, mas deve ser consistente com from_dict
    assert d["data_vencimento"] is not None
    # Se serializa como string ISO:
    assert d["data_vencimento"] == "2026-12-31"
```

---

#### TC-008 — Round-trip to_dict/from_dict preserva todos os campos

| Campo | Valor |
|-------|-------|
| **Tipo** | Unitário |
| **Pré-condições** | Nenhuma |
| **Passos** | Criar task completa; chamar `to_dict()`; chamar `Task.from_dict(d)` |
| **Resultado esperado** | Task reconstruída é igual à original em todos os campos |

```python
def test_task_round_trip_to_from_dict():
    from datetime import date
    original = Task(
        titulo="Tarefa completa",
        descricao="Descrição detalhada",
        prioridade=Prioridade.ALTA,
        data_vencimento=date(2026, 6, 15),
        status=StatusTarefa.PENDENTE,
        coluna_kanban="Em Andamento",
        posicao_kanban=3,
    )
    reconstruida = Task.from_dict(original.to_dict())

    assert reconstruida.id == original.id
    assert reconstruida.titulo == original.titulo
    assert reconstruida.descricao == original.descricao
    assert reconstruida.prioridade == original.prioridade
    assert reconstruida.data_vencimento == original.data_vencimento
    assert reconstruida.status == original.status
    assert reconstruida.coluna_kanban == original.coluna_kanban
    assert reconstruida.posicao_kanban == original.posicao_kanban
```

---

#### TC-009 — from_dict com data_vencimento None

| Campo | Valor |
|-------|-------|
| **Tipo** | Unitário |
| **Pré-condições** | Nenhuma |
| **Passos** | Chamar `Task.from_dict({"titulo": "X", ..., "data_vencimento": None})` |
| **Resultado esperado** | Task criada com `data_vencimento is None` sem erro |

---

#### TC-010 — marcar_concluida() muda status para CONCLUIDA

| Campo | Valor |
|-------|-------|
| **Tipo** | Unitário |
| **Pré-condições** | Task com `status == PENDENTE` |
| **Passos** | Chamar `task.marcar_concluida()` |
| **Resultado esperado** | `task.status == StatusTarefa.CONCLUIDA`; `atualizado_em` foi atualizado |

```python
def test_task_marcar_concluida():
    task = Task(titulo="Pendente")
    ts_antes = task.atualizado_em

    task.marcar_concluida()

    assert task.status == StatusTarefa.CONCLUIDA
    assert task.atualizado_em >= ts_antes
```

---

#### TC-011 — marcar_concluida() em task já concluída é idempotente

| Campo | Valor |
|-------|-------|
| **Tipo** | Unitário |
| **Pré-condições** | Task com `status == CONCLUIDA` |
| **Passos** | Chamar `task.marcar_concluida()` novamente |
| **Resultado esperado** | Sem exceção; status permanece `CONCLUIDA` |

---

#### TC-012 — reabrir() muda status de CONCLUIDA para PENDENTE

| Campo | Valor |
|-------|-------|
| **Tipo** | Unitário |
| **Pré-condições** | Task com `status == CONCLUIDA` |
| **Passos** | Chamar `task.reabrir()` |
| **Resultado esperado** | `task.status == StatusTarefa.PENDENTE` |

```python
def test_task_reabrir():
    task = Task(titulo="Concluída")
    task.marcar_concluida()

    task.reabrir()

    assert task.status == StatusTarefa.PENDENTE
```

---

#### TC-013 — Dois IDs de Tasks distintos são únicos

| Campo | Valor |
|-------|-------|
| **Tipo** | Unitário |
| **Passos** | Criar duas Tasks; comparar `id` |
| **Resultado esperado** | `task1.id != task2.id` |

```python
def test_task_ids_unicos():
    t1 = Task(titulo="A")
    t2 = Task(titulo="B")
    assert t1.id != t2.id
```

---

### 2.2 `models/kanban_column.py`

**Arquivo de teste:** `tests/test_models/test_task.py` (seção KanbanColumn) ou `test_kanban_column.py`

---

#### TC-014 — Criação válida de KanbanColumn

| Campo | Valor |
|-------|-------|
| **Tipo** | Unitário |
| **Passos** | `KanbanColumn(nome="A Fazer", posicao=0)` |
| **Resultado esperado** | Objeto criado; `id` não vazio; `criado_em` é `datetime` |

---

#### TC-015 — Nome vazio levanta ValueError

| Campo | Valor |
|-------|-------|
| **Tipo** | Unitário |
| **Passos** | `KanbanColumn(nome="", posicao=0)` |
| **Resultado esperado** | `ValueError` |

---

#### TC-016 — Round-trip to_dict/from_dict de KanbanColumn

| Campo | Valor |
|-------|-------|
| **Tipo** | Unitário |
| **Passos** | Criar coluna, serializar e reconstruir |
| **Resultado esperado** | Todos os campos preservados |

---

### 2.3 `database/task_repository.py`

**Arquivo de teste:** `tests/test_database/test_task_repository.py`
**Tipo predominante:** Integração (SQLite `:memory:`)

---

#### TC-017 — create() persiste task e retorna com mesmo id

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | `task_repo` fixture; `sample_task` fixture |
| **Passos** | `task_repo.create(sample_task)` |
| **Resultado esperado** | Task retornada tem mesmo `id`, `titulo`, `status`; row inserida no banco |

```python
def test_task_repository_create(task_repo, sample_task):
    criada = task_repo.create(sample_task)

    assert criada.id == sample_task.id
    assert criada.titulo == sample_task.titulo
    assert task_repo.get_by_id(criada.id) is not None
```

---

#### TC-018 — get_by_id() retorna None para id inexistente

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Passos** | `task_repo.get_by_id("id-que-nao-existe")` |
| **Resultado esperado** | Retorna `None` |

```python
def test_task_repository_get_by_id_inexistente(task_repo):
    result = task_repo.get_by_id("00000000-0000-0000-0000-000000000000")
    assert result is None
```

---

#### TC-019 — get_all() retorna todas as tasks criadas

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | `sample_tasks` fixture (5 tasks) já criadas |
| **Passos** | `task_repo.get_all()` |
| **Resultado esperado** | Lista com 5 itens |

```python
def test_task_repository_get_all(task_repo, sample_tasks):
    for t in sample_tasks:
        task_repo.create(t)

    resultado = task_repo.get_all()
    assert len(resultado) == 5
```

---

#### TC-020 — get_all() em banco vazio retorna lista vazia

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Passos** | `task_repo.get_all()` sem nenhum `create()` anterior |
| **Resultado esperado** | `[]` |

---

#### TC-021 — update() persiste alterações corretamente

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Task previamente criada |
| **Passos** | Alterar `titulo` e `prioridade`; chamar `task_repo.update(task)` |
| **Resultado esperado** | `get_by_id()` retorna task com novos valores; `atualizado_em` > `criado_em` |

```python
def test_task_repository_update(task_repo, sample_task):
    task_repo.create(sample_task)
    sample_task.titulo = "Título Atualizado"
    sample_task.prioridade = Prioridade.ALTA

    task_repo.update(sample_task)
    recuperada = task_repo.get_by_id(sample_task.id)

    assert recuperada.titulo == "Título Atualizado"
    assert recuperada.prioridade == Prioridade.ALTA
    assert recuperada.atualizado_em > recuperada.criado_em
```

---

#### TC-022 — delete() remove task e retorna True

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Task criada |
| **Passos** | `task_repo.delete(task.id)` |
| **Resultado esperado** | Retorna `True`; `get_by_id()` retorna `None` |

```python
def test_task_repository_delete(task_repo, sample_task):
    task_repo.create(sample_task)

    resultado = task_repo.delete(sample_task.id)

    assert resultado is True
    assert task_repo.get_by_id(sample_task.id) is None
```

---

#### TC-023 — delete() para id inexistente retorna False

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Passos** | `task_repo.delete("id-inexistente")` |
| **Resultado esperado** | Retorna `False`; nenhuma exceção |

---

#### TC-024 — get_by_column() retorna tasks ordenadas por posicao_kanban

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | 3 tasks na coluna "A Fazer" com posições 2, 0, 1 |
| **Passos** | `task_repo.get_by_column("A Fazer")` |
| **Resultado esperado** | Lista retornada na ordem 0, 1, 2 (ordenada por `posicao_kanban`) |

```python
def test_task_repository_get_by_column_ordenado(task_repo):
    tasks = [
        Task(titulo="C", coluna_kanban="A Fazer", posicao_kanban=2),
        Task(titulo="A", coluna_kanban="A Fazer", posicao_kanban=0),
        Task(titulo="B", coluna_kanban="A Fazer", posicao_kanban=1),
    ]
    for t in tasks:
        task_repo.create(t)

    resultado = task_repo.get_by_column("A Fazer")

    assert [r.posicao_kanban for r in resultado] == [0, 1, 2]
    assert resultado[0].titulo == "A"
```

---

#### TC-025 — get_by_column() para coluna inexistente retorna lista vazia

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Passos** | `task_repo.get_by_column("Coluna Fantasma")` |
| **Resultado esperado** | `[]` |

---

#### TC-026 — update_position() atualiza coluna e posição

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Task criada em "A Fazer", posição 0 |
| **Passos** | `task_repo.update_position(task.id, "Em Andamento", 2)` |
| **Resultado esperado** | `get_by_id()` retorna task com `coluna_kanban == "Em Andamento"` e `posicao_kanban == 2` |

```python
def test_task_repository_update_position(task_repo, sample_task):
    task_repo.create(sample_task)

    task_repo.update_position(sample_task.id, "Em Andamento", 2)
    recuperada = task_repo.get_by_id(sample_task.id)

    assert recuperada.coluna_kanban == "Em Andamento"
    assert recuperada.posicao_kanban == 2
```

---

#### TC-027 — search() retorna tasks com match no título (case-insensitive)

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Tasks com títulos "Estudar Python", "Revisar PR", "estudar matemática" |
| **Passos** | `task_repo.search("ESTUDAR")` |
| **Resultado esperado** | Retorna exatamente 2 tasks (case-insensitive LIKE) |

```python
def test_task_repository_search_case_insensitive(task_repo):
    task_repo.create(Task(titulo="Estudar Python"))
    task_repo.create(Task(titulo="Revisar PR"))
    task_repo.create(Task(titulo="estudar matemática"))

    resultado = task_repo.search("ESTUDAR")

    assert len(resultado) == 2
    titulos = {t.titulo for t in resultado}
    assert "Estudar Python" in titulos
    assert "estudar matemática" in titulos
```

---

#### TC-028 — search() busca também na descrição

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Task com título diferente mas descrição contendo o termo |
| **Passos** | `task_repo.search("importante")` |
| **Resultado esperado** | Task cujo título não contém "importante" mas a descrição contém é retornada |

```python
def test_task_repository_search_na_descricao(task_repo):
    task_repo.create(Task(titulo="Reunião", descricao="Assunto muito importante"))
    task_repo.create(Task(titulo="Almoço"))

    resultado = task_repo.search("importante")

    assert len(resultado) == 1
    assert resultado[0].titulo == "Reunião"
```

---

#### TC-029 — search() com query vazia retorna todas as tasks

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | 3 tasks criadas |
| **Passos** | `task_repo.search("")` |
| **Resultado esperado** | Lista com 3 tasks (ou equivalente a `get_all()`) |

---

#### TC-030 — search() sem resultados retorna lista vazia

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Passos** | `task_repo.search("zzzzNaoExiste")` |
| **Resultado esperado** | `[]` |

---

#### TC-031 — Isolamento entre testes (banco limpo a cada teste)

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Verificação** | Cada teste que usa `task_repo` deve ter banco vazio inicialmente; isso é garantido pela fixture `db_conn` com escopo `function` que cria nova conexão `:memory:` a cada teste |
| **Resultado esperado** | `task_repo.get_all()` no início de qualquer teste retorna `[]` |

---

### 2.4 `database/column_repository.py`

**Arquivo de teste:** `tests/test_database/test_column_repository.py`

---

#### TC-032 — create() persiste coluna

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Passos** | `column_repo.create(KanbanColumn(nome="Backlog", posicao=0))` |
| **Resultado esperado** | Coluna recuperável via `get_all()` |

---

#### TC-033 — get_all() retorna colunas ordenadas por posicao

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Colunas criadas com posições 2, 0, 1 |
| **Passos** | `column_repo.get_all()` |
| **Resultado esperado** | Lista ordenada: posições [0, 1, 2] |

```python
def test_column_repository_get_all_ordenado(column_repo):
    column_repo.create(KanbanColumn(nome="C", posicao=2))
    column_repo.create(KanbanColumn(nome="A", posicao=0))
    column_repo.create(KanbanColumn(nome="B", posicao=1))

    colunas = column_repo.get_all()

    assert [c.posicao for c in colunas] == [0, 1, 2]
    assert colunas[0].nome == "A"
```

---

#### TC-034 — update() renomeia coluna

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Passos** | Criar coluna; alterar `nome`; chamar `column_repo.update(coluna)` |
| **Resultado esperado** | `get_all()` retorna coluna com novo nome |

---

#### TC-035 — delete() remove coluna vazia

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Coluna sem tasks |
| **Passos** | `column_repo.delete(coluna.id)` |
| **Resultado esperado** | `True`; coluna não aparece em `get_all()` |

---

#### TC-036 — reorder() atualiza posições de todas as colunas

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | 3 colunas com ids [id_a, id_b, id_c] e posições [0, 1, 2] |
| **Passos** | `column_repo.reorder([id_c, id_a, id_b])` |
| **Resultado esperado** | `get_all()` retorna colunas na nova ordem [c, a, b] com posições [0, 1, 2] atualizadas |

```python
def test_column_repository_reorder(column_repo):
    col_a = column_repo.create(KanbanColumn(nome="A", posicao=0))
    col_b = column_repo.create(KanbanColumn(nome="B", posicao=1))
    col_c = column_repo.create(KanbanColumn(nome="C", posicao=2))

    # Nova ordem: C, A, B
    column_repo.reorder([col_c.id, col_a.id, col_b.id])

    colunas = column_repo.get_all()
    assert colunas[0].nome == "C"
    assert colunas[0].posicao == 0
    assert colunas[1].nome == "A"
    assert colunas[1].posicao == 1
    assert colunas[2].nome == "B"
    assert colunas[2].posicao == 2
```

---

#### TC-037 — reorder() com lista parcial (subconjunto de ids) não corrompe dados

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Caso de borda** | Passar apenas 2 de 3 ids |
| **Resultado esperado** | Sem exceção; posições reordenadas para os IDs fornecidos; coluna omitida mantém posição anterior ou recebe posição consistente (comportamento definido pela implementação) |

---

#### TC-038 — has_tasks() retorna True quando coluna tem tasks

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Task criada com `coluna_kanban` apontando para nome da coluna |
| **Passos** | `column_repo.has_tasks(coluna.id)` |
| **Resultado esperado** | `True` |

```python
def test_column_repository_has_tasks_verdadeiro(db_conn, column_repo, task_repo):
    coluna = column_repo.create(KanbanColumn(nome="Minha Coluna", posicao=0))
    task_repo.create(Task(titulo="Task X", coluna_kanban="Minha Coluna"))

    assert column_repo.has_tasks(coluna.id) is True
```

---

#### TC-039 — has_tasks() retorna False quando coluna está vazia

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Coluna criada, sem tasks |
| **Passos** | `column_repo.has_tasks(coluna.id)` |
| **Resultado esperado** | `False` |

---

#### TC-040 — Não é possível excluir coluna que contém tasks

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Coluna com tasks |
| **Passos** | Tentar `column_repo.delete(coluna.id)` |
| **Resultado esperado** | `False` ou `ValueError`/`PermissionError` indicando que a coluna não pode ser excluída; task permanece no banco |

> **Nota:** O comportamento exato (retornar `False` vs levantar exceção) deve ser definido na implementação e o teste deve refletir essa decisão. Recomenda-se levantar uma exceção semântica (`ColumnNotEmptyError`) para deixar o código mais expressivo.

---

### 2.5 `services/task_service.py`

**Arquivo de teste:** `tests/test_services/test_task_service.py`
**Tipo predominante:** Integração (QObject + SQLite `:memory:`)

> **Importante:** `TaskService` herda de `QObject`, portanto uma `QApplication` deve existir. O pytest-qt garante isso automaticamente quando `qtbot` é listado como fixture.

---

#### TC-041 — create_task() persiste e emite signal task_created

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | `task_service` fixture |
| **Passos** | Capturar signal `task_created`; chamar `task_service.create_task(titulo="Nova Tarefa")` |
| **Resultado esperado** | Signal emitido 1 vez; argumento é objeto `Task` com `titulo == "Nova Tarefa"`; task persiste no banco |

```python
def test_task_service_create_emite_signal(qtbot, task_service):
    with qtbot.waitSignal(task_service.task_created, timeout=1000) as blocker:
        task_service.create_task(titulo="Nova Tarefa")

    task_emitida: Task = blocker.args[0]
    assert task_emitida.titulo == "Nova Tarefa"
    assert task_emitida.id != ""

    # Verifica persistência
    tasks = task_service.get_all_tasks()
    assert any(t.titulo == "Nova Tarefa" for t in tasks)
```

---

#### TC-042 — update_task() atualiza e emite signal task_updated

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Task criada via service |
| **Passos** | Capturar signal `task_updated`; alterar `titulo` e chamar `update_task()` |
| **Resultado esperado** | Signal `task_updated` emitido com task atualizada; banco reflete mudança |

```python
def test_task_service_update_emite_signal(qtbot, task_service, sample_task):
    task_service.create_task(titulo=sample_task.titulo)
    task = task_service.get_all_tasks()[0]
    task.titulo = "Título Modificado"

    with qtbot.waitSignal(task_service.task_updated, timeout=1000) as blocker:
        task_service.update_task(task)

    assert blocker.args[0].titulo == "Título Modificado"
```

---

#### TC-043 — delete_task() remove e emite signal task_deleted com id

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Task criada |
| **Passos** | Capturar signal `task_deleted`; chamar `task_service.delete_task(task.id)` |
| **Resultado esperado** | Signal `task_deleted` emitido com string do id; task não existe mais no banco |

```python
def test_task_service_delete_emite_signal(qtbot, task_service):
    task_service.create_task(titulo="Para Deletar")
    task = task_service.get_all_tasks()[0]

    with qtbot.waitSignal(task_service.task_deleted, timeout=1000) as blocker:
        task_service.delete_task(task.id)

    assert blocker.args[0] == task.id
    assert task_service.get_all_tasks() == []
```

---

#### TC-044 — toggle_status() altera de PENDENTE para CONCLUIDA e emite task_updated

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Task com `status == PENDENTE` |
| **Passos** | Capturar signal; `task_service.toggle_status(task.id)` |
| **Resultado esperado** | Task retornada com `status == CONCLUIDA`; signal `task_updated` emitido |

```python
def test_task_service_toggle_status_pendente_para_concluida(qtbot, task_service):
    task_service.create_task(titulo="Tarefa Pendente")
    task = task_service.get_all_tasks()[0]
    assert task.status == StatusTarefa.PENDENTE

    with qtbot.waitSignal(task_service.task_updated, timeout=1000) as blocker:
        task_service.toggle_status(task.id)

    task_atualizada = blocker.args[0]
    assert task_atualizada.status == StatusTarefa.CONCLUIDA
```

---

#### TC-045 — toggle_status() altera de CONCLUIDA para PENDENTE (reversão)

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Task com `status == CONCLUIDA` |
| **Passos** | `task_service.toggle_status(task.id)` |
| **Resultado esperado** | `status == PENDENTE`; signal emitido |

```python
def test_task_service_toggle_status_concluida_para_pendente(qtbot, task_service):
    task_service.create_task(titulo="Tarefa")
    task = task_service.get_all_tasks()[0]
    task_service.toggle_status(task.id)  # PENDENTE → CONCLUIDA

    with qtbot.waitSignal(task_service.task_updated, timeout=1000):
        task_service.toggle_status(task.id)  # CONCLUIDA → PENDENTE

    task_final = task_service.get_all_tasks()[0]
    assert task_final.status == StatusTarefa.PENDENTE
```

---

#### TC-046 — toggle_status() move task para coluna "Concluído" ao concluir

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Descrição** | Sincronização com Kanban: ao concluir uma task na Todo List, ela deve ir para a coluna "Concluído" |
| **Pré-condições** | Task com `coluna_kanban == "A Fazer"` |
| **Passos** | `task_service.toggle_status(task.id)` |
| **Resultado esperado** | Task com `coluna_kanban == "Concluído"` e `status == CONCLUIDA` |

```python
def test_task_service_toggle_status_move_para_coluna_concluido(qtbot, task_service):
    task_service.create_task(titulo="Tarefa")
    task = task_service.get_all_tasks()[0]
    assert task.coluna_kanban == "A Fazer"

    task_service.toggle_status(task.id)

    task_atualizada = task_service.get_all_tasks()[0]
    assert task_atualizada.coluna_kanban == "Concluído"
    assert task_atualizada.status == StatusTarefa.CONCLUIDA
```

---

#### TC-047 — toggle_status() move task de "Concluído" para "A Fazer" ao reabrir

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Task concluída e na coluna "Concluído" |
| **Passos** | `task_service.toggle_status(task.id)` |
| **Resultado esperado** | `coluna_kanban == "A Fazer"` e `status == PENDENTE` |

---

#### TC-048 — move_to_column() atualiza coluna e posição

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Task na coluna "A Fazer" |
| **Passos** | `task_service.move_to_column(task.id, "Em Andamento", 0)` |
| **Resultado esperado** | `coluna_kanban == "Em Andamento"`, `posicao_kanban == 0`; signal `task_updated` emitido |

```python
def test_task_service_move_to_column(qtbot, task_service):
    task_service.create_task(titulo="Tarefa")
    task = task_service.get_all_tasks()[0]

    with qtbot.waitSignal(task_service.task_updated, timeout=1000) as blocker:
        task_service.move_to_column(task.id, "Em Andamento", 0)

    task_movida = blocker.args[0]
    assert task_movida.coluna_kanban == "Em Andamento"
    assert task_movida.posicao_kanban == 0
```

---

#### TC-049 — move_to_column() para "Concluído" marca status como CONCLUIDA

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Task com `status == PENDENTE` |
| **Passos** | `task_service.move_to_column(task.id, "Concluído", 0)` |
| **Resultado esperado** | `status == CONCLUIDA`; `coluna_kanban == "Concluído"` |

```python
def test_task_service_move_para_concluido_atualiza_status(qtbot, task_service):
    task_service.create_task(titulo="Pendente")
    task = task_service.get_all_tasks()[0]
    assert task.status == StatusTarefa.PENDENTE

    task_service.move_to_column(task.id, "Concluído", 0)

    task_final = task_service.get_all_tasks()[0]
    assert task_final.status == StatusTarefa.CONCLUIDA
    assert task_final.coluna_kanban == "Concluído"
```

---

#### TC-050 — move_to_column() de "Concluído" para outra coluna reverte status para PENDENTE

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Task concluída na coluna "Concluído" |
| **Passos** | `task_service.move_to_column(task.id, "Em Andamento", 0)` |
| **Resultado esperado** | `status == PENDENTE`; `coluna_kanban == "Em Andamento"` |

---

#### TC-051 — create_task() com título vazio levanta ValidationError / ValueError

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Passos** | `task_service.create_task(titulo="")` |
| **Resultado esperado** | Exceção levantada; nenhum signal emitido; banco não alterado |

```python
def test_task_service_create_titulo_vazio_sem_signal(qtbot, task_service):
    spy = QSignalSpy(task_service.task_created)

    with pytest.raises((ValueError, Exception)):
        task_service.create_task(titulo="")

    assert len(spy) == 0
    assert task_service.get_all_tasks() == []
```

---

#### TC-052 — search_tasks() retorna tasks correspondentes

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Passos** | Criar tasks; `task_service.search_tasks("python")` |
| **Resultado esperado** | Somente tasks com "python" no título ou descrição |

---

### 2.6 Sincronização entre Abas

**Arquivo de teste:** `tests/test_services/test_task_service.py` (cenários de integração)
**e** `tests/test_ui/test_todo_widget.py` + `tests/test_ui/test_kanban_widget.py` (cenários E2E)

---

#### TC-053 — Tarefa criada na Todo List aparece no Kanban na coluna "A Fazer"

| Campo | Valor |
|-------|-------|
| **Tipo** | E2E / UI |
| **Pré-condições** | `MainWindow` com ambas as abas ativas; `KanbanWidget` conectado ao signal `task_created` do `TaskService` |
| **Passos** | (1) Criar tarefa via `TodoWidget`; (2) Verificar lista de cards do `KanbanWidget` na coluna "A Fazer" |
| **Resultado esperado** | Card com o título criado aparece na coluna "A Fazer" do Kanban |

```python
def test_sync_criar_na_todo_aparece_no_kanban(qtbot, main_window):
    todo_widget = main_window.todo_widget
    kanban_widget = main_window.kanban_widget

    # Simular criação de tarefa na Todo List
    with qtbot.waitSignal(main_window.task_service.task_created, timeout=2000):
        main_window.task_service.create_task(titulo="Sincronização Teste")

    # Verificar que o card apareceu no Kanban
    coluna_a_fazer = kanban_widget.get_column_widget("A Fazer")
    titulos_cards = [card.task.titulo for card in coluna_a_fazer.cards]
    assert "Sincronização Teste" in titulos_cards
```

---

#### TC-054 — Tarefa criada no Kanban aparece na Todo List

| Campo | Valor |
|-------|-------|
| **Tipo** | E2E / UI |
| **Passos** | Criar task via `KanbanWidget` (coluna "Em Andamento"); verificar que aparece no `TodoWidget` |
| **Resultado esperado** | Task visível na Todo List com os dados corretos |

---

#### TC-055 — Mover card para "Concluído" no Kanban reflete na Todo List

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Task com `status == PENDENTE` |
| **Passos** | `task_service.move_to_column(task.id, "Concluído", 0)` |
| **Resultado esperado** | Signal `task_updated` emitido; task obtida via `get_all_tasks()` tem `status == CONCLUIDA` |

```python
def test_sync_mover_para_concluido_reflete_status(qtbot, task_service):
    task_service.create_task(titulo="Em Progresso")
    task = task_service.get_all_tasks()[0]

    with qtbot.waitSignal(task_service.task_updated, timeout=1000):
        task_service.move_to_column(task.id, "Concluído", 0)

    task_atualizada = task_service.get_all_tasks()[0]
    assert task_atualizada.status == StatusTarefa.CONCLUIDA
```

---

#### TC-056 — Desmarcar tarefa na Todo List move card de volta para "A Fazer" no Kanban

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Task com `status == CONCLUIDA`, `coluna_kanban == "Concluído"` |
| **Passos** | `task_service.toggle_status(task.id)` |
| **Resultado esperado** | `status == PENDENTE`; `coluna_kanban == "A Fazer"` |

---

#### TC-057 — Excluir tarefa em qualquer aba remove de ambas

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Passos** | Criar task; `task_service.delete_task(task.id)` |
| **Resultado esperado** | Signal `task_deleted` emitido; `get_all_tasks()` vazio; nenhuma duplicata ou tarefa fantasma |

---

#### TC-058 — Sem duplicatas após create + signal

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Passos** | Chamar `create_task()` uma vez; verificar `get_all_tasks()` |
| **Resultado esperado** | Exatamente 1 task no banco (signal não causa dupla inserção) |

```python
def test_sem_duplicatas_apos_create(task_service):
    task_service.create_task(titulo="Única")
    tasks = task_service.get_all_tasks()
    assert len(tasks) == 1
```

---

### 2.7 Filtros e Busca

**Arquivo de teste:** `tests/test_services/test_task_service.py` e `tests/test_ui/test_todo_widget.py`

---

#### TC-059 — Busca vazia retorna todas as tasks

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | 5 tasks criadas |
| **Passos** | `task_service.search_tasks("")` |
| **Resultado esperado** | Lista com 5 tasks |

---

#### TC-060 — Busca com resultado retorna somente tasks correspondentes

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Tasks: "Comprar pão", "Comprar leite", "Estudar" |
| **Passos** | `task_service.search_tasks("Comprar")` |
| **Resultado esperado** | 2 tasks; "Estudar" não incluída |

---

#### TC-061 — Busca sem resultado retorna lista vazia

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Tasks que não contêm o termo buscado |
| **Passos** | `task_service.search_tasks("TermoInexistente")` |
| **Resultado esperado** | `[]` |

---

#### TC-062 — UI exibe "Nenhuma tarefa encontrada" quando busca retorna vazio

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Pré-condições** | `TodoWidget` com `qtbot`; tasks que não correspondem ao termo |
| **Passos** | Digitar no campo de busca um termo que não retorna resultados |
| **Resultado esperado** | Label ou widget com texto "Nenhuma tarefa encontrada" visível; lista de tasks vazia |

```python
def test_todo_widget_busca_sem_resultado_exibe_mensagem(qtbot, todo_widget):
    todo_widget.task_service.create_task(titulo="Tarefa Existente")
    qtbot.keyClicks(todo_widget.search_field, "TermoQueNaoExiste")

    # Aguardar debounce do QTimer (300ms)
    qtbot.wait(400)

    assert todo_widget.empty_message_label.isVisible()
    assert "Nenhuma tarefa encontrada" in todo_widget.empty_message_label.text()
```

---

#### TC-063 — Busca é case-insensitive na UI

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Pré-condições** | Task "Estudar Python" criada |
| **Passos** | Digitar "ESTUDAR" no campo de busca |
| **Resultado esperado** | Task "Estudar Python" aparece nos resultados |

---

#### TC-064 — Filtro por prioridade ALTA retorna somente tasks com prioridade ALTA

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Tasks com prioridades BAIXA, MEDIA, ALTA |
| **Passos** | Aplicar filtro `prioridade=Prioridade.ALTA` |
| **Resultado esperado** | Somente task com ALTA retornada |

---

#### TC-065 — Filtro por prioridade + busca de texto combinados

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | Tasks: ("Comprar pão", ALTA), ("Comprar leite", BAIXA), ("Estudar", ALTA) |
| **Passos** | Filtrar por ALTA e buscar "comprar" |
| **Resultado esperado** | Somente ("Comprar pão", ALTA) — intersecção dos dois critérios |

```python
def test_filtro_prioridade_mais_busca_texto(task_service):
    task_service.create_task(titulo="Comprar pão", prioridade=Prioridade.ALTA)
    task_service.create_task(titulo="Comprar leite", prioridade=Prioridade.BAIXA)
    task_service.create_task(titulo="Estudar", prioridade=Prioridade.ALTA)

    # O service deve expor um método de busca combinada
    resultado = task_service.get_filtered_tasks(
        prioridade=Prioridade.ALTA,
        query="comprar"
    )

    assert len(resultado) == 1
    assert resultado[0].titulo == "Comprar pão"
```

---

#### TC-066 — Filtro por status PENDENTE exclui tasks concluídas

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Pré-condições** | 2 tasks pendentes e 1 concluída |
| **Passos** | Filtrar por `status=StatusTarefa.PENDENTE` |
| **Resultado esperado** | 2 tasks retornadas; task concluída excluída |

---

#### TC-067 — Botão "Limpar filtros" restaura lista completa

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Pré-condições** | Filtro por prioridade ativo; apenas algumas tasks visíveis |
| **Passos** | Clicar em "Limpar filtros" |
| **Resultado esperado** | Todas as tasks visíveis novamente; filtros resetados |

---

### 2.8 `ui/TodoWidget`

**Arquivo de teste:** `tests/test_ui/test_todo_widget.py`

---

#### TC-068 — TodoWidget renderiza sem erros com banco vazio

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Passos** | Instanciar `TodoWidget(task_service)` com `qtbot.addWidget()` |
| **Resultado esperado** | Widget visível sem erros; lista de tasks vazia; botão "+ Nova Tarefa" presente |

```python
def test_todo_widget_renderiza_sem_erros(qtbot, todo_widget):
    qtbot.addWidget(todo_widget)
    assert todo_widget.isVisible() or not todo_widget.isHidden()
    assert todo_widget.new_task_button is not None
```

---

#### TC-069 — Clicar em "+ Nova Tarefa" abre TaskForm

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Passos** | `qtbot.mouseClick(todo_widget.new_task_button, Qt.MouseButton.LeftButton)` |
| **Resultado esperado** | Instância de `TaskForm` visível/aberta |

---

#### TC-070 — Atalho Ctrl+N abre TaskForm

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Passos** | `qtbot.keyClick(todo_widget, Qt.Key.Key_N, Qt.KeyboardModifier.ControlModifier)` |
| **Resultado esperado** | `TaskForm` aberto |

---

#### TC-071 — Criar tarefa via formulário atualiza a lista

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Passos** | Abrir formulário; preencher título; confirmar |
| **Resultado esperado** | Task aparece na lista do `TodoWidget` |

---

#### TC-072 — Checkbox de status aciona toggle_status no service

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Pré-condições** | Task pendente na lista |
| **Passos** | Clicar no checkbox do item |
| **Resultado esperado** | Signal `task_updated` emitido; item atualizado com visual de concluído (riscado/esmaecido) |

---

#### TC-073 — TaskForm não permite salvar com título vazio

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Passos** | Abrir `TaskForm`; não preencher título; verificar botão Salvar |
| **Resultado esperado** | Botão "Salvar" desabilitado enquanto título estiver vazio |

```python
def test_task_form_salvar_desabilitado_sem_titulo(qtbot):
    form = TaskForm()
    qtbot.addWidget(form)

    assert not form.save_button.isEnabled()

    qtbot.keyClicks(form.titulo_field, "Algo")
    assert form.save_button.isEnabled()

    form.titulo_field.clear()
    assert not form.save_button.isEnabled()
```

---

#### TC-074 — Botão excluir exibe diálogo de confirmação

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Passos** | Clicar no botão excluir de um item; verificar diálogo |
| **Resultado esperado** | `QMessageBox` ou `ConfirmDialog` exibido com texto de confirmação |

---

### 2.9 `ui/KanbanWidget`

**Arquivo de teste:** `tests/test_ui/test_kanban_widget.py`

---

#### TC-075 — KanbanWidget renderiza colunas padrão

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Passos** | Instanciar `KanbanWidget` com banco inicializado |
| **Resultado esperado** | 3 colunas visíveis: "A Fazer", "Em Andamento", "Concluído" |

```python
def test_kanban_widget_renderiza_colunas_padrao(qtbot, kanban_widget):
    qtbot.addWidget(kanban_widget)

    nomes_colunas = [col.nome for col in kanban_widget.column_widgets]
    assert "A Fazer" in nomes_colunas
    assert "Em Andamento" in nomes_colunas
    assert "Concluído" in nomes_colunas
```

---

#### TC-076 — Cards são renderizados nas colunas corretas

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Pré-condições** | Tasks nas colunas "A Fazer" e "Em Andamento" |
| **Passos** | Inicializar `KanbanWidget` |
| **Resultado esperado** | Cards distribuídos nas colunas corretas |

---

#### TC-077 — Não é possível excluir coluna com cards

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Pré-condições** | Coluna "A Fazer" com ao menos 1 card |
| **Passos** | Acionar exclusão da coluna "A Fazer" via menu de contexto |
| **Resultado esperado** | Aviso exibido; coluna não removida |

---

#### TC-078 — Adicionar nova coluna via botão "+"

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Passos** | Clicar em "+" no `KanbanWidget`; digitar "Revisão" no `QInputDialog` |
| **Resultado esperado** | Coluna "Revisão" aparece no board |

---

#### TC-079 — Coluna sem título não é criada

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Passos** | Acionar criação de coluna; confirmar sem digitar nome |
| **Resultado esperado** | Nenhuma coluna adicionada; nenhuma exceção |

---

### 2.10 Criação de card no Kanban (US-10)

**Arquivo(s) de teste:** `tests/test_services/test_task_service_create_in_column.py`, `tests/test_ui/test_inline_task_form.py`, `tests/test_ui/test_kanban_column_inline.py`, `tests/test_integration/test_kanban_create_card.py`.

---

#### TC-080 — `create_task_in_column` em coluna "Concluído" nasce com status CONCLUIDA

| Campo | Valor |
|-------|-------|
| **Tipo** | Unit (service) |
| **Pré-condições** | `TaskService` inicializado com banco `:memory:` |
| **Passos** | `service.create_task_in_column("X", coluna=COLUNA_CONCLUIDO)` |
| **Resultado esperado** | Task persistida com `status=CONCLUIDA`; signal `task_created` emitido 1 vez |

---

#### TC-081 — `create_task_in_column` em coluna comum nasce com status PENDENTE

| Campo | Valor |
|-------|-------|
| **Tipo** | Unit (service) |
| **Passos** | `service.create_task_in_column("X", coluna="Em Andamento")` e idem para "A Fazer" |
| **Resultado esperado** | Task persistida com `status=PENDENTE` e `coluna_kanban` correto; card entra no final (ordem estável) |

---

#### TC-082 — `InlineTaskForm` abre com foco no campo título

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Passos** | Instanciar `InlineTaskForm` e exibir via `qtbot` |
| **Resultado esperado** | `QLineEdit` de título tem `hasFocus() == True` após próximo event loop |

---

#### TC-083 — `InlineTaskForm`: `Enter` confirma e `Esc` cancela

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Passos** | Digitar título válido, pressionar `Enter`; abrir novamente e pressionar `Esc` |
| **Resultado esperado** | `Enter` → emite `submitted` com dict correto; `Esc` → emite `cancelled`; eventos não propagam para o pai |

---

#### TC-084 — `InlineTaskForm`: validações de entrada

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Passos** | (a) Confirmar com título vazio/só espaços; (b) tentar colar 250 chars no título; (c) deixar data em formato inválido |
| **Resultado esperado** | (a) `submitted` **não** emitido, form mostra erro inline; (b) título truncado para 200 (`setMaxLength`); (c) `QDateEdit` impede data inválida |

---

#### TC-085 — `InlineTaskForm`: ordem de Tab e reset após submissão

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Passos** | Pressionar Tab sequencialmente a partir do título; depois emitir `submitted` e chamar `reset()` |
| **Resultado esperado** | Ordem: título → prioridade → data → Adicionar → Cancelar; após `reset()`, campos limpos, prioridade volta a MEDIA, foco retorna ao título |

---

#### TC-086 — Rodapé "+ Adicionar card" alterna para form inline

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Passos** | Clicar no botão "+ Adicionar card" da coluna; depois cancelar |
| **Resultado esperado** | Botão some e `InlineTaskForm` aparece no rodapé; após cancelar, form some e botão reaparece; `has_inline_form_open()` reflete estado |

---

#### TC-087 — Clicar fora do form inline não o fecha

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Passos** | Abrir form em coluna A; clicar em card de outra coluna e em área vazia do board |
| **Resultado esperado** | `has_inline_form_open()` continua `True` na coluna A; conteúdo digitado preservado |

---

#### TC-088 — `KanbanColumnWidget.set_tasks` recarrega cards preservando form e atualiza contador

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Pré-condições** | Coluna com 2 cards e form inline aberto com rascunho "teste" |
| **Passos** | Chamar `col.set_tasks([t1, t2, t3])` |
| **Resultado esperado** | 3 cards renderizados; contador da coluna = 3; form inline continua aberto com texto "teste" preservado |

---

#### TC-089 — Confirmar form cria card no final da coluna e sincroniza Todo List

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração (UI+Service+DB) |
| **Passos** | Abrir form em "Em Andamento", confirmar "Nova X"; inspecionar Kanban e `TodoWidget` |
| **Resultado esperado** | Card "Nova X" aparece como último em "Em Andamento"; form permanece aberto e limpo com foco no título; `TodoWidget` lista a task via signal `task_created` |

---

#### TC-090 — Dois forms abertos simultaneamente não interferem

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Passos** | Abrir form em A com título "rascunho A"; abrir form em B com título "rascunho B"; confirmar em A |
| **Resultado esperado** | Card criado só em A; form de B segue aberto com "rascunho B" intacto; cancelar em A não afeta B |

---

#### TC-091 — Falha de persistência mantém form aberto e exibe erro

| Campo | Valor |
|-------|-------|
| **Tipo** | UI + mock service |
| **Passos** | Mockar `TaskService.create_task_in_column` para levantar exceção; confirmar form |
| **Resultado esperado** | Nenhum card adicionado; form permanece aberto com dados preservados; `show_error` exibe mensagem inline |

---

#### TC-092 — Benchmark: criação em quadro com 10k tarefas ≤ 300ms

| Campo | Valor |
|-------|-------|
| **Tipo** | Performance (`pytest.mark.slow`) |
| **Pré-condições** | Banco pré-populado com 10.000 tasks distribuídas entre 3 colunas |
| **Passos** | Medir tempo de `create_task_in_column` + atualização de UI da coluna afetada |
| **Resultado esperado** | Tempo total ≤ 300 ms; apenas a coluna alvo é repintada (set_tasks) |

> **Nota (2026-04-25):** threshold relaxado de 200ms para 300ms após DT-042 adicionar validação de `coluna_kanban` em `TaskService` (~30ms de custo adicional). O valor de 300ms mantém a garantia funcional do RNF-01 (responsividade percebida em desktop).

---

#### TC-093 — `Enter` com título vazio exibe erro e não cria card (US-10.2, cenário negativo)

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Pré-condições** | `InlineTaskForm` aberto via `qtbot`; campo título vazio |
| **Passos** | Pressionar `Enter` no campo de título sem digitar nada |
| **Resultado esperado** | Signal `submitted` **não** emitido; form exibe erro inline ("título obrigatório"); nenhum card criado; form permanece aberto |

---

#### TC-094 — Prioridade padrão ao abrir `InlineTaskForm` é MEDIA (US-10.1)

| Campo | Valor |
|-------|-------|
| **Tipo** | UI |
| **Passos** | Instanciar `InlineTaskForm` via `qtbot` sem passar parâmetros; ler valor do `QComboBox` de prioridade |
| **Resultado esperado** | Prioridade selecionada = `Prioridade.MEDIA` antes de qualquer interação do usuário |

---

> **Risco não coberto por TC (aceito formalmente):** descarte de rascunho ao perda de foco da janela para fora do Kanban (US-10.3). Comportamento dependente de evento de janela do SO (QApplication.focusChanged / windowDeactivated), difícil de testar de forma determinista em `pytest-qt`. Validação: smoke test manual no checklist de release.
>
> [DECISÃO] Não criar TC automatizado para descarte por perda de foco de janela.
> Alternativas: A) TC automatizado com mock de evento de janela | B) Apenas smoke test manual.
> Escolha: B. Por quê: custo de mock de evento de SO supera benefício; comportamento é consequência natural de não persistir rascunho — já coberto como comportamento ausente por TC-091 (dados não persistidos em falha) e pela regra de descarte documentada na spec.
> Risco aceito: regressão nesse cenário específico só seria detectada manualmente.

---

## 3. Fixtures Recomendadas (conftest.py)

**Arquivo:** `tests/conftest.py`

```python
import sqlite3
from datetime import date
import pytest
from pytestqt.qtbot import QtBot  # type: ignore

from own_board_list.database.migrations import initialize_database
from own_board_list.database.task_repository import TaskRepository
from own_board_list.database.column_repository import ColumnRepository
from own_board_list.services.task_service import TaskService
from own_board_list.models.task import Task
from own_board_list.utils.constants import Prioridade, StatusTarefa


# ---------------------------------------------------------------------------
# Banco de dados em memória (isolado por teste — escopo function)
# ---------------------------------------------------------------------------

@pytest.fixture
def db_conn():
    """
    Conexão SQLite :memory: com schema inicializado.
    Escopo 'function': cada teste recebe um banco limpo e isolado.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    initialize_database(conn)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------

@pytest.fixture
def task_repo(db_conn):
    """TaskRepository instanciado com banco em memória."""
    return TaskRepository(db_conn)


@pytest.fixture
def column_repo(db_conn):
    """ColumnRepository instanciado com banco em memória."""
    return ColumnRepository(db_conn)


# ---------------------------------------------------------------------------
# Service (requer QApplication — garantida pelo pytest-qt via qtbot)
# ---------------------------------------------------------------------------

@pytest.fixture
def task_service(qtbot: QtBot, task_repo, column_repo):
    """
    TaskService instanciado com repositórios reais em memória.
    O parâmetro 'qtbot' garante que uma QApplication existe antes do
    TaskService (que herda QObject) ser instanciado.
    """
    service = TaskService(task_repo=task_repo, column_repo=column_repo)
    return service


# ---------------------------------------------------------------------------
# Tasks de exemplo
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_task():
    """Task válida padrão para reutilização nos testes."""
    return Task(
        titulo="Tarefa de Exemplo",
        descricao="Descrição da tarefa de exemplo",
        prioridade=Prioridade.MEDIA,
    )


@pytest.fixture
def sample_tasks():
    """
    Lista de 5 tasks com variações de prioridade e status para
    testes de filtro, ordenação e busca.
    """
    return [
        Task(
            titulo="Tarefa Alta Prioridade",
            prioridade=Prioridade.ALTA,
            status=StatusTarefa.PENDENTE,
        ),
        Task(
            titulo="Tarefa Média Pendente",
            prioridade=Prioridade.MEDIA,
            status=StatusTarefa.PENDENTE,
            descricao="Descrição detalhada para busca",
        ),
        Task(
            titulo="Tarefa Baixa Concluída",
            prioridade=Prioridade.BAIXA,
            status=StatusTarefa.CONCLUIDA,
            coluna_kanban="Concluído",
        ),
        Task(
            titulo="Tarefa com Data",
            prioridade=Prioridade.MEDIA,
            data_vencimento=date(2026, 12, 31),
        ),
        Task(
            titulo="Tarefa Em Andamento",
            prioridade=Prioridade.ALTA,
            coluna_kanban="Em Andamento",
            posicao_kanban=1,
        ),
    ]


# ---------------------------------------------------------------------------
# Widgets (requerem qtbot)
# ---------------------------------------------------------------------------

@pytest.fixture
def todo_widget(qtbot: QtBot, task_service):
    """TodoWidget instanciado com service real em memória."""
    from own_board_list.ui.todo.todo_widget import TodoWidget
    widget = TodoWidget(task_service=task_service)
    qtbot.addWidget(widget)
    widget.show()
    return widget


@pytest.fixture
def kanban_widget(qtbot: QtBot, task_service, column_repo):
    """KanbanWidget instanciado com service e column_repo reais."""
    from own_board_list.ui.kanban.kanban_widget import KanbanWidget
    widget = KanbanWidget(task_service=task_service, column_repo=column_repo)
    qtbot.addWidget(widget)
    widget.show()
    return widget


@pytest.fixture
def main_window(qtbot: QtBot, db_conn):
    """
    MainWindow completa para testes E2E.
    Usa db_conn :memory: para isolamento.
    """
    from own_board_list.ui.main_window import MainWindow
    window = MainWindow(db_conn=db_conn)
    qtbot.addWidget(window)
    window.show()
    return window
```

### Configuração do pytest (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
    "-p", "no:warnings",  # remover em desenvolvimento; manter em CI
]
markers = [
    "unit: testes unitários sem dependências externas",
    "integration: testes com SQLite :memory:",
    "ui: testes de componentes Qt com qtbot",
    "e2e: testes end-to-end com MainWindow completa",
]

[tool.pytest.ini_options.qt]
# Garante execução sem display físico em CI
qt_default_raising = true
```

```bash
# Rodar apenas unitários (CI rápido)
pytest -m unit

# Rodar sem testes E2E (desenvolvimento)
pytest -m "not e2e"

# Rodar com cobertura
QT_QPA_PLATFORM=offscreen pytest --cov=src/own_board_list --cov-report=term-missing --cov-report=html
```

---

## 4. Cobertura Mínima Esperada

| Camada | Módulos | Meta | Justificativa |
|--------|---------|------|---------------|
| `models/` | `task.py`, `kanban_column.py` | **100%** | Lógica pura, zero dependências — não há desculpa para linha não testada |
| `utils/` | `constants.py` | **100%** | Apenas definições; cobertura trivial |
| `database/` | `task_repository.py`, `column_repository.py`, `migrations.py` | **90%** | Paths de erro de SQL (ex: constraint violation) são difíceis de provocar artificialmente |
| `services/` | `task_service.py`, `export_service.py` | **85%** | Caminhos de erro de I/O do export e edge cases de signal não críticos |
| `ui/` | Todos os widgets | **60%** | Drag-and-drop real e eventos de paint são difíceis de testar; cobrir lógica de slots e rendering inicial |
| **Overall** | Projeto completo | **≥ 80%** | Meta geral do projeto |

### Configuração de cobertura (`pyproject.toml`)

```toml
[tool.coverage.run]
source = ["src/own_board_list"]
omit = [
    "src/own_board_list/main.py",          # entry point — testado via E2E
    "src/own_board_list/ui/theme/*.py",    # QSS loading — testado manualmente
]

[tool.coverage.report]
fail_under = 80
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
    "@overload",
]
```

### Relatório de cobertura em HTML

```bash
QT_QPA_PLATFORM=offscreen pytest --cov=src/own_board_list --cov-report=html:htmlcov/
# Abrir: htmlcov/index.html
```

---

## 5. Checklist de Release (Smoke Tests Manuais)

Lista de verificações obrigatórias antes de cada release. Deve ser executada em todas as plataformas suportadas (Windows 10+, macOS 12+, Ubuntu 22.04+).

### 5.1 Inicialização

- [ ] Aplicativo abre sem erros ou tracebacks no terminal
- [ ] Banco de dados criado em `~/.own-board-list/data.db` na primeira execução
- [ ] Janela exibida no tamanho mínimo de 1024×768 sem conteúdo cortado
- [ ] As duas abas "Todo List" e "Kanban" estão visíveis e clicáveis
- [ ] Colunas padrão do Kanban ("A Fazer", "Em Andamento", "Concluído") presentes

### 5.2 CRUD de Tarefas (Todo List)

- [ ] `Ctrl+N` abre formulário de nova tarefa
- [ ] Botão "+ Nova Tarefa" abre formulário
- [ ] Formulário com título vazio mantém botão "Salvar" desabilitado
- [ ] Criar tarefa com todos os campos preenchidos (título, descrição, prioridade ALTA, data 2026-12-31)
- [ ] Tarefa criada aparece no topo da lista com dados corretos
- [ ] Duplo clique na tarefa abre formulário de edição preenchido
- [ ] Editar título e salvar atualiza a lista
- [ ] Cancelar edição não altera os dados originais
- [ ] Botão excluir exibe diálogo "Tem certeza?"
- [ ] Confirmar exclusão remove a tarefa da lista
- [ ] Cancelar exclusão mantém a tarefa

### 5.3 Status e Sincronização

- [ ] Clicar no checkbox marca tarefa como concluída (visual riscado/esmaecido)
- [ ] Tarefa concluída move para seção "Concluídas" na Todo List
- [ ] Tarefa concluída aparece na coluna "Concluído" do Kanban
- [ ] Desmarcar tarefa concluída reverte status para pendente
- [ ] Tarefa reaberta volta para "A Fazer" no Kanban

### 5.4 Kanban

- [ ] Cards exibem título, prioridade (cor) e data de vencimento
- [ ] Drag-and-drop de card entre colunas funciona
- [ ] Mover card para "Concluído" marca como concluída na Todo List
- [ ] Mover card de "Concluído" para outra coluna reabre a tarefa
- [ ] Botão "+ Adicionar card" em cada coluna cria task naquela coluna
- [ ] Card criado no Kanban aparece na Todo List
- [ ] Clicar em card abre painel de detalhes com todos os campos

### 5.5 Gerenciamento de Colunas

- [ ] Botão "+" cria nova coluna com nome fornecido
- [ ] Não é possível criar coluna sem nome
- [ ] Duplo clique no título da coluna permite renomear (Enter confirma, Esc cancela)
- [ ] Excluir coluna vazia funciona com confirmação
- [ ] Excluir coluna com cards exibe aviso e não exclui
- [ ] Não é possível excluir a última coluna do board
- [ ] Reordenar colunas via drag-and-drop persiste a nova ordem após reabrir

### 5.6 Filtros e Busca

- [ ] Campo de busca filtra em tempo real ao digitar
- [ ] Busca "PYTHON" encontra tarefas com "python" no título (case-insensitive)
- [ ] Busca sem resultado exibe "Nenhuma tarefa encontrada"
- [ ] Limpar campo de busca restaura todas as tarefas
- [ ] Filtro por prioridade ALTA mostra somente tarefas de alta prioridade
- [ ] Filtro combinado (prioridade + busca) aplica intersecção corretamente
- [ ] Botão "Limpar filtros" visível quando filtro ativo; limpa tudo ao clicar

### 5.7 Persistência

- [ ] Fechar e reabrir o aplicativo preserva todas as tarefas criadas
- [ ] Fechar e reabrir preserva posições dos cards no Kanban
- [ ] Fechar e reabrir preserva colunas customizadas criadas

### 5.8 Performance

- [ ] Criar 50 tarefas consecutivamente sem lentidão perceptível
- [ ] Abrir a aba com 100+ tarefas em menos de 1 segundo
- [ ] Drag-and-drop fluido sem travamentos com 20+ cards na coluna

### 5.9 Temas (quando implementado)

- [ ] Alternar para tema escuro aplica corretamente em todos os widgets
- [ ] Fechar e reabrir mantém o tema selecionado

---

## 6. Riscos de Qualidade Identificados

### Risco 1 — Sincronização de signals em threads

**Criticidade:** Alta
**Descrição:** O PyQt6 proíbe atualizações de UI fora da thread principal. Se qualquer operação de banco de dados for executada em uma `QThread` futura (para melhorar responsividade), o `task_service` deverá usar `QMetaObject.invokeMethod` ou `pyqtSignal` com `Qt.ConnectionType.QueuedConnection` para garantir que os slots de UI sejam chamados na thread correta.
**Mitigação:** Manter todo o DB no MVP na thread principal; adicionar teste específico se threading for introduzido.

---

### Risco 2 — Drag-and-drop: cálculo de posição de inserção

**Criticidade:** Alta
**Descrição:** Ao soltar um card em uma coluna, a posição de inserção deve ser calculada com base na coordenada Y do drop relativa aos cards existentes. Um cálculo errado pode causar inversão de ordem ou perda de posições. Este é o cenário mais difícil de testar automaticamente.
**Mitigação:** Testar `move_to_column()` com diferentes valores de `posicao` via testes de integração; criar testes de UI que verificam a ordem dos cards após múltiplos moves; smoke test manual obrigatório no checklist de release.

---

### Risco 3 — Coluna "Concluído" hardcoded

**Criticidade:** Alta
**Descrição:** A lógica de `move_to_column()` e `toggle_status()` depende do nome exato "Concluído" para determinar se o status deve ser `CONCLUIDA`. Se o usuário renomear essa coluna, a sincronização quebrará silenciosamente.
**Mitigação:** Usar uma flag `is_done_column: bool` na entidade `KanbanColumn` em vez de comparar pelo nome. Criar teste específico: renomear coluna "Concluído" e verificar que mover card para ela ainda atualiza o status.

---

### Risco 4 — Race condition no debounce de busca

**Criticidade:** Média
**Descrição:** O campo de busca usa `QTimer` com debounce de 300ms. Se o usuário digitar rápido e o timer disparar durante uma query SQL lenta (ex: banco com 10k tasks), pode haver inconsistência entre o texto no campo e o resultado exibido.
**Mitigação:** Cancelar o timer anterior antes de iniciar um novo; testar com `qtbot.wait(400)` após digitação rápida simulada.

---

### Risco 5 — Perda de dados em exclusão acidental

**Criticidade:** Alta
**Descrição:** A exclusão é permanente e irreversível (US-05). Um clique acidental no botão excluir, seguido de confirmação inadvertida, resulta em perda definitiva de dados.
**Mitigação:** Garantir que o diálogo de confirmação seja sempre exibido (teste TC-074); considerar funcionalidade de "desfazer" com timeout (fora do escopo do MVP, mas recomendado como melhoria); smoke test manual obrigatório.

---

### Risco 6 — Inconsistência no reorder de colunas

**Criticidade:** Média
**Descrição:** `column_repo.reorder()` recebe uma lista de IDs e atualiza as posições em uma única transação. Se a lista não contiver todos os IDs existentes, colunas omitidas podem ficar com posições duplicadas ou inválidas.
**Mitigação:** `reorder()` deve verificar que a lista contém exatamente os IDs presentes no banco; levantar `ValueError` caso contrário. Coberto pelo TC-037.

---

### Risco 7 — Múltiplas conexões ao banco em testes E2E

**Criticidade:** Baixa-Média
**Descrição:** Se `MainWindow` abrir sua própria conexão com o banco em vez de receber a `db_conn` de teste via injeção de dependência, os testes E2E apontarão para o banco real do usuário (`~/.own-board-list/data.db`), contaminando dados reais.
**Mitigação:** `MainWindow` deve aceitar `db_conn` como parâmetro opcional no construtor (injeção de dependência); testes E2E sempre passam a fixture `db_conn` em memória. Verificar no `conftest.py` que a fixture `main_window` injeta a conexão correta.

---

### Risco 8 — Vazamento de recursos Qt em testes

**Criticidade:** Baixa
**Descrição:** Widgets criados em testes mas não destruídos podem acumular, causando erros como "QWidget destroyed while pending timer events" ou crash ao final da suíte.
**Mitigação:** Sempre usar `qtbot.addWidget(widget)` para que o pytest-qt destrua os widgets automaticamente após cada teste. Nunca instanciar `QApplication` manualmente dentro de testes.

---

### Risco 9 — Cobertura ilusória de UI com mocks excessivos

**Criticidade:** Média
**Descrição:** Testes de UI que mockam o `TaskService` inteiramente podem atingir a meta de 60% de cobertura sem nunca validar o comportamento real do fluxo. Um bug na integração entre `TodoWidget` e `TaskService` passaria despercebido.
**Mitigação:** Nos testes de UI, usar o `task_service` real com banco `:memory:` (conforme definido nas fixtures). Reservar mocks apenas para dependências externas verdadeiras (ex: diálogos que precisam de interação humana, como `QFileDialog`).

---

---

## 7. Casos de Teste — DT-040 + DT-013 (Migrations e Constraints — US-011)

> TCs desta seção cobrem a feature de política de migrations e constraints de integridade do schema (spec 011-migrations-policy-schema-constraints). Adicionados em TASK-061/TASK-062/TASK-067.
> **Nota de numeração:** Os números TC-093 e TC-094 foram reutilizados por US-10 (ver seção 2.9). Os TCs desta seção (feature 011) mantêm os IDs canônicos conforme `plan.md` da spec 011 e são implementados nos arquivos de teste correspondentes — a convivência de IDs iguais é rastreada aqui e na nota da seção 2.9.

#### TC-093 — Banco novo (sem arquivo): `initialize_database` cria schema v2 direto (TASK-049, TASK-052)

**Objetivo:** Garantir que ao iniciar o aplicativo sem arquivo de banco pré-existente, `initialize_database` cria o schema diretamente na versão 2 (`SCHEMA_VERSION_ATUAL`), sem acionar backup, sem quarentena, e com todas as constraints ativas desde o primeiro uso.

**Arquivo de teste:** `tests/test_database/test_migrations.py` — classe `TestTC093BancoNovo`

**Subconjuntos cobertos:**

| Subcaso | Verificação |
|---|---|
| TC-093a | `schema_version` == `SCHEMA_VERSION_ATUAL` (2) após `initialize_database` em banco vazio |
| TC-093b | Tabelas `tasks` e `kanban_columns` existem com estrutura v2 |
| TC-093c | Colunas padrão ("A Fazer", "Em Andamento", "Concluído") presentes |
| TC-093d | Nenhum arquivo de quarentena criado |
| TC-093e | Nenhum arquivo de backup criado |

**Critérios de aceite:** todos os subcasos verdes; `MigrationReport.backup_path is None`.

**Resultado (2026-04-25):** PASS — testes verdes em `tests/test_database/test_migrations.py`.

---

#### TC-094 — Banco legado v1 válido migra para v2 sem perda (TASK-062)

**Objetivo:** Garantir que um banco v1 com dados completamente válidos migra para v2 preservando todos os registros, sem acionar quarentena, e registra a versão correta em `schema_version`.

**Arquivo de teste:** `tests/test_database/test_migrations.py` — classe `TestTC094BancoLegadoValido`

**Subconjuntos cobertos:**

| Subcaso | Verificação |
|---|---|
| TC-094a | `schema_version` == `SCHEMA_VERSION_ATUAL` após migration |
| TC-094b | Contagem de tarefas inalterada |
| TC-094c | Contagem de colunas inalterada |
| TC-094d | Títulos originais preservados |
| TC-094e | Prioridades válidas não alteradas |

**Critérios de aceite:** todos os subcasos verdes; gates OK.

**Resultado (2026-04-25):** PASS — 5 testes verdes.

---

#### TC-095 — Prioridade nula saneada para "Média" com quarentena (TASK-062)

**Objetivo:** Garantir que tarefa com `prioridade IS NULL` é saneada para `"Média"` e o registro original é preservado na quarentena com motivo `"prioridade_invalida"`.

**Arquivo de teste:** `tests/test_database/test_migrations.py` — classe `TestTC095PrioridadeNula`

**Subconjuntos cobertos:**

| Subcaso | Verificação |
|---|---|
| TC-095a | `prioridade` == `"Média"` após migration |
| TC-095b | Arquivo de quarentena criado com motivo `"prioridade_invalida"` |
| TC-095c | `saneamento_aplicado` == `{"prioridade": "Média"}` |
| TC-095d | `payload_original.prioridade` é `None` |
| TC-095e | `schema_version` == `SCHEMA_VERSION_ATUAL` após migration |

**Critérios de aceite:** todos os subcasos verdes.

**Resultado (2026-04-25):** PASS — 4 testes verdes.

---

#### TC-096 — Status desconhecido saneado para "Pendente" com quarentena (TASK-062)

**Objetivo:** Garantir que tarefa com status fora do conjunto `{"Pendente", "Concluída"}` é saneada para `"Pendente"` e registrada na quarentena com motivo `"status_invalido"`.

**Arquivo de teste:** `tests/test_database/test_migrations.py` — classe `TestTC096StatusInvalido`

**Subconjuntos cobertos:**

| Subcaso | Verificação |
|---|---|
| TC-096a | `status` == `"Pendente"` após migration |
| TC-096b | Arquivo de quarentena criado com motivo `"status_invalido"` |
| TC-096c | `payload_original.status` contém valor original (`"Fazendo"`) |
| TC-096d | `schema_version` == `SCHEMA_VERSION_ATUAL` após migration |

**Critérios de aceite:** todos os subcasos verdes.

**Resultado (2026-04-25):** PASS — 4 testes verdes.

---

#### TC-097 — Tarefa com coluna fantasma realocada para "A Fazer" (TASK-062)

**Objetivo:** Garantir que tarefa cujo `coluna_kanban` aponta para ID inexistente é realocada para a coluna `"A Fazer"` e registrada na quarentena com motivo `"coluna_inexistente"`.

**Arquivo de teste:** `tests/test_database/test_migrations.py` — classe `TestTC097ColunaFantasma`

**Subconjuntos cobertos:**

| Subcaso | Verificação |
|---|---|
| TC-097a | `coluna_kanban` aponta para o `id` da coluna `"A Fazer"` após migration |
| TC-097b | Arquivo de quarentena criado com motivo `"coluna_inexistente"` |
| TC-097c | `payload_original.coluna_kanban` contém o ID fantasma original |
| TC-097d | `saneamento_aplicado.coluna_kanban` é o ID de `"A Fazer"` |
| TC-097e | `schema_version` == `SCHEMA_VERSION_ATUAL` após migration |

**Critérios de aceite:** todos os subcasos verdes.

**Resultado (2026-04-25):** PASS — 5 testes verdes.

---

#### TC-098 — criado_em/atualizado_em nulos preenchidos com UTC (TASK-062)

**Objetivo:** Garantir que datas `NULL` em `criado_em`/`atualizado_em` são preenchidas com o timestamp UTC do momento da migration, e registradas na quarentena com observação `"data desconhecida (migrado em YYYY-MM-DD)"`.

**Arquivo de teste:** `tests/test_database/test_migrations.py` — classe `TestTC098DatasNulas`

**Subconjuntos cobertos:**

| Subcaso | Verificação |
|---|---|
| TC-098a | `criado_em` e `atualizado_em` não nulos após migration |
| TC-098b | Timestamps preenchidos são ISO válidos dentro do intervalo da migration |
| TC-098c | Arquivo de quarentena criado com motivo `"data_ausente"` |
| TC-098d | `saneamento_aplicado.observacao` contém `"data desconhecida"` e `"migrado em"` |
| TC-098e | `payload_original.criado_em` e `atualizado_em` são `None` |
| TC-098f | `schema_version` == `SCHEMA_VERSION_ATUAL` após migration |

**Critérios de aceite:** todos os subcasos verdes.

**Resultado (2026-04-25):** PASS — 6 testes verdes.

---

#### TC-099 — Versão futura gera VersaoFuturaError, arquivo intacto (TASK-062)

**Objetivo:** Garantir que banco com `schema_version > SCHEMA_VERSION_ATUAL` gera `VersaoFuturaError` com mensagem clara e não modifica o arquivo de banco.

**Arquivo de teste:** `tests/test_database/test_migrations.py` — classe `TestTC099VersaoFutura`

**Subconjuntos cobertos:**

| Subcaso | Verificação |
|---|---|
| TC-099a | `verificar_versao_futura` levanta `VersaoFuturaError` |
| TC-099b | Mensagem do erro menciona versão do banco e da aplicação |
| TC-099c | `err.versao_banco` e `err.versao_app` com valores corretos |
| TC-099d | `MigrationService.executar` retorna `sucesso=False` para versão futura |
| TC-099e | Tamanho do arquivo permanece inalterado após falha |
| TC-099f | `schema_version` do banco não é alterada após falha |

**Critérios de aceite:** todos os subcasos verdes; arquivo intacto confirmado.

**Resultado (2026-04-25):** PASS — 5 testes verdes.

---

#### TC-100 — Falha no meio da migration: rollback automático e retomada na próxima execução (TASK-056, TASK-058)

**Objetivo:** Garantir que, se a migration falhar (simulando erro SQL injetado), ocorre rollback automático da transação, o backup pré-migração permanece intacto, e uma segunda chamada a `MigrationService.executar` retoma a migration corretamente (idempotência).

**Arquivo de teste:** `tests/test_database/test_migrations.py` — classe `TestTC100FalhaMigration`

**Subconjuntos cobertos:**

| Subcaso | Verificação |
|---|---|
| TC-100a | `MigrationReport.sucesso == False` quando migration levanta exceção |
| TC-100b | Arquivo de banco permanece no tamanho pré-falha (conteúdo intacto) |
| TC-100c | Backup criado antes da falha existe e é legível |
| TC-100d | Segunda chamada a `executar` completa com `sucesso=True` |
| TC-100e | `schema_version` após retomada == `SCHEMA_VERSION_ATUAL` |

**Critérios de aceite:** todos os subcasos verdes; atomicidade garantida.

**Resultado (2026-04-25):** PASS — testes verdes em `tests/test_database/test_migrations.py`.

---

#### TC-104 — Indicador de progresso condicional no MigrationSplash (TASK-065)

**Objetivo:** Confirmar que o indicador de progresso (barra indeterminada) do `MigrationSplash` permanece oculto enquanto `show_progress()` não for chamado, e fica visível somente após essa chamada. Valida também que a barra é ocultada ao transitar para modo quarentena ou modo erro.

**Arquivo de teste:** `tests/test_ui/test_splash.py` — classe `TestTC104ProgressoCondicional`

**Subconjuntos cobertos:**

| Subcaso | Pré-condição | Ação | Resultado esperado |
|---|---|---|---|
| TC-104a | splash exibido (sem show_progress) | inspecionar `progresso_visivel` | `False` |
| TC-104b | splash exibido | chamar `show_progress("Migrando…")` | `progresso_visivel == True` |
| TC-104c | splash exibido | chamar `show_progress(msg)` | `_lbl_status.text() == msg` e não-oculto |
| TC-104d | splash exibido | inspecionar `limiar_progresso_s` | igual a `LIMIAR_PROGRESSO_MIGRACAO_S` (1,5) |
| TC-104e | splash exibido | inspecionar todos os painéis | progresso, quarentena e erro ocultos |
| TC-104f | show_progress ativo | chamar `show_quarantine_path(...)` | `progresso_visivel == False` |
| TC-104g | show_progress ativo | chamar `show_error(...)` | `progresso_visivel == False` |

**Critérios de aceite:** 7 subcasos verdes; gates ruff + mypy verdes.

**Resultado (2026-04-25):** PASS — 7 testes verdes.

---

#### TC-105 — Exibição do caminho de quarentena no MigrationSplash (TASK-065)

**Objetivo:** Confirmar que `show_quarantine_path(caminho)` exibe o painel de quarentena com o título e o caminho do arquivo corretamente, sem ativar o painel de erro nem a barra de progresso.

**Arquivo de teste:** `tests/test_ui/test_splash.py` — classe `TestTC105Quarentena`

**Subconjuntos cobertos:**

| Subcaso | Ação | Resultado esperado |
|---|---|---|
| TC-105a | `show_quarantine_path(caminho)` | `quarentena_visivel == True` |
| TC-105b | `show_quarantine_path(caminho)` | `caminho_quarentena_exibido == str(caminho)` |
| TC-105c | `show_quarantine_path(caminho)` | `_lbl_quarentena_titulo` não-oculto |
| TC-105d | `show_quarantine_path(caminho)` | `_lbl_quarentena_caminho` não-oculto |
| TC-105e | `show_quarantine_path(caminho)` | `erro_visivel == False` |
| TC-105f | `show_quarantine_path(tmp_path/...)` | caminho de `tmp_path` exibido corretamente |

**Critérios de aceite:** 6 subcasos verdes; gates ruff + mypy verdes.

**Resultado (2026-04-25):** PASS — 6 testes verdes.

---

#### TC-106 — Modo erro do MigrationSplash: mensagem, backup e botão Fechar (TASK-065)

**Objetivo:** Confirmar que `show_error(mensagem, backup_path)` exibe o painel de erro com a mensagem correta, o caminho do backup (quando fornecido), as instruções de recuperação e o botão "Fechar". Valida também que o botão fecha o widget e que o painel de backup fica oculto quando `backup_path=None`.

**Arquivo de teste:** `tests/test_ui/test_splash.py` — classe `TestTC106Erro`

**Subconjuntos cobertos:**

| Subcaso | Ação | Resultado esperado |
|---|---|---|
| TC-106a | `show_error(msg, None)` | `erro_visivel == True` |
| TC-106b | `show_error(msg, None)` | `_lbl_erro_mensagem.text() == msg` e não-oculto |
| TC-106c | antes e após `show_error` | `_btn_fechar` oculto antes, visível após |
| TC-106d | `show_error(msg, backup_path)` | `caminho_backup_exibido == str(backup_path)` e `_lbl_backup_caminho` não-oculto |
| TC-106e | `show_error(msg, None)` | `_lbl_backup_caminho` e `_lbl_backup_titulo` ocultos |
| TC-106f | `show_error(msg, None)` | `_lbl_instrucoes` não-oculto |
| TC-106g | `show_error(msg, None)` | `quarentena_visivel == False` |
| TC-106h | clicar em `_btn_fechar` | splash fecha (`isVisible() == False`) |

**Critérios de aceite:** 8 subcasos verdes; gates ruff + mypy verdes.

**Resultado (2026-04-25):** PASS — 8 testes verdes.

---

#### TC-095 — Saneamento de prioridade nula/inválida: linha em quarentena (TASK-064)

**Objetivo:** `registrar_em_quarentena` com motivo `prioridade_invalida` cria arquivo diário, preserva `payload_original` e registra `saneamento_aplicado`.

**Arquivo de teste:** `tests/test_database/test_backup_quarantine.py`

**Critérios de aceite:** arquivo de quarentena criado; `motivo == "prioridade_invalida"`; `payload_original` preservado fielmente; `saneamento_aplicado == {"prioridade": "Média"}`.

**Resultado (2026-04-25):** PASS — 2 testes verdes.

---

#### TC-096 — Saneamento de status desconhecido: linha em quarentena (TASK-064)

**Objetivo:** `registrar_em_quarentena` com motivo `status_invalido` preserva valor original e indica saneamento para "Pendente".

**Arquivo de teste:** `tests/test_database/test_backup_quarantine.py`

**Critérios de aceite:** `motivo == "status_invalido"`; `payload_original["status"]` contém valor legado; `saneamento_aplicado == {"status": "Pendente"}`.

**Resultado (2026-04-25):** PASS — 1 teste verde.

---

#### TC-097 — Saneamento de tarefa com coluna inexistente: linha em quarentena (TASK-064)

**Objetivo:** `registrar_em_quarentena` com motivo `coluna_inexistente` preserva id da coluna fantasma e indica realocação.

**Arquivo de teste:** `tests/test_database/test_backup_quarantine.py`

**Critérios de aceite:** `motivo == "coluna_inexistente"`; `payload_original["coluna_kanban"]` contém id fantasma; `saneamento_aplicado["coluna_kanban"]` contém id da coluna padrão.

**Resultado (2026-04-25):** PASS — 1 teste verde.

---

#### TC-098 — Saneamento de data ausente: linha em quarentena com observação (TASK-064)

**Objetivo:** `registrar_em_quarentena` com motivo `data_ausente` preserva `criado_em=None` e inclui observação de migração.

**Arquivo de teste:** `tests/test_database/test_backup_quarantine.py`

**Critérios de aceite:** `motivo == "data_ausente"`; `payload_original["criado_em"] is None`; `saneamento_aplicado` contém campo `observacao` com menção a "data desconhecida".

**Resultado (2026-04-25):** PASS — 1 teste verde.

---

#### TC-101 — Rotação de backup mantém apenas as 3 mais recentes (TASK-064)

**Objetivo:** `rotacionar_backups` com `manter=3` aplica política FIFO; `criar_backup` rejeita arquivo inexistente; `listar_backups` retorna lista ordenada cronologicamente pelo nome.

**Arquivo de teste:** `tests/test_database/test_backup_quarantine.py`

**Subconjuntos cobertos:**

| Subcaso | Cenário | Resultado esperado |
|---|---|---|
| TC-101a | `criar_backup` com arquivo inexistente | `FileNotFoundError` |
| TC-101b | `listar_backups` com arquivos em ordem invertida | retorna ordenados por nome |
| TC-101c | rotacionar com exatamente 3 | nenhum removido |
| TC-101d | rotacionar com 4 | mais antigo removido; restam 3 |
| TC-101e | rotacionar com 5 | 2 mais antigos removidos; restam 3 |
| TC-101f | fluxo completo: criar + rotacionar | backup novo entre os 3 restantes |

**Critérios de aceite:** 16 testes verdes (classes `TestCriarBackup`, `TestListarBackups`, `TestRotacionarBackups`).

**Resultado (2026-04-25):** PASS — 16 testes verdes.

---

#### TC-102 — Constraints SQL ativas: INSERT direto com violação via banco migrado (TASK-063)

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Arquivo** | `tests/test_database/test_sql_constraints.py` |
| **Pré-condições** | Banco legado v1 migrado para v2 via `initialize_database`; `PRAGMA foreign_keys=ON` ativo |

**Objetivo:** Verificar que o schema v2 resultante da migration real (não DDL inline) rejeita via `sqlite3.IntegrityError` todos os estados inválidos via INSERT cru.

**Subconjuntos cobertos:**

| Subcaso | Cenário | Resultado esperado |
|---|---|---|
| TC-102a | `titulo=NULL` | `IntegrityError` (NOT NULL) |
| TC-102a | `prioridade=NULL` | `IntegrityError` (NOT NULL) |
| TC-102a | `status=NULL` | `IntegrityError` (NOT NULL) |
| TC-102a | `criado_em=NULL` | `IntegrityError` (NOT NULL) |
| TC-102a | `atualizado_em=NULL` | `IntegrityError` (NOT NULL) |
| TC-102a | `nome=NULL` em kanban_columns | `IntegrityError` (NOT NULL) |
| TC-102a | `criado_em=NULL` em kanban_columns | `IntegrityError` (NOT NULL) |
| TC-102b | `status='Arquivada'` (e outros 5 valores fora do enum) | `IntegrityError` (CHECK) |
| TC-102b | `status='Pendente'` e `status='Concluída'` | aceitos (smoke positivo) |
| TC-102c | `prioridade='Urgente'` (e outros 5 fora do enum) | `IntegrityError` (CHECK) |
| TC-102c | `prioridade='Baixa'`, `'Média'`, `'Alta'` | aceitos (smoke positivo) |
| TC-102d | `posicao_kanban=-1` | `IntegrityError` (CHECK >= 0) |
| TC-102d | `posicao_kanban=0` | aceito |
| TC-102d | `posicao=-1` em kanban_columns | `IntegrityError` (CHECK >= 0) |
| TC-102e | `titulo=''` | `IntegrityError` (CHECK trim) |
| TC-102e | `titulo='   '` | `IntegrityError` (CHECK trim) |
| TC-102f | `coluna_kanban` com ID inexistente | `IntegrityError` (FK REFERENCES) |
| TC-102f | task com coluna existente | aceita |

**Critérios de aceite:** 37 testes verdes.

**Resultado (2026-04-25):** PASS — 37 testes verdes.

---

#### TC-103 — `PRAGMA foreign_key_check` retorna vazio após migration (TASK-063)

| Campo | Valor |
|-------|-------|
| **Tipo** | Integração |
| **Arquivo** | `tests/test_database/test_sql_constraints.py` (classe `TestPragmaForeignKeyCheck`) |
| **Pré-condições** | Banco legado v1 migrado para v2; `PRAGMA foreign_keys=ON` ativo |

**Objetivo:** Garantir que `PRAGMA foreign_key_check` retorna resultado vazio (sem violações) após migration v1→v2 em todos os cenários: banco recém-migrado, após insert válido, após tentativa rejeitada de violação, e para tabela `tasks` especificamente. Complementa TC-102 confirmando integridade referencial pós-migration.

**Subconjuntos cobertos:**

| Subcaso | Cenário | Resultado esperado |
|---|---|---|
| TC-103a | Banco recém-migrado sem dados extras | `PRAGMA foreign_key_check` retorna `[]` |
| TC-103b | Após insert de task válida | `PRAGMA foreign_key_check` retorna `[]` |
| TC-103c | Após tentativa rejeitada de FK violation | banco permanece íntegro; `[]` |
| TC-103d | `PRAGMA foreign_key_check(tasks)` com dados válidos | retorna `[]` |
| TC-103e | FK OFF → injetar task órfã → FK ON | `PRAGMA foreign_key_check` detecta ≥ 1 violação (valida eficácia do PRAGMA) |

**Critérios de aceite:** Inclusos nos 37 testes verdes de TC-102 (mesma suíte).

**Resultado (2026-04-25):** PASS — 5 subcasos verdes (classes `TestPragmaForeignKeyCheck`).

---

#### TC-108 — Defesa em profundidade: domínio×schema (TASK-061)

**Objetivo:** Confirmar que tanto o domínio (`Task.__post_init__`, `KanbanColumn.__post_init__`) quanto o schema SQL (constraints CHECK/NOT NULL/FK da migration v1→v2) rejeitam o mesmo conjunto de estados inválidos, independentemente do caminho de entrada.

**Arquivo de teste:** `tests/test_models/test_domain_schema_consistency.py`

**Subconjuntos cobertos:**

| Subcaso | Camada | Violação | Erro esperado |
|---|---|---|---|
| TC-108a | domínio + schema | `titulo` vazio ou apenas espaços | `ValueError` / `IntegrityError` |
| TC-108b | domínio + schema | `prioridade` inválida ou NULL | `ValueError` / `IntegrityError` |
| TC-108c | domínio + schema | `status` inválido ou NULL | `ValueError` / `IntegrityError` |
| TC-108d | domínio + schema | `posicao_kanban` negativa | `ValueError` / `IntegrityError` |
| TC-108e | domínio + schema | `nome` de coluna vazio ou apenas espaços | `ValueError` / `IntegrityError` |
| TC-108f | domínio + schema | `posicao` de coluna negativa | `ValueError` / `IntegrityError` |
| TC-108g | schema | FK `coluna_kanban` aponta para ID inexistente | `IntegrityError` |
| TC-108h | schema | Task completamente válida é inserida com sucesso | sem erro (smoke positivo) |

**Critérios de aceite:** todos os subcasos verdes em `pytest`; `ruff check`, `ruff format --check` e `mypy src/` sem erros.

**Resultado (2026-04-25):** PASS — 20 testes verdes, gates verdes.

---

#### TC-107 — Benchmark: migração de 10 000 tarefas conclui em ≤ 3 s (TASK-066)

**Objetivo:** Garantir que `MigrationService.executar` completo (backup + migration v1→v2 + validação de integridade + rotação de backups) em banco legado com 10 000 tarefas conclui dentro do threshold de 3 s, validando o critério não-funcional de performance da spec (Feature.3) e o risco documentado no plan.md.

**Arquivo de teste:** `tests/test_integration/test_migration_slow.py`

**Marcação:** `@pytest.mark.slow` — execução via `pytest -m slow`.

**Configuração do banco legado:**
- Schema v1 sem `schema_version`, sem constraints CHECK/NOT NULL/FK (estado real pré-DT-040).
- 3 colunas padrão com IDs UUID fixos.
- 10 000 tarefas distribuídas round-robin entre as 3 colunas; 10% com `prioridade=NULL` para exercitar saneamento.
- Banco em arquivo temporário (não `:memory:`) para incluir custo real de I/O.

**Subconjuntos cobertos:**

| Subcaso | Verificação | Critério |
|---|---|---|
| TC-107a | Tempo total de `MigrationService.executar` | `duracao_s ≤ 3,0 s` |
| TC-107b | `schema_version` registrada após migration | `versao == 2` |
| TC-107c | Nenhuma tarefa perdida na migration | `COUNT(*) == 10 000` |
| TC-107d | `MigrationReport.duracao_s` coerente | `0 < duracao_s < 30 s` |

**Critérios de aceite:**
- `report.sucesso == True` antes da verificação de tempo (falha de migration != falha de performance).
- `report.versao_destino == 2`.
- `report.duracao_s ≤ 3,0`.
- `COUNT(*) FROM tasks == 10 000` após migration.

**Resultado (2026-04-25):** PASS — 3 testes verdes; `duracao_s` medida dentro do threshold de 3 s.

*Fim do Plano de Testes — Own Board List v1.0*
