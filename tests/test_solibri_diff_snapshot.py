"""Plan F Task 12: diff_snapshot compares two RuleResult lists."""

from __future__ import annotations

from tools.solibri import diff_snapshot

BASELINE = [
    {
        "rule_name": "Talo2000 classification coverage",
        "severity": "warning",
        "ifc_guid": "GUID-1",
        "message": "missing classification on IfcWall A",
    },
    {
        "rule_name": "Units are millimetres",
        "severity": "info",
        "ifc_guid": "GUID-2",
        "message": "ok",
    },
]


def test_diff_returns_empty_when_lists_identical():
    delta = diff_snapshot.diff(BASELINE, BASELINE)
    assert delta.added == []
    assert delta.removed == []


def test_diff_detects_new_failure():
    new = BASELINE + [
        {
            "rule_name": "IfcSystem grouping",
            "severity": "error",
            "ifc_guid": "GUID-3",
            "message": "pipe missing system",
        }
    ]
    delta = diff_snapshot.diff(BASELINE, new)
    assert len(delta.added) == 1
    assert delta.added[0]["rule_name"] == "IfcSystem grouping"
    assert delta.removed == []


def test_diff_detects_resolved_failure():
    new = BASELINE[:1]  # second entry resolved
    delta = diff_snapshot.diff(BASELINE, new)
    assert delta.added == []
    assert len(delta.removed) == 1
    assert delta.removed[0]["ifc_guid"] == "GUID-2"


def test_diff_treats_severity_change_as_added_and_removed():
    new = list(BASELINE)
    new[0] = dict(new[0])
    new[0]["severity"] = "error"
    delta = diff_snapshot.diff(BASELINE, new)
    assert any(r["severity"] == "warning" for r in delta.removed)
    assert any(a["severity"] == "error" for a in delta.added)


def test_diff_is_stable_against_iteration_order():
    reversed_baseline = list(reversed(BASELINE))
    delta = diff_snapshot.diff(BASELINE, reversed_baseline)
    assert delta.added == []
    assert delta.removed == []
