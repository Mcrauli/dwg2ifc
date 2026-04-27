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


def test_main_window_convert_flow_updates_status_on_success(qtbot, tmp_path):
    from unittest.mock import patch

    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    panel = window.file_panel
    panel.input_edit.setText(str(tmp_path / "in.dxf"))
    panel.output_edit.setText(str(tmp_path / "out.ifc"))

    with patch("dxf2ifc.gui.convert_worker.convert_dxf", return_value={}):
        with qtbot.waitSignal(window.convert_finished, timeout=2000):
            panel.convert_button.click()

    bar = window.statusBar()
    assert "Done" in bar.currentMessage()
    assert bar.property("level") == "success"
    assert panel.convert_button.isEnabled()


def test_main_window_convert_flow_disables_button_during_run(qtbot, tmp_path):
    from unittest.mock import patch

    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    panel = window.file_panel
    panel.input_edit.setText(str(tmp_path / "in.dxf"))
    panel.output_edit.setText(str(tmp_path / "out.ifc"))

    with patch("dxf2ifc.gui.convert_worker.convert_dxf", return_value={}):
        panel.convert_button.click()
        assert not panel.convert_button.isEnabled()
        qtbot.waitUntil(lambda: panel.convert_button.isEnabled(), timeout=2000)


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
