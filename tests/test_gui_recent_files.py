"""Plan D Task 22: recent files store keeps the latest 5 DXF paths."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _make_store(tmp_path):
    from PySide6 import QtCore

    from dxf2ifc.gui.recent_files import RecentFilesStore

    settings = QtCore.QSettings(str(tmp_path / "settings.ini"), QtCore.QSettings.Format.IniFormat)
    return RecentFilesStore(settings=settings)


def test_recent_files_records_unique_paths_in_lru_order(qtbot, tmp_path):
    store = _make_store(tmp_path)
    assert store.list() == []
    for i in range(7):
        store.add(f"/data/{i}.dxf")
    paths = store.list()
    assert len(paths) == 5
    assert paths[0] == "/data/6.dxf"
    assert paths[-1] == "/data/2.dxf"


def test_recent_files_promotes_existing_path_without_duplicating(qtbot, tmp_path):
    store = _make_store(tmp_path)
    for path in ("/a.dxf", "/b.dxf", "/c.dxf"):
        store.add(path)
    store.add("/a.dxf")
    paths = store.list()
    assert paths.count("/a.dxf") == 1
    assert paths[0] == "/a.dxf"


def test_recent_files_persists_across_store_instances(qtbot, tmp_path):
    store = _make_store(tmp_path)
    store.add("/x.dxf")
    fresh = _make_store(tmp_path)
    assert fresh.list() == ["/x.dxf"]


def test_recent_files_last_profile_path_round_trips(qtbot, tmp_path):
    store = _make_store(tmp_path)
    assert store.last_profile_path is None
    store.last_profile_path = "/profiles/custom.toml"
    fresh = _make_store(tmp_path)
    assert fresh.last_profile_path == "/profiles/custom.toml"


def test_recent_files_last_profile_path_clears_on_none(qtbot, tmp_path):
    store = _make_store(tmp_path)
    store.last_profile_path = "/profiles/custom.toml"
    store.last_profile_path = None
    fresh = _make_store(tmp_path)
    assert fresh.last_profile_path is None


def test_recent_files_floor_elevation_default_is_zero(qtbot, tmp_path):
    store = _make_store(tmp_path)
    assert store.floor_elevation_mm == 0.0


def test_recent_files_floor_elevation_round_trips(qtbot, tmp_path):
    store = _make_store(tmp_path)
    store.floor_elevation_mm = 12000.0
    fresh = _make_store(tmp_path)
    assert fresh.floor_elevation_mm == 12000.0


def test_recent_files_floor_elevation_negative_round_trips(qtbot, tmp_path):
    """Below-grade reference points (basements, sloped sites) need
    negative offsets — the QSettings round-trip must preserve sign."""
    store = _make_store(tmp_path)
    store.floor_elevation_mm = -2500.0
    fresh = _make_store(tmp_path)
    assert fresh.floor_elevation_mm == -2500.0


def test_recent_files_floor_elevation_handles_string_storage(qtbot, tmp_path):
    """QSettings on Windows can return floats stored as strings depending
    on the backend; the getter coerces back to float."""
    store = _make_store(tmp_path)
    store._settings.setValue("floor_elevation_mm", "15000")
    assert store.floor_elevation_mm == 15000.0


def test_recent_files_floor_elevation_enabled_default_is_true(qtbot, tmp_path):
    """First-launch default — most refrigeration designers draw floor-
    relative and benefit from the offset. Lauri's absolute-coord
    workflow opts out by unticking once."""
    store = _make_store(tmp_path)
    assert store.floor_elevation_enabled is True


def test_recent_files_floor_elevation_enabled_round_trips(qtbot, tmp_path):
    store = _make_store(tmp_path)
    store.floor_elevation_enabled = False
    fresh = _make_store(tmp_path)
    assert fresh.floor_elevation_enabled is False


def test_recent_files_floor_elevation_enabled_handles_string_storage(qtbot, tmp_path):
    """QSettings on Windows returns booleans as 'true'/'false' strings."""
    store = _make_store(tmp_path)
    store._settings.setValue("floor_elevation_enabled", "false")
    assert store.floor_elevation_enabled is False
    store._settings.setValue("floor_elevation_enabled", "true")
    assert store.floor_elevation_enabled is True


