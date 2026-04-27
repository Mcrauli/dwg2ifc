"""Form dialog for editing a single profile Rule with live pydantic validation."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets
from pydantic import ValidationError

from dxf2ifc.profiles.schema import Rule

_IFC_TYPES = (
    "IfcWall",
    "IfcSlab",
    "IfcDoor",
    "IfcWindow",
    "IfcPipeSegment",
    "IfcCableCarrierSegment",
    "IfcFurniture",
    "IfcBuildingElementProxy",
    "IfcEvaporator",
    "IfcCondenser",
    "IfcCompressor",
)
_ENTITY_KINDS = ("LINE", "POLYLINE", "CIRCLE", "INSERT")


class RuleEditDialog(QtWidgets.QDialog):
    def __init__(
        self,
        *,
        rule: Rule | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit rule")

        layout = QtWidgets.QFormLayout(self)
        self.layer_pattern_edit = QtWidgets.QLineEdit()
        self.entity_kind_combo = QtWidgets.QComboBox()
        self.entity_kind_combo.addItems(_ENTITY_KINDS)
        self.block_name_edit = QtWidgets.QLineEdit()
        self.ifc_type_combo = QtWidgets.QComboBox()
        self.ifc_type_combo.addItems(_IFC_TYPES)
        self.predefined_type_edit = QtWidgets.QLineEdit()
        self.talo2000_code_edit = QtWidgets.QLineEdit()
        self.talo2000_name_edit = QtWidgets.QLineEdit()
        self.system_name_edit = QtWidgets.QLineEdit()

        layout.addRow("Layer pattern", self.layer_pattern_edit)
        layout.addRow("Entity kind", self.entity_kind_combo)
        layout.addRow("Block name", self.block_name_edit)
        layout.addRow("IFC type", self.ifc_type_combo)
        layout.addRow("Predefined type", self.predefined_type_edit)
        layout.addRow("Talo2000 code", self.talo2000_code_edit)
        layout.addRow("Talo2000 name", self.talo2000_name_edit)
        layout.addRow("System name", self.system_name_edit)

        self.error_label = QtWidgets.QLabel("")
        self.error_label.setProperty("level", "error")
        layout.addRow(self.error_label)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        layout.addRow(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.ok_button = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)

        for widget in (
            self.layer_pattern_edit,
            self.block_name_edit,
            self.predefined_type_edit,
            self.talo2000_code_edit,
            self.talo2000_name_edit,
            self.system_name_edit,
        ):
            widget.textChanged.connect(self._refresh_validation)
        self.entity_kind_combo.currentTextChanged.connect(self._refresh_validation)
        self.ifc_type_combo.currentTextChanged.connect(self._refresh_validation)

        if rule is not None:
            self._fill_from_rule(rule)
        self._refresh_validation()

    def _fill_from_rule(self, rule: Rule) -> None:
        self.layer_pattern_edit.setText(rule.layer_pattern)
        self.entity_kind_combo.setCurrentText(rule.entity_kind)
        self.block_name_edit.setText(rule.block_name or "")
        self.ifc_type_combo.setCurrentText(rule.ifc_type)
        self.predefined_type_edit.setText(rule.predefined_type or "")
        self.talo2000_code_edit.setText(rule.talo2000_code)
        self.talo2000_name_edit.setText(rule.talo2000_name)
        self.system_name_edit.setText(rule.system_name or "")

    def _candidate_payload(self) -> dict[str, object]:
        return {
            "layer_pattern": self.layer_pattern_edit.text().strip(),
            "entity_kind": self.entity_kind_combo.currentText(),
            "block_name": self.block_name_edit.text().strip() or None,
            "ifc_type": self.ifc_type_combo.currentText(),
            "predefined_type": self.predefined_type_edit.text().strip() or None,
            "talo2000_code": self.talo2000_code_edit.text().strip(),
            "talo2000_name": self.talo2000_name_edit.text().strip(),
            "system_name": self.system_name_edit.text().strip() or None,
        }

    @QtCore.Slot()
    def _refresh_validation(self) -> None:
        try:
            Rule.model_validate(self._candidate_payload())
        except ValidationError as exc:
            self.ok_button.setEnabled(False)
            self.error_label.setText(_summarise_validation_error(exc))
            return
        self.ok_button.setEnabled(True)
        self.error_label.setText("")

    def rule(self) -> Rule | None:
        try:
            return Rule.model_validate(self._candidate_payload())
        except ValidationError:
            return None


def _summarise_validation_error(exc: ValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return ""
    return errors[0].get("msg", str(exc))
