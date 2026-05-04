"""About dialog showing version, license and the GitHub project URL."""

from __future__ import annotations

import importlib.metadata

from PySide6 import QtCore, QtWidgets


class AboutDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About dxf2ifc")
        self.setModal(True)
        version = importlib.metadata.version("dxf2ifc")
        self._summary = (
            f"<h1>dxf2ifc {version}</h1>"
            "<p>AutoCAD DXF → IFC 4 -konvertteri suomalaiseen "
            "kylmäsuunnitteluun (RAVA3Pro).</p>"
            "<p>MIT-licensed.</p>"
            '<p><a href="https://github.com/Mcrauli/dxf2ifc">'
            "https://github.com/Mcrauli/dxf2ifc</a></p>"
        )

        layout = QtWidgets.QVBoxLayout(self)
        self._label = QtWidgets.QLabel(self._summary)
        self._label.setOpenExternalLinks(True)
        self._label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        layout.addWidget(self._label)
        button = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        button.accepted.connect(self.accept)
        layout.addWidget(button)

    def findChild_text(self) -> str:  # noqa: N802 — test helper using snake_case
        return self._summary


def show_about(parent: QtWidgets.QWidget | None = None) -> AboutDialog:
    return AboutDialog(parent)
