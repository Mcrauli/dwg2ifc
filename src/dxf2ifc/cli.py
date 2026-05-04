"""Command-line interface for dxf2ifc."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dxf2ifc import __version__
from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.core.quality import validate_ifc
from dxf2ifc.profiles.loader import load_default_profile, load_profile
from dxf2ifc.profiles.schema import CRSConfig


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
    convert.add_argument(
        "--eastings",
        type=float,
        default=None,
        help="ETRS-TM35FIN easting (mm) for IfcMapConversion. Requires --northings.",
    )
    convert.add_argument(
        "--northings",
        type=float,
        default=None,
        help="ETRS-TM35FIN northing (mm) for IfcMapConversion. Requires --eastings.",
    )
    convert.add_argument(
        "--orthogonal-height",
        type=float,
        default=None,
        help="Orthogonal height (mm) for IfcMapConversion (default: profile value or 0).",
    )
    convert.add_argument(
        "--energy-specs",
        type=Path,
        default=None,
        help=(
            "Optional .xlsx / .csv with refrigeration-equipment energy "
            "specs. Rows are matched against POSITIO-resolved "
            "(koneikko, laitetunnus) pairs and the resulting fields are "
            "merged into FI_Tekninen."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "convert":
        if (args.eastings is None) != (args.northings is None):
            parser.error("--eastings and --northings must be given together")
        profile = load_profile(args.profile) if args.profile else load_default_profile()
        if args.eastings is not None:
            base = profile.crs
            crs = CRSConfig(
                epsg_code=base.epsg_code if base else "EPSG:3067",
                name=base.name if base else "ETRS-TM35FIN",
                geodetic_datum=base.geodetic_datum if base else "ETRS89",
                eastings_mm=args.eastings,
                northings_mm=args.northings,
                orthogonal_height_mm=(
                    args.orthogonal_height
                    if args.orthogonal_height is not None
                    else (base.orthogonal_height_mm if base else 0.0)
                ),
                x_axis_abscissa=base.x_axis_abscissa if base else 1.0,
                x_axis_ordinate=base.x_axis_ordinate if base else 0.0,
                scale=base.scale if base else 1.0,
            )
            profile = profile.model_copy(update={"crs": crs})
        convert_dxf(
            dxf_path=args.input,
            output_path=args.output,
            profile=profile,
            schema=args.schema.upper(),
            energy_specs_path=args.energy_specs,
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
