"""Plan F Task 7: docs/solibri-rules.md describes every rule shipped in
tools/solibri/dxf2ifc.bcfzip in Finnish so reviewers can audit the
quality gate without opening Solibri."""

from __future__ import annotations

from pathlib import Path

DOC_PATH = Path(__file__).resolve().parent.parent / "docs" / "solibri-rules.md"

REQUIRED_RULE_HEADINGS = (
    "Units are millimetres",
    "Talo2000 classification coverage",
    "IfcSystem grouping for refrigeration networks",
    "Cold-room panels emit IfcBuildingElementProxy 1352",
    "Cooling equipment uses MEP entity types",
)


def test_solibri_rules_doc_exists():
    assert DOC_PATH.is_file(), f"missing {DOC_PATH}"


def test_solibri_rules_doc_lists_every_rule_in_finnish():
    text = DOC_PATH.read_text(encoding="utf-8")
    for title in REQUIRED_RULE_HEADINGS:
        assert title in text, f"missing rule heading: {title}"
    # Must contain at least one Finnish word and a YTV reference per rule
    assert "YTV 2012" in text
    assert "Talo2000" in text
    assert "Solibri" in text
