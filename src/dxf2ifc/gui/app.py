"""GUI entry point: build a QApplication, apply the brand theme, show MainWindow."""

from __future__ import annotations

import sys

from PySide6 import QtWidgets

from dxf2ifc.gui.main_window import MainWindow
from dxf2ifc.gui.theme import apply_theme

__all__ = ["MainWindow", "run"]


def run(argv: list[str] | None = None) -> int:
    args = sys.argv if argv is None else argv
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(args)
    apply_theme(app)
    window = MainWindow()
    window.show()
    return app.exec()
