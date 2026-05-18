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

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
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


def fetch_expected_sha256(asset_url: str, *, timeout: float = 5.0) -> str | None:
    """Fetch the GitHub Releases ``.sha256`` sidecar for an asset.

    Convention: sidecar URL is the asset URL with ``.sha256`` appended.
    File payload is sha256sum-formatted: ``"<64-hex-digest>  <filename>\\n"``.

    Returns the lowercase hex digest, or ``None`` if the sidecar is
    unreachable, malformed, or the digest is not 64 hex chars. Silent
    failure so a transient sidecar issue never blocks the update — the
    download verification then degrades to size-only via
    ``Content-Length``.
    """
    sidecar_url = asset_url + ".sha256"
    request = urllib.request.Request(sidecar_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("ascii", errors="replace").strip()
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    parts = payload.split()
    if not parts or len(parts[0]) != 64:
        return None
    try:
        bytes.fromhex(parts[0])
    except ValueError:
        return None
    return parts[0].lower()


def download_asset(
    url: str,
    target_path: Path,
    *,
    progress_cb: Callable[[int, int], None] | None = None,
    chunk_size: int = 256 * 1024,
    timeout: float = 30.0,
    expected_sha256: str | None = None,
) -> None:
    """Stream an asset to ``target_path``, calling ``progress_cb(done, total)``.

    Writes to ``target_path.with_suffix(target_path.suffix + '.part')``
    first and renames on success — partial downloads do not pollute the
    target slot if the connection drops.

    When ``expected_sha256`` is given, every downloaded byte feeds a
    SHA-256 hasher streaming-style. On completion the digest is compared
    case-insensitively to ``expected_sha256``. Mismatch → ``.part`` file
    deleted and :class:`ValueError` raised — protects the swap from
    corrupted/truncated downloads (a partial file with a bad embedded
    archive is the most plausible cause of "Failed to start embedded
    python interpreter" right after self-update).
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    part_path = target_path.with_suffix(target_path.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    hasher = hashlib.sha256() if expected_sha256 else None
    with urllib.request.urlopen(request, timeout=timeout) as response:
        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        with open(part_path, "wb") as out:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                out.write(chunk)
                if hasher is not None:
                    hasher.update(chunk)
                downloaded += len(chunk)
                if progress_cb is not None:
                    try:
                        progress_cb(downloaded, total)
                    except Exception:  # noqa: BLE001 — UI errors must not abort
                        pass
    if hasher is not None:
        actual = hasher.hexdigest()
        if actual.lower() != expected_sha256.lower():
            try:
                part_path.unlink()
            except OSError:
                pass
            raise ValueError(
                f"SHA-256 mismatch on {target_path.name}: "
                f"expected {expected_sha256.lower()}, got {actual}"
            )
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


def _restart_log_path() -> Path:
    """Where the delayed-launcher writes its breadcrumb log.

    Single fixed location in ``%TEMP%`` so users (and bug reports) can
    find evidence of a silent restart failure without hunting through
    per-launch temp dirs.
    """
    return Path(tempfile.gettempdir()) / "dxf2ifc_restart.log"


def _cmd_quote(s: str) -> str:
    """Escape a string for use as a double-quoted cmd.exe argument.

    cmd.exe has no real escaping — embedded ``"`` is the only character
    that breaks parsing; replace it with the conventional empty
    ``""`` (``cmd /c`` interprets ``""`` inside a quoted string as a
    literal ``"``). Path strings authored by Windows itself never
    contain ``"``, so this is overwhelmingly a no-op in practice.
    """
    return '"' + s.replace('"', '""') + '"'


def _build_restart_batch(
    current_exe: Path,
    extra_args: list[str] | None,
    delay_seconds: int,
    log_path: Path,
) -> str:
    """Build the cmd.exe batch script the delayed launcher executes.

    The batch sleeps, launches the new exe via ``start ""`` (detached
    from cmd, so cmd can exit without waiting), and self-deletes the
    batch file afterwards. Every step writes a breadcrumb to
    ``log_path`` so silent failures (Defender quarantine, locked file,
    missing exe) can be diagnosed from a stable location.
    """
    args_quoted = ""
    if extra_args:
        args_quoted = " " + " ".join(_cmd_quote(a) for a in extra_args)
    exe_quoted = _cmd_quote(str(current_exe))
    log_quoted = _cmd_quote(str(log_path))
    lines = [
        "@echo off",
        f"echo [%date% %time%] launcher started, will wait {delay_seconds}s >> {log_quoted}",
        f"timeout /t {delay_seconds} /nobreak >nul 2>&1",
        f"echo [%date% %time%] launching {exe_quoted}{args_quoted} >> {log_quoted}",
        f"start \"\" {exe_quoted}{args_quoted}",
        f"if errorlevel 1 (echo [%date% %time%] start FAILED errorlevel=%errorlevel% >> {log_quoted}) else (echo [%date% %time%] start ok >> {log_quoted})",
        "(goto) 2>nul & del \"%~f0\"",
    ]
    # cmd.exe expects CRLF line endings and the OEM codepage; Lauri's
    # install paths are ASCII so the codepage rarely matters, but
    # writing as cp1252 keeps Finnish characters in env-derived paths
    # (e.g. usernames with ä/ö) intact for the breadcrumb log.
    return "\r\n".join(lines) + "\r\n"


def _spawn_delayed_launcher(
    current_exe: Path,
    *,
    extra_args: list[str] | None = None,
    delay_seconds: int = 3,
) -> None:
    """Spawn a hidden helper that waits ``delay_seconds`` then starts ``current_exe``.

    The delay closes a race window observed in the field: the outgoing
    process's ``os._exit(0)`` is not synchronous — Windows takes some
    milliseconds to close handles and release the OS-level lock on the
    just-renamed ``.old`` exe. Spawning the new exe in the same instant
    has been observed to surface "Failed to start embedded python
    interpreter" from the PyInstaller bootloader, plausibly caused by
    Defender real-time scanning the freshly-downloaded unsigned exe at
    the same time as its bootloader extracts to ``%TEMP%``.

    On Windows the helper is a self-deleting ``.cmd`` batch invoked via
    a detached ``cmd.exe`` child. cmd is preferred over powershell here
    because the previous powershell-based launcher failed silently on
    some users' machines (suspected execution-policy or ``Start-Process``
    quirks under ``-NonInteractive``), leaving the app shut down with
    no restart. cmd has no execution policy, no profile, and ``start ""``
    is the canonical Windows way to spawn a detached GUI process.

    A breadcrumb log is appended to ``%TEMP%\\dxf2ifc_restart.log`` on
    every step so a silent failure leaves diagnosable evidence.

    Non-Windows platforms fall back to a direct detached spawn (no
    delay) — we don't ship bundled binaries there, so race conditions
    do not apply; the path exists for tests on dev machines.
    """
    if sys.platform != "win32":
        subprocess.Popen(
            [str(current_exe), *(extra_args or [])],
            start_new_session=True,
            close_fds=True,
        )
        return

    log_path = _restart_log_path()
    batch_dir = Path(tempfile.mkdtemp(prefix="dxf2ifc_restart_"))
    batch_path = batch_dir / "restart.cmd"
    batch_path.write_text(
        _build_restart_batch(current_exe, extra_args, delay_seconds, log_path),
        encoding="cp1252",
    )

    # Best-effort log entry on the Python side: confirms the spawn was
    # at least attempted even if cmd never runs.
    try:
        with log_path.open("a", encoding="cp1252") as fh:
            fh.write(
                f"[python] spawning {batch_path} for {current_exe} "
                f"(delay={delay_seconds}s)\r\n"
            )
    except OSError:
        pass

    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    CREATE_NO_WINDOW = 0x08000000
    flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
    subprocess.Popen(
        ["cmd.exe", "/c", str(batch_path)],
        creationflags=flags,
        close_fds=True,
    )


def schedule_replace_and_restart(
    new_exe: Path,
    *,
    current_exe: Path | None = None,
    extra_args: list[str] | None = None,
    delay_seconds: int = 3,
) -> None:
    """Swap ``current_exe`` for ``new_exe`` and schedule a delayed restart.

    Caller is responsible for quitting the Qt event loop right after
    this returns so that the OS releases the ``.old`` handle. The
    helper is synchronous: by the time it returns, ``current_exe``
    points at the new bytes and a detached PowerShell launcher has
    been spawned that will run the new exe ``delay_seconds`` later.

    The delay (3 s default) lets the outgoing process release the
    ``.old`` exe handle and gives Windows Defender time to finish its
    real-time scan on the freshly-written current exe — both observed
    contributors to "Failed to start embedded python interpreter" right
    after self-update.

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

    _spawn_delayed_launcher(
        current_exe,
        extra_args=extra_args,
        delay_seconds=delay_seconds,
    )
