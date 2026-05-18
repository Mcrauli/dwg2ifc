"""Brand theme: load bundled fonts and apply the QSS stylesheet."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from PySide6 import QtGui, QtWidgets

_FONT_FILES = (
    "Inter-Regular.ttf",
    "Inter-Medium.ttf",
    "Inter-SemiBold.ttf",
    "Inter-Bold.ttf",
    "SpaceGrotesk-Medium.ttf",
    "SpaceGrotesk-Bold.ttf",
    "JetBrainsMono-Medium.ttf",
)


def _font_dir() -> Path:
    """Return a directory containing bundled TTFs.

    Wheel installs use ``dwg2ifc/gui/fonts/`` (populated via force-include).
    Editable / source checkouts fall back to ``assets/fonts/`` at the repo
    root so the GUI works straight from the source tree without a build.
    """
    here = Path(__file__).resolve()
    bundled = here.parent / "fonts"
    if (bundled / _FONT_FILES[0]).is_file():
        return bundled
    return here.parents[3] / "assets" / "fonts"


def apply_theme(app: QtWidgets.QApplication) -> None:
    font_dir = _font_dir()
    for name in _FONT_FILES:
        path = font_dir / name
        if path.is_file():
            QtGui.QFontDatabase.addApplicationFont(str(path))

    qss = resources.files("dwg2ifc.gui").joinpath("style.qss").read_text(encoding="utf-8")
    app.setStyleSheet(qss)
    app.setFont(QtGui.QFont("Inter", 10))
