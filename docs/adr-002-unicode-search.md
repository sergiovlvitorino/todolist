# ADR-002 — Busca case-insensitive Unicode no SQLite via `PY_UPPER`

**Status:** Aceito
**Data:** 2026-04-19
**Autor:** Tech Lead (agente tl-python)
**Relacionado:** DT-021 (bug), ADR-001 (stack), ADR-003 (extração de enums)

---

## Contexto

A funcionalidade de busca de tarefas (`TaskRepository.search`) precisa ser **case-insensitive** e **acento-insensível-parcial** — mais precisamente, deve tratar a variação de caixa corretamente para caracteres Unicode (acentuados, cedilha, diacríticos latinos).

O SQLite, usando a configuração padrão do módulo `sqlite3` da stdlib do Python, **não** lida com isso nativamente:

- As funções SQL `UPPER()` e `LOWER()` do SQLite operam apenas sobre **ASCII**. Ex.: `UPPER('ação')` retorna `'ação'` (o `ç` e o `ã` ficam inalterados), enquanto `str.upper('ação')` em Python retorna `'AÇÃO'`.
- O operador `LIKE` é case-insensitive por padrão, mas **também** só para ASCII.
- Não há extensão ICU carregada por padrão (e exigir que o usuário tenha o SQLite compilado com ICU não é razoável para um app desktop distribuído por PyInstaller).

O sintoma foi reportado como bug em produção: buscar `"acao"` não encontrava a tarefa com título `"Ação"`.

---

## Problema

Como fazer a busca reconhecer correspondências entre strings que diferem apenas em caixa para caracteres Unicode, sem:

1. Exigir configuração especial do SQLite (compilação com ICU ou carregamento de extensão nativa);
2. Manter uma coluna "shadow" denormalizada com a versão uppercase da string (custo de migração + sincronização);
3. Carregar todas as tarefas em Python e filtrar na memória (viola o padrão Repository e não escala).

---

## Alternativas avaliadas

| Abordagem | Prós | Contras | Veredicto |
|-----------|------|---------|-----------|
| **Registrar função Python no SQLite via `create_function`** | Zero dependências extras; usa `str.upper()` que é 100% Unicode-aware; solução localizada em uma query | Função roda no Python (atravessa FFI por linha); performance cai em buscas sobre muitos registros | **Escolhido** |
| Extensão ICU do SQLite | Nativo, performante | Requer SQLite compilado com ICU; complica empacotamento PyInstaller; não portável entre plataformas | Descartado |
| Coluna "shadow" `titulo_upper`/`descricao_upper` denormalizada | Zero custo em runtime de query | Migração obrigatória; sincronização a cada UPDATE; dobra o tamanho dos índices de texto | Descartado para a escala atual; reconsiderar se volume passar de ~50k registros |
| Carregar todas e filtrar em Python | Simples | Viola o padrão Repository; carrega tudo mesmo em filtro pontual; não usa índices | Descartado |
| Biblioteca externa (ex.: `sqlite-icu`) | Delega para solução estabelecida | Nova dependência nativa; ganho não justifica para este projeto | Descartado |

---

## Decisão

Registrar uma função `PY_UPPER` na conexão SQLite que delega para `str.upper()` do Python, e usá-la na query de busca.

**Implementação:**

```python
# src/own_board_list/database/task_repository.py

def _unicode_upper(value: str | None) -> str | None:
    if value is None:
        return None
    return value.upper()


class TaskRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._conn.row_factory = sqlite3.Row
        self._conn.create_function("PY_UPPER", 1, _unicode_upper)

    def search(self, query: str) -> list[Task]:
        pattern = f"%{query.upper()}%"
        cursor = self._conn.execute(
            """
            SELECT * FROM tasks
            WHERE PY_UPPER(titulo) LIKE ? OR PY_UPPER(descricao) LIKE ?
            ORDER BY criado_em DESC
            """,
            (pattern, pattern),
        )
        return [self._row_to_task(row) for row in cursor.fetchall()]
```

A query aplica `PY_UPPER` em ambos os lados (coluna e padrão), garantindo correspondência correta independentemente da caixa original. O padrão `f"%{query.upper()}%"` também usa `str.upper()` (Python), portanto o cliente já normaliza o input.

---

## Consequências

### Positivas

- **Correção funcional:** busca por `"acao"` encontra `"Ação"`, `"café"` encontra `"CAFÉ"`, etc.
- **Zero dependências novas:** solução confinada ao `sqlite3` da stdlib.
- **Portabilidade mantida:** empacotamento PyInstaller continua trivial.
- **Testável e reversível:** troca localizada de uma função; se surgir motivo para migrar para ICU ou coluna shadow, o escopo da refatoração fica contido em `TaskRepository`.

### Negativas / Trade-offs

- **Performance em grande volume:** cada chamada de `PY_UPPER` atravessa a camada Python↔C do `sqlite3`. Para 10k registros em uma busca, é aceitável (benchmark informal: < 50ms). Para ordens de grandeza maiores, precisaríamos de índice funcional ou coluna denormalizada.
- **Sem uso de índice:** `PY_UPPER(titulo) LIKE ?` não usa o índice de `titulo` (não que tenhamos um hoje). Um índice funcional `ON tasks(PY_UPPER(titulo))` não é possível no SQLite sobre uma função definida pelo usuário (a função precisa ser determinística e registrada antes do índice — complicação que não vale a pena agora).
- **Acoplamento à conexão:** quem usa `TaskRepository.search` precisa que a função esteja registrada na conexão. Isso é feito no `__init__` do repositório, então é transparente para chamadores — mas quebraria caso alguém construa a query manualmente sem passar pelo repositório.

### Efeito colateral (tratado em ADR-003)

A primeira tentativa de implementação registrava `PY_UPPER` no `TaskService`, mas isso introduzia uma dependência circular `services → models → services` por conta de `Prioridade`/`StatusTarefa` importados em ambos os lados. A solução — extrair os enums para `models/enums.py` — virou o [ADR-003](adr-003-enums-module.md).

---

## Gatilhos para revisar

- Volume de tarefas passar de ~50k registros (performance deixa de ser aceitável).
- Necessidade de busca com **normalização de acentos** (ex.: `"acao"` casar com `"Ação"` sem o usuário digitar o acento). Hoje isso não funciona — `PY_UPPER` cuida de caixa, não de diacríticos. Se essa feature entrar, reavaliar usando `unicodedata.normalize('NFKD', s)` antes de gravar, ou coluna shadow normalizada.
- SQLite ganhar suporte nativo a `UPPER` Unicode (improvável).

---

## Referências

- [sqlite3 — `Connection.create_function`](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.create_function)
- [SQLite — The LIKE, GLOB, REGEXP, MATCH, and GLOB Operators](https://www.sqlite.org/lang_expr.html#like) (seção "The LIKE Operator" — nota sobre ASCII-only)
- DT-021 em `docs/tasks.md` (descrição original do bug e da correção)
