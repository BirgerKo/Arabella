"""RenameDialog — assign a custom name to a connected fan."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
    QLineEdit, QVBoxLayout,
)

NAME_MIN = 4
NAME_MAX = 30


class RenameDialog(QDialog):
    """Input dialog that accepts a 4–30-character Unicode fan name."""

    def __init__(self, current_name: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rename Fan")
        self.setMinimumWidth(360)
        self.setModal(True)

        # ── Input row ──────────────────────────────────────────────────
        self._edit = QLineEdit(current_name)
        self._edit.setMaxLength(NAME_MAX)
        self._edit.setPlaceholderText("e.g. Living Room Fan")
        self._edit.textChanged.connect(self._on_text_changed)

        self._counter = QLabel()
        self._counter.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._counter.setMinimumWidth(50)

        input_row = QHBoxLayout()
        input_row.addWidget(self._edit, 1)
        input_row.addWidget(self._counter)

        # ── Hint ───────────────────────────────────────────────────────
        hint = QLabel(f"Name must be {NAME_MIN}–{NAME_MAX} characters (Unicode ok).")
        hint.setObjectName("HintLabel")

        # ── Buttons ────────────────────────────────────────────────────
        self._bbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        self._ok = self._bbox.button(QDialogButtonBox.StandardButton.Ok)
        self._bbox.accepted.connect(self.accept)
        self._bbox.rejected.connect(self.reject)

        # ── Layout ─────────────────────────────────────────────────────
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Fan name:"))
        layout.addLayout(input_row)
        layout.addWidget(hint)
        layout.addWidget(self._bbox)

        # Initialise counter and OK-button state
        self._on_text_changed(current_name)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def name(self) -> str:
        """The validated name (stripped).  Only call after accept()."""
        return self._edit.text().strip()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_text_changed(self, text: str) -> None:
        n = len(text.strip())
        valid = NAME_MIN <= n <= NAME_MAX

        self._counter.setText(f"{n}\u202f/\u202f{NAME_MAX}")   # narrow no-break space

        if n == 0:
            colour = "#6272a4"   # muted — nothing typed yet
        elif valid:
            colour = "#50fa7b"   # green — valid
        else:
            colour = "#ff5555"   # red — too short (or strip edge case)

        self._counter.setStyleSheet(f"color: {colour}; font-weight: bold;")
        self._ok.setEnabled(valid)
