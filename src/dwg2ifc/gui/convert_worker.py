"""Background worker that wraps multi-floor convert() so the GUI thread stays responsive."""

from __future__ import annotations

from PySide6 import QtCore

from dwg2ifc.core.ifc_writer import convert
from dwg2ifc.core.types import FileEntry
from dwg2ifc.profiles.schema import Profile


class ConvertWorker(QtCore.QObject):
    finished = QtCore.Signal(str)
    failed = QtCore.Signal(str)
    report_ready = QtCore.Signal(object)
    progress = QtCore.Signal(str)

    def run(
        self,
        *,
        files: list[FileEntry],
        out: str,
        profile: Profile,
        validate: bool = False,
        energy_specs: str | None = None,
        magicad_ifc: str | None = None,
        reservations_only: bool = False,
    ) -> None:
        runnable = _ConvertRunnable(
            self,
            files=files,
            out=out,
            profile=profile,
            validate=validate,
            energy_specs=energy_specs,
            magicad_ifc=magicad_ifc,
            reservations_only=reservations_only,
        )
        QtCore.QThreadPool.globalInstance().start(runnable)


class _ConvertRunnable(QtCore.QRunnable):
    def __init__(
        self,
        worker: ConvertWorker,
        *,
        files: list[FileEntry],
        out: str,
        profile: Profile,
        validate: bool,
        energy_specs: str | None,
        magicad_ifc: str | None,
        reservations_only: bool,
    ) -> None:
        super().__init__()
        self._worker = worker
        self._files = files
        self._out = out
        self._profile = profile
        self._validate = validate
        self._energy_specs = energy_specs
        self._magicad_ifc = magicad_ifc
        self._reservations_only = reservations_only

    def run(self) -> None:  # type: ignore[override]
        try:
            _, report = convert(
                files=self._files,
                output_path=self._out,
                profile=self._profile,
                validate=self._validate,
                progress=self._worker.progress.emit,
                energy_specs_path=self._energy_specs or None,
                magicad_ifc_path=self._magicad_ifc or None,
                reservations_only=self._reservations_only,
            )
        except Exception as exc:  # noqa: BLE001 — surface every failure to the GUI
            self._worker.failed.emit(f"{type(exc).__name__}: {exc}")
            return
        if report is not None:
            self._worker.report_ready.emit(report)
        self._worker.finished.emit(self._out)
