"""Plan D Task 11: ConvertWorker runs convert_dxf off the GUI thread."""

import os
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_convert_worker_emits_finished_with_output_path(qtbot, tmp_path):
    from dxf2ifc.gui.convert_worker import ConvertWorker
    from dxf2ifc.profiles.loader import load_default_profile

    worker = ConvertWorker()

    out = str(tmp_path / "out.ifc")
    with patch("dxf2ifc.gui.convert_worker.convert_dxf", return_value={}) as mock_convert:
        with qtbot.waitSignal(worker.finished, timeout=2000) as sig:
            worker.run(dxf="dummy.dxf", out=out, profile=load_default_profile())
    assert sig.args == [out]
    mock_convert.assert_called_once()


def test_convert_worker_emits_failed_on_exception(qtbot, tmp_path):
    from dxf2ifc.gui.convert_worker import ConvertWorker
    from dxf2ifc.profiles.loader import load_default_profile

    worker = ConvertWorker()

    def boom(**kwargs):
        raise RuntimeError("boom")

    with patch("dxf2ifc.gui.convert_worker.convert_dxf", side_effect=boom):
        with qtbot.waitSignal(worker.failed, timeout=2000) as sig:
            worker.run(
                dxf="dummy.dxf",
                out=str(tmp_path / "out.ifc"),
                profile=load_default_profile(),
            )
    assert "boom" in sig.args[0]
