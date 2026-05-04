"""GUI entry point: build a QApplication, apply the brand theme, show MainWindow."""

from __future__ import annotations

import ctypes
import os
import shutil
import sys
import tempfile

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

from importlib import resources

from PySide6 import QtGui, QtWidgets

from dxf2ifc.core.updater import cleanup_old_exe
from dxf2ifc.gui.main_window import MainWindow
from dxf2ifc.gui.theme import apply_theme

__all__ = ["MainWindow", "run"]


_CLI_SUBCOMMANDS = {"convert", "validate"}


def _set_app_user_model_id() -> None:
    """Tell Windows that this process is the dxf2ifc app (not python.exe).

    Without an explicit AppUserModelID, Windows groups the app under the
    PyInstaller bootloader's identity and the taskbar / Alt-Tab uses a
    generic exe icon instead of our embedded one. The string is the
    canonical Microsoft form ``CompanyName.ProductName.SubProduct.Version``
    — once registered, taskbar grouping and pin-to-taskbar use the
    correct icon and label.
    """
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Radika.dxf2ifc.kylmalaite.1"
        )
    except (AttributeError, OSError):
        pass


def cleanup_stale_meipass_dirs() -> None:
    """Sweep leftover ``_MEI***`` PyInstaller temp dirs.

    The self-update flow swaps the running exe and uses ``os._exit`` on
    the way out, which skips the bootloader's normal _MEI cleanup. The
    abandoned directory then sits in %TEMP% until something deletes it.
    On the next launch we walk %TEMP% for ``_MEI*`` dirs not tied to a
    running process and remove them. Failures are silent — Windows
    cleans up stragglers on reboot anyway.
    """
    if sys.platform != "win32":
        return
    if not getattr(sys, "frozen", False):
        return
    try:
        my_meipass = getattr(sys, "_MEIPASS", None)
        temp_root = tempfile.gettempdir()
        for entry in os.scandir(temp_root):
            if not entry.is_dir():
                continue
            if not entry.name.startswith("_MEI"):
                continue
            if my_meipass and os.path.normcase(entry.path) == os.path.normcase(my_meipass):
                continue
            try:
                shutil.rmtree(entry.path, ignore_errors=True)
            except OSError:
                pass
    except OSError:
        pass


def _load_app_icon() -> QtGui.QIcon | None:
    """Return the dxf2ifc application icon as a QIcon.

    Loads from the bundled package resource so the same call works in
    both the frozen exe (``dxf2ifc.gui/dxf2ifc.ico`` inside _MEIPASS)
    and a source checkout (``assets/dxf2ifc.ico`` via importlib).
    Falls back to the PNG when the .ico is unavailable. Returns
    ``None`` and lets Qt use the default if neither asset is present.
    """
    for filename in ("dxf2ifc.ico", "dxf2ifc.png"):
        try:
            ref = resources.files("dxf2ifc.gui").joinpath(filename)
            if ref.is_file():
                with resources.as_file(ref) as path:
                    icon = QtGui.QIcon(str(path))
                if not icon.isNull():
                    return icon
        except (FileNotFoundError, ModuleNotFoundError, OSError):
            continue
    return None


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
    cleanup_stale_meipass_dirs()

    # Must run BEFORE QApplication so the taskbar honours the icon.
    _set_app_user_model_id()

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(args)
    icon = _load_app_icon()
    if icon is not None:
        app.setWindowIcon(icon)
    apply_theme(app)
    window = MainWindow()
    if icon is not None:
        window.setWindowIcon(icon)
    window.show()
    return app.exec()
