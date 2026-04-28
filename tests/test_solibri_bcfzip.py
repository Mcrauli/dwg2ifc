"""Plan F Task 5: dxf2ifc.bcfzip Solibri rule-set fixture lives at
tools/solibri/dxf2ifc.bcfzip and exposes the YTV 2012 + Talo2000 minimum
rules as BCF 2.1 topics."""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

BCFZIP_PATH = Path(__file__).resolve().parent.parent / "tools" / "solibri" / "dxf2ifc.bcfzip"

REQUIRED_RULE_TITLES = {
    "Units are millimetres",
    "Talo2000 classification coverage",
    "IfcSystem grouping for refrigeration networks",
}


def test_bcfzip_exists():
    assert BCFZIP_PATH.is_file(), f"missing {BCFZIP_PATH}"


def test_bcfzip_contains_version_marker_and_is_bcf_2_1():
    with zipfile.ZipFile(BCFZIP_PATH) as zf:
        names = zf.namelist()
        assert "bcf.version" in names, names
        with zf.open("bcf.version") as fp:
            tree = ET.parse(fp)
        root = tree.getroot()
        assert root.tag.endswith("Version")
        assert root.attrib.get("VersionId") == "2.1"


def test_bcfzip_contains_required_rule_topics():
    with zipfile.ZipFile(BCFZIP_PATH) as zf:
        markup_paths = [n for n in zf.namelist() if n.endswith("/markup.bcf")]
        titles: set[str] = set()
        for markup_path in markup_paths:
            with zf.open(markup_path) as fp:
                root = ET.parse(fp).getroot()
            title = root.findtext(".//Title")
            if title:
                titles.add(title.strip())
    missing = REQUIRED_RULE_TITLES - titles
    assert not missing, f"missing rule topics: {sorted(missing)} (have {sorted(titles)})"
