"""Form dialog for editing a single profile Rule with live pydantic validation."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets
from pydantic import ValidationError

from dxf2ifc.profiles.rava.loader import load_rava_codes
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
# KYL first so that "Add rule" defaults to refrigeration (this app's
# primary domain) and the Talo2000 fields stay hidden — those are only
# relevant when the user explicitly switches to ARK.
_DOMAINS = ("KYL", "TATE", "ARK")
_BLANK = ""


def _rava_choices(codeset: str) -> list[str]:
    return [_BLANK] + sorted(c.code for c in load_rava_codes().values() if c.codeset == codeset)


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
        self._layout = layout
        self.layer_pattern_edit = QtWidgets.QLineEdit()
        self.entity_kind_combo = QtWidgets.QComboBox()
        self.entity_kind_combo.addItems(_ENTITY_KINDS)
        self.block_name_edit = QtWidgets.QLineEdit()
        self.ifc_type_combo = QtWidgets.QComboBox()
        self.ifc_type_combo.addItems(_IFC_TYPES)
        self.predefined_type_edit = QtWidgets.QLineEdit()
        self.domain_combo = QtWidgets.QComboBox()
        self.domain_combo.addItems(_DOMAINS)
        self.talo2000_code_edit = QtWidgets.QLineEdit()
        self.talo2000_name_edit = QtWidgets.QLineEdit()
        # setEditable(True) lets the user type a custom RAVA code that
        # is not in the bundled codeset (e.g. a recent addition not yet
        # synced to ``profiles/rava/``). The combo still surfaces the
        # known choices via the dropdown, but the line edit accepts free
        # text. ``Rule.model_validate`` then does the canonical check.
        self.lvi_code_combo = QtWidgets.QComboBox()
        self.lvi_code_combo.setEditable(True)
        self.lvi_code_combo.addItems(_rava_choices("LVI-TUOTEOSA"))
        self.talotekniikka_code_combo = QtWidgets.QComboBox()
        self.talotekniikka_code_combo.setEditable(True)
        self.talotekniikka_code_combo.addItems(_rava_choices("TALOTEKNIIKKA-TUOTEOSA"))
        self.system_name_edit = QtWidgets.QLineEdit()

        layout.addRow("Layer pattern", self.layer_pattern_edit)
        layout.addRow("Entity kind", self.entity_kind_combo)
        layout.addRow("Block name", self.block_name_edit)
        layout.addRow("IFC type", self.ifc_type_combo)
        layout.addRow("Predefined type", self.predefined_type_edit)
        layout.addRow("Domain", self.domain_combo)
        self._talo2000_code_label = QtWidgets.QLabel("Talo2000 code")
        layout.addRow(self._talo2000_code_label, self.talo2000_code_edit)
        self._talo2000_name_label = QtWidgets.QLabel("Talo2000 name")
        layout.addRow(self._talo2000_name_label, self.talo2000_name_edit)
        self._lvi_code_label = QtWidgets.QLabel("LVI-TUOTEOSA code")
        layout.addRow(self._lvi_code_label, self.lvi_code_combo)
        self._talotekniikka_code_label = QtWidgets.QLabel("TALOTEKNIIKKA-TUOTEOSA code")
        layout.addRow(self._talotekniikka_code_label, self.talotekniikka_code_combo)
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
        for combo in (
            self.entity_kind_combo,
            self.ifc_type_combo,
            self.lvi_code_combo,
            self.talotekniikka_code_combo,
        ):
            combo.currentTextChanged.connect(self._refresh_validation)
        self.domain_combo.currentTextChanged.connect(self._on_domain_changed)

        if rule is not None:
            self._fill_from_rule(rule)
        self._on_domain_changed(self.domain_combo.currentText())

    def _fill_from_rule(self, rule: Rule) -> None:
        self.layer_pattern_edit.setText(rule.layer_pattern)
        self.entity_kind_combo.setCurrentText(rule.entity_kind)
        self.block_name_edit.setText(rule.block_name or "")
        self.ifc_type_combo.setCurrentText(rule.ifc_type)
        self.predefined_type_edit.setText(rule.predefined_type or "")
        self.domain_combo.setCurrentText(rule.domain)
        self.talo2000_code_edit.setText(rule.talo2000_code or "")
        self.talo2000_name_edit.setText(rule.talo2000_name or "")
        self.lvi_code_combo.setCurrentText(rule.lvi_code or _BLANK)
        self.talotekniikka_code_combo.setCurrentText(rule.talotekniikka_code or _BLANK)
        self.system_name_edit.setText(rule.system_name or "")

    def _set_row_visible(
        self, label: QtWidgets.QWidget, field: QtWidgets.QWidget, visible: bool
    ) -> None:
        label.setVisible(visible)
        field.setVisible(visible)

    @QtCore.Slot(str)
    def _on_domain_changed(self, domain: str) -> None:
        is_ark = domain == "ARK"
        self._set_row_visible(self._talo2000_code_label, self.talo2000_code_edit, is_ark)
        self._set_row_visible(self._talo2000_name_label, self.talo2000_name_edit, is_ark)
        self._set_row_visible(self._lvi_code_label, self.lvi_code_combo, not is_ark)
        self._set_row_visible(
            self._talotekniikka_code_label, self.talotekniikka_code_combo, not is_ark
        )
        self._refresh_validation()

    def _candidate_payload(self) -> dict[str, object]:
        domain = self.domain_combo.currentText()
        is_ark = domain == "ARK"
        return {
            "layer_pattern": self.layer_pattern_edit.text().strip(),
            "entity_kind": self.entity_kind_combo.currentText(),
            "block_name": self.block_name_edit.text().strip() or None,
            "ifc_type": self.ifc_type_combo.currentText(),
            "predefined_type": self.predefined_type_edit.text().strip() or None,
            "domain": domain,
            "talo2000_code": (self.talo2000_code_edit.text().strip() or None) if is_ark else None,
            "talo2000_name": (self.talo2000_name_edit.text().strip() or None) if is_ark else None,
            "lvi_code": (self.lvi_code_combo.currentText().strip() or None) if not is_ark else None,
            "talotekniikka_code": (self.talotekniikka_code_combo.currentText().strip() or None)
            if not is_ark
            else None,
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
