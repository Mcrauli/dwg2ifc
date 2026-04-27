"""Plan D Task 2: gui.app.run + placeholder MainWindow opens via qtbot."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_main_window_opens_with_expected_title(qtbot):
    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert window.windowTitle() == "dxf2ifc"


def test_main_window_has_splitter_layout_and_status_bar(qtbot):
    from PySide6 import QtWidgets

    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    splitter = window.findChild(QtWidgets.QSplitter)
    assert splitter is not None
    assert splitter.count() == 2
    assert window.statusBar() is not None


def _menu_action_texts(window) -> list[str]:
    texts: list[str] = []
    for menu_action in window.menuBar().actions():
        menu = menu_action.menu()
        if menu is None:
            continue
        for action in menu.actions():
            if action.isSeparator():
                continue
            text = action.text()
            if text:
                texts.append(text)
    return texts


def test_main_window_menubar_has_expected_actions(qtbot):
    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    texts = _menu_action_texts(window)
    assert "Open DXF…" in texts
    assert "Quit" in texts
    assert "About" in texts


def test_main_window_quit_action_closes_window(qtbot):
    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window._quit_action.trigger()
    assert not window.isVisible()


def test_main_window_set_status_levels(qtbot):
    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    bar = window.statusBar()

    window.set_status("Converting…")
    assert bar.currentMessage() == "Converting…"
    assert bar.property("level") == "info"

    window.set_status("Done", level="success")
    assert bar.currentMessage() == "Done"
    assert bar.property("level") == "success"

    window.set_status("Boom", level="error")
    assert bar.currentMessage() == "Boom"
    assert bar.property("level") == "error"


def test_main_window_renders_h1_and_caption_labels(qtbot):
    from PySide6 import QtWidgets

    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    labels = window.findChildren(QtWidgets.QLabel)
    h1 = next((lbl for lbl in labels if lbl.property("role") == "h1"), None)
    caption = next((lbl for lbl in labels if lbl.property("role") == "caption"), None)
    assert h1 is not None and h1.text() == "dxf2ifc"
    assert caption is not None and "DXF" in caption.text()


def test_run_is_callable():
    from dxf2ifc.gui.app import run

    assert callable(run)
