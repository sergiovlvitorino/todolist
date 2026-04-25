# Spec — &lt;Nome da Feature&gt;

> **ID:** US-NN (referência em [docs/funcionalidades.md](../../funcionalidades.md))
> **Diretório:** `docs/specs/NNN-slug/`
> **Fase:** `/specify` → artefato de entrada para `/plan`
> **Autor:** agente `po`
> **Data:** YYYY-MM-DD

---

## Regras desta fase

- **Proibido mencionar tecnologia** (PyQt, SQLite, signals, tabelas, SQL, nomes de classes/arquivos). Se a spec inclui tecnologia, ela é plano, não spec.
- **Proibido prescrever solução**. Descreva o problema do usuário e o resultado observável.
- Toda ambiguidade deve virar pergunta explícita na seção **Questões em aberto**, não palpite.

---

## Contexto

<!--
Uma ou duas frases. Qual problema do usuário esta feature resolve? Qual o estado atual e por que não basta? Referencie outras US se há dependência ou continuidade.
-->

## User Stories

### US-NN.1 — &lt;Título curto&gt;

> Como &lt;papel&gt;, quero &lt;ação/resultado&gt;, para que &lt;benefício&gt;.

**Critérios de aceite:**
- [ ] Critério 1 (observável, testável, sem implementação)
- [ ] Critério 2
- [ ] ...

**Cenários negativos / erros:**
- Quando &lt;condição inválida&gt;, o sistema deve &lt;comportamento observável&gt;.

---

<!-- Repita o bloco US-NN.X para cada história desta feature. -->

## Requisitos não-funcionais específicos

<!--
Apenas RNFs que emergem desta feature e não estão na constitution. Ex: "busca deve responder em ≤ 100ms para 10k tarefas". Se o RNF já está na constitution ou em `funcionalidades.md` §RNFs, não repita aqui — apenas referencie.
-->

## Fora de escopo

<!--
Explicitamente o que NÃO é entregue nesta feature, para evitar scope creep no /plan.
-->

## Questões em aberto

<!--
Perguntas para o usuário/PO. Cada uma bloqueia /plan até ser respondida.
-->

- [ ] Pergunta 1?

## Ligações

- **Catálogo mestre:** [docs/funcionalidades.md §US-NN](../../funcionalidades.md)
- **Testes relacionados:** TC-NNN, TC-NNN (ver [docs/plano-testes.md](../../plano-testes.md))
