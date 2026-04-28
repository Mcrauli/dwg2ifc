"""Background worker that wraps convert_dxf so the GUI thread stays responsive."""

from __future__ import annotations

from PySide6 import QtCore

from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.profiles.schema import Profile


class ConvertWorker(QtCore.QObject):
    finished = QtCore.Signal(str)
    failed = QtCore.Signal(str)
    report_ready = QtCore.Signal(object)

    def run(
        self,
        *,
        dxf: str,
        out: str,
        profile: Profile,
        validate: bool = False,
    ) -> None:
        runnable = _ConvertRunnable(self, dxf=dxf, out=out, profile=profile, validate=validate)
        QtCore.QThreadPool.globalInstance().start(runnable)


class _ConvertRunnable(QtCore.QRunnable):
    def __init__(
        self,
        worker: ConvertWorker,
        *,
        dxf: str,
        out: str,
        profile: Profile,
        validate: bool,
    ) -> None:
        super().__init__()
        self._worker = worker
        self._dxf = dxf
        self._out = out
        self._profile = profile
        self._validate = validate

    def run(self) -> None:  # type: ignore[override]
        try:
            _, report = convert_dxf(
                dxf_path=self._dxf,
                output_path=self._out,
                profile=self._profile,
                validate=self._validate,
            )
        except Exception as exc:  # noqa: BLE001 — surface every failure to the GUI
            self._worker.failed.emit(f"{type(exc).__name__}: {exc}")
            return
        if report is not None:
            self._worker.report_ready.emit(report)
        self._worker.finished.emit(self._out)
