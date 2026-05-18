"""Allow ``python -m dwg2ifc.gui`` to launch the GUI."""

from dwg2ifc.gui.app import run

if __name__ == "__main__":
    raise SystemExit(run())
