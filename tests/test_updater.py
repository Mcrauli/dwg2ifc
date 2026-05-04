"""Tests for self-update logic.

Network calls and the actual exe swap are mocked so the suite stays
hermetic. The Windows-only swap helper is exercised via a fake
"current exe" file that the tests can rename freely.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from dxf2ifc.core import updater


def _release_payload(
    *,
    tag: str,
    version: str,
    prerelease: bool = False,
    draft: bool = False,
    asset_name: str | None = None,
    asset_size: int = 102_000_000,
) -> dict:
    assets = []
    if asset_name is not None:
        assets.append(
            {
                "name": asset_name,
                "browser_download_url": f"https://github.com/x/y/releases/download/{tag}/{asset_name}",
                "size": asset_size,
            }
        )
    return {
        "tag_name": tag,
        "name": tag,
        "draft": draft,
        "prerelease": prerelease,
        "html_url": f"https://github.com/x/y/releases/tag/{tag}",
        "body": f"Release notes for {version}",
        "assets": assets,
    }


class TestNormaliseVersion:
    def test_strips_v_prefix(self) -> None:
        assert str(updater._normalise_version("v0.1.0")) == "0.1.0"

    def test_alpha_suffix_maps_to_pep440(self) -> None:
        assert updater._normalise_version("v0.1.0-alpha") < updater._normalise_version("0.1.0")

    def test_beta_suffix_maps_to_pep440(self) -> None:
        assert updater._normalise_version("v0.1.0-beta") < updater._normalise_version("0.1.0")
        assert updater._normalise_version("v0.1.0-alpha") < updater._normalise_version("v0.1.0-beta")

    def test_rc_suffix_maps_to_pep440(self) -> None:
        assert updater._normalise_version("v0.1.0-rc") < updater._normalise_version("0.1.0")
        assert updater._normalise_version("v0.1.0-beta") < updater._normalise_version("v0.1.0-rc")

    def test_invalid_returns_none(self) -> None:
        assert updater._normalise_version("not-a-version") is None
        assert updater._normalise_version("") is None


class TestSelectAsset:
    def test_returns_exe_url_and_size(self) -> None:
        release = _release_payload(
            tag="v0.1.0", version="0.1.0", asset_name="dxf2ifc-0.1.0.exe", asset_size=999
        )
        assert updater._select_asset(release) == (
            "https://github.com/x/y/releases/download/v0.1.0/dxf2ifc-0.1.0.exe",
            999,
        )

    def test_skips_sha256_sidecar(self) -> None:
        release = {
            "assets": [
                {"name": "dxf2ifc-0.1.0.exe.sha256", "browser_download_url": "...", "size": 64},
                {"name": "dxf2ifc-0.1.0.exe", "browser_download_url": "real.exe", "size": 999},
            ]
        }
        url, _ = updater._select_asset(release)
        assert url == "real.exe"

    def test_returns_none_when_no_exe(self) -> None:
        release = {
            "assets": [
                {"name": "LICENSES.md", "browser_download_url": "...", "size": 1024},
            ]
        }
        assert updater._select_asset(release) is None


class TestCheckForUpdate:
    def _patch_releases(self, releases: list[dict]):
        return patch.object(updater, "_open_releases", return_value=releases)

    def test_returns_none_when_no_newer_release(self) -> None:
        releases = [
            _release_payload(tag="v0.1.0", version="0.1.0", asset_name="dxf2ifc-0.1.0.exe"),
        ]
        with self._patch_releases(releases):
            assert updater.check_for_update(current_version="0.1.0") is None

    def test_returns_info_when_newer_stable_exists(self) -> None:
        releases = [
            _release_payload(tag="v0.1.0", version="0.1.0", asset_name="dxf2ifc-0.1.0.exe"),
            _release_payload(tag="v0.2.0", version="0.2.0", asset_name="dxf2ifc-0.2.0.exe"),
        ]
        with self._patch_releases(releases):
            info = updater.check_for_update(current_version="0.1.0")
        assert info is not None
        assert info.tag == "v0.2.0"
        assert info.version == "0.2.0"
        assert "dxf2ifc-0.2.0.exe" in info.download_url

    def test_picks_highest_version_among_many(self) -> None:
        releases = [
            _release_payload(tag="v0.1.5", version="0.1.5", asset_name="a.exe"),
            _release_payload(tag="v0.2.0", version="0.2.0", asset_name="b.exe"),
            _release_payload(tag="v0.1.9", version="0.1.9", asset_name="c.exe"),
        ]
        with self._patch_releases(releases):
            info = updater.check_for_update(current_version="0.1.0")
        assert info is not None
        assert info.tag == "v0.2.0"

    def test_skips_drafts(self) -> None:
        releases = [
            _release_payload(
                tag="v0.2.0",
                version="0.2.0",
                draft=True,
                asset_name="dxf2ifc-0.2.0.exe",
            ),
        ]
        with self._patch_releases(releases):
            assert updater.check_for_update(current_version="0.1.0") is None

    def test_skips_prereleases_when_requested(self) -> None:
        releases = [
            _release_payload(
                tag="v0.2.0-alpha",
                version="0.2.0a0",
                prerelease=True,
                asset_name="dxf2ifc-0.2.0a0.exe",
            ),
        ]
        with self._patch_releases(releases):
            info = updater.check_for_update(
                current_version="0.1.0", include_prereleases=False
            )
        assert info is None

    def test_includes_prereleases_by_default(self) -> None:
        releases = [
            _release_payload(
                tag="v0.2.0-alpha",
                version="0.2.0a0",
                prerelease=True,
                asset_name="dxf2ifc-0.2.0a0.exe",
            ),
        ]
        with self._patch_releases(releases):
            info = updater.check_for_update(current_version="0.1.0")
        assert info is not None
        assert info.tag == "v0.2.0-alpha"

    def test_returns_none_when_newer_release_has_no_exe(self) -> None:
        releases = [
            _release_payload(tag="v0.2.0", version="0.2.0", asset_name=None),
        ]
        with self._patch_releases(releases):
            assert updater.check_for_update(current_version="0.1.0") is None

    def test_alpha_user_sees_stable_release(self) -> None:
        # Lauri's exact case: installed v0.1.0-alpha, repo has v0.1.0 (stable).
        releases = [
            _release_payload(tag="v0.1.0", version="0.1.0", asset_name="dxf2ifc-0.1.0.exe"),
        ]
        with self._patch_releases(releases):
            info = updater.check_for_update(current_version="0.1.0-alpha")
        assert info is not None
        assert info.tag == "v0.1.0"

    def test_network_error_returns_none(self) -> None:
        with patch.object(
            updater, "_open_releases", side_effect=OSError("network down")
        ):
            assert updater.check_for_update(current_version="0.1.0") is None


class TestDownloadAsset:
    def test_writes_bytes_via_part_then_renames(self, tmp_path: Path) -> None:
        target = tmp_path / "subdir" / "out.exe"
        chunks = [b"hello ", b"world", b""]
        index = {"i": 0}

        class FakeResponse:
            headers = {"Content-Length": "11"}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self, n: int) -> bytes:
                i = index["i"]
                index["i"] = i + 1
                return chunks[min(i, len(chunks) - 1)]

        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            updater.download_asset("http://x/a.exe", target)
        assert target.read_bytes() == b"hello world"
        assert not (target.with_suffix(target.suffix + ".part")).exists()

    def test_progress_callback_invoked(self, tmp_path: Path) -> None:
        target = tmp_path / "out.exe"
        chunks = [b"abcdef", b"ghij", b""]
        index = {"i": 0}

        class FakeResponse:
            headers = {"Content-Length": "10"}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self, n: int) -> bytes:
                i = index["i"]
                index["i"] = i + 1
                return chunks[min(i, len(chunks) - 1)]

        progress: list[tuple[int, int]] = []
        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            updater.download_asset(
                "http://x/a.exe",
                target,
                progress_cb=lambda d, t: progress.append((d, t)),
            )
        assert progress == [(6, 10), (10, 10)]


class TestSwapHelpers:
    def test_old_path_appends_old_suffix(self, tmp_path: Path) -> None:
        exe = tmp_path / "dxf2ifc-0.1.0.exe"
        assert updater._old_path_for(exe).name == "dxf2ifc-0.1.0.exe.old"

    def test_cleanup_old_exe_removes_leftover(self, tmp_path: Path) -> None:
        current = tmp_path / "app.exe"
        current.write_bytes(b"current")
        old = updater._old_path_for(current)
        old.write_bytes(b"old")
        assert old.exists()
        updater.cleanup_old_exe(current)
        assert not old.exists()
        assert current.exists()  # untouched

    def test_cleanup_no_op_when_no_leftover(self, tmp_path: Path) -> None:
        current = tmp_path / "app.exe"
        current.write_bytes(b"current")
        # Should be a no-op; must not error.
        updater.cleanup_old_exe(current)
        assert current.exists()

    def test_schedule_replace_swaps_files_and_spawns(self, tmp_path: Path) -> None:
        current = tmp_path / "app.exe"
        new = tmp_path / "downloaded.exe"
        current.write_bytes(b"OLD")
        new.write_bytes(b"NEW")

        with patch("subprocess.Popen") as popen:
            updater.schedule_replace_and_restart(new, current_exe=current)

        assert current.read_bytes() == b"NEW"
        assert updater._old_path_for(current).read_bytes() == b"OLD"
        assert not new.exists()
        popen.assert_called_once()

    def test_schedule_replace_cleans_prior_old(self, tmp_path: Path) -> None:
        current = tmp_path / "app.exe"
        new = tmp_path / "downloaded.exe"
        current.write_bytes(b"OLD")
        new.write_bytes(b"NEW")
        old = updater._old_path_for(current)
        old.write_bytes(b"PRIOR-OLD")

        with patch("subprocess.Popen"):
            updater.schedule_replace_and_restart(new, current_exe=current)

        assert old.read_bytes() == b"OLD"

    def test_schedule_replace_raises_when_not_bundled(self, tmp_path: Path) -> None:
        new = tmp_path / "downloaded.exe"
        new.write_bytes(b"NEW")
        with patch.object(updater, "is_running_bundled", return_value=False):
            with pytest.raises(RuntimeError, match="frozen exe"):
                updater.schedule_replace_and_restart(new)


class TestIsRunningBundled:
    def test_false_when_not_frozen(self) -> None:
        # During pytest sys.frozen is unset.
        assert updater.is_running_bundled() is False
