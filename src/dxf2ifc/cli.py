"""Command-line interface for dxf2ifc."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dxf2ifc import __version__
from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.profiles.loader import load_default_profile, load_profile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dxf2ifc",
        description="Convert AutoCAD DXF drawings to IFC 4 with Talo2000 classification.",
    )
    parser.add_argument(
        "--version", action="version", version=f"dxf2ifc {__version__}"
    )
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "convert":
        profile = (
            load_profile(args.profile) if args.profile else load_default_profile()
        )
        convert_dxf(
            dxf_path=args.input,
            output_path=args.output,
            profile=profile,
        )
        print(f"Wrote {args.output}", file=sys.stderr)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
