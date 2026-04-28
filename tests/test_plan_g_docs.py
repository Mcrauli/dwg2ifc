"""Plan G Task 19: docs/coordinate-system.md exists and covers the
key CRS topics."""

from __future__ import annotations

from pathlib import Path

DOC_PATH = Path(__file__).resolve().parent.parent / "docs" / "coordinate-system.md"

REQUIRED_HEADINGS = (
    "ETRS-TM35FIN",
    "IfcProjectedCRS",
    "IfcMapConversion",
    "Geometria pysyy LOCAL",
    "storey_z_levels_mm",
    "max_local_extent",
)


def test_coordinate_system_doc_exists():
    assert DOC_PATH.is_file(), f"missing {DOC_PATH}"


def test_coordinate_system_doc_covers_key_topics():
    text = DOC_PATH.read_text(encoding="utf-8")
    missing = [h for h in REQUIRED_HEADINGS if h not in text]
    assert not missing, f"missing topics: {missing}"
