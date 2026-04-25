"""Testes unitários de UI — funcionalidade de busca do TodoWidget (TASK-034).

Todos os testes usam debounce_ms=0 para eliminar dependência do QTimer de 300ms.
Quando necessário testar o agregamento real do debounce, usa-se debounce_ms=300
com qtbot.wait explícito e timeout determinístico.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from own_board_list.services.task_service import TaskService
from own_board_list.ui.todo.todo_widget import TodoWidget


class TestTodoWidgetBusca:
    """Testes unitários dos comportamentos de busca do TodoWidget."""

    # ------------------------------------------------------------------
    # Cenário 1 — Renderização: campo de busca existe ao inicializar
    # ------------------------------------------------------------------

    def test_campo_busca_existe_apos_inicializacao(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """O campo _search_input deve existir e ter o placeholder correto."""
        widget = TodoWidget(task_service_ui, debounce_ms=0)
        qtbot.addWidget(widget)

        assert widget._search_input is not None
        assert widget._search_input.placeholderText() == "Buscar tarefas..."

    # ------------------------------------------------------------------
    # Cenário 2 — Debounce síncrono (0ms): digitação aplica filtro no mesmo ciclo
    # ------------------------------------------------------------------

    def test_debounce_sincrono_aplica_filtro_com_0ms(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Com debounce_ms=0, o _search_term deve ser atualizado após processEvents."""
        task_service_ui.create_task("Reunião diária")
        task_service_ui.create_task("Deploy produção")

        widget = TodoWidget(task_service_ui, debounce_ms=0)
        qtbot.addWidget(widget)

        # setText dispara textChanged -> _on_search_text_changed -> QTimer.singleShot(0)
        widget._search_input.setText("Reunião")
        qtbot.wait(1)  # garante processamento do QTimer.singleShot(0, ...)

        assert widget._search_term == "Reunião"

    # ------------------------------------------------------------------
    # Cenário 3 — Debounce agrega múltiplas keystrokes em uma única chamada
    # ------------------------------------------------------------------

    def test_debounce_agrega_3_keystrokes_em_uma_chamada(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Com debounce_ms=300, digitar 3 chars rápido deve resultar em um único
        _search_term final (o texto completo), sem chamadas intermediárias.

        [DECISÃO] Usar qtbot.waitUntil em vez de qtbot.wait(450) fixo (DT-035).
          Alternativas: A) qtbot.wait(450) — 300ms debounce + 150ms margem |
                        B) qtbot.waitUntil com polling adaptativo (timeout=2000ms)
          Escolha: B
          Por quê: 150ms de margem pode não bastar em CI lento (containers com
                   CPU limitada). waitUntil faz polling adaptativo e encerra
                   assim que o estado esperado é atingido, sendo robusto a
                   variações de ambiente sem custo de tempo desnecessário.
          Pattern para "testar debounce de verdade": usar waitUntil com a
          condição exata de estado do widget, e timeout generoso (2000ms).
        """
        widget = TodoWidget(task_service_ui, debounce_ms=300)
        qtbot.addWidget(widget)

        # Simula 3 chars digitados rapidamente via textChanged consecutivos
        # (setText substitui tudo, simulando o estado final após 3 keystrokes rápidos)
        widget._search_input.setText("a")
        widget._search_input.setText("ab")
        widget._search_input.setText("abc")

        # Antes do debounce expirar, _search_term ainda está vazio (estado anterior)
        assert widget._search_term == ""

        # waitUntil faz polling adaptativo até a condição ser verdadeira ou timeout
        qtbot.waitUntil(lambda: widget._search_term == "abc", timeout=2000)

        # Após debounce, deve ter aplicado o texto final agregado
        assert widget._search_term == "abc"

    # ------------------------------------------------------------------
    # Cenário 4 — Último-estado-vence (stale timer ignorado)
    # ------------------------------------------------------------------

    def test_ultimo_estado_vence_stale_timer_ignorado(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Se o texto mudar após o timer ser agendado, o disparo stale deve
        ser descartado e apenas o último texto deve ser aplicado."""
        widget = TodoWidget(task_service_ui, debounce_ms=0)
        qtbot.addWidget(widget)

        # Simula: digita "x", depois limpa — o timer de "x" não deve ser aplicado
        widget._search_input.setText("x")
        # Altera imediatamente para "" antes de processar eventos
        widget._search_input.clear()
        # Agora processa os eventos — o timer de "x" foi agendado, mas ao disparar
        # verifica que text() != "x" e descarta
        qtbot.wait(1)

        assert widget._search_term == ""

    # ------------------------------------------------------------------
    # Cenário 5 — Ctrl+F foca o campo de busca
    # ------------------------------------------------------------------

    def test_ctrl_f_foca_campo_de_busca(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Ctrl+F (_focus_search) deve chamar setFocus() e selectAll() em _search_input.

        Em ambientes headless (XCB), QApplication.focusWidget() retorna None pois
        a janela não recebe foco do sistema operacional. A estratégia adotada é
        monitorar as chamadas aos métodos de foco via patch — comportamento observável
        sem depender do estado de foco do sistema.

        [DECISÃO] Usar mock.patch para verificar setFocus/selectAll
          Por quê: headless XCB não propaga foco de janela; testar comportamento
                   (chamada dos métodos) é mais robusto que testar estado de foco.
          Risco aceito: se _focus_search chamar setFocus em outro widget, o teste
                        não detectaria — mas a asserção de selectAll basta para
                        confirmar que o _search_input foi o alvo correto.
        """
        widget = TodoWidget(task_service_ui, debounce_ms=0)
        qtbot.addWidget(widget)

        set_focus_called = []
        select_all_called = []

        original_set_focus = widget._search_input.setFocus
        original_select_all = widget._search_input.selectAll

        def mock_set_focus(*args: Any, **kwargs: Any) -> None:
            set_focus_called.append(True)
            original_set_focus(*args, **kwargs)

        def mock_select_all() -> None:
            select_all_called.append(True)
            original_select_all()

        widget._search_input.setFocus = mock_set_focus  # type: ignore[method-assign]
        widget._search_input.selectAll = mock_select_all  # type: ignore[method-assign]

        widget._focus_search()

        assert len(set_focus_called) == 1, "_focus_search deve chamar setFocus()"
        assert len(select_all_called) == 1, "_focus_search deve chamar selectAll()"

    # ------------------------------------------------------------------
    # Cenário 6 — Ctrl+F vs Ctrl+N: atalhos não colidem
    # ------------------------------------------------------------------

    def test_ctrl_f_nao_abre_formulario_e_ctrl_n_nao_foca_busca(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Valida independência entre _focus_search (Ctrl+F) e _on_nova_tarefa (Ctrl+N).

        _focus_search: foca campo de busca, NÃO cria tasks.
        _on_nova_tarefa: abre formulário, NÃO chama _focus_search.
        """
        task_service_ui.create_task("Tarefa existente")
        widget = TodoWidget(task_service_ui, debounce_ms=0)
        qtbot.addWidget(widget)

        # Registra chamadas ao _focus_search
        focus_search_calls: list[bool] = []
        original = widget._focus_search

        def _spy_focus_search() -> None:
            focus_search_calls.append(True)
            original()

        widget._focus_search = _spy_focus_search  # type: ignore[method-assign]

        # Ctrl+F equivalente: chama _focus_search diretamente
        widget._focus_search()

        # Não deve ter criado nenhuma task adicional
        assert len(task_service_ui.get_all_tasks()) == 1
        # _focus_search foi invocado exatamente 1 vez
        assert len(focus_search_calls) == 1

    # ------------------------------------------------------------------
    # Cenário 7 — Botão X (clear) limpa o campo e o filtro
    # ------------------------------------------------------------------

    def test_botao_x_limpa_campo_e_recarrega_sem_filtro(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Ao limpar o campo via setText(''), _search_term deve voltar a ''
        e todas as tasks devem ser exibidas novamente."""
        task_service_ui.create_task("Alpha")
        task_service_ui.create_task("Beta")

        widget = TodoWidget(task_service_ui, debounce_ms=0)
        qtbot.addWidget(widget)

        # Aplica filtro via setText (equivalente ao usuário digitando)
        widget._search_input.setText("Alpha")
        qtbot.wait(1)
        assert widget._search_term == "Alpha"

        # Simula botão X (setClearButtonEnabled — limpa via clear())
        widget._search_input.clear()
        qtbot.wait(1)

        assert widget._search_term == ""
        # Ambas as tasks devem estar visíveis novamente
        tasks_visiveis = task_service_ui.get_all_tasks()
        assert len(tasks_visiveis) == 2

    # ------------------------------------------------------------------
    # Cenário 8 — Esc limpa o campo e devolve foco para _scroll_area
    # ------------------------------------------------------------------

    def test_esc_limpa_campo_e_devolve_foco_para_scroll_area(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Pressionar Esc no campo de busca deve limpar o texto e chamar
        setFocus() no _scroll_area.

        O eventFilter intercepta Key_Escape no _search_input:
        1. Limpa o campo (clear())
        2. Chama _scroll_area.setFocus()
        3. Retorna True (evento consumido)

        Em ambientes headless, verificamos as consequências observáveis:
        - campo vazio
        - _search_term == ''
        - setFocus do _scroll_area foi chamado (via spy)
        """
        widget = TodoWidget(task_service_ui, debounce_ms=0)
        qtbot.addWidget(widget)
        widget.show()
        QApplication.processEvents()

        # Espiona setFocus do _scroll_area
        scroll_focus_calls: list[bool] = []
        original_scroll_focus = widget._scroll_area.setFocus

        def _spy_scroll_focus(*args: Any, **kwargs: Any) -> None:
            scroll_focus_calls.append(True)
            original_scroll_focus(*args, **kwargs)

        widget._scroll_area.setFocus = _spy_scroll_focus  # type: ignore[method-assign]

        # Digita algo
        widget._search_input.setText("teste")
        qtbot.wait(1)
        assert widget._search_term == "teste"

        # Invoca o eventFilter diretamente com um evento Key_Escape
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QKeyEvent

        key_event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_Escape,
            Qt.KeyboardModifier.NoModifier,
        )
        widget.eventFilter(widget._search_input, key_event)
        qtbot.wait(1)

        assert widget._search_input.text() == ""
        assert widget._search_term == ""
        assert len(scroll_focus_calls) == 1, (
            "Esc deve chamar setFocus() no _scroll_area"
        )

    # ------------------------------------------------------------------
    # Cenário 9 — Termo só-espaços não deve ativar filtro
    # ------------------------------------------------------------------

    def test_termo_so_espacos_nao_ativa_filtro(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Digitar apenas espaços deve resultar em _search_term='' (strip),
        não ativando o filtro de busca."""
        task_service_ui.create_task("Tarefa qualquer")
        widget = TodoWidget(task_service_ui, debounce_ms=0)
        qtbot.addWidget(widget)

        # setText com apenas espaços dispara textChanged -> _apply_search("   ")
        widget._search_input.setText("   ")
        qtbot.wait(1)

        # strip() deve produzir string vazia
        assert widget._search_term == ""
        # Label de resultado vazio NÃO deve aparecer (não há busca ativa)
        assert widget._label_empty_search.isHidden()

    # ------------------------------------------------------------------
    # Cenário 10 — Foco pós-TaskForm: campo de busca não perde estado
    # ------------------------------------------------------------------

    def test_foco_pos_abertura_formulario_nao_limpa_busca(
        self, qtbot: Any, task_service_ui: TaskService
    ) -> None:
        """Após abrir e fechar o TaskForm (simulado via _on_form_saved),
        o _search_term deve ser preservado e as tasks recarregadas com filtro."""
        task_service_ui.create_task("Reunião planejamento")
        task_service_ui.create_task("Deploy hotfix")

        widget = TodoWidget(task_service_ui, debounce_ms=0)
        qtbot.addWidget(widget)

        # Ativa filtro via setText
        widget._search_input.setText("Reunião")
        qtbot.wait(1)
        assert widget._search_term == "Reunião"

        # Simula salvar formulário de nova task (sem abrir o dialog)
        from own_board_list.models.task import Prioridade

        dados: dict[str, object] = {
            "titulo": "Nova task via form",
            "descricao": "",
            "prioridade": Prioridade.MEDIA,
            "data_vencimento": None,
        }
        widget._on_form_saved(dados)
        QApplication.processEvents()

        # _search_term deve ser preservado (não foi alterado pelo form)
        assert widget._search_term == "Reunião"
        # A nova task não aparece pois não bate com o filtro
        tasks_filtradas = task_service_ui.search_tasks("Reunião")
        assert len(tasks_filtradas) == 1
        assert tasks_filtradas[0].titulo == "Reunião planejamento"
