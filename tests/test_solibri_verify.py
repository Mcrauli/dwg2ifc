"""Plan F Task 8: tools/solibri/verify.py wraps Solibri Anywhere CLI."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from tools.solibri import verify


def test_build_command_uses_required_args(tmp_path: Path):
    ifc = tmp_path / "input.ifc"
    ifc.touch()
    bcfzip = tmp_path / "ruleset.bcfzip"
    bcfzip.touch()
    report = tmp_path / "report.xml"

    cmd = verify.build_command(
        solibri_exe="C:/Solibri/Solibri.exe",
        ifc_path=ifc,
        ruleset_path=bcfzip,
        report_path=report,
    )

    assert cmd[0] == "C:/Solibri/Solibri.exe"
    assert "-load" in cmd
    assert str(ifc) in cmd
    assert "-ruleset" in cmd
    assert str(bcfzip) in cmd
    assert "-output" in cmd
    assert str(report) in cmd
    assert "-exit" in cmd


def test_run_solibri_invokes_subprocess_with_command(monkeypatch, tmp_path: Path):
    ifc = tmp_path / "input.ifc"
    ifc.touch()
    bcfzip = tmp_path / "ruleset.bcfzip"
    bcfzip.touch()
    report = tmp_path / "report.xml"

    seen: dict[str, object] = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = list(cmd)
        seen["kwargs"] = kwargs
        report.write_text("<report/>", encoding="utf-8")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(verify.subprocess, "run", fake_run)
    monkeypatch.setattr(verify.shutil, "which", lambda name: "C:/Solibri/Solibri.exe")

    out = verify.run_solibri(
        ifc_path=ifc, ruleset_path=bcfzip, report_path=report
    )

    assert out == report
    assert seen["cmd"][0] == "C:/Solibri/Solibri.exe"
    assert "-load" in seen["cmd"]
    assert "-exit" in seen["cmd"]


def test_run_solibri_raises_when_executable_missing(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(verify.shutil, "which", lambda name: None)
    ifc = tmp_path / "input.ifc"
    ifc.touch()
    bcfzip = tmp_path / "ruleset.bcfzip"
    bcfzip.touch()
    report = tmp_path / "report.xml"

    with pytest.raises(FileNotFoundError, match="Solibri.exe"):
        verify.run_solibri(
            ifc_path=ifc, ruleset_path=bcfzip, report_path=report
        )


def test_run_solibri_raises_on_nonzero_exit(monkeypatch, tmp_path: Path):
    ifc = tmp_path / "input.ifc"
    ifc.touch()
    bcfzip = tmp_path / "ruleset.bcfzip"
    bcfzip.touch()
    report = tmp_path / "report.xml"

    monkeypatch.setattr(verify.shutil, "which", lambda name: "Solibri.exe")

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(args=cmd, returncode=2, stdout="", stderr="boom")

    monkeypatch.setattr(verify.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="boom"):
        verify.run_solibri(
            ifc_path=ifc, ruleset_path=bcfzip, report_path=report
        )


def test_shutil_which_used_at_module_level():
    # Defensive sanity check that the wrapper actually leans on shutil.which
    assert hasattr(verify, "shutil") and verify.shutil is shutil