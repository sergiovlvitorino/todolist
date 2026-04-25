# Tasks — &lt;Nome da Feature&gt;

> **Plan:** [plan.md](plan.md)
> **Fase:** `/tasks` → artefato de entrada para `/implement`
> **Autores:** agentes `tl-python` + `qa`
> **Data:** YYYY-MM-DD

---

## Regras desta fase

- Cada task é **atômica**: um ser humano (ou `dev-python`) consegue pegar e fechar em uma sentada sem precisar de decisão arquitetural.
- **Toda task** referencia um TASK-NNN do backlog global em [docs/tasks.md](../../tasks.md). Se a task não existe lá, adicione-a antes.
- **Toda task** tem pelo menos um TC de aceite que passa ao final.
- Ordem respeita dependências (topologia).

---

## Estimativas

- **P (Pequena):** até 2 horas
- **M (Média):** 2–6 horas
- **G (Grande):** 6–16 horas — **deve ser quebrada**; tasks G não entram em `/implement`

---

## Decomposição

| # | ID | Descrição | Camada | Esforço | Depende | TC aceite |
|---|---|---|---|---|---|---|
| 1 | TASK-NNN | &lt;ação observável&gt; | models | P | — | TC-NNN |
| 2 | TASK-NNN | &lt;ação observável&gt; | database | M | #1 | TC-NNN |
| 3 | TASK-NNN | &lt;ação observável&gt; | services | P | #2 | TC-NNN |
| 4 | TASK-NNN | &lt;ação observável&gt; | ui | M | #3 | TC-NNN |

## Checklist de encerramento da feature

- [ ] Todos os TCs da spec passando
- [ ] Gates de qualidade verdes (ver [../../constitution.md §Gates](../../constitution.md#-gates-de-qualidade))
- [ ] `funcionalidades.md` marcado como implementado (se US nova ou ampliada)
- [ ] ADRs novos merged (se aplicável)
- [ ] Entrada em [CHANGELOG.md](../../../CHANGELOG.md) (se mudança perceptível ao usuário)

## Ligações

- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)
- **Backlog global:** [docs/tasks.md](../../tasks.md)
- **Plano de testes:** [docs/plano-testes.md](../../plano-testes.md)
