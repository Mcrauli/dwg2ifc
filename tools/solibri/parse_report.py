"""Solibri XML report parser (Plan F Section 3 Task 9).

Turns the XML produced by ``Solibri.exe -output <report.xml>`` into a flat
list of ``RuleResult``-shaped dicts. Each violation gets one entry; passed
rules are skipped. The parser uses :mod:`xml.etree.ElementTree` from the
stdlib so dxf2ifc does not pull lxml in just for this helper.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

RuleResult = dict[str, Any]


def parse_report(report_path: Path | str) -> list[RuleResult]:
    """Return one dict per ``<Result>`` node found under any ``<Rule>``.

    The dict carries ``rule_name``, ``severity`` (rule-level fallback),
    ``ifc_guid`` and ``message``. Rules whose ``status`` attribute is
    ``passed`` are still scanned for nested ``Result`` nodes — Solibri
    occasionally emits informational results on otherwise-clean rules.
    """
    tree = ET.parse(report_path)
    root = tree.getroot()
    out: list[RuleResult] = []
    for rule in root.iter("Rule"):
        rule_name = rule.attrib.get("name", "")
        rule_severity = rule.attrib.get("severity", "info")
        for result in rule.findall("Result"):
            out.append(
                {
                    "rule_name": rule_name,
                    "severity": result.attrib.get("severity", rule_severity),
                    "ifc_guid": result.attrib.get("guid", ""),
                    "message": result.attrib.get("message", ""),
                }
            )
    return out
