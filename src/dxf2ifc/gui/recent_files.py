"""Persisted MRU list of DXF paths backed by QSettings."""

from __future__ import annotations

from PySide6 import QtCore

_KEY = "recent_files"
_LAST_PROFILE_KEY = "last_profile_path"
_FLOOR_ELEVATION_KEY = "floor_elevation_mm"
_FLOOR_ELEVATION_ENABLED_KEY = "floor_elevation_enabled"
_MAX_ENTRIES = 5


class RecentFilesStore:
    """Store the most-recently-opened DXF paths via QSettings."""

    def __init__(self, *, settings: QtCore.QSettings | None = None) -> None:
        self._settings = settings or QtCore.QSettings("Mcrauli", "dxf2ifc")

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

    @property
    def floor_elevation_mm(self) -> float:
        """Last-entered absolute Z elevation of 1.krs (mm).

        Used to pre-fill the FilePanel input on the next session so the
        user does not retype the same building elevation per conversion.
        Defaults to 0.0 (no offset) when no value has ever been set.
        """
        raw = self._settings.value(_FLOOR_ELEVATION_KEY, 0.0)
        try:
            return float(raw) if raw is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    @floor_elevation_mm.setter
    def floor_elevation_mm(self, value: float) -> None:
        # Always store as float — QSettings round-trips Python floats
        # through Qt's variant system, which on Windows can return them
        # as str. The getter coerces back, so we just store float here.
        self._settings.setValue(_FLOOR_ELEVATION_KEY, float(value))
        self._settings.sync()

    @property
    def floor_elevation_enabled(self) -> bool:
        """Whether the user wants the 1.krs absolute Z offset applied.

        Default ``True`` because most Finnish refrigeration designers draw
        floor-relative (DXF Z=0 at slab) and rely on this offset to land
        the IFC at the project's absolute Finnish elevation. Designers who
        already draw in absolute coords (Lauri's own workflow) untick the
        checkbox once and the choice persists per machine.
        """
        raw = self._settings.value(_FLOOR_ELEVATION_ENABLED_KEY, True)
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            return raw.strip().lower() in ("true", "1", "yes")
        return bool(raw)

    @floor_elevation_enabled.setter
    def floor_elevation_enabled(self, value: bool) -> None:
        self._settings.setValue(_FLOOR_ELEVATION_ENABLED_KEY, bool(value))
        self._settings.sync()
