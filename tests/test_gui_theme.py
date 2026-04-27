"""Plan D Task 6: theme.apply_theme registers brand fonts and stylesheet."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_apply_theme_registers_brand_font_families(qtbot):
    from PySide6 import QtGui, QtWidgets

    from dxf2ifc.gui.theme import apply_theme

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    apply_theme(app)

    families = set(QtGui.QFontDatabase.families())
    for family in ("Inter", "Space Grotesk", "JetBrains Mono"):
        assert family in families, f"font family '{family}' not registered"


def test_apply_theme_sets_non_empty_stylesheet(qtbot):
    from PySide6 import QtWidgets

    from dxf2ifc.gui.theme import apply_theme

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    apply_theme(app)
    assert app.styleSheet().strip(), "apply_theme did not install a stylesheet"


def test_apply_theme_sets_default_inter_font(qtbot):
    from PySide6 import QtWidgets

    from dxf2ifc.gui.theme import apply_theme

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    apply_theme(app)
    assert app.font().family() == "Inter"
