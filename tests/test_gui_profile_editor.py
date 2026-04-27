"""Plan D Task 18: ProfileEditorDialog shows all rules with Add/Edit/Remove/Save."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_profile_editor_lists_all_default_rules(qtbot):
    from PySide6 import QtWidgets

    from dxf2ifc.gui.profile_editor import ProfileEditorDialog
    from dxf2ifc.profiles.loader import load_default_profile

    profile = load_default_profile()
    dialog = ProfileEditorDialog(profile)
    qtbot.addWidget(dialog)
    table = dialog.findChild(QtWidgets.QTableView)
    assert table is not None
    assert table.model().rowCount() == len(profile.rules)
    assert table.model().columnCount() == 6


def test_profile_editor_remove_drops_selected_rule(qtbot):
    from dxf2ifc.gui.profile_editor import ProfileEditorDialog
    from dxf2ifc.profiles.loader import load_default_profile

    profile = load_default_profile()
    dialog = ProfileEditorDialog(profile)
    qtbot.addWidget(dialog)
    initial = dialog.table.model().rowCount()
    dialog.table.selectRow(0)
    dialog.remove_button.click()
    assert dialog.table.model().rowCount() == initial - 1


def test_profile_editor_save_writes_via_dump_profile(qtbot, tmp_path):
    from unittest.mock import patch

    from PySide6 import QtWidgets

    from dxf2ifc.gui.profile_editor import ProfileEditorDialog
    from dxf2ifc.profiles.loader import load_default_profile

    profile = load_default_profile()
    dialog = ProfileEditorDialog(profile)
    qtbot.addWidget(dialog)

    target = tmp_path / "saved.toml"
    with patch(
        "dxf2ifc.gui.profile_editor.QtWidgets.QFileDialog.getSaveFileName",
        return_value=(str(target), "TOML files (*.toml)"),
    ):
        dialog.save_button.click()

    assert target.is_file()
    assert "[[rules]]" in target.read_text(encoding="utf-8") or target.read_text(
        encoding="utf-8"
    ).startswith("[profile]")
    # Suppress unused-import warning for QtWidgets when running ruff outside pytest.
    _ = QtWidgets
