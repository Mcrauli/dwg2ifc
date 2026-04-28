"""Table widget that lists DXF layers and their resolved profile mapping."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from dxf2ifc.core.mapper import layer_matches
from dxf2ifc.profiles.schema import Profile, Rule

_PLACEHOLDER = "—"
_HEADERS = ("Layer", "IFC type", "Domain", "Code", "System")


def _domain_code(rule: Rule) -> tuple[str, str]:
    """Return (codeset_label, code_value) for the rule's active classification."""
    if rule.domain == "ARK":
        return "Talo2000", rule.talo2000_code or _PLACEHOLDER
    if rule.lvi_code:
        return "RAVA-LVI", rule.lvi_code
    if rule.talotekniikka_code:
        return "RAVA-TATE", rule.talotekniikka_code
    return rule.domain, _PLACEHOLDER


class LayerTable(QtWidgets.QTableWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setColumnCount(len(_HEADERS))
        self.setHorizontalHeaderLabels(_HEADERS)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)

    def set_layers(self, layers: list[str], profile: Profile) -> None:
        self.setRowCount(len(layers))
        mono = QtGui.QFont("JetBrains Mono")
        for row, layer in enumerate(layers):
            rule = _first_matching_rule(layer, profile)
            if rule is None:
                cells = [layer, _PLACEHOLDER, _PLACEHOLDER, _PLACEHOLDER, _PLACEHOLDER]
            else:
                domain_label, code_text = _domain_code(rule)
                cells = [
                    layer,
                    rule.ifc_type,
                    domain_label,
                    code_text,
                    rule.system_name or _PLACEHOLDER,
                ]
            for col, text in enumerate(cells):
                item = QtWidgets.QTableWidgetItem(text)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                if col in (0, 3):
                    item.setFont(mono)
                self.setItem(row, col, item)


def _first_matching_rule(layer: str, profile: Profile) -> Rule | None:
    for rule in profile.rules:
        if layer_matches(rule.layer_pattern, layer):
            return rule
    return None
