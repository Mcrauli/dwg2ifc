"""GUI entry point: build a QApplication, apply the brand theme, show MainWindow."""

from __future__ import annotations

import os
import sys

# PyInstaller onefile workaround: ifcopenshell/express/__init__.py at import
# time runs `subprocess.call([sys.executable, "bootstrap.py"], cwd=express_dir)`
# whenever a sentinel `express_parser.py` is missing on disk. In a frozen exe
# `sys.executable` is dxf2ifc.exe, so this re-launches the GUI as soon as
# ifcopenshell.validate (transitively imports ifcopenshell.express) is touched.
# Pre-create an empty stub to satisfy the os.path.exists check.
if getattr(sys, "frozen", False):
    import ifcopenshell  # noqa: F401 — locate the package dir

    _express_dir = os.path.join(os.path.dirname(ifcopenshell.__file__), "express")
    os.makedirs(_express_dir, exist_ok=True)
    _stub = os.path.join(_express_dir, "express_parser.py")
    if not os.path.exists(_stub):
        try:
            open(_stub, "w").close()
        except OSError:
            pass

from PySide6 import QtWidgets

from dxf2ifc.core.updater import cleanup_old_exe
from dxf2ifc.gui.main_window import MainWindow
from dxf2ifc.gui.theme import apply_theme

__all__ = ["MainWindow", "run"]


_CLI_SUBCOMMANDS = {"convert", "validate"}


def run(argv: list[str] | None = None) -> int:
    args = list(sys.argv if argv is None else argv)

    # CLI dispatch: when the frozen exe is invoked as
    # ``dxf2ifc.exe convert <dxf> <ifc> ...`` (or any other CLI
    # subcommand) we bypass the Qt event loop and route to
    # :func:`dxf2ifc.cli.main`. Without this hop the GUI window opens
    # in the background, the convert sub-arguments get fed to
    # QApplication, and the process hangs forever on the empty event
    # loop. ``--version`` and ``--help`` flags also belong to the CLI
    # parser; reroute them too.
    if len(args) > 1 and (
        args[1] in _CLI_SUBCOMMANDS
        or args[1] in {"--version", "-V", "--help", "-h"}
    ):
        from dxf2ifc.cli import main as cli_main

        return cli_main(args[1:])

    # Best-effort cleanup of the previous exe parked by self-update.
    # Always safe to call: no-op when running from source.
    cleanup_old_exe()

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(args)
    apply_theme(app)
    window = MainWindow()
    window.show()
    return app.exec()
