"""Plan D Task 2: gui.app.run + placeholder MainWindow opens via qtbot."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_main_window_opens_with_expected_title(qtbot):
    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert window.windowTitle() == "dxf2ifc"


def test_main_window_has_splitter_layout_and_status_bar(qtbot):
    from PySide6 import QtWidgets

    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    splitter = window.findChild(QtWidgets.QSplitter)
    assert splitter is not None
    assert splitter.count() == 2
    assert window.statusBar() is not None


def _menu_action_texts(window) -> list[str]:
    texts: list[str] = []
    for menu_action in window.menuBar().actions():
        menu = menu_action.menu()
        if menu is None:
            continue
        for action in menu.actions():
            if action.isSeparator():
                continue
            text = action.text()
            if text:
                texts.append(text)
    return texts


def test_main_window_menubar_has_expected_actions(qtbot):
    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    texts = _menu_action_texts(window)
    assert "Open DXF…" in texts
    assert "Quit" in texts
    assert "About" in texts


def test_main_window_quit_action_closes_window(qtbot):
    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window._quit_action.trigger()
    assert not window.isVisible()


def test_main_window_set_status_levels(qtbot):
    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    bar = window.statusBar()

    window.set_status("Converting…")
    assert bar.currentMessage() == "Converting…"
    assert bar.property("level") == "info"

    window.set_status("Done", level="success")
    assert bar.currentMessage() == "Done"
    assert bar.property("level") == "success"

    window.set_status("Boom", level="error")
    assert bar.currentMessage() == "Boom"
    assert bar.property("level") == "error"


def test_main_window_convert_flow_updates_status_on_success(qtbot, tmp_path):
    from unittest.mock import patch

    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    panel = window.file_panel
    panel.input_edit.setText(str(tmp_path / "in.dxf"))
    panel.output_edit.setText(str(tmp_path / "out.ifc"))

    with patch("dxf2ifc.gui.convert_worker.convert_dxf", return_value=({}, None)):
        with qtbot.waitSignal(window.convert_finished, timeout=2000):
            panel.convert_button.click()

    bar = window.statusBar()
    assert "Done" in bar.currentMessage()
    assert bar.property("level") == "success"
    assert panel.convert_button.isEnabled()


def test_main_window_convert_flow_disables_button_during_run(qtbot, tmp_path):
    from unittest.mock import patch

    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    panel = window.file_panel
    panel.input_edit.setText(str(tmp_path / "in.dxf"))
    panel.output_edit.setText(str(tmp_path / "out.ifc"))

    with patch("dxf2ifc.gui.convert_worker.convert_dxf", return_value=({}, None)):
        panel.convert_button.click()
        assert not panel.convert_button.isEnabled()
        qtbot.waitUntil(lambda: panel.convert_button.isEnabled(), timeout=2000)


def test_main_window_profile_menu_has_edit_action(qtbot):
    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    texts = _menu_action_texts(window)
    assert "Edit profile…" in texts


def test_main_window_apply_profile_after_editor_save(qtbot, fixtures_dir, tmp_path):
    from dxf2ifc.gui.app import MainWindow
    from dxf2ifc.profiles.loader import dump_profile, load_default_profile
    from dxf2ifc.profiles.schema import Profile, Rule

    window = MainWindow()
    qtbot.addWidget(window)
    window.file_panel.input_edit.setText(str(fixtures_dir / "simple_wall.dxf"))
    window.file_panel.input_edit.editingFinished.emit()

    extended = load_default_profile()
    extended_rules = list(extended.rules) + [
        Rule(
            layer_pattern="CUSTOM-LAYER*",
            entity_kind="LINE",
            ifc_type="IfcWall",
            talo2000_code="9999",
            talo2000_name="Custom",
        )
    ]
    extended = Profile.model_validate({**extended.model_dump(), "rules": extended_rules})

    target = tmp_path / "custom.toml"
    dump_profile(extended, target)
    window.apply_profile_from_path(target)

    assert any(r.layer_pattern == "CUSTOM-LAYER*" for r in window._profile.rules)


def test_main_window_layer_table_updates_when_input_path_set(qtbot, fixtures_dir):
    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    assert window.layer_table.rowCount() == 0
    window.file_panel.input_edit.setText(str(fixtures_dir / "simple_wall.dxf"))
    window.file_panel.input_edit.editingFinished.emit()
    assert window.layer_table.rowCount() >= 1
    layers = [window.layer_table.item(r, 0).text() for r in range(window.layer_table.rowCount())]
    assert "KYL-ULKOSEINA" in layers


def test_main_window_logs_report_errors_in_preview_log(qtbot):
    from dxf2ifc.core.quality import ValidationReport
    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    report = ValidationReport(
        errors=[{"level": "ERROR", "message": "fake validation error 42"}],
        warnings=[
            {"level": "WARNING", "message": "missing Talo2000 classification on IfcWall 'X'"}
        ],
        summary="IFC4: 1 errors, 1 warnings",
    )
    window._on_report_ready(report)

    text = window.preview_log.toPlainText()
    assert "fake validation error 42" in text
    assert "missing Talo2000 classification" in text
    assert "IFC4: 1 errors" in text


def test_main_window_convert_flow_passes_validate_true(qtbot, tmp_path):
    from unittest.mock import patch

    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    panel = window.file_panel
    panel.input_edit.setText(str(tmp_path / "in.dxf"))
    panel.output_edit.setText(str(tmp_path / "out.ifc"))

    with patch("dxf2ifc.gui.convert_worker.convert_dxf", return_value=({}, None)) as mock_convert:
        with qtbot.waitSignal(window.convert_finished, timeout=2000):
            panel.convert_button.click()

    assert mock_convert.call_args.kwargs.get("validate") is True


def test_main_window_renders_h1_and_caption_labels(qtbot):
    from PySide6 import QtWidgets

    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    labels = window.findChildren(QtWidgets.QLabel)
    h1 = next((lbl for lbl in labels if lbl.property("role") == "h1"), None)
    caption = next((lbl for lbl in labels if lbl.property("role") == "caption"), None)
    assert h1 is not None and h1.text() == "dxf2ifc"
    assert caption is not None and "DXF" in caption.text()


def test_run_is_callable():
    from dxf2ifc.gui.app import run

    assert callable(run)


def _isolated_store(tmp_path):
    from PySide6 import QtCore

    from dxf2ifc.gui.recent_files import RecentFilesStore

    settings = QtCore.QSettings(str(tmp_path / "settings.ini"), QtCore.QSettings.Format.IniFormat)
    return RecentFilesStore(settings=settings)


def test_main_window_loads_last_profile_on_startup(qtbot, tmp_path):
    from dxf2ifc.gui.app import MainWindow
    from dxf2ifc.profiles.loader import dump_profile, load_default_profile
    from dxf2ifc.profiles.schema import Profile, Rule

    custom_path = tmp_path / "last.toml"
    dump_profile(
        Profile(
            name="last",
            ifc_schema="IFC4",
            rules=[
                Rule(
                    layer_pattern="ZZ",
                    ifc_type="IfcWall",
                    predefined_type="STANDARD",
                    talo2000_code="1241",
                    talo2000_name="Ulkoseinät",
                )
            ],
        ),
        str(custom_path),
    )

    store = _isolated_store(tmp_path)
    store.last_profile_path = str(custom_path)

    window = MainWindow(recent_files=store)
    qtbot.addWidget(window)

    assert [r.layer_pattern for r in window._profile.rules] == ["ZZ"]
    _ = load_default_profile  # imported to keep parity with sibling tests


def test_main_window_persists_profile_path_after_load(qtbot, tmp_path):
    from dxf2ifc.gui.app import MainWindow
    from dxf2ifc.profiles.loader import dump_profile, load_default_profile

    snapshot = tmp_path / "snapshot.toml"
    dump_profile(load_default_profile(), str(snapshot))

    store = _isolated_store(tmp_path)
    window = MainWindow(recent_files=store)
    qtbot.addWidget(window)

    window.apply_profile_from_path(str(snapshot))
    assert store.last_profile_path == str(snapshot)


def test_main_window_preview_log_summarizes_dxf_on_open(qtbot, fixtures_dir):
    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.file_panel.input_edit.setText(str(fixtures_dir / "simple_wall.dxf"))
    window.file_panel.input_edit.editingFinished.emit()
    text = window.preview_log.text()
    assert "simple_wall.dxf" in text
    assert "KYL-ULKOSEINA" in text


def test_main_window_skips_missing_last_profile(qtbot, tmp_path):
    from dxf2ifc.gui.app import MainWindow

    store = _isolated_store(tmp_path)
    store.last_profile_path = str(tmp_path / "ghost.toml")

    window = MainWindow(recent_files=store)
    qtbot.addWidget(window)

    # Falls back to default profile when last_profile_path no longer exists.
    assert window._profile.name != "last"
    # And forgets the dangling path.
    assert store.last_profile_path is None
