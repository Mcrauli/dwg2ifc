"""MainWindow startup-profile behaviour: auto-load from the store, with
a bundled-default fallback when nothing is saved or the file is corrupt."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def test_main_window_loads_saved_profile_on_startup(qtbot, appdata):
    from dxf2ifc.gui.main_window import MainWindow
    from dxf2ifc.profiles.schema import Profile, Rule
    from dxf2ifc.profiles.store import save_active_profile

    custom = Profile(
        name="custom-test-profile",
        ifc_schema="IFC4",
        rules=[
            Rule(
                layer_pattern="X",
                ifc_type="IfcWall",
                predefined_type="STANDARD",
                domain="ARK",
                talo2000_code="1241",
                talo2000_name="Ulkoseinät",
            )
        ],
    )
    save_active_profile(custom)

    window = MainWindow()
    qtbot.addWidget(window)
    assert window._profile.name == "custom-test-profile"


def test_main_window_falls_back_to_default_when_nothing_saved(qtbot, appdata):
    from dxf2ifc.gui.main_window import MainWindow
    from dxf2ifc.profiles.loader import load_default_profile

    window = MainWindow()
    qtbot.addWidget(window)
    assert window._profile.name == load_default_profile().name


def test_main_window_warns_on_corrupt_saved_profile(qtbot, appdata):
    from dxf2ifc.gui.main_window import MainWindow
    from dxf2ifc.profiles.loader import load_default_profile
    from dxf2ifc.profiles.store import active_profile_path

    path = active_profile_path()
    path.parent.mkdir(parents=True)
    path.write_text("not = valid [toml\n", encoding="utf-8")

    window = MainWindow()
    qtbot.addWidget(window)
    # fell back to the bundled default …
    assert window._profile.name == load_default_profile().name
    # … and surfaced a warning in the status bar
    assert "viallinen" in window.statusBar().currentMessage().lower()
