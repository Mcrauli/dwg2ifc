"""Plan D Task 1: smoke-test that PySide6 + pytest-qt are importable."""

import os


def test_pyside6_qtwidgets_import():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtWidgets

    assert hasattr(QtWidgets, "QApplication")


def test_pytest_qt_plugin_importable():
    import pytestqt  # noqa: F401
