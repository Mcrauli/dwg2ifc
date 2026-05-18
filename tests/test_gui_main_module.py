"""Plan D Task 3: dwg2ifc.gui as a runnable module + console-script entry."""

import os
from unittest.mock import patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")




def test_module_main_invokes_run():
    import runpy

    with patch("dwg2ifc.gui.app.run", return_value=0) as run:
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("dwg2ifc.gui", run_name="__main__")
    run.assert_called_once()
    assert exc_info.value.code == 0
