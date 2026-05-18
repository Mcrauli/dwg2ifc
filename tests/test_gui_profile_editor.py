"""ProfileEditorDialog: searchable rule table + Save-to-store.

The editor no longer has file-path Load/Save dialogs — Save persists to
the per-user store (profiles/store.py) and emits the edited Profile.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6 import QtWidgets


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def test_profile_editor_lists_all_default_rules(qtbot):
    from dwg2ifc.gui.profile_editor import ProfileEditorDialog
    from dwg2ifc.profiles.loader import load_default_profile

    profile = load_default_profile()
    dialog = ProfileEditorDialog(profile)
    qtbot.addWidget(dialog)
    table = dialog.findChild(QtWidgets.QTableView)
    assert table is not None
    assert table.model().rowCount() == len(profile.rules)
    assert table.model().columnCount() == 7


def test_search_filters_rows_and_updates_count(qtbot):
    from dwg2ifc.gui.profile_editor import ProfileEditorDialog
    from dwg2ifc.profiles.loader import load_default_profile

    profile = load_default_profile()
    dialog = ProfileEditorDialog(profile)
    qtbot.addWidget(dialog)
    total = dialog._model.rowCount()
    assert dialog.row_count_label.text() == f"{total} riviä"

    dialog.search_edit.setText("zzz-nonexistent-zzz")
    assert dialog._proxy.rowCount() == 0
    assert dialog.row_count_label.text() == f"0 / {total} riviä"

    dialog.search_edit.setText("")
    assert dialog._proxy.rowCount() == total
    assert dialog.row_count_label.text() == f"{total} riviä"


def test_search_matches_ifc_type_column(qtbot):
    from dwg2ifc.gui.profile_editor import ProfileEditorDialog
    from dwg2ifc.profiles.loader import load_default_profile

    profile = load_default_profile()
    dialog = ProfileEditorDialog(profile)
    qtbot.addWidget(dialog)
    dialog.search_edit.setText("evaporator")
    shown = dialog._proxy.rowCount()
    assert 0 < shown < dialog._model.rowCount()
    for proxy_row in range(shown):
        src = dialog._proxy.mapToSource(dialog._proxy.index(proxy_row, 0)).row()
        assert "evaporator" in dialog._model.rules[src].ifc_type.lower()


def test_remove_drops_correct_rule_when_filtered(qtbot):
    """With the table filtered, Remove must delete the source rule that
    backs the selected proxy row — not whatever sits at that source index."""
    from dwg2ifc.gui.profile_editor import ProfileEditorDialog
    from dwg2ifc.profiles.loader import load_default_profile

    profile = load_default_profile()
    dialog = ProfileEditorDialog(profile)
    qtbot.addWidget(dialog)
    dialog.search_edit.setText("evaporator")
    first_src = dialog._proxy.mapToSource(dialog._proxy.index(0, 0)).row()
    target_pattern = dialog._model.rules[first_src].layer_pattern
    initial = dialog._model.rowCount()

    dialog.table.selectRow(0)
    dialog.remove_button.click()

    assert dialog._model.rowCount() == initial - 1
    assert target_pattern not in [r.layer_pattern for r in dialog._model.rules]


def test_save_persists_to_store_and_emits_profile(qtbot, appdata):
    from dwg2ifc.gui.profile_editor import ProfileEditorDialog
    from dwg2ifc.profiles.loader import load_default_profile
    from dwg2ifc.profiles.store import active_profile_path, load_active_profile

    profile = load_default_profile()
    dialog = ProfileEditorDialog(profile)
    qtbot.addWidget(dialog)
    dialog.table.selectRow(0)
    dialog.remove_button.click()  # make one edit

    received = []
    dialog.profile_saved.connect(received.append)
    dialog.save_button.click()

    assert active_profile_path().is_file()
    assert len(received) == 1
    assert len(received[0].rules) == len(profile.rules) - 1
    saved = load_active_profile()
    assert saved is not None
    assert len(saved.rules) == len(profile.rules) - 1


def test_save_failure_shows_error_and_keeps_dialog_open(qtbot, appdata):
    from unittest.mock import patch

    from dwg2ifc.gui.profile_editor import ProfileEditorDialog
    from dwg2ifc.profiles.loader import load_default_profile

    dialog = ProfileEditorDialog(load_default_profile())
    qtbot.addWidget(dialog)
    received = []
    dialog.profile_saved.connect(received.append)

    with (
        patch(
            "dwg2ifc.gui.profile_editor.save_active_profile",
            side_effect=OSError("disk full"),
        ),
        patch(
            "dwg2ifc.gui.profile_editor.QtWidgets.QMessageBox.critical"
        ) as msgbox,
    ):
        dialog.save_button.click()

    assert msgbox.called
    assert received == []
    assert dialog.result() != QtWidgets.QDialog.DialogCode.Accepted


def test_close_button_rejects_without_saving(qtbot, appdata):
    from dwg2ifc.gui.profile_editor import ProfileEditorDialog
    from dwg2ifc.profiles.loader import load_default_profile
    from dwg2ifc.profiles.store import active_profile_path

    dialog = ProfileEditorDialog(load_default_profile())
    qtbot.addWidget(dialog)
    dialog.table.selectRow(0)
    dialog.remove_button.click()
    dialog.close_button.click()

    assert dialog.result() == QtWidgets.QDialog.DialogCode.Rejected
    assert not active_profile_path().is_file()
