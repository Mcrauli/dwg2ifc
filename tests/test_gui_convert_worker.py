"""Plan D Task 11: ConvertWorker runs convert_dxf off the GUI thread."""

import os
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_convert_worker_emits_finished_with_output_path(qtbot, tmp_path):
    from dxf2ifc.gui.convert_worker import ConvertWorker
    from dxf2ifc.profiles.loader import load_default_profile

    worker = ConvertWorker()

    out = str(tmp_path / "out.ifc")
    with patch("dxf2ifc.gui.convert_worker.convert_dxf", return_value=({}, None)) as mock_convert:
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


def test_convert_worker_emits_report_ready_when_validate_true(qtbot, tmp_path):
    from dxf2ifc.core.quality import ValidationReport
    from dxf2ifc.gui.convert_worker import ConvertWorker
    from dxf2ifc.profiles.loader import load_default_profile

    worker = ConvertWorker()
    report = ValidationReport(
        errors=[{"level": "ERROR", "message": "boom"}],
        warnings=[],
        summary="IFC4: 1 errors, 0 warnings",
    )

    out = str(tmp_path / "out.ifc")
    with patch("dxf2ifc.gui.convert_worker.convert_dxf", return_value=({}, report)) as mock_convert:
        with qtbot.waitSignal(worker.report_ready, timeout=2000) as sig:
            worker.run(
                dxf="dummy.dxf",
                out=out,
                profile=load_default_profile(),
                validate=True,
            )
    assert sig.args[0] is report
    assert mock_convert.call_args.kwargs.get("validate") is True


def test_convert_worker_does_not_emit_report_when_validate_false(qtbot, tmp_path):
    from dxf2ifc.gui.convert_worker import ConvertWorker
    from dxf2ifc.profiles.loader import load_default_profile

    worker = ConvertWorker()

    out = str(tmp_path / "out.ifc")
    with patch("dxf2ifc.gui.convert_worker.convert_dxf", return_value=({}, None)) as mock_convert:
        with qtbot.assertNotEmitted(worker.report_ready, wait=200):
            with qtbot.waitSignal(worker.finished, timeout=2000):
                worker.run(dxf="dummy.dxf", out=out, profile=load_default_profile())
    assert mock_convert.call_args.kwargs.get("validate") is False


def test_convert_worker_passes_skip_acis_through_to_convert_dxf(qtbot, tmp_path):
    """skip_acis=True must translate to preprocess_acis=False so the
    accoreconsole-launching code path is not entered."""
    from dxf2ifc.gui.convert_worker import ConvertWorker
    from dxf2ifc.profiles.loader import load_default_profile

    worker = ConvertWorker()

    out = str(tmp_path / "out.ifc")
    with patch("dxf2ifc.gui.convert_worker.convert_dxf", return_value=({}, None)) as mock_convert:
        with qtbot.waitSignal(worker.finished, timeout=2000):
            worker.run(
                dxf="dummy.dxf",
                out=out,
                profile=load_default_profile(),
                skip_acis=True,
            )
    assert mock_convert.call_args.kwargs.get("preprocess_acis") is False


def test_convert_worker_default_skip_acis_false_runs_preprocess(qtbot, tmp_path):
    from dxf2ifc.gui.convert_worker import ConvertWorker
    from dxf2ifc.profiles.loader import load_default_profile

    worker = ConvertWorker()

    out = str(tmp_path / "out.ifc")
    with patch("dxf2ifc.gui.convert_worker.convert_dxf", return_value=({}, None)) as mock_convert:
        with qtbot.waitSignal(worker.finished, timeout=2000):
            worker.run(dxf="dummy.dxf", out=out, profile=load_default_profile())
    assert mock_convert.call_args.kwargs.get("preprocess_acis") is True
