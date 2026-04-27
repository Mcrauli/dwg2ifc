"""Plan D Task 3: dxf2ifc.gui as a runnable module + console-script entry."""

import os
from unittest.mock import patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_console_script_entrypoint_registered():
    import importlib.metadata

    eps = importlib.metadata.entry_points(group="console_scripts")
    names = {ep.name for ep in eps}
    assert "dxf2ifc-gui" in names
    target = next(ep for ep in eps if ep.name == "dxf2ifc-gui")
    assert target.value == "dxf2ifc.gui.app:run"


def test_module_main_invokes_run():
    import runpy

    with patch("dxf2ifc.gui.app.run", return_value=0) as run:
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("dxf2ifc.gui", run_name="__main__")
    run.assert_called_once()
    assert exc_info.value.code == 0
