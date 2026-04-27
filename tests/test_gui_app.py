"""Plan D Task 2: gui.app.run + placeholder MainWindow opens via qtbot."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_main_window_opens_with_expected_title(qtbot):
    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert window.windowTitle() == "dxf2ifc"


def test_run_is_callable():
    from dxf2ifc.gui.app import run

    assert callable(run)
