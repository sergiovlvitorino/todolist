# Plan — &lt;Nome da Feature&gt;

> **Spec:** [spec.md](spec.md)
> **Fase:** `/plan` → artefato de entrada para `/tasks`
> **Autor:** agente `tl-python`
> **Data:** YYYY-MM-DD

---

## Regras desta fase

- **Constitution é lei.** Antes de propor qualquer decisão, valide contra [../../constitution.md](../../constitution.md). Violação de princípio 🔒 requer ADR novo **e aprovação explícita do usuário**.
- **Sem código**. Contratos (assinaturas, shapes de dados) são permitidos; implementação não.
- **Toda decisão de arquitetura reversível vai aqui**; decisões irreversíveis ou que afetam todo o projeto vão em ADR global (`docs/adr-NNN-*.md`).

---

## Resumo técnico

<!-- 2-3 frases. Qual a estratégia de implementação em alto nível? -->

## Camadas afetadas

Marque e justifique só as camadas impactadas. Layering `utils → models → database → services → ui` deve ser preservado.

| Camada | Muda? | Natureza da mudança |
|---|---|---|
| `utils/` | sim/não | &lt;ex.: nova constante `X`; nenhuma&gt; |
| `models/` | sim/não | &lt;novo campo, novo dataclass, nova validação&gt; |
| `database/` | sim/não | &lt;migração, nova query, novo repositório&gt; |
| `services/` | sim/não | &lt;novo signal, nova operação, nova validação&gt; |
| `ui/` | sim/não | &lt;novo widget, novo campo em form, novo atalho&gt; |

## Contratos

Assinaturas de novas funções/classes ou mudanças em existentes (sem corpo):

```python
# exemplo
class TaskRepository:
    def buscar_por_texto(self, termo: str) -> list[Task]: ...
```

## Migração de dados / schema

<!-- Omita se não aplicável. Detalhe passos, reversibilidade e impacto em dados existentes. -->

## ADRs novos necessários

- [ ] ADR-NNN — &lt;título&gt; — &lt;uma frase explicando por que precisa de ADR próprio&gt;

Se nenhum ADR novo é necessário, escreva "Nenhum" e por quê.

## Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
|  |  |  |  |

## Plano de testes

Traga do `qa` (pair) os TCs a criar ou ampliar. Cada task de `/implement` deve fechar com ao menos um TC.

- [ ] TC-NNN — &lt;descrição curta&gt; (unit/integração/UI)

## Dependências

- Tasks bloqueantes no backlog global: TASK-NNN, DT-NNN
- Features: US-NN

## Ligações

- **Constitution:** [../../constitution.md](../../constitution.md)
- **ADRs relevantes:** [ADR-NNN](../../adr-NNN-*.md)
- **Backlog global:** [docs/tasks.md](../../tasks.md)
