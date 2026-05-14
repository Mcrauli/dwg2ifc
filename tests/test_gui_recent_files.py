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



