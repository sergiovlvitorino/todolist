"""Diálogo de confirmação reutilizável."""

from __future__ import annotations

from PyQt6.QtWidgets import QMessageBox, QWidget


def confirm_dialog(
    parent: QWidget | None,
    title: str,
    message: str,
) -> bool:
    """Exibe um diálogo de confirmação e retorna True se o usuário confirmar."""
    reply = QMessageBox.question(
        parent,
        title,
        message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return reply == QMessageBox.StandardButton.Yes
