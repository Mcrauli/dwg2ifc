"""Top-level QMainWindow with title row, QSplitter body and status bar."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from pathlib import Path

from collections import Counter

from dwg2ifc import __version__
from dwg2ifc.core.dxf_reader import list_layers
from dwg2ifc.gui.convert_worker import ConvertWorker
from dwg2ifc.gui.file_panel import FilePanel
from dwg2ifc.gui.layer_table import LayerTable
from dwg2ifc.gui.preview_log import PreviewLogPanel
from dwg2ifc.gui.recent_files import RecentFilesStore
from dwg2ifc.gui.update_banner import (
    UpdateBanner,
    UpdateChecker,
    perform_update,
)
from dwg2ifc.profiles.loader import load_default_profile
from dwg2ifc.profiles.store import (
    active_profile_path,
    clear_active_profile,
    load_active_profile,
)


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
        self.setWindowTitle("dwg2ifc")
        self.resize(1100, 700)
        self._recent_files = recent_files or RecentFilesStore()
        self._startup_profile_warning: str | None = None
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

        title = QtWidgets.QLabel("dwg2ifc")
        title.setProperty("role", "h1")
        caption = QtWidgets.QLabel("AutoCAD DWG/DXF → IFC 4 kylmäsuunnitteluun (RAVA3Pro)")
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
        if self._startup_profile_warning:
            self.set_status(self._startup_profile_warning, level="error")

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
        """File menu entry — delegate to the panel's add-files dialog so
        the user lands in the multi-row table flow."""
        self.file_panel._on_add_files()

    def _on_edit_profile(self) -> None:
        from dwg2ifc.gui.profile_editor import ProfileEditorDialog

        dialog = ProfileEditorDialog(self._profile, parent=self)
        dialog.profile_saved.connect(self._on_profile_saved)
        dialog.exec()

    def _on_profile_saved(self, profile: object) -> None:
        """ProfileEditorDialog persisted the edited profile to the
        per-user store and handed us the in-memory copy — adopt it and
        refresh the layer preview."""
        self._profile = profile
        self._refresh_layer_table()
        self.set_status("Profiili tallennettu", level="success")

    def _on_reset_profile(self) -> None:
        """Delete the saved active profile and reload the bundled
        default, so the next launch starts clean too."""
        clear_active_profile()
        self._profile = load_default_profile()
        self._refresh_layer_table()
        self.set_status("Profile reset to bundled default", level="success")

    def _load_initial_profile(self):
        """Load the user's saved active profile, or the bundled default.

        The profile editor's Save button persists to a per-user file
        (see ``profiles.store``); we auto-load it here so edits stick
        across launches with no manual re-loading. A saved file that is
        present but unreadable falls back to the bundled default and
        stashes a warning, surfaced once the status bar exists (see the
        end of ``__init__``)."""
        stored = load_active_profile()
        if stored is not None:
            return stored
        if active_profile_path().is_file():
            self._startup_profile_warning = (
                "Tallennettu profiili oli viallinen — "
                "palautettiin oletusprofiili"
            )
        return load_default_profile()

    def _on_convert_requested(self, payload: dict) -> None:
        files = payload.get("files") or []
        out = payload.get("output_path", "")
        energy_specs = payload.get("energy_specs_path", "")
        magicad_ifc = payload.get("magicad_ifc_path", "")
        if not files or not out:
            self.set_status(
                "Lisää vähintään yksi tiedosto + IFC-output ennen konversiota",
                level="error",
            )
            self.preview_log.append_error(
                "Lisää vähintään yksi tiedosto + IFC-output ennen konversiota"
            )
            return
        self.file_panel.convert_button.setEnabled(False)
        self.set_status(f"Konvertoidaan {len(files)} tiedostoa → {Path(out).name}…")
        for fe in files:
            self.preview_log.append_info(
                f"  [{fe.floor_label} @ {int(fe.elevation_mm)} mm] {Path(fe.path).name}"
            )
        if energy_specs:
            self.preview_log.append_info(
                f"Energiateho-listasta: {Path(energy_specs).name}"
            )
        if magicad_ifc:
            self.preview_log.append_info(
                f"MagiCAD-IFC merge: {Path(magicad_ifc).name}"
            )
        self._worker.run(
            files=files,
            out=out,
            profile=self._profile,
            validate=True,
            energy_specs=energy_specs or None,
            magicad_ifc=magicad_ifc or None,
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
        from dwg2ifc.gui.about import show_about

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
        self.file_panel.convert_requested.connect(self._on_convert_requested)
        # Refresh the layer table preview whenever the file list changes —
        # we read the first row's path so the user sees what's in the
        # primary floor before clicking Convert.
        self.file_panel.files_table.itemChanged.connect(self._refresh_layer_table)
        self.file_panel.files_table.model().rowsInserted.connect(
            lambda *_args: self._refresh_layer_table()
        )
        self.file_panel.files_table.model().rowsRemoved.connect(
            lambda *_args: self._refresh_layer_table()
        )
        layout.addWidget(self.file_panel)
        self.layer_table = LayerTable()
        layout.addWidget(self.layer_table, stretch=1)
        return panel

    def _refresh_layer_table(self) -> None:
        # Multi-floor: preview against the first row's file. The
        # converter reads every file at convert time, but the planning
        # preview only needs one representative DXF to show layer→IFC
        # mappings.
        table = self.file_panel.files_table
        path_text = ""
        if table.rowCount() > 0:
            first = table.item(0, 0)
            if first is not None:
                path_text = first.text().strip()
        if not path_text:
            self.layer_table.set_layers([], self._profile)
            return
        path = Path(path_text)
        if not path.is_file() or path.suffix.lower() not in (".dxf", ".dwg"):
            return
        if path.suffix.lower() == ".dwg":
            # ezdxf cannot read DWG. DWG input is preconverted via accoreconsole
            # DXFOUT inside convert_dxf, but we don't run that here just to
            # populate the layer preview — the conversion itself surfaces the
            # layer information after preconversion.
            self.layer_table.set_layers([], self._profile)
            self.set_status(
                "DWG-syöte: layer-esikatselu näkyy konversion jälkeen "
                "(ezdxf ei lue DWG:tä suoraan).",
                level="info",
            )
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
            # Defensive against non-graphical custom entities (e.g. the
            # MagiCAD MAGIFLOORORIGO control object) which raise on
            # ``entity.dxf.layer`` access — same skip pattern as
            # core.dxf_reader.list_layers.
            def _safe_layer(entity):
                try:
                    return entity.dxf.layer
                except Exception:  # noqa: BLE001
                    return None
            layer_counts: dict[str, int] = dict(
                Counter(
                    layer for layer in (_safe_layer(e) for e in _doc.modelspace())
                    if layer is not None
                )
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
        from dwg2ifc.core.mapper import layer_matches as _layer_matches
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
