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
        description="Convert AutoCAD DXF drawings to IFC 4 for refrigeration design (RAVA3Pro classification).",
    )
    parser.add_argument("--version", action="version", version=f"dxf2ifc {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    convert = subparsers.add_parser("convert", help="Convert a DXF file to IFC.")
    convert.add_argument(
        "input",
        type=Path,
        help="Path to the input .dxf file.",
    )
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
        "--floor-elevation",
        type=float,
        default=0.0,
        metavar="MM",
        help=(
            "Absolute Z elevation (mm) of the ground floor (1.krs). The "
            "DXF is assumed to be drawn with Z=0 at the ground floor; "
            "this offset is added to every IfcBuildingStorey.Elevation. "
            "Default 0 (no offset)."
        ),
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
    convert.add_argument(
        "--magicad-ifc",
        type=Path,
        default=None,
        help=(
            "Optional IFC produced by MagiCAD's -MAGIIFCCD command "
            "(or any other tool that writes per-MagiCAD-product IFC "
            "with MagiCAD types/PSets). When supplied, MagiCAD parts "
            "in the DXF (MAGI* native classes + ACAD_PROXY_ENTITY) "
            "are skipped to avoid duplicates, and the supplied IFC's "
            "products are appended into the master IFC under the "
            "first IfcBuildingStorey."
        ),
    )
    convert.add_argument(
        "--skip-acis",
        action="store_true",
        help=(
            "Skip the accoreconsole.exe ACIS-triangulation pass. DXF "
            "3DSOLID/SURFACE/REGION bodies will not appear in the IFC "
            "(dynamic-block and INSERT-pohjainen geometria tulee silti "
            "normaalisti). Käytä jos accoreconsole heittää AutoCAD-crash-"
            "reportin, tai jos haluat varmistaa että erillistä AutoCAD-"
            "prosessia ei käynnistetä lainkaan."
        ),
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
            energy_specs_path=args.energy_specs,
            floor_elevation_mm=args.floor_elevation,
            magicad_ifc_path=args.magicad_ifc,
            preprocess_acis=not args.skip_acis,
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
