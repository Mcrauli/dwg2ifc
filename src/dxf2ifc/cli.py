"""Command-line interface for dxf2ifc."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dxf2ifc import __version__
from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.core.quality import validate_ifc
from dxf2ifc.profiles.loader import load_default_profile, load_profile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dxf2ifc",
        description="Convert AutoCAD DXF drawings to IFC 4 with Talo2000 classification.",
    )
    parser.add_argument("--version", action="version", version=f"dxf2ifc {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    convert = subparsers.add_parser("convert", help="Convert a DXF file to IFC.")
    convert.add_argument("input", type=Path, help="Path to the DXF input file.")
    convert.add_argument("output", type=Path, help="Path for the IFC output file.")
    convert.add_argument(
        "--profile",
        type=Path,
        default=None,
        help="Custom profile TOML. Omit to use the shipped Kylmälaite Talo2000 profile.",
    )
    convert.add_argument(
        "--validate",
        action="store_true",
        help=(
            "Run ifcopenshell.validate + YTV Talo2000 checks on the output IFC. "
            "Exits with code 1 if validation errors are reported."
        ),
    )
    convert.add_argument(
        "--schema",
        choices=["ifc4", "ifc4x3"],
        default="ifc4",
        help="IFC schema to emit (default: ifc4). Plan H switches default to ifc4x3.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "convert":
        profile = load_profile(args.profile) if args.profile else load_default_profile()
        convert_dxf(
            dxf_path=args.input,
            output_path=args.output,
            profile=profile,
            schema=args.schema.upper(),
        )
        print(f"Wrote {args.output}", file=sys.stderr)
        if args.validate:
            report = validate_ifc(args.output)
            print(report.summary, file=sys.stderr)
            for warning in report.warnings:
                print(f"WARNING: {warning.get('message', warning)}", file=sys.stderr)
            if report.errors:
                for error in report.errors:
                    print(f"ERROR: {error.get('message', error)}", file=sys.stderr)
                return 1
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
