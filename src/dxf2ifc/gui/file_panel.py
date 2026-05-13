"""Widget that lets the user pick a DXF input + IFC output and request conversion."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class FilePanel(QtWidgets.QWidget):
    # Emits (dxf_path, ifc_path, energy_specs_path, floor_elevation_mm,
    # magicad_ifc_path).
    # ``energy_specs_path`` is empty string when the user has not picked
    # a spec file. ``floor_elevation_mm`` is the absolute Z elevation of
    # 1.krs (mm) — added to every IfcBuildingStorey.Elevation in the
    # output IFC. When the "Lisää 1.krs absoluuttinen korko" checkbox is
    # unchecked, the panel emits 0.0 here regardless of the spinbox
    # value, so DXF Z coordinates pass through to IFC unchanged. That
    # is the right mode when the source DXF is already drawn in
    # absolute Finnish coordinates; the offset path is for the more
    # common case where designers draw entities relative to floor Z=0.
    # ``magicad_ifc_path`` is empty string when no MagiCAD-IFC has been
    # picked. When non-empty, the converter merges that IFC (typically
    # produced by a colleague's FULL-MagiCAD ``-MAGIIFCCD`` export) into
    # the master IFC and skips MagiCAD parts in the DXF to avoid duplicates.
    convert_requested = QtCore.Signal(str, str, str, float, str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(10)

        layout.addWidget(self._caption("DXF input"), 0, 0)
        self.input_edit = QtWidgets.QLineEdit()
        self.input_edit.setPlaceholderText("Polku .dxf- tai .dwg-tiedostoon")
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

        layout.addWidget(self._caption("MagiCAD-IFC"), 3, 0)
        self.magicad_ifc_edit = QtWidgets.QLineEdit()
        self.magicad_ifc_edit.setPlaceholderText(
            "Valinnainen -MAGIIFCCD-tuotos (LVI-puoli yhdistetään master-IFC:hen)"
        )
        self.magicad_ifc_edit.setToolTip(
            "Valinnainen MagiCAD-IFC. Kun annettu, dxf2ifc skippaa "
            "MagiCAD-objektit DXF:stä (MAGI*-luokat + ACAD_PROXY_ENTITY) "
            "ja yhdistää tämän IFC:n IfcProduct:t master-IFC:hen ensimmäisen "
            "IfcBuildingStoreyn alle. Tarkoitettu kollegan FULL-MagiCAD-"
            "lisenssin koneella ajettavaa -MAGIIFCCD:n tuotosta varten."
        )
        layout.addWidget(self.magicad_ifc_edit, 3, 1)
        self.browse_magicad_ifc_button = QtWidgets.QPushButton("Browse…")
        self.browse_magicad_ifc_button.setProperty("secondary", "true")
        self.browse_magicad_ifc_button.clicked.connect(self._on_browse_magicad_ifc)
        layout.addWidget(self.browse_magicad_ifc_button, 3, 2)

        self.floor_elevation_enabled_checkbox = QtWidgets.QCheckBox(
            "Lisää 1.krs absoluuttinen korko"
        )
        self.floor_elevation_enabled_checkbox.setChecked(True)
        self.floor_elevation_enabled_checkbox.setToolTip(
            "Päällä: DXF:n Z=0 tulkitaan 1.krs lattiaksi ja alla annettu "
            "korko lisätään jokaiseen IfcBuildingStorey.Elevation- ja "
            "elementti-Z-arvoon. Pois: DXF:n Z-koordinaatit menevät IFC:hen "
            "sellaisinaan (käytä jos piirrät suoraan absoluuttiseen korkoon)."
        )
        layout.addWidget(self.floor_elevation_enabled_checkbox, 4, 0, 1, 3)

        layout.addWidget(self._caption("1.krs korko (mm)"), 5, 0)
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
        layout.addWidget(self.floor_elevation_edit, 5, 1, 1, 2)
        self.floor_elevation_enabled_checkbox.toggled.connect(
            self.floor_elevation_edit.setEnabled
        )

        self.convert_button = QtWidgets.QPushButton("Convert")
        self.convert_button.setProperty("primary", "true")
        self.convert_button.clicked.connect(self._on_convert)
        layout.addWidget(self.convert_button, 6, 1, 1, 2)

        layout.setColumnStretch(1, 1)

    def _caption(self, text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setProperty("role", "caption")
        return label

    def _on_browse_input(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Avaa DXF- tai DWG-tiedosto",
            "",
            "AutoCAD-piirustukset (*.dxf *.dwg);;DXF (*.dxf);;DWG (*.dwg);;All files (*)",
        )
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

    def _on_browse_magicad_ifc(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Avaa MagiCAD-IFC (-MAGIIFCCD-tuotos)",
            "",
            "IFC-tiedostot (*.ifc);;All files (*)",
        )
        if path:
            self.magicad_ifc_edit.setText(path)

    def _on_convert(self) -> None:
        floor_elev = (
            float(self.floor_elevation_edit.value())
            if self.floor_elevation_enabled_checkbox.isChecked()
            else 0.0
        )
        self.convert_requested.emit(
            self.input_edit.text(),
            self.output_edit.text(),
            self.energy_edit.text(),
            floor_elev,
            self.magicad_ifc_edit.text(),
        )
