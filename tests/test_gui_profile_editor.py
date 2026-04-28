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


def test_profile_editor_load_button_replaces_rules(qtbot, tmp_path):
    from unittest.mock import patch

    from dxf2ifc.gui.profile_editor import ProfileEditorDialog
    from dxf2ifc.profiles.loader import dump_profile, load_default_profile
    from dxf2ifc.profiles.schema import Profile, Rule

    default = load_default_profile()
    custom_path = tmp_path / "tiny.toml"
    tiny = Profile(
        name="tiny",
        ifc_schema="IFC4",
        rules=[
            Rule(
                layer_pattern="ONE",
                ifc_type="IfcWall",
                predefined_type="STANDARD",
                talo2000_code="1241",
                talo2000_name="Ulkoseinät",
            )
        ],
    )
    dump_profile(tiny, str(custom_path))

    dialog = ProfileEditorDialog(default)
    qtbot.addWidget(dialog)
    assert dialog.table.model().rowCount() == len(default.rules)

    with patch(
        "dxf2ifc.gui.profile_editor.QtWidgets.QFileDialog.getOpenFileName",
        return_value=(str(custom_path), "TOML files (*.toml)"),
    ):
        dialog.load_button.click()

    assert dialog.table.model().rowCount() == 1
    assert dialog.current_rules()[0].layer_pattern == "ONE"


def test_profile_editor_load_emits_loaded_signal(qtbot, tmp_path):
    from unittest.mock import patch

    from dxf2ifc.gui.profile_editor import ProfileEditorDialog
    from dxf2ifc.profiles.loader import dump_profile, load_default_profile

    default = load_default_profile()
    target = tmp_path / "snapshot.toml"
    dump_profile(default, str(target))

    dialog = ProfileEditorDialog(default)
    qtbot.addWidget(dialog)

    received: list[str] = []
    dialog.profile_loaded.connect(received.append)

    with patch(
        "dxf2ifc.gui.profile_editor.QtWidgets.QFileDialog.getOpenFileName",
        return_value=(str(target), "TOML files (*.toml)"),
    ):
        dialog.load_button.click()

    assert received == [str(target)]
