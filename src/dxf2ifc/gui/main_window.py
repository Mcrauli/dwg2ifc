"""Top-level QMainWindow with title row, QSplitter body and status bar."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


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
        self._build_menubar()
        self.set_status("Ready")

    def _build_menubar(self) -> None:
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        self._open_action = QtGui.QAction("Open DXF…", self)
        self._open_action.triggered.connect(self._on_open_dxf)
        file_menu.addAction(self._open_action)
        file_menu.addSeparator()
        self._quit_action = QtGui.QAction("Quit", self)
        self._quit_action.triggered.connect(self.close)
        file_menu.addAction(self._quit_action)
        help_menu = menubar.addMenu("Help")
        self._about_action = QtGui.QAction("About", self)
        self._about_action.triggered.connect(self._on_about)
        help_menu.addAction(self._about_action)

    def _on_open_dxf(self) -> None:  # placeholder until Section 4 wires it up
        self.set_status("Open DXF: not implemented yet", level="info")

    def _on_about(self) -> None:
        QtWidgets.QMessageBox.about(
            self,
            "dxf2ifc",
            "<b>dxf2ifc</b><br>AutoCAD DXF → IFC 4 with Talo2000 classification.<br>"
            'MIT-licensed. <a href="https://github.com/Mcrauli/dxf2ifc">GitHub repository</a>.',
        )

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
