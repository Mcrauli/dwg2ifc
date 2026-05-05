"""Widget that lets the user pick a DXF input + IFC output and request conversion."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class FilePanel(QtWidgets.QWidget):
    # Emits (dxf_path, ifc_path, energy_specs_path, floor_elevation_mm).
    # ``energy_specs_path`` is empty string when the user has not picked
    # a spec file. ``floor_elevation_mm`` is the absolute Z elevation of
    # 1.krs (mm) — added to every IfcBuildingStorey.Elevation in the
    # output IFC. Default 0 = no offset.
    convert_requested = QtCore.Signal(str, str, str, float)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(10)

        layout.addWidget(self._caption("DXF input"), 0, 0)
        self.input_edit = QtWidgets.QLineEdit()
        self.input_edit.setPlaceholderText("Path to .dxf")
        layout.addWidget(self.input_edit, 0, 1)
        self.browse_input_button = QtWidgets.QPushButton("Browse…")
        self.browse_input_button.setProperty("secondary", "true")
        self.browse_input_button.clicked.connect(self._on_browse_input)
        layout.addWidget(self.browse_input_button, 0, 2)

        layout.addWidget(self._caption("IFC output"), 1, 0)
        self.output_edit = QtWidgets.QLineEdit()
        self.output_edit.setPlaceholderText("Path to .ifc")
        layout.addWidget(self.output_edit, 1, 1)
        self.browse_output_button = QtWidgets.QPushButton("Browse…")
        self.browse_output_button.setProperty("secondary", "true")
        self.browse_output_button.clicked.connect(self._on_browse_output)
        layout.addWidget(self.browse_output_button, 1, 2)

        layout.addWidget(self._caption("Energiateho-listasta"), 2, 0)
        self.energy_edit = QtWidgets.QLineEdit()
        self.energy_edit.setPlaceholderText(
            "Valinnainen .xlsx tai .csv jossa Koneikko, Laitetunnus + tehot"
        )
        layout.addWidget(self.energy_edit, 2, 1)
        self.browse_energy_button = QtWidgets.QPushButton("Browse…")
        self.browse_energy_button.setProperty("secondary", "true")
        self.browse_energy_button.clicked.connect(self._on_browse_energy)
        layout.addWidget(self.browse_energy_button, 2, 2)

        layout.addWidget(self._caption("1.krs korko (mm)"), 3, 0)
        self.floor_elevation_edit = QtWidgets.QDoubleSpinBox()
        # AutoCAD drawings can place 1.krs anywhere on the absolute
        # Finnish coordinate map — typical values 0…30000 mm but
        # leave generous slack for unusual sites and below-grade refs.
        self.floor_elevation_edit.setRange(-50_000.0, 500_000.0)
        self.floor_elevation_edit.setDecimals(0)
        self.floor_elevation_edit.setSingleStep(100.0)
        self.floor_elevation_edit.setSuffix(" mm")
        self.floor_elevation_edit.setToolTip(
            "Absoluuttinen 1.krs korko (mm). "
            "DXF:n Z=0 = 1.krs lattia. Tämä arvo lisätään jokaiseen "
            "IfcBuildingStorey.Elevation-arvoon."
        )
        layout.addWidget(self.floor_elevation_edit, 3, 1, 1, 2)

        self.convert_button = QtWidgets.QPushButton("Convert")
        self.convert_button.setProperty("primary", "true")
        self.convert_button.clicked.connect(self._on_convert)
        layout.addWidget(self.convert_button, 4, 1, 1, 2)

        layout.setColumnStretch(1, 1)

    def _caption(self, text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setProperty("role", "caption")
        return label

    def _on_browse_input(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open DXF", "", "DXF files (*.dxf)")
        if path:
            self.input_edit.setText(path)

    def _on_browse_output(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save IFC", "", "IFC files (*.ifc)")
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

    def _on_convert(self) -> None:
        self.convert_requested.emit(
            self.input_edit.text(),
            self.output_edit.text(),
            self.energy_edit.text(),
            float(self.floor_elevation_edit.value()),
        )
