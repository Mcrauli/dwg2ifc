"""Plan F Task 10: `python -m tools.solibri verify` CLI entry chains
verify.run_solibri + parse_report.parse_report."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools.solibri import cli, verify


def _make_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    ifc = tmp_path / "model.ifc"
    ifc.write_text("dummy")
    bcfzip = tmp_path / "rules.bcfzip"
    bcfzip.write_bytes(b"PK")
    report = tmp_path / "report.xml"
    return ifc, bcfzip, report


def test_cli_verify_returns_zero_when_solibri_clean(monkeypatch, tmp_path: Path):
    ifc, bcfzip, report = _make_inputs(tmp_path)

    def fake_run(cmd, **kwargs):
        report.write_text(
            '<?xml version="1.0"?><SolibriReport>'
            '<Rule name="Units" severity="info" status="passed"/>'
            "</SolibriReport>",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(verify.shutil, "which", lambda name: "Solibri.exe")
    monkeypatch.setattr(verify.subprocess, "run", fake_run)

    rc = cli.main(
        [
            "verify",
            "--ifc",
            str(ifc),
            "--ruleset",
            str(bcfzip),
            "--report",
            str(report),
        ]
    )
    assert rc == 0


def test_cli_verify_returns_one_when_violations_present(monkeypatch, tmp_path: Path, capsys):
    ifc, bcfzip, report = _make_inputs(tmp_path)

    def fake_run(cmd, **kwargs):
        report.write_text(
            '<?xml version="1.0"?><SolibriReport>'
            '<Rule name="Talo2000" severity="error" status="failed">'
            '<Result severity="error" guid="2N9..." message="missing classification"/>'
            "</Rule></SolibriReport>",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(verify.shutil, "which", lambda name: "Solibri.exe")
    monkeypatch.setattr(verify.subprocess, "run", fake_run)

    rc = cli.main(
        [
            "verify",
            "--ifc",
            str(ifc),
            "--ruleset",
            str(bcfzip),
            "--report",
            str(report),
        ]
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert "missing classification" in captured.out + captured.err
    assert "Talo2000" in captured.out + captured.err


def test_cli_verify_reports_missing_solibri(monkeypatch, tmp_path: Path, capsys):
    ifc, bcfzip, report = _make_inputs(tmp_path)
    monkeypatch.setattr(verify.shutil, "which", lambda name: None)

    rc = cli.main(
        [
            "verify",
            "--ifc",
            str(ifc),
            "--ruleset",
            str(bcfzip),
            "--report",
            str(report),
        ]
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert "Solibri.exe not found" in captured.err


def test_cli_no_command_prints_help(capsys):
    with pytest.raises(SystemExit):
        cli.main([])
