"""Plan G Task 15: ``CRSDialog`` lets the user set the IFC project's
georeferencing (IfcProjectedCRS + IfcMapConversion) without editing the
profile TOML by hand."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from dxf2ifc.profiles.schema import CRSConfig

_KNOWN_EPSG = [("EPSG:3067", "ETRS-TM35FIN", "ETRS89")]


class CRSDialog(QtWidgets.QDialog):
    """Modal dialog with EPSG combo + Eastings/Northings/OrthogonalHeight
    line edits. Emits ``crs_accepted(CRSConfig)`` when the user clicks OK."""

    crs_accepted = QtCore.Signal(object)

    def __init__(
        self,
        crs: CRSConfig | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Set CRS — dxf2ifc")
        self.setModal(True)

        self._epsg_combo = QtWidgets.QComboBox(self)
        for code, name, _ in _KNOWN_EPSG:
            self._epsg_combo.addItem(f"{code} {name}", code)

        self._eastings_edit = QtWidgets.QLineEdit(self)
        self._eastings_edit.setValidator(QtGui.QDoubleValidator(self))
        self._northings_edit = QtWidgets.QLineEdit(self)
        self._northings_edit.setValidator(QtGui.QDoubleValidator(self))
        self._orth_height_edit = QtWidgets.QLineEdit(self)
        self._orth_height_edit.setValidator(QtGui.QDoubleValidator(self))

        seed = crs or CRSConfig(eastings_mm=0.0, northings_mm=0.0)
        self._eastings_edit.setText(_fmt(seed.eastings_mm))
        self._northings_edit.setText(_fmt(seed.northings_mm))
        self._orth_height_edit.setText(_fmt(seed.orthogonal_height_mm))

        form = QtWidgets.QFormLayout()
        form.addRow("EPSG", self._epsg_combo)
        form.addRow("Eastings (mm)", self._eastings_edit)
        form.addRow("Northings (mm)", self._northings_edit)
        form.addRow("Orthogonal height (mm)", self._orth_height_edit)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        epsg = self._epsg_combo.currentData()
        _, name, datum = next(row for row in _KNOWN_EPSG if row[0] == epsg)
        crs = CRSConfig(
            epsg_code=epsg,
            name=name,
            geodetic_datum=datum,
            eastings_mm=float(self._eastings_edit.text() or 0.0),
            northings_mm=float(self._northings_edit.text() or 0.0),
            orthogonal_height_mm=float(self._orth_height_edit.text() or 0.0),
        )
        self.crs_accepted.emit(crs)
        self.accept()

    def current_values(self) -> dict:
        """Test helper: return the currently-entered field values."""
        return {
            "epsg": self._epsg_combo.currentData(),
            "eastings_mm": float(self._eastings_edit.text() or 0.0),
            "northings_mm": float(self._northings_edit.text() or 0.0),
            "orthogonal_height_mm": float(self._orth_height_edit.text() or 0.0),
        }


def _fmt(value: float) -> str:
    return f"{value:g}"
