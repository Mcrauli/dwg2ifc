"""Self-update for the bundled Windows exe.

Polls GitHub Releases for newer versions of dxf2ifc and exposes a
helper to download + swap + restart. The swap relies on a Windows
quirk: a running ``.exe`` cannot be deleted but it CAN be renamed,
so the update flow is:

    1. Download new exe to a temp path
    2. Rename current ``dxf2ifc-X.Y.Z.exe`` → ``…X.Y.Z.exe.old``
    3. Move the temp exe into the freed slot
    4. Spawn the new exe detached
    5. Quit the running process; the OS releases the ``.old`` handle
       and ``cleanup_old_exe()`` deletes it on the next startup.

When running from source (``python -m dxf2ifc.gui``) the entire
mechanism is no-op — :func:`is_running_bundled` returns ``False`` and
:func:`check_for_update` exits early.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from packaging.version import InvalidVersion, Version

from dxf2ifc import __version__

DEFAULT_REPO: str = "Mcrauli/dxf2ifc"
GITHUB_API_URL: str = "https://api.github.com/repos/{repo}/releases"
USER_AGENT: str = f"dxf2ifc-updater/{__version__}"


@dataclass(frozen=True)
class UpdateInfo:
    """Metadata for a release that is newer than the current version."""

    version: str
    """PEP 440-normalised version string (e.g. ``"0.1.0"``)."""

    tag: str
    """GitHub release tag (e.g. ``"v0.1.0-alpha"``)."""

    release_url: str
    """Human-readable URL of the release page on GitHub."""

    download_url: str
    """Direct asset download URL for the bundled ``.exe``."""

    download_size: int
    """Size of the asset in bytes (from the GitHub API ``size`` field)."""

    notes: str
    """Markdown release notes (the ``body`` field)."""


def is_running_bundled() -> bool:
    """Return True only when running inside the PyInstaller bundle.

    Self-update is meaningless when the user runs ``python -m dxf2ifc.gui``
    against a source checkout — the swap target would be the Python
    interpreter, not the dxf2ifc exe.
    """
    return bool(getattr(sys, "frozen", False))


def _normalise_version(raw: str) -> Version | None:
    """Best-effort PEP 440 normalisation. Strips a leading ``v`` and
    converts ``-alpha``/``-beta``/``-rc`` suffixes that GitHub tags use
    but PEP 440 does not. Returns ``None`` on unparseable input."""
    cleaned = raw.lstrip("vV").strip()
    # Map the GitHub-style suffixes to PEP 440-style "a"/"b"/"rc".
    cleaned = (
        cleaned.replace("-alpha", "a0")
        .replace("-beta", "b0")
        .replace("-rc", "rc0")
    )
    try:
        return Version(cleaned)
    except InvalidVersion:
        return None


def _select_asset(release: dict) -> tuple[str, int] | None:
    """Pick the bundled ``.exe`` asset from a release JSON payload.

    Skips ``.sha256`` sidecar files and ``LICENSES.md`` so we land on
    the actual installer. Returns ``(download_url, size_bytes)`` or
    ``None`` if no exe asset is published with this release.
    """
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        if not name.lower().endswith(".exe"):
            continue
        if name.lower().endswith(".sha256"):
            continue
        return asset.get("browser_download_url"), int(asset.get("size", 0))
    return None


def _open_releases(repo: str, *, timeout: float) -> list[dict]:
    """Fetch the releases list from the GitHub REST API."""
    url = GITHUB_API_URL.format(repo=repo) + "?per_page=10"
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read()
    data = json.loads(payload)
    if not isinstance(data, list):
        return []
    return data


def check_for_update(
    *,
    current_version: str = __version__,
    repo: str = DEFAULT_REPO,
    include_prereleases: bool = True,
    timeout: float = 5.0,
) -> UpdateInfo | None:
    """Return :class:`UpdateInfo` if a newer release has an exe asset.

    ``include_prereleases=True`` so that users on ``v0.1.0-alpha`` see
    later alphas/betas. ``current_version`` defaults to the installed
    package version. Returns ``None`` for any of: no newer release,
    network failure, GitHub rate-limit, malformed payload — silent so
    that a transient failure never blocks app startup.
    """
    current = _normalise_version(current_version)
    if current is None:
        return None
    try:
        releases = _open_releases(repo, timeout=timeout)
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    except json.JSONDecodeError:
        return None

    newest: tuple[Version, dict] | None = None
    for release in releases:
        if release.get("draft"):
            continue
        if release.get("prerelease") and not include_prereleases:
            continue
        tag = release.get("tag_name", "")
        version = _normalise_version(tag)
        if version is None or version <= current:
            continue
        if newest is None or version > newest[0]:
            newest = (version, release)

    if newest is None:
        return None

    version, release = newest
    asset = _select_asset(release)
    if asset is None:
        return None  # Newer release exists but no exe attached yet.
    download_url, download_size = asset
    return UpdateInfo(
        version=str(version),
        tag=release.get("tag_name", ""),
        release_url=release.get("html_url", ""),
        download_url=download_url,
        download_size=download_size,
        notes=release.get("body", "") or "",
    )


def download_asset(
    url: str,
    target_path: Path,
    *,
    progress_cb: Callable[[int, int], None] | None = None,
    chunk_size: int = 256 * 1024,
    timeout: float = 30.0,
) -> None:
    """Stream an asset to ``target_path``, calling ``progress_cb(done, total)``.

    Writes to ``target_path.with_suffix(target_path.suffix + '.part')``
    first and renames on success — partial downloads do not pollute the
    target slot if the connection drops.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    part_path = target_path.with_suffix(target_path.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        with open(part_path, "wb") as out:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                out.write(chunk)
                downloaded += len(chunk)
                if progress_cb is not None:
                    try:
                        progress_cb(downloaded, total)
                    except Exception:  # noqa: BLE001 — UI errors must not abort
                        pass
    if target_path.exists():
        target_path.unlink()
    part_path.rename(target_path)


def _old_path_for(exe_path: Path) -> Path:
    """The ``.old`` sidecar where the previous exe is parked during swap."""
    return exe_path.with_suffix(exe_path.suffix + ".old")


def cleanup_old_exe(exe_path: Path | None = None) -> None:
    """Delete a leftover ``.old`` exe from a previous self-update.

    Called once on GUI startup. Silent on any error: the file may still
    be locked by a not-yet-released handle in which case the next
    startup will catch it.
    """
    if exe_path is None:
        if not is_running_bundled():
            return
        exe_path = Path(sys.executable)
    old_path = _old_path_for(exe_path)
    if not old_path.exists():
        return
    try:
        old_path.unlink()
    except OSError:
        pass


def schedule_replace_and_restart(
    new_exe: Path,
    *,
    current_exe: Path | None = None,
    extra_args: list[str] | None = None,
) -> None:
    """Swap ``current_exe`` for ``new_exe`` and launch the new exe.

    Caller is responsible for quitting the Qt event loop right after
    this returns so that the OS releases the ``.old`` handle. The
    helper is synchronous: by the time it returns, ``current_exe``
    points at the new bytes and a detached child has been spawned.

    Raises :class:`RuntimeError` if not running inside a bundled exe.
    """
    if current_exe is None:
        if not is_running_bundled():
            raise RuntimeError(
                "schedule_replace_and_restart requires a frozen exe; "
                "running from source has nothing meaningful to swap."
            )
        current_exe = Path(sys.executable)

    if not new_exe.exists():
        raise FileNotFoundError(f"new exe not found: {new_exe}")
    if not current_exe.exists():
        raise FileNotFoundError(f"current exe not found: {current_exe}")

    old_path = _old_path_for(current_exe)
    if old_path.exists():
        try:
            old_path.unlink()
        except OSError:
            pass  # leftover from earlier swap; tolerable, gets retried later

    # Windows quirk: os.rename on the running exe succeeds; the OS
    # tracks the file by handle, not by path. Once the running process
    # exits, the .old file becomes deletable.
    current_exe.rename(old_path)
    shutil.move(str(new_exe), str(current_exe))

    args = [str(current_exe), *(extra_args or [])]
    if sys.platform == "win32":
        # DETACHED_PROCESS so the child survives our exit; CREATE_NEW_PROCESS_GROUP
        # so Ctrl-C in any parent shell does not propagate.
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(args, creationflags=flags, close_fds=True)
    else:
        # macOS/Linux: just fork-exec via Popen. We do not actually ship
        # bundled binaries for these platforms but the helper stays
        # portable for tests on dev machines.
        subprocess.Popen(args, start_new_session=True, close_fds=True)
