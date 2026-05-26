"""ConvertWorker runs the multi-floor convert() off the GUI thread."""

import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dwg2ifc.core.types import FileEntry


def _one_floor(tmp_path) -> list[FileEntry]:
    return [FileEntry(path=Path(tmp_path) / "1krs.dwg", floor_label="1.krs", elevation_mm=0.0)]


def test_convert_worker_emits_finished_with_output_path(qtbot, tmp_path):
    from dwg2ifc.gui.convert_worker import ConvertWorker
    from dwg2ifc.profiles.loader import load_default_profile

    worker = ConvertWorker()
    out = str(tmp_path / "out.ifc")
    with patch("dwg2ifc.gui.convert_worker.convert", return_value=({}, None)) as mock_convert:
        with qtbot.waitSignal(worker.finished, timeout=2000) as sig:
            worker.run(files=_one_floor(tmp_path), out=out, profile=load_default_profile())
    assert sig.args == [out]
    mock_convert.assert_called_once()


def test_convert_worker_emits_failed_on_exception(qtbot, tmp_path):
    from dwg2ifc.gui.convert_worker import ConvertWorker
    from dwg2ifc.profiles.loader import load_default_profile

    worker = ConvertWorker()

    def boom(**kwargs):
        raise RuntimeError("boom")

    with patch("dwg2ifc.gui.convert_worker.convert", side_effect=boom):
        with qtbot.waitSignal(worker.failed, timeout=2000) as sig:
            worker.run(
                files=_one_floor(tmp_path),
                out=str(tmp_path / "out.ifc"),
                profile=load_default_profile(),
            )
    assert "boom" in sig.args[0]


def test_convert_worker_emits_report_ready_when_validate_true(qtbot, tmp_path):
    from dwg2ifc.core.quality import ValidationReport
    from dwg2ifc.gui.convert_worker import ConvertWorker
    from dwg2ifc.profiles.loader import load_default_profile

    worker = ConvertWorker()
    report = ValidationReport(
        errors=[{"level": "ERROR", "message": "boom"}],
        warnings=[],
        summary="IFC4: 1 errors, 0 warnings",
    )

    out = str(tmp_path / "out.ifc")
    with patch("dwg2ifc.gui.convert_worker.convert", return_value=({}, report)) as mock_convert:
        with qtbot.waitSignal(worker.report_ready, timeout=2000) as sig:
            worker.run(
                files=_one_floor(tmp_path),
                out=out,
                profile=load_default_profile(),
                validate=True,
            )
    assert sig.args[0] is report
    assert mock_convert.call_args.kwargs.get("validate") is True


def test_convert_worker_does_not_emit_report_when_validate_false(qtbot, tmp_path):
    from dwg2ifc.gui.convert_worker import ConvertWorker
    from dwg2ifc.profiles.loader import load_default_profile

    worker = ConvertWorker()

    out = str(tmp_path / "out.ifc")
    with patch("dwg2ifc.gui.convert_worker.convert", return_value=({}, None)) as mock_convert:
        with qtbot.assertNotEmitted(worker.report_ready, wait=200):
            with qtbot.waitSignal(worker.finished, timeout=2000):
                worker.run(files=_one_floor(tmp_path), out=out, profile=load_default_profile())
    assert mock_convert.call_args.kwargs.get("validate") is False


def test_convert_worker_passes_reservations_only_to_convert(qtbot, tmp_path):
    from dwg2ifc.gui.convert_worker import ConvertWorker
    from dwg2ifc.profiles.loader import load_default_profile

    worker = ConvertWorker()
    out = str(tmp_path / "out.ifc")
    with patch("dwg2ifc.gui.convert_worker.convert", return_value=({}, None)) as mock_convert:
        with qtbot.waitSignal(worker.finished, timeout=2000):
            worker.run(
                files=_one_floor(tmp_path),
                out=out,
                profile=load_default_profile(),
                reservations_only=True,
            )
    assert mock_convert.call_args.kwargs.get("reservations_only") is True
