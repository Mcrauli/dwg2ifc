"""Plan F Task 9: parse_report.py turns Solibri XML reports into a list
of RuleResult dicts."""

from __future__ import annotations

from pathlib import Path

from tools.solibri import parse_report

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "solibri_report_sample.xml"


def test_parse_report_returns_one_entry_per_result_node():
    results = parse_report.parse_report(FIXTURE)
    assert isinstance(results, list)
    # Two warnings under Talo2000 + one error under IfcSystem == 3 entries
    assert len(results) == 3


def test_parse_report_extracts_rule_severity_guid_and_message():
    results = parse_report.parse_report(FIXTURE)
    by_guid = {r["ifc_guid"]: r for r in results}

    first = by_guid["2N9FQX0000000000000001"]
    assert first["rule_name"] == "Talo2000 classification coverage"
    assert first["severity"] == "warning"
    assert "missing Talo2000" in first["message"]

    error = by_guid["2N9FQX0000000000000010"]
    assert error["rule_name"] == "IfcSystem grouping for refrigeration networks"
    assert error["severity"] == "error"
    assert "Refrigeration LT" in error["message"]


def test_parse_report_supports_string_path():
    results = parse_report.parse_report(str(FIXTURE))
    assert len(results) == 3


def test_parse_report_returns_empty_list_for_clean_report(tmp_path: Path):
    clean = tmp_path / "clean.xml"
    clean.write_text(
        '<?xml version="1.0"?><SolibriReport>'
        '<Rule name="Units" severity="info" status="passed"/>'
        "</SolibriReport>",
        encoding="utf-8",
    )
    assert parse_report.parse_report(clean) == []
