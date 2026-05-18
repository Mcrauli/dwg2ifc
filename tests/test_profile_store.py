"""Per-user active-profile store (profiles/store.py)."""

from __future__ import annotations

import pytest

from dwg2ifc.profiles.loader import load_default_profile
from dwg2ifc.profiles.store import (
    active_profile_path,
    clear_active_profile,
    load_active_profile,
    save_active_profile,
)


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    """Redirect %APPDATA% so the store writes inside the test's tmp dir."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def test_active_profile_path_lives_under_appdata(appdata):
    assert active_profile_path() == appdata / "Mcrauli" / "dwg2ifc" / "active_profile.toml"


def test_save_then_load_round_trips(appdata):
    profile = load_default_profile()
    assert load_active_profile() is None
    save_active_profile(profile)
    loaded = load_active_profile()
    assert loaded is not None
    assert loaded.name == profile.name
    assert len(loaded.rules) == len(profile.rules)


def test_save_creates_parent_dirs(appdata):
    assert not active_profile_path().parent.exists()
    save_active_profile(load_default_profile())
    assert active_profile_path().is_file()


def test_load_returns_none_when_missing(appdata):
    assert load_active_profile() is None


def test_load_returns_none_for_corrupt_file(appdata):
    path = active_profile_path()
    path.parent.mkdir(parents=True)
    path.write_text("this is not = valid [toml\n", encoding="utf-8")
    assert load_active_profile() is None


def test_clear_removes_saved_profile(appdata):
    save_active_profile(load_default_profile())
    assert active_profile_path().is_file()
    clear_active_profile()
    assert not active_profile_path().is_file()


def test_clear_is_noop_when_nothing_saved(appdata):
    clear_active_profile()  # must not raise


def test_save_leaves_no_temp_files_behind(appdata):
    save_active_profile(load_default_profile())
    leftovers = list(active_profile_path().parent.glob(".active_profile_*"))
    assert leftovers == []
