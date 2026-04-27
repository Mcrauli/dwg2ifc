"""GUI entry point: build a QApplication and show the placeholder MainWindow."""

from __future__ import annotations

import sys

from PySide6 import QtWidgets


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("dxf2ifc")
        self.resize(900, 600)


def run(argv: list[str] | None = None) -> int:
    args = sys.argv if argv is None else argv
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(args)
    window = MainWindow()
    window.show()
    return app.exec()
