"""Per-user persistence of the active GUI mapping profile.

The profile editor saves the user's edited profile here instead of to a
file the user has to remember and re-load. The path is per-Windows-user
(under ``%APPDATA%``), writable without admin rights, and created on
demand — it never touches shared/global state, the registry (beyond the
existing QSettings), or the user's AutoCAD profile.

The CLI is unaffected: it still takes an explicit ``--profile`` TOML path
and falls back to the bundled default. This store is GUI-only.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from dxf2ifc.profiles.loader import dump_profile, load_profile
from dxf2ifc.profiles.schema import Profile

_log = logging.getLogger(__name__)

_ORG = "Mcrauli"
_APP = "dxf2ifc"
_FILENAME = "active_profile.toml"


def _app_data_root() -> Path:
    """Per-user writable config root.

    ``%APPDATA%`` on Windows (always set for an interactive user); a
    ``~/.config`` style fallback elsewhere so the test suite and any
    non-Windows dev machine still work.
    """
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata)
    return Path.home() / ".config"


def active_profile_path() -> Path:
    """Fixed per-user path of the saved active profile."""
    return _app_data_root() / _ORG / _APP / _FILENAME


def save_active_profile(profile: Profile) -> None:
    """Persist ``profile`` to :func:`active_profile_path`, atomically.

    Writes to a temp file in the target directory and ``os.replace``s it
    over the destination, so a crash mid-write can never leave a
    half-written profile behind. Raises ``OSError`` on IO failure — the
    caller (the editor dialog) surfaces that to the user.
    """
    target = active_profile_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(target.parent), prefix=".active_profile_", suffix=".tmp"
    )
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        dump_profile(profile, tmp_path)
        os.replace(tmp_path, target)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def load_active_profile() -> Profile | None:
    """Return the saved active profile, or ``None``.

    ``None`` means *use the bundled default*: either nothing has been
    saved yet, or the saved file is unreadable / fails schema validation
    (logged, never raised — a corrupt file must not block startup).
    """
    path = active_profile_path()
    if not path.is_file():
        return None
    try:
        return load_profile(path)
    except Exception:  # noqa: BLE001 — corrupt file must not crash startup
        _log.exception("Saved active profile at %s is unreadable", path)
        return None


def clear_active_profile() -> None:
    """Delete the saved active profile if it exists (no-op otherwise)."""
    active_profile_path().unlink(missing_ok=True)
