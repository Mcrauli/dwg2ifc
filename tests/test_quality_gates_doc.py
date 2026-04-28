"""Plan F Task 15: docs/quality-gates.md describes the two-tier QA process."""

from __future__ import annotations

from pathlib import Path

DOC = Path(__file__).resolve().parent.parent / "docs" / "quality-gates.md"


def test_quality_gates_doc_exists():
    assert DOC.is_file()


def test_quality_gates_doc_describes_both_tiers():
    text = DOC.read_text(encoding="utf-8")
    assert "ifcopenshell.validate" in text
    assert "Solibri" in text
    assert "Talo2000" in text
    assert "packaging-smoke.md" in text
    assert "tag" in text.lower() or "release" in text.lower()
