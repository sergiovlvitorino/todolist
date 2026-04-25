# ADR-003 — Extração de enums de domínio para `models/enums.py`

**Status:** Aceito
**Data:** 2026-04-19
**Autor:** Tech Lead (agente tl-python)
**Relacionado:** ADR-002 (bug que tornou o problema visível), DT-021

---

## Contexto

Os enums `Prioridade` e `StatusTarefa` foram originalmente definidos em `src/own_board_list/models/task.py`, junto com a dataclass `Task`. Essa organização era razoável enquanto os enums eram usados apenas dentro da camada de domínio.

Com a introdução de `src/own_board_list/utils/constants.py` (concluindo DT-009 e centralizando `COLUNA_*`, `TITULO_MAX_LEN` e o mapeamento `COR_PRIORIDADE`), o módulo `utils/constants.py` passou a precisar do enum `Prioridade` para tipar a chave do dicionário `COR_PRIORIDADE: dict[Prioridade, str]`.

Simultaneamente, `models/task.py` já importa `COLUNA_PADRAO` de `utils/constants.py`. Isso fechou um **ciclo de importação**:

```
utils/constants.py ──► models/task.py ──► utils/constants.py
                          (Prioridade)       (COLUNA_PADRAO)
```

O ciclo se manifestou ao implementar ADR-002 (busca Unicode) porque `services/task_service.py` precisava de `Prioridade` e `StatusTarefa`, que eram reexportados de `task.py`, aumentando a superfície de importações e tornando o ciclo mais frágil.

---

## Problema

Resolver a dependência circular entre `utils/constants.py` e `models/task.py` sem:

1. Duplicar a definição dos enums em dois lugares (violaria DRY);
2. Mover constantes de UI (`COR_PRIORIDADE`) para dentro de `models/` (viola a separação de camadas — `models/` não deve conhecer questões de apresentação);
3. Usar imports locais dentro de funções (workaround que esconde a dependência e polui cada função).

---

## Alternativas avaliadas

| Abordagem | Prós | Contras | Veredicto |
|-----------|------|---------|-----------|
| **Extrair enums para `models/enums.py` (módulo folha sem imports internos)** | Quebra o ciclo de forma estrutural; enums ficam em local canônico; compatibilidade mantida via re-export em `models/task.py` | Novo arquivo (overhead mínimo); precisa atualizar alguns imports | **Escolhido** |
| Mover `COR_PRIORIDADE` para `ui/` (ex.: `ui/styles.py`) | Elimina a dependência de `constants.py` em `Prioridade` | `COR_PRIORIDADE` é conceito transversal (pode ser usado em export/relatórios futuros); quebra a ideia de `utils/constants.py` como hub único | Descartado |
| Import local (lazy) dentro de `constants.py` | Quebra o ciclo sem criar arquivo | Cada acesso paga custo; imports locais são anti-pattern e mascaram a estrutura real | Descartado |
| Duplicar enums em `constants.py` | Zero import entre os dois | Viola DRY; abre espaço para divergência silenciosa; dois tipos `Prioridade` incompatíveis | Descartado |
| Inverter a dependência (constantes em `models/`) | Simples | Mistura preocupações de camadas (`models` deixaria de ser folha) | Descartado |

---

## Decisão

Criar um **módulo folha** `src/own_board_list/models/enums.py` contendo apenas as definições dos enums, sem nenhuma importação interna do projeto.

**Implementação:**

```python
# src/own_board_list/models/enums.py
from __future__ import annotations
from enum import StrEnum


class Prioridade(StrEnum):
    BAIXA = "Baixa"
    MEDIA = "Média"
    ALTA = "Alta"


class StatusTarefa(StrEnum):
    PENDENTE = "Pendente"
    CONCLUIDA = "Concluída"
```

```python
# src/own_board_list/models/task.py
from own_board_list.models.enums import Prioridade as Prioridade
from own_board_list.models.enums import StatusTarefa as StatusTarefa
# ... resto do módulo
```

```python
# src/own_board_list/utils/constants.py
from own_board_list.models.enums import Prioridade
# ... usa Prioridade no type hint de COR_PRIORIDADE
```

O grafo de dependência passa a ser acíclico:

```
models/enums.py   (folha — sem imports do projeto)
   ▲        ▲
   │        │
   │    utils/constants.py
   │        ▲
   │        │
models/task.py ───────────┐
                          │
                  database/*, services/*, ui/*
```

O re-export em `models/task.py` (`from ... import Prioridade as Prioridade`) preserva a **compatibilidade**: código existente que faz `from own_board_list.models.task import Prioridade` continua funcionando. Novos imports devem preferir `from own_board_list.models.enums import ...` ou `from own_board_list.models import ...` (via `__init__.py`).

---

## Consequências

### Positivas

- **Ciclo eliminado estruturalmente**, não mascarado. Qualquer novo módulo pode importar `utils/constants.py` ou `models/enums.py` livremente.
- **Separação clara de camadas:** `enums.py` é a camada mais baixa do domínio; tudo mais depende dele, ele não depende de nada.
- **Compatibilidade retroativa:** imports antigos funcionam por re-export.
- **Padrão replicável:** se surgirem novos enums de domínio (ex.: `TipoVisualizacao`, `TemaUI`), seguem o mesmo lugar.

### Negativas

- Um novo arquivo pequeno (~15 linhas) — trade-off mínimo.
- Desenvolvedores precisam estar cientes de que a localização canônica dos enums é `models/enums.py`. Mitigação: docstring do módulo explica; ADR registra.

### Riscos

- Nenhum identificado. A mudança é localmente segura; `mypy --strict` e a suíte de testes (234 casos) validam que nenhuma semântica foi alterada.

---

## Convenção resultante

- **Módulos folha** do projeto (sem imports internos): `models/enums.py`.
- Qualquer outro módulo novo que precise ser importado por `utils/` deve ser folha ou depender apenas de folhas.
- Se um novo ciclo aparecer, a primeira pergunta deve ser: "que tipo de dado eu preciso isolar como folha?" antes de recorrer a imports locais.

---

## Referências

- PEP 328 (absolute imports)
- `docs/tasks.md` §DT-021 (contexto da descoberta)
- `docs/adr-002-unicode-search.md` (feature cuja implementação expôs o ciclo)
