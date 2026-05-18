"""About dialog showing version, license and the GitHub project URL."""

from __future__ import annotations

import importlib.metadata

from PySide6 import QtCore, QtWidgets


class AboutDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About dwg2ifc")
        self.setModal(True)
        version = importlib.metadata.version("dwg2ifc")
        self._summary = (
            f"<h1>dwg2ifc {version}</h1>"
            "<p>AutoCAD DWG/DXF → IFC 4 -konvertteri suomalaiseen "
            "kylmäsuunnitteluun (RAVA3Pro).</p>"
            '<p><a href="https://mcrauli.github.io/autocad-lisp-ohjeet/dwg2ifc.html">'
            "Käyttöohjeet ja lataukset</a></p>"
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
