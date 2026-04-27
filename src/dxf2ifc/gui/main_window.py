"""Top-level QMainWindow with title row, QSplitter body and status bar."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("dxf2ifc")
        self.resize(1100, 700)

        central = QtWidgets.QWidget(self)
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 0)
        root.setSpacing(12)

        title = QtWidgets.QLabel("dxf2ifc")
        title.setProperty("role", "h1")
        caption = QtWidgets.QLabel("AutoCAD DXF → IFC 4 with Talo2000 classification")
        caption.setProperty("role", "caption")
        root.addWidget(title)
        root.addWidget(caption)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.setObjectName("body_splitter")
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter, stretch=1)

        self.setCentralWidget(central)
        self.setStatusBar(QtWidgets.QStatusBar(self))
        self.set_status("Ready")

    def set_status(self, text: str, *, level: str = "info") -> None:
        bar = self.statusBar()
        bar.showMessage(text)
        bar.setProperty("level", level)
        bar.style().unpolish(bar)
        bar.style().polish(bar)

    def _build_left_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 12, 16)
        placeholder = QtWidgets.QLabel("Files & profile")
        placeholder.setProperty("role", "h2")
        layout.addWidget(placeholder)
        layout.addStretch(1)
        return panel

    def _build_right_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(12, 8, 0, 16)
        placeholder = QtWidgets.QLabel("Preview & log")
        placeholder.setProperty("role", "h2")
        layout.addWidget(placeholder)
        layout.addStretch(1)
        return panel
