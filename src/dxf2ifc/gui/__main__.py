"""Allow ``python -m dxf2ifc.gui`` to launch the GUI."""

from dxf2ifc.gui.app import run

if __name__ == "__main__":
    raise SystemExit(run())
