"""Tests for DWG -> DXF preconversion via accoreconsole + DXFOUT.

The end-to-end test that actually invokes accoreconsole is gated on the
host having AutoCAD installed. CI / Lauri's laptop without AutoCAD skip
that test; the unit-level tests below validate the error paths and the
script-generation logic via subprocess mocking.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dxf2ifc.core.dwg_preconvert import (
    DwgPreconvertError,
    convert_dwg_to_dxf,
)
from dxf2ifc.core.preprocessing import find_accoreconsole


def _has_accoreconsole() -> bool:
    return find_accoreconsole() is not None


def test_raises_filenotfound_when_accoreconsole_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If find_accoreconsole returns None, surface a clear FileNotFoundError."""
    monkeypatch.setattr(
        "dxf2ifc.core.dwg_preconvert.find_accoreconsole", lambda: None
    )
    dwg = tmp_path / "fake.dwg"
    dwg.write_bytes(b"dummy")

    with pytest.raises(FileNotFoundError) as excinfo:
        convert_dwg_to_dxf(dwg, tmp_path / "work")

    assert "accoreconsole.exe not found" in str(excinfo.value)
    assert "DXFOUT" in str(excinfo.value)


def test_returns_path_when_subprocess_writes_output_dxf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Successful accoreconsole subprocess + present DXF -> returns the .dxf path."""

    fake_acc = tmp_path / "accoreconsole.exe"
    fake_acc.write_bytes(b"fake")

    def fake_run(cmd: list[str], **kwargs: Any) -> Any:  # noqa: ANN401
        # Locate the output path from cmd args: /i input.dwg /s script.scr
        scr_path = Path(cmd[cmd.index("/s") + 1])
        script_text = scr_path.read_text(encoding="utf-8")
        # Extract the quoted output path from the LISP body
        out_path_str = script_text.split('"_.DXFOUT" "')[1].split('"')[0]
        out_path = Path(out_path_str)
        # Simulate DXFOUT producing a non-trivial DXF
        out_path.write_bytes(b"  0\nSECTION\n  2\nHEADER\n" + b"X" * 2048)

        class _Completed:
            returncode = 0

        return _Completed()

    monkeypatch.setattr("subprocess.run", fake_run)

    dwg = tmp_path / "co2-anturi.dwg"
    dwg.write_bytes(b"dummy-dwg")

    out = convert_dwg_to_dxf(dwg, tmp_path / "work", accoreconsole=fake_acc)

    assert out.exists()
    assert out.suffix == ".dxf"
    assert out.stat().st_size > 1024
    assert out.name == "co2-anturi.dxf"


def test_raises_when_output_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If accoreconsole exits but no DXF was written, raise DwgPreconvertError."""
    fake_acc = tmp_path / "accoreconsole.exe"
    fake_acc.write_bytes(b"fake")

    def fake_run(cmd: list[str], **kwargs: Any) -> Any:  # noqa: ANN401
        class _Completed:
            returncode = 0

        return _Completed()  # subprocess "succeeds" but writes nothing

    monkeypatch.setattr("subprocess.run", fake_run)

    dwg = tmp_path / "broken.dwg"
    dwg.write_bytes(b"dummy")

    with pytest.raises(DwgPreconvertError) as excinfo:
        convert_dwg_to_dxf(dwg, tmp_path / "work", accoreconsole=fake_acc)

    assert "did not produce an output DXF" in str(excinfo.value)


def test_raises_when_output_too_small(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Output DXF under 1 KB is treated as a failed conversion."""
    fake_acc = tmp_path / "accoreconsole.exe"
    fake_acc.write_bytes(b"fake")

    def fake_run(cmd: list[str], **kwargs: Any) -> Any:  # noqa: ANN401
        scr_path = Path(cmd[cmd.index("/s") + 1])
        script_text = scr_path.read_text(encoding="utf-8")
        out_path_str = script_text.split('"_.DXFOUT" "')[1].split('"')[0]
        Path(out_path_str).write_bytes(b"too small")

        class _Completed:
            returncode = 0

        return _Completed()

    monkeypatch.setattr("subprocess.run", fake_run)

    dwg = tmp_path / "tiny.dwg"
    dwg.write_bytes(b"dummy")

    with pytest.raises(DwgPreconvertError) as excinfo:
        convert_dwg_to_dxf(dwg, tmp_path / "work", accoreconsole=fake_acc)

    assert "suspiciously small" in str(excinfo.value)


def test_script_uses_forward_slashes_in_lisp_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LISP string literals must use forward slashes — backslashes are escape chars."""
    fake_acc = tmp_path / "accoreconsole.exe"
    fake_acc.write_bytes(b"fake")

    captured_script: dict[str, str] = {}

    def fake_run(cmd: list[str], **kwargs: Any) -> Any:  # noqa: ANN401
        scr_path = Path(cmd[cmd.index("/s") + 1])
        captured_script["text"] = scr_path.read_text(encoding="utf-8")
        out_path_str = captured_script["text"].split('"_.DXFOUT" "')[1].split('"')[0]
        Path(out_path_str).write_bytes(b"X" * 2048)

        class _Completed:
            returncode = 0

        return _Completed()

    monkeypatch.setattr("subprocess.run", fake_run)

    dwg = tmp_path / "x.dwg"
    dwg.write_bytes(b"dummy")

    convert_dwg_to_dxf(dwg, tmp_path / "work", accoreconsole=fake_acc)

    assert "\\" not in captured_script["text"].split('"_.DXFOUT" "')[1].split('"')[0]
    assert "/" in captured_script["text"].split('"_.DXFOUT" "')[1].split('"')[0]


@pytest.mark.skipif(
    not _has_accoreconsole(),
    reason="Vaatii AutoCAD-asennuksen (accoreconsole.exe)",
)
def test_end_to_end_real_accoreconsole(tmp_path: Path) -> None:
    """Aja oikea accoreconsole DXFOUT pienellä DWG-fileellä.

    Käyttää autocad-lisp-ohjeet-repon co2-anturi.dwg:tä jos saatavilla.
    Skip jos source-DWG puuttuu.
    """
    onedrive = Path.home() / "OneDrive - RADIKA OY"
    dwg = onedrive / "Työpöytä" / "work" / "autocad-lisp-ohjeet" / "files" / "co2-anturi.dwg"
    if not dwg.is_file():
        pytest.skip(f"Source DWG not found at {dwg}")

    out = convert_dwg_to_dxf(dwg, tmp_path)

    assert out.exists()
    assert out.suffix == ".dxf"
    assert out.stat().st_size > 1024

    # Verify ezdxf can parse the output and the 6 source 3DSOLIDs survive
    import ezdxf

    doc = ezdxf.readfile(str(out))
    msp = doc.modelspace()
    solid_count = sum(1 for e in msp if e.dxftype() == "3DSOLID")
    assert solid_count >= 1, f"Expected 3DSOLID(s) in output DXF, got {solid_count}"
