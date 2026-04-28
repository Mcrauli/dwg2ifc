"""Plan F Section 4 Task 13: full Solibri chain (verify → parse → diff)
runs against the committed baseline snapshot.

The test is gated behind the ``@pytest.mark.solibri`` marker, which the
project's conftest auto-skips when ``Solibri.exe`` is missing from PATH.
Lauri runs this on his Windows host before publishing a release.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.solibri import diff_snapshot, parse_report, verify

REPO_ROOT = Path(__file__).resolve().parent.parent
RULESET = REPO_ROOT / "tools" / "solibri" / "dxf2ifc.bcfzip"
REFERENCE_IFC = REPO_ROOT / "tests" / "fixtures" / "solibri_reference_full.ifc"
SNAPSHOT = (
    REPO_ROOT / "tests" / "snapshots" / "solibri" / "full_kylmaelement.json"
)


@pytest.mark.solibri
def test_solibri_chain_matches_baseline_snapshot(tmp_path: Path):
    report_path = tmp_path / "live_report.xml"

    verify.run_solibri(
        ifc_path=REFERENCE_IFC,
        ruleset_path=RULESET,
        report_path=report_path,
    )

    current_results = parse_report.parse_report(report_path)
    baseline_data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    delta = diff_snapshot.diff(baseline_data["results"], current_results)

    assert delta.is_clean, (
        f"Solibri report diverges from baseline.\n"
        f"  added:   {delta.added}\n"
        f"  removed: {delta.removed}"
    )
