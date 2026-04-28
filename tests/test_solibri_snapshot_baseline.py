"""Plan F Task 11: tests/snapshots/solibri/full_kylmaelement.json baseline
matches the parse_report.RuleResult schema."""

from __future__ import annotations

import json
from pathlib import Path

SNAPSHOT_PATH = Path(__file__).resolve().parent / "snapshots" / "solibri" / "full_kylmaelement.json"


def test_snapshot_exists():
    assert SNAPSHOT_PATH.is_file(), f"missing {SNAPSHOT_PATH}"


def test_snapshot_has_metadata_and_results_list():
    data = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert "$schema" in data
    assert "model" in data
    assert "ruleset" in data
    assert "captured" in data
    assert isinstance(data["results"], list)


def test_snapshot_results_match_rule_result_schema():
    data = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    for entry in data["results"]:
        assert set(entry.keys()) >= {"rule_name", "severity", "ifc_guid", "message"}
        for key in ("rule_name", "severity", "ifc_guid", "message"):
            assert isinstance(entry[key], str)


def test_snapshot_baseline_is_clean_today():
    """Plan B's full-fixture passes ifcopenshell.validate today, so the
    Solibri baseline starts empty. As real Solibri findings emerge Lauri
    refreshes this snapshot manually."""
    data = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert data["results"] == []
