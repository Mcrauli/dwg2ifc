"""Widget for picking DXF/DWG inputs (multi-floor) and requesting conversion."""

from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from dwg2ifc.core.types import FileEntry


class FilePanel(QtWidgets.QWidget):
    """Multi-row file table → emits ``convert_requested(dict)`` payload.

    Payload shape::

        {
            "files": list[FileEntry],
            "output_path": str,
            "energy_specs_path": str,   # "" if unset
            "magicad_ifc_path": str,    # "" if unset
            "reservations_only": bool,  # export skeleton + reservations only
        }
    """

    convert_requested = QtCore.Signal(dict)

    _HEADERS = ("Tiedosto", "Kerros", "Z (mm)")

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(10)

        # --- File table -----------------------------------------------------
        self.files_table = QtWidgets.QTableWidget(0, 3)
        self.files_table.setHorizontalHeaderLabels(list(self._HEADERS))
        self.files_table.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.files_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.files_table.verticalHeader().setVisible(False)
        layout.addWidget(self.files_table, 0, 0, 1, 3)

        # Add / Remove toolbar
        toolbar = QtWidgets.QHBoxLayout()
        self.add_files_button = QtWidgets.QPushButton("Lisää tiedosto(t)…")
        self.add_files_button.setProperty("secondary", "true")
        self.add_files_button.clicked.connect(self._on_add_files)
        self.remove_button = QtWidgets.QPushButton("Poista")
        self.remove_button.setProperty("secondary", "true")
        self.remove_button.clicked.connect(self._on_remove)
        toolbar.addWidget(self.add_files_button)
        toolbar.addWidget(self.remove_button)
        toolbar.addStretch(1)
        layout.addLayout(toolbar, 1, 0, 1, 3)

        # --- Output IFC -----------------------------------------------------
        layout.addWidget(self._caption("IFC output"), 2, 0)
        self.output_edit = QtWidgets.QLineEdit()
        self.output_edit.setPlaceholderText("Path to .ifc")
        layout.addWidget(self.output_edit, 2, 1)
        self.browse_output_button = QtWidgets.QPushButton("Browse…")
        self.browse_output_button.setProperty("secondary", "true")
        self.browse_output_button.clicked.connect(self._on_browse_output)
        layout.addWidget(self.browse_output_button, 2, 2)

        # --- Energy specs --------------------------------------------------
        layout.addWidget(self._caption("Energiateho-listasta"), 3, 0)
        self.energy_edit = QtWidgets.QLineEdit()
        self.energy_edit.setPlaceholderText(
            "Valinnainen .xlsx tai .csv jossa Koneikko, Laitetunnus + tehot"
        )
        layout.addWidget(self.energy_edit, 3, 1)
        self.browse_energy_button = QtWidgets.QPushButton("Browse…")
        self.browse_energy_button.setProperty("secondary", "true")
        self.browse_energy_button.clicked.connect(self._on_browse_energy)
        layout.addWidget(self.browse_energy_button, 3, 2)

        # --- MagiCAD IFC ----------------------------------------------------
        layout.addWidget(self._caption("MagiCAD-IFC"), 4, 0)
        self.magicad_ifc_edit = QtWidgets.QLineEdit()
        self.magicad_ifc_edit.setPlaceholderText(
            "Valinnainen -MAGIIFCCD-tuotos (kollegan IFC mergetään master-IFC:hen)"
        )
        self.magicad_ifc_edit.setToolTip(
            "Valinnainen MagiCAD-IFC. Kun annettu, dwg2ifc skippaa "
            "MagiCAD-objektit DXF:stä (MAGI*-luokat + ACAD_PROXY_ENTITY) "
            "ja yhdistää tämän IFC:n IfcProduct:t master-IFC:hen ensimmäisen "
            "IfcBuildingStoreyn alle."
        )
        layout.addWidget(self.magicad_ifc_edit, 4, 1)
        self.browse_magicad_ifc_button = QtWidgets.QPushButton("Browse…")
        self.browse_magicad_ifc_button.setProperty("secondary", "true")
        self.browse_magicad_ifc_button.clicked.connect(self._on_browse_magicad_ifc)
        layout.addWidget(self.browse_magicad_ifc_button, 4, 2)

        # --- Reservations-only export --------------------------------------
        self.reservations_only_check = QtWidgets.QCheckBox(
            "Vain reikävaraukset + IFC skeleton"
        )
        self.reservations_only_check.setToolTip(
            "Kun valittu, IFC:hen viedään vain KYL-REIKAVARAUS-"
            "varaukset ja normaali IFC-skeleton."
        )
        layout.addWidget(self.reservations_only_check, 5, 1, 1, 2)

        # --- Convert button -------------------------------------------------
        self.convert_button = QtWidgets.QPushButton("Convert")
        self.convert_button.setProperty("primary", "true")
        self.convert_button.setEnabled(False)
        self.convert_button.clicked.connect(self._on_convert)
        layout.addWidget(self.convert_button, 6, 1, 1, 2)

        layout.setColumnStretch(1, 1)

        self.files_table.itemChanged.connect(self._refresh_convert_enabled)
        self.output_edit.textChanged.connect(self._refresh_convert_enabled)

    # ---------------------------------------------------------------- helpers

    def _caption(self, text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setProperty("role", "caption")
        return label

    def _on_add_files(self) -> None:
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Avaa DXF- tai DWG-tiedostot",
            "",
            "AutoCAD-piirustukset (*.dxf *.dwg);;DXF (*.dxf);;DWG (*.dwg);;All files (*)",
        )
        for path in paths:
            self._append_row(path)
        self._refresh_convert_enabled()

    def _append_row(self, path: str) -> None:
        row = self.files_table.rowCount()
        self.files_table.insertRow(row)
        # File path: read-only (the table edits label + Z only).
        path_item = QtWidgets.QTableWidgetItem(path)
        path_item.setFlags(path_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        self.files_table.setItem(row, 0, path_item)
        self.files_table.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{row + 1}.krs"))
        self.files_table.setItem(row, 2, QtWidgets.QTableWidgetItem("0"))

    def _on_remove(self) -> None:
        rows = sorted(
            {index.row() for index in self.files_table.selectedIndexes()},
            reverse=True,
        )
        for row in rows:
            self.files_table.removeRow(row)
        self._refresh_convert_enabled()

    def _on_browse_output(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save IFC", "", "IFC files (*.ifc)"
        )
        if path:
            self.output_edit.setText(path)

    def _on_browse_energy(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Avaa energiateho-lista",
            "",
            "Excel & CSV (*.xlsx *.xlsm *.csv *.tsv);;All files (*)",
        )
        if path:
            self.energy_edit.setText(path)

    def _on_browse_magicad_ifc(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Avaa MagiCAD-IFC (-MAGIIFCCD-tuotos)",
            "",
            "IFC-tiedostot (*.ifc);;All files (*)",
        )
        if path:
            self.magicad_ifc_edit.setText(path)

    def _collect_file_entries(self) -> list[FileEntry] | None:
        rows = self.files_table.rowCount()
        if rows == 0:
            return None
        entries: list[FileEntry] = []
        for row in range(rows):
            path_item = self.files_table.item(row, 0)
            label_item = self.files_table.item(row, 1)
            elev_item = self.files_table.item(row, 2)
            if path_item is None or label_item is None or elev_item is None:
                return None
            path = path_item.text().strip()
            label = label_item.text().strip()
            if not path or not label:
                return None
            try:
                elev = float(elev_item.text().strip() or "0")
            except ValueError:
                return None
            entries.append(
                FileEntry(path=Path(path), floor_label=label, elevation_mm=elev)
            )
        labels_lower = [e.floor_label.lower() for e in entries]
        if len(set(labels_lower)) != len(labels_lower):
            return None
        return entries

    def _refresh_convert_enabled(self) -> None:
        entries = self._collect_file_entries()
        has_output = bool(self.output_edit.text().strip())
        self.convert_button.setEnabled(bool(entries) and has_output)

    def _on_convert(self) -> None:
        entries = self._collect_file_entries()
        if not entries:
            return
        self.convert_requested.emit(
            {
                "files": entries,
                "output_path": self.output_edit.text(),
                "energy_specs_path": self.energy_edit.text(),
                "magicad_ifc_path": self.magicad_ifc_edit.text(),
                "reservations_only": self.reservations_only_check.isChecked(),
            }
        )


__all__ = ["FilePanel"]
_ = QtGui
