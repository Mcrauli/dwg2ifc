"""Dialog for inspecting and tweaking the active mapping profile.

The edited profile is persisted to the per-user store (profiles.store)
via the Save button — there is no file-path picker. A search box backed
by a QSortFilterProxyModel makes the rule table navigable; Add / Edit
/ Remove map the selected proxy row back to the source model so they hit
the right rule even while the table is filtered.
"""

from __future__ import annotations

import logging
from copy import deepcopy

from PySide6 import QtCore, QtGui, QtWidgets

from dwg2ifc.profiles.schema import Profile, Rule
from dwg2ifc.profiles.store import save_active_profile

_log = logging.getLogger(__name__)

_HEADERS = (
    "Layer pattern",
    "IFC type",
    "Predefined",
    "Domain",
    "Code",
    "Name",
    "System",
)


def _row_for(rule: Rule) -> tuple[str, str, str, str, str, str, str]:
    if rule.domain == "ARK":
        code = rule.talo2000_code or ""
        name = rule.talo2000_name or ""
    else:
        code = rule.lvi_code or rule.talotekniikka_code or ""
        name = ""
    return (
        rule.layer_pattern,
        rule.ifc_type,
        rule.predefined_type or "",
        rule.domain,
        code,
        name,
        rule.system_name or "",
    )


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
        return _row_for(rule)[index.column()]

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
    # Emitted after a successful Save-to-store, carrying the edited
    # Profile object so the main window can adopt it without re-reading
    # anything from disk.
    profile_saved = QtCore.Signal(object)

    def __init__(
        self,
        profile: Profile,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Profile editor")
        self.resize(820, 520)
        self._profile = deepcopy(profile)
        self._model = _RuleTableModel(self._profile.rules, self)
        self._proxy = QtCore.QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(
            QtCore.Qt.CaseSensitivity.CaseInsensitive
        )
        self._proxy.setFilterKeyColumn(-1)  # match against every column

        layout = QtWidgets.QVBoxLayout(self)

        # --- search row -------------------------------------------------
        search_row = QtWidgets.QHBoxLayout()
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText(
            "Hae sääntöjä (layer, IFC-tyyppi, domain, koodi…)"
        )
        self.search_edit.setClearButtonEnabled(True)
        self.row_count_label = QtWidgets.QLabel()
        self.row_count_label.setProperty("role", "caption")
        search_row.addWidget(self.search_edit, stretch=1)
        search_row.addWidget(self.row_count_label)
        layout.addLayout(search_row)

        # --- table ------------------------------------------------------
        self.table = QtWidgets.QTableView()
        self.table.setModel(self._proxy)
        self.table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.table.setVerticalScrollMode(
            QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        layout.addWidget(self.table)

        # --- toolbar ----------------------------------------------------
        toolbar = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton("Add")
        self.add_button.setProperty("secondary", "true")
        self.edit_button = QtWidgets.QPushButton("Edit…")
        self.edit_button.setProperty("secondary", "true")
        self.remove_button = QtWidgets.QPushButton("Remove")
        self.remove_button.setProperty("secondary", "true")
        self.close_button = QtWidgets.QPushButton("Sulje")
        self.close_button.setProperty("secondary", "true")
        self.save_button = QtWidgets.QPushButton("Tallenna")
        self.save_button.setProperty("primary", "true")
        for button in (self.add_button, self.edit_button, self.remove_button):
            toolbar.addWidget(button)
        toolbar.addStretch(1)
        toolbar.addWidget(self.close_button)
        toolbar.addWidget(self.save_button)
        layout.addLayout(toolbar)

        self.add_button.clicked.connect(self._on_add)
        self.edit_button.clicked.connect(self._on_edit)
        self.remove_button.clicked.connect(self._on_remove)
        self.close_button.clicked.connect(self.reject)
        self.save_button.clicked.connect(self._on_save)
        self.search_edit.textChanged.connect(self._on_search_changed)
        self._model.rowsInserted.connect(self._update_row_count)
        self._model.rowsRemoved.connect(self._update_row_count)
        self._update_row_count()

    def current_rules(self) -> list[Rule]:
        return self._model.rules

    def _on_search_changed(self, text: str) -> None:
        self._proxy.setFilterFixedString(text)
        self._update_row_count()

    def _update_row_count(self) -> None:
        total = self._model.rowCount()
        shown = self._proxy.rowCount()
        if shown == total:
            self.row_count_label.setText(f"{total} riviä")
        else:
            self.row_count_label.setText(f"{shown} / {total} riviä")

    def _selected_source_row(self) -> int | None:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        return self._proxy.mapToSource(indexes[0]).row()

    def _on_add(self) -> None:
        from dwg2ifc.gui.rule_dialog import RuleEditDialog

        dialog = RuleEditDialog(parent=self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            rule = dialog.rule()
            if rule is not None:
                self._model.append_rule(rule)

    def _on_edit(self) -> None:
        row = self._selected_source_row()
        if row is None:
            return
        from dwg2ifc.gui.rule_dialog import RuleEditDialog

        dialog = RuleEditDialog(rule=self._model.rules[row], parent=self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            rule = dialog.rule()
            if rule is not None:
                self._model.replace_rule(row, rule)

    def _on_remove(self) -> None:
        row = self._selected_source_row()
        if row is None:
            return
        self._model.remove_row(row)

    def _on_save(self) -> None:
        updated = self._profile.model_copy(update={"rules": self._model.rules})
        try:
            save_active_profile(updated)
        except OSError as exc:  # disk full, permission, …
            _log.exception("Failed to save the active profile")
            QtWidgets.QMessageBox.critical(
                self,
                "Profiilin tallennus epäonnistui",
                f"Profiilia ei voitu tallentaa:\n\n{type(exc).__name__}: {exc}",
            )
            return
        self._profile = updated
        self.profile_saved.emit(updated)
        self.accept()


# QtGui is imported for downstream consumers expecting it from this module.
__all__ = ["ProfileEditorDialog"]
_ = QtGui
