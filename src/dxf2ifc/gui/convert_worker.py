"""Background worker that wraps convert_dxf so the GUI thread stays responsive."""

from __future__ import annotations

from PySide6 import QtCore

from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.profiles.schema import Profile


class ConvertWorker(QtCore.QObject):
    finished = QtCore.Signal(str)
    failed = QtCore.Signal(str)
    report_ready = QtCore.Signal(object)
    # Streaming status updates from convert_dxf — e.g. "Triangulating ACIS
    # bodies via accoreconsole…" / "ACIS extraction produced N meshes" — so
    # the GUI status bar stays informative during the headless preprocess.
    progress = QtCore.Signal(str)

    def run(
        self,
        *,
        dxf: str,
        out: str,
        profile: Profile,
        validate: bool = False,
        preprocess_acis: bool = True,
        preprocess_proxies: bool = True,
        energy_specs: str | None = None,
        floor_elevation_mm: float = 0.0,
        quick_convert: bool = False,
        magicad_ifc: str | None = None,
    ) -> None:
        # quick_convert is the user-facing knob; it overrides BOTH
        # preprocess_acis AND preprocess_proxies when True so the
        # orchestrator skips every accoreconsole-touching step
        # (typically 5–10× faster) for layer-mapping verification.
        if quick_convert:
            preprocess_acis = False
            preprocess_proxies = False
        runnable = _ConvertRunnable(
            self,
            dxf=dxf,
            out=out,
            profile=profile,
            validate=validate,
            preprocess_acis=preprocess_acis,
            preprocess_proxies=preprocess_proxies,
            energy_specs=energy_specs,
            floor_elevation_mm=floor_elevation_mm,
            magicad_ifc=magicad_ifc,
        )
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
        preprocess_acis: bool,
        preprocess_proxies: bool,
        energy_specs: str | None,
        floor_elevation_mm: float = 0.0,
        magicad_ifc: str | None = None,
    ) -> None:
        super().__init__()
        self._worker = worker
        self._dxf = dxf
        self._out = out
        self._profile = profile
        self._validate = validate
        self._preprocess_acis = preprocess_acis
        self._preprocess_proxies = preprocess_proxies
        self._energy_specs = energy_specs
        self._floor_elevation_mm = floor_elevation_mm
        self._magicad_ifc = magicad_ifc

    def run(self) -> None:  # type: ignore[override]
        try:
            _, report = convert_dxf(
                dxf_path=self._dxf,
                output_path=self._out,
                profile=self._profile,
                validate=self._validate,
                preprocess_acis=self._preprocess_acis,
                preprocess_proxies=self._preprocess_proxies,
                progress=self._worker.progress.emit,
                energy_specs_path=self._energy_specs or None,
                floor_elevation_mm=self._floor_elevation_mm,
                magicad_ifc_path=self._magicad_ifc or None,
            )
        except Exception as exc:  # noqa: BLE001 — surface every failure to the GUI
            self._worker.failed.emit(f"{type(exc).__name__}: {exc}")
            return
        if report is not None:
            self._worker.report_ready.emit(report)
        self._worker.finished.emit(self._out)
