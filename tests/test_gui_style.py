"""Plan D Task 5: brand QSS stylesheet ships with required selectors."""

import os
from importlib import resources

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _load_qss() -> str:
    return resources.files("dxf2ifc.gui").joinpath("style.qss").read_text(encoding="utf-8")


def test_style_qss_is_loaded_via_importlib_resources():
    qss = _load_qss()
    assert qss.strip(), "style.qss is empty"


def test_style_qss_contains_brand_colors_and_fonts():
    qss = _load_qss()
    for token in ("#f59e0b", "#60a5fa", "#0f172a", "#020617"):
        assert token in qss, f"missing brand color {token}"
    for family in ("Inter", "Space Grotesk", "JetBrains Mono"):
        assert family in qss, f"missing font family {family}"


def test_style_qss_styles_required_selectors():
    qss = _load_qss()
    for selector in (
        "QMainWindow",
        'QPushButton[primary="true"]',
        'QPushButton[secondary="true"]',
        'QLabel[role="h1"]',
        'QLabel[role="h2"]',
        'QLabel[role="caption"]',
        "QStatusBar",
    ):
        assert selector in qss, f"missing selector {selector}"


def test_qapplication_accepts_style_sheet(qtbot):
    from PySide6 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    qss = _load_qss()
    app.setStyleSheet(qss)
    assert app.styleSheet() == qss
