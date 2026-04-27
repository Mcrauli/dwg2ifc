"""Background worker that wraps convert_dxf so the GUI thread stays responsive."""

from __future__ import annotations

from PySide6 import QtCore

from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.profiles.schema import Profile


class ConvertWorker(QtCore.QObject):
    finished = QtCore.Signal(str)
    failed = QtCore.Signal(str)

    def run(self, *, dxf: str, out: str, profile: Profile) -> None:
        runnable = _ConvertRunnable(self, dxf=dxf, out=out, profile=profile)
        QtCore.QThreadPool.globalInstance().start(runnable)


class _ConvertRunnable(QtCore.QRunnable):
    def __init__(
        self,
        worker: ConvertWorker,
        *,
        dxf: str,
        out: str,
        profile: Profile,
    ) -> None:
        super().__init__()
        self._worker = worker
        self._dxf = dxf
        self._out = out
        self._profile = profile

    def run(self) -> None:  # type: ignore[override]
        try:
            convert_dxf(dxf_path=self._dxf, output_path=self._out, profile=self._profile)
        except Exception as exc:  # noqa: BLE001 — surface every failure to the GUI
            self._worker.failed.emit(f"{type(exc).__name__}: {exc}")
            return
        self._worker.finished.emit(self._out)
