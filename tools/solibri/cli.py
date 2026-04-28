"""CLI entry that chains :mod:`tools.solibri.verify` and
:mod:`tools.solibri.parse_report` (Plan F Section 3 Task 10).

Run with::

    python -m tools.solibri verify --ifc model.ifc \\
        --ruleset tools/solibri/dxf2ifc.bcfzip \\
        --report report.xml

Returns 0 on a clean Solibri report, 1 if any violations were emitted, and
2 if Solibri Anywhere is not on PATH.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.solibri import parse_report, verify


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.solibri",
        description="Run Solibri Anywhere headlessly and print rule violations.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    v = sub.add_parser("verify", help="Run Solibri rule-check on an IFC.")
    v.add_argument("--ifc", type=Path, required=True, help="Input IFC path.")
    v.add_argument(
        "--ruleset",
        type=Path,
        required=True,
        help="Solibri ruleset (.bcfzip) path.",
    )
    v.add_argument(
        "--report",
        type=Path,
        required=True,
        help="Where Solibri should write the XML report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "verify":
        return 1

    try:
        report_path = verify.run_solibri(
            ifc_path=args.ifc,
            ruleset_path=args.ruleset,
            report_path=args.report,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"ERROR: Solibri run failed: {exc}", file=sys.stderr)
        return 2

    results = parse_report.parse_report(report_path)
    if not results:
        print("Solibri report clean — no violations.")
        return 0

    print(f"Solibri report: {len(results)} violation(s)")
    for r in results:
        print(
            f"  [{r.get('severity', '?')}] {r.get('rule_name', '?')} "
            f"({r.get('ifc_guid', '')}) — {r.get('message', '')}"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
