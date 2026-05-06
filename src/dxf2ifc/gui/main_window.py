"""Top-level QMainWindow with title row, QSplitter body and status bar."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from pathlib import Path

from collections import Counter

from dxf2ifc import __version__
from dxf2ifc.core.dxf_reader import list_layers
from dxf2ifc.gui.convert_worker import ConvertWorker
from dxf2ifc.gui.file_panel import FilePanel
from dxf2ifc.gui.layer_table import LayerTable
from dxf2ifc.gui.preview_log import PreviewLogPanel
from dxf2ifc.gui.recent_files import RecentFilesStore
from dxf2ifc.gui.update_banner import (
    UpdateBanner,
    UpdateChecker,
    perform_update,
)
from dxf2ifc.profiles.loader import load_default_profile, load_profile


class MainWindow(QtWidgets.QMainWindow):
    convert_finished = QtCore.Signal(str)
    convert_failed = QtCore.Signal(str)

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        *,
        recent_files: RecentFilesStore | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("dxf2ifc")
        self.resize(1100, 700)
        self._recent_files = recent_files or RecentFilesStore()
        self._profile = self._load_initial_profile()
        self._worker = ConvertWorker(self)
        self._worker.finished.connect(self._on_convert_finished)
        self._worker.failed.connect(self._on_convert_failed)
        self._worker.report_ready.connect(self._on_report_ready)
        # Status updates emitted by the AutoCAD COM preprocessing path during
        # its 10–25 s cold start — surface them in both the status bar and
        # the preview log so the user knows the app isn't frozen.
        self._worker.progress.connect(self._on_convert_progress)

        central = QtWidgets.QWidget(self)
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 0)
        root.setSpacing(12)

        title = QtWidgets.QLabel("dxf2ifc")
        title.setProperty("role", "h1")
        caption = QtWidgets.QLabel("AutoCAD DXF → IFC 4 kylmäsuunnitteluun (RAVA3Pro)")
        caption.setProperty("role", "caption")
        root.addWidget(title)
        root.addWidget(caption)

        self._update_banner = UpdateBanner(self)
        self._update_banner.update_requested.connect(self._on_update_requested)
        root.addWidget(self._update_banner)
        self._update_checker = UpdateChecker(self)
        self._update_checker.result.connect(self._on_update_check_done)
        # Defer the network call until the window is on screen — there's no
        # value in slowing down first paint for a background poll.
        QtCore.QTimer.singleShot(500, self._update_checker.start)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.setObjectName("body_splitter")
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter, stretch=1)

        self.setCentralWidget(central)
        self.setStatusBar(QtWidgets.QStatusBar(self))
        self._version_label = QtWidgets.QLabel(f"v{__version__}")
        self._version_label.setProperty("role", "version_badge")
        self.statusBar().addPermanentWidget(self._version_label)
        self._build_menubar()
        self.set_status("Ready")

    def _build_menubar(self) -> None:
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        self._open_action = QtGui.QAction("Open DXF…", self)
        self._open_action.triggered.connect(self._on_open_dxf)
        file_menu.addAction(self._open_action)
        file_menu.addSeparator()
        self._quit_action = QtGui.QAction("Quit", self)
        self._quit_action.triggered.connect(self.close)
        file_menu.addAction(self._quit_action)
        profile_menu = menubar.addMenu("Profile")
        self._edit_profile_action = QtGui.QAction("Edit profile…", self)
        self._edit_profile_action.triggered.connect(self._on_edit_profile)
        profile_menu.addAction(self._edit_profile_action)
        profile_menu.addSeparator()
        self._reset_profile_action = QtGui.QAction("Reset to bundled default", self)
        self._reset_profile_action.triggered.connect(self._on_reset_profile)
        profile_menu.addAction(self._reset_profile_action)
        help_menu = menubar.addMenu("Help")
        self._about_action = QtGui.QAction("About", self)
        self._about_action.triggered.connect(self._on_about)
        help_menu.addAction(self._about_action)

    def _on_open_dxf(self) -> None:
        self.file_panel._on_browse_input()

    def _on_edit_profile(self) -> None:
        from dxf2ifc.gui.profile_editor import ProfileEditorDialog

        dialog = ProfileEditorDialog(self._profile, parent=self)
        dialog.profile_saved.connect(self.apply_profile_from_path)
        dialog.profile_loaded.connect(self.apply_profile_from_path)
        dialog.exec()

    def _on_reset_profile(self) -> None:
        """Discard any cached last_profile_path and reload the bundled default.
        Useful after an app upgrade ships new default-profile rules — without
        this, RecentFilesStore keeps pointing at the user's stale TOML."""
        self._recent_files.last_profile_path = None
        self._profile = load_default_profile()
        self._refresh_layer_table()
        self.set_status("Profile reset to bundled default", level="success")

    def _load_initial_profile(self):
        """Always start with the bundled default profile.

        ``last_profile_path`` is no longer auto-loaded at startup — when we
        ship updated default rules (e.g. Bugfix 12 narrowing scope to
        refrigeration-only), users with a stale on-disk TOML otherwise keep
        seeing the old rules and have to manually reset. The Load button in
        the profile editor still lets users open a custom TOML on demand."""
        self._recent_files.last_profile_path = None
        return load_default_profile()

    def apply_profile_from_path(self, path: str) -> None:
        self._profile = load_profile(path)
        self._recent_files.last_profile_path = path
        self._refresh_layer_table()
        self.set_status(f"Profile loaded: {path}", level="success")

    def _on_convert_requested(
        self,
        dxf: str,
        out: str,
        energy_specs: str = "",
        floor_elevation_mm: float = 0.0,
        quick_convert: bool = False,
    ) -> None:
        if not dxf or not out:
            self.set_status("Pick both a DXF input and an IFC output first", level="error")
            self.preview_log.append_error("Pick both a DXF input and an IFC output first")
            return
        # Persist the latest values so they pre-fill next session.
        # Save the spinbox value separately from the enabled-flag so an
        # enabled→disabled toggle doesn't wipe the last typed elevation.
        self._recent_files.floor_elevation_mm = float(
            self.file_panel.floor_elevation_edit.value()
        )
        self._recent_files.floor_elevation_enabled = bool(
            self.file_panel.floor_elevation_enabled_checkbox.isChecked()
        )
        self._recent_files.quick_convert = bool(quick_convert)
        self.file_panel.convert_button.setEnabled(False)
        self.set_status(f"Converting {dxf}…")
        self.preview_log.append_info(f"Converting {Path(dxf).name} -> {Path(out).name}")
        if energy_specs:
            self.preview_log.append_info(
                f"Energiateho-listasta: {Path(energy_specs).name}"
            )
        if floor_elevation_mm:
            self.preview_log.append_info(
                f"1.krs korko: +{int(floor_elevation_mm)} mm"
            )
        if quick_convert:
            self.preview_log.append_info(
                "Pikakonversio: 3D-tessellaatio (accoreconsole) ohitettu"
            )
        self._worker.run(
            dxf=dxf,
            out=out,
            profile=self._profile,
            validate=True,
            energy_specs=energy_specs or None,
            floor_elevation_mm=float(floor_elevation_mm),
            quick_convert=bool(quick_convert),
        )

    def _on_convert_finished(self, out: str) -> None:
        self.file_panel.convert_button.setEnabled(True)
        self.set_status(f"Done: {out}", level="success")
        self.preview_log.append_success(f"Wrote {Path(out).name}")
        self.convert_finished.emit(out)

    def _on_convert_progress(self, message: str) -> None:
        """Forward streamed status from the worker to the status bar + log."""
        self.set_status(message)
        self.preview_log.append_info(message)

    def _on_convert_failed(self, message: str) -> None:
        self.file_panel.convert_button.setEnabled(True)
        self.set_status(f"Error: {message}", level="error")
        self.preview_log.append_error(message)
        self.convert_failed.emit(message)

    def _on_report_ready(self, report: object) -> None:
        """Display ValidationReport summary, warnings and errors in the
        preview log so the user sees Plan F's quality-gate results."""
        summary = getattr(report, "summary", "")
        if summary:
            self.preview_log.append_info(summary)
        for warning in getattr(report, "warnings", []) or []:
            message = warning.get("message") if isinstance(warning, dict) else str(warning)
            self.preview_log.append_info(f"WARNING: {message}")
        for error in getattr(report, "errors", []) or []:
            message = error.get("message") if isinstance(error, dict) else str(error)
            self.preview_log.append_error(f"ERROR: {message}")

    def _on_about(self) -> None:
        from dxf2ifc.gui.about import show_about

        show_about(self).exec()

    def _on_update_check_done(self, info: object) -> None:
        if info is None:
            return  # no update or check failed silently
        self._update_banner.show_for(info)  # type: ignore[arg-type]

    def _on_update_requested(self, info: object) -> None:
        perform_update(info, self)  # type: ignore[arg-type]

    def set_status(self, text: str, *, level: str = "info") -> None:
        bar = self.statusBar()
        bar.showMessage(text)
        bar.setProperty("level", level)
        bar.style().unpolish(bar)
        bar.style().polish(bar)

    def _build_left_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 12, 16)
        heading = QtWidgets.QLabel("Files & profile")
        heading.setProperty("role", "h2")
        layout.addWidget(heading)
        self.file_panel = FilePanel()
        # Pre-fill 1.krs korko with the value used in the previous
        # session so the user does not retype their building elevation
        # for every conversion of the same project. The enabled-flag
        # also persists — Lauri's "draw in absolute coords" workflow
        # ticks this off once and stays off; coworkers who draw
        # floor-relative leave it on.
        self.file_panel.floor_elevation_enabled_checkbox.setChecked(
            self._recent_files.floor_elevation_enabled
        )
        self.file_panel.floor_elevation_edit.setEnabled(
            self._recent_files.floor_elevation_enabled
        )
        self.file_panel.floor_elevation_edit.setValue(
            self._recent_files.floor_elevation_mm
        )
        self.file_panel.quick_convert_checkbox.setChecked(
            self._recent_files.quick_convert
        )
        self.file_panel.convert_requested.connect(self._on_convert_requested)
        self.file_panel.input_edit.editingFinished.connect(self._refresh_layer_table)
        # editingFinished only fires on manual edit-and-Enter — not when
        # _on_browse_input setText()s a path. textChanged covers both flows.
        self.file_panel.input_edit.textChanged.connect(self._refresh_layer_table)
        layout.addWidget(self.file_panel)
        self.layer_table = LayerTable()
        layout.addWidget(self.layer_table, stretch=1)
        return panel

    def _refresh_layer_table(self) -> None:
        path_text = self.file_panel.input_edit.text().strip()
        if not path_text:
            self.layer_table.set_layers([], self._profile)
            return
        path = Path(path_text)
        if not path.is_file() or path.suffix.lower() != ".dxf":
            return
        try:
            layers = list_layers(path)
        except Exception as exc:  # noqa: BLE001 — bad DXF should not crash GUI
            self.set_status(f"Failed to read DXF layers: {exc}", level="error")
            self.preview_log.append_error(f"Failed to read {path.name}: {exc}")
            return
        self.layer_table.set_layers(layers, self._profile)
        # Raw layer/entity census via ezdxf — counts EVERY model-space entity
        # including 3DSOLID/SURFACE bodies that read_dxf would silently drop
        # without a side-channel mesh. The preview is a planning aid, not a
        # post-conversion report; it should reflect what's in the DXF, not
        # what survived the geometry pipeline.
        try:
            import ezdxf as _ezdxf
            _doc = _ezdxf.readfile(str(path))
            layer_counts: dict[str, int] = dict(
                Counter(entity.dxf.layer for entity in _doc.modelspace())
            )
            entity_count = sum(layer_counts.values())
        except Exception as exc:  # noqa: BLE001 — summary is best-effort
            self.preview_log.append_error(f"Failed to summarize {path.name}: {exc}")
            return
        self.preview_log.set_dxf_summary(
            path=str(path), entity_count=entity_count, layer_counts=layer_counts
        )
        # Conversion plan: show the user what each layer will become before
        # they hit Convert. Match each DXF layer against the active profile
        # using the same first-match-wins semantics as the mapper.
        from dxf2ifc.core.mapper import layer_matches as _layer_matches
        plan_lines = ["", "Conversion plan:"]
        mapped_n = 0
        skipped_n = 0
        for layer, count in sorted(layer_counts.items()):
            rule = next(
                (r for r in self._profile.rules if _layer_matches(r.layer_pattern, layer)),
                None,
            )
            if rule is None:
                plan_lines.append(f"  {layer} ({count}) → no rule, skipped")
                skipped_n += count
                continue
            mapped_n += count
            code = rule.lvi_code or rule.talotekniikka_code or rule.talo2000_code or "—"
            predef = f" {rule.predefined_type}" if rule.predefined_type else ""
            plan_lines.append(
                f"  {layer} ({count}) → {rule.ifc_type}{predef} ({rule.domain} {code})"
            )
        plan_lines.append(f"Total: {mapped_n} mapped, {skipped_n} skipped (of {entity_count} read)")
        self.preview_log.append_info("\n".join(plan_lines))

    def _build_right_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(12, 8, 0, 16)
        heading = QtWidgets.QLabel("Preview & log")
        heading.setProperty("role", "h2")
        layout.addWidget(heading)
        self.preview_log = PreviewLogPanel()
        layout.addWidget(self.preview_log, stretch=1)
        return panel
