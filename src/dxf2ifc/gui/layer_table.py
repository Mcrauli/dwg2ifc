"""Table widget that lists DXF layers and their resolved profile mapping."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from dxf2ifc.core.mapper import layer_matches
from dxf2ifc.profiles.schema import Profile, Rule

_PLACEHOLDER = "—"
_HEADERS = ("Layer", "IFC type", "Talo2000", "System")


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
            cells = [
                layer,
                rule.ifc_type if rule else _PLACEHOLDER,
                rule.talo2000_code if rule else _PLACEHOLDER,
                (rule.system_name if rule and rule.system_name else _PLACEHOLDER),
            ]
            for col, text in enumerate(cells):
                item = QtWidgets.QTableWidgetItem(text)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                if col in (0, 2):
                    item.setFont(mono)
                self.setItem(row, col, item)


def _first_matching_rule(layer: str, profile: Profile) -> Rule | None:
    for rule in profile.rules:
        if layer_matches(rule.layer_pattern, layer):
            return rule
    return None
