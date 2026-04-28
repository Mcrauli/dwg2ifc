"""Persisted MRU list of DXF paths backed by QSettings."""

from __future__ import annotations

from PySide6 import QtCore

_KEY = "recent_files"
_LAST_PROFILE_KEY = "last_profile_path"
_MAX_ENTRIES = 5


class RecentFilesStore:
    """Store the most-recently-opened DXF paths via QSettings."""

    def __init__(self, *, settings: QtCore.QSettings | None = None) -> None:
        self._settings = settings or QtCore.QSettings("Radika", "dxf2ifc")

    def list(self) -> list[str]:
        raw = self._settings.value(_KEY, [], type=list)
        return [str(item) for item in raw if item]

    def add(self, path: str) -> None:
        existing = [p for p in self.list() if p != path]
        updated = [path, *existing][:_MAX_ENTRIES]
        self._settings.setValue(_KEY, updated)
        self._settings.sync()

    def clear(self) -> None:
        self._settings.remove(_KEY)
        self._settings.sync()

    @property
    def last_profile_path(self) -> str | None:
        raw = self._settings.value(_LAST_PROFILE_KEY, None)
        return str(raw) if raw else None

    @last_profile_path.setter
    def last_profile_path(self, path: str | None) -> None:
        if path is None:
            self._settings.remove(_LAST_PROFILE_KEY)
        else:
            self._settings.setValue(_LAST_PROFILE_KEY, path)
        self._settings.sync()
