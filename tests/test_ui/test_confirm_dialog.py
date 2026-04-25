"""Testes do diálogo de confirmação (confirm_dialog)."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from own_board_list.ui.dialogs.confirm_dialog import confirm_dialog


class TestConfirmDialog:
    """Testes do diálogo de confirmação reutilizável."""

    def test_retorna_true_quando_usuario_confirma(self, qtbot: Any) -> None:
        """Deve retornar True quando o usuário clica em 'Sim'."""
        from PyQt6.QtWidgets import QMessageBox

        with patch.object(
            QMessageBox,
            "question",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            result = confirm_dialog(None, "Confirmar", "Tem certeza?")
            assert result is True

    def test_retorna_false_quando_usuario_cancela(self, qtbot: Any) -> None:
        """Deve retornar False quando o usuário clica em 'Não'."""
        from PyQt6.QtWidgets import QMessageBox

        with patch.object(
            QMessageBox,
            "question",
            return_value=QMessageBox.StandardButton.No,
        ):
            result = confirm_dialog(None, "Confirmar", "Tem certeza?")
            assert result is False

    def test_chama_question_com_parametros_corretos(self, qtbot: Any) -> None:
        """Deve chamar QMessageBox.question com título e mensagem corretos."""
        from PyQt6.QtWidgets import QMessageBox

        with patch.object(
            QMessageBox,
            "question",
            return_value=QMessageBox.StandardButton.No,
        ) as mock_question:
            confirm_dialog(None, "Meu Título", "Minha Mensagem")

            mock_question.assert_called_once()
            args = mock_question.call_args[0]
            assert args[1] == "Meu Título"
            assert args[2] == "Minha Mensagem"

    def test_botao_padrao_e_no(self, qtbot: Any) -> None:
        """O botão padrão deve ser 'No' (confirmação explícita necessária)."""
        from PyQt6.QtWidgets import QMessageBox

        with patch.object(
            QMessageBox,
            "question",
            return_value=QMessageBox.StandardButton.No,
        ) as mock_question:
            confirm_dialog(None, "Título", "Mensagem")

            args = mock_question.call_args[0]
            # O quinto argumento é o botão padrão
            assert args[4] == QMessageBox.StandardButton.No
