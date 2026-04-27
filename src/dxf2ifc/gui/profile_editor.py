"""Dialog for inspecting and tweaking the active mapping profile."""

from __future__ import annotations

from copy import deepcopy

from PySide6 import QtCore, QtGui, QtWidgets

from dxf2ifc.profiles.loader import dump_profile
from dxf2ifc.profiles.schema import Profile, Rule

_HEADERS = ("Layer pattern", "IFC type", "Predefined", "Talo2000 code", "Talo2000 name", "System")


class _RuleTableModel(QtCore.QAbstractTableModel):
    def __init__(self, rules: list[Rule], parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._rules = list(rules)

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self._rules)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(_HEADERS)

    def data(
        self,
        index: QtCore.QModelIndex,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if not index.isValid() or role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None
        rule = self._rules[index.row()]
        column_value = (
            rule.layer_pattern,
            rule.ifc_type,
            rule.predefined_type or "",
            rule.talo2000_code,
            rule.talo2000_name,
            rule.system_name or "",
        )
        return column_value[index.column()]

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == QtCore.Qt.Orientation.Horizontal:
            return _HEADERS[section]
        return section + 1

    def remove_row(self, row: int) -> None:
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        del self._rules[row]
        self.endRemoveRows()

    def append_rule(self, rule: Rule) -> None:
        row = len(self._rules)
        self.beginInsertRows(QtCore.QModelIndex(), row, row)
        self._rules.append(rule)
        self.endInsertRows()

    def replace_rule(self, row: int, rule: Rule) -> None:
        self._rules[row] = rule
        top_left = self.index(row, 0)
        bottom_right = self.index(row, len(_HEADERS) - 1)
        self.dataChanged.emit(top_left, bottom_right)

    @property
    def rules(self) -> list[Rule]:
        return list(self._rules)


class ProfileEditorDialog(QtWidgets.QDialog):
    profile_saved = QtCore.Signal(str)

    def __init__(
        self,
        profile: Profile,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Profile editor")
        self._profile = deepcopy(profile)
        self._model = _RuleTableModel(self._profile.rules, self)

        layout = QtWidgets.QVBoxLayout(self)
        self.table = QtWidgets.QTableView()
        self.table.setModel(self._model)
        self.table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table)

        toolbar = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton("Add")
        self.add_button.setProperty("secondary", "true")
        self.edit_button = QtWidgets.QPushButton("Edit…")
        self.edit_button.setProperty("secondary", "true")
        self.remove_button = QtWidgets.QPushButton("Remove")
        self.remove_button.setProperty("secondary", "true")
        self.save_button = QtWidgets.QPushButton("Save profile…")
        self.save_button.setProperty("primary", "true")
        for button in (self.add_button, self.edit_button, self.remove_button):
            toolbar.addWidget(button)
        toolbar.addStretch(1)
        toolbar.addWidget(self.save_button)
        layout.addLayout(toolbar)

        self.add_button.clicked.connect(self._on_add)
        self.edit_button.clicked.connect(self._on_edit)
        self.remove_button.clicked.connect(self._on_remove)
        self.save_button.clicked.connect(self._on_save)

    def current_rules(self) -> list[Rule]:
        return self._model.rules

    def _selected_row(self) -> int | None:
        indexes = self.table.selectionModel().selectedRows()
        return indexes[0].row() if indexes else None

    def _on_add(self) -> None:
        from dxf2ifc.gui.rule_dialog import RuleEditDialog

        dialog = RuleEditDialog(parent=self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            rule = dialog.rule()
            if rule is not None:
                self._model.append_rule(rule)

    def _on_edit(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        from dxf2ifc.gui.rule_dialog import RuleEditDialog

        dialog = RuleEditDialog(rule=self._model.rules[row], parent=self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            rule = dialog.rule()
            if rule is not None:
                self._model.replace_rule(row, rule)

    def _on_remove(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        self._model.remove_row(row)

    def _on_save(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save profile", "", "TOML files (*.toml)"
        )
        if not path:
            return
        self._profile = self._profile.model_copy(update={"rules": self._model.rules})
        dump_profile(self._profile, path)
        self.profile_saved.emit(path)


# QtGui is imported for downstream consumers expecting it from this module.
__all__ = ["ProfileEditorDialog"]
_ = QtGui
