"""Persisted MRU list of DXF paths backed by QSettings."""

from __future__ import annotations

from PySide6 import QtCore

_KEY = "recent_files"
_MAX_ENTRIES = 5


class RecentFilesStore:
    """Store the most-recently-opened DXF paths via QSettings."""

    def __init__(self, *, settings: QtCore.QSettings | None = None) -> None:
        self._settings = settings or QtCore.QSettings("Mcrauli", "dwg2ifc")

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
