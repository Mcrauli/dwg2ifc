"""Read-only preview & log panel that renders DXF summaries and Convert progress.

The panel is wired into :class:`MainWindow`'s right pane so the user gets
immediate feedback after an Open DXF (entity / layer summary) or a
Convert run (per-layer mappings + completion / error). The body uses
JetBrains Mono so column alignment in summaries reads cleanly.
"""

from __future__ import annotations

from pathlib import Path

from PySide6 import QtGui, QtWidgets

_INFO_COLOR = "#cbd5f5"
_SUCCESS_COLOR = "#22c55e"
_ERROR_COLOR = "#ef4444"


class PreviewLogPanel(QtWidgets.QTextEdit):
    """A read-only QTextEdit specialised as a colour-coded log viewer."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setObjectName("preview_log")
        font = QtGui.QFont("JetBrains Mono")
        font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        font.setPointSize(10)
        self.setFont(font)

    def text(self) -> str:
        return self.toPlainText()

    def append_info(self, text: str) -> None:
        self._append(text, _INFO_COLOR)

    def append_success(self, text: str) -> None:
        self._append(text, _SUCCESS_COLOR)

    def append_error(self, text: str) -> None:
        self._append(text, _ERROR_COLOR)

    def set_dxf_summary(
        self,
        *,
        path: str,
        entity_count: int,
        layer_counts: dict[str, int],
    ) -> None:
        """Render a multi-line summary for a freshly opened DXF."""
        name = Path(path).name
        self.append_info(
            f"Loaded {name}: {entity_count} entities across {len(layer_counts)} layers"
        )
        for layer in sorted(layer_counts):
            self.append_info(f"  {layer:<24} {layer_counts[layer]:>4}")

    def _append(self, text: str, color: str) -> None:
        self.setTextColor(QtGui.QColor(color))
        self.append(text)
