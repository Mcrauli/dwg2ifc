"""Command-line interface for dwg2ifc."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dwg2ifc import __version__
from dwg2ifc.core.ifc_writer import FileEntry, convert, convert_dxf
from dwg2ifc.core.quality import validate_ifc
from dwg2ifc.profiles.loader import load_default_profile, load_profile


def _parse_floor_arg(value: str, *, default_index: int) -> FileEntry:
    """Parse a ``--floor PATH[:LABEL[:ELEV_MM]]`` value into a FileEntry.

    ``default_index`` is 0-based and only used to derive a default label
    (``"{N + 1}.krs"``) when the caller did not supply one.
    """
    parts = value.split(":")
    if len(parts) > 3:
        raise ValueError(
            f"--floor expects PATH[:LABEL[:ELEV_MM]], got {value!r}"
        )
    path = Path(parts[0])
    label = parts[1] if len(parts) >= 2 and parts[1] else f"{default_index + 1}.krs"
    elev_str = parts[2] if len(parts) == 3 else "0"
    try:
        elev_mm = float(elev_str)
    except ValueError as exc:
        raise ValueError(
            f"--floor elevation must be a number, got {elev_str!r}"
        ) from exc
    return FileEntry(path=path, floor_label=label, elevation_mm=elev_mm)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dwg2ifc",
        description="Convert AutoCAD DWG/DXF drawings to IFC 4 for refrigeration design (RAVA3Pro classification).",
    )
    parser.add_argument("--version", action="version", version=f"dwg2ifc {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    convert = subparsers.add_parser(
        "convert", help="Convert one or more DXF/DWG files to a single IFC."
    )
    convert.add_argument(
        "input",
        type=Path,
        nargs="?",
        default=None,
        help=(
            "Single DXF/DWG input (legacy form, becomes storey '1.krs'). "
            "Mutually exclusive with --floor. DWG inputs are preconverted "
            "via accoreconsole + DXFOUT (requires AutoCAD)."
        ),
    )
    convert.add_argument("output", type=Path, help="Path for the IFC output file.")
    convert.add_argument(
        "--floor",
        action="append",
        default=[],
        metavar="PATH[:LABEL[:ELEV_MM]]",
        help=(
            "Multi-floor input. Repeatable: each occurrence adds one storey. "
            "LABEL defaults to '<N>.krs' (1-based by --floor order). "
            "ELEV_MM defaults to 0. Mutually exclusive with positional INPUT."
        ),
    )
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "convert":
        profile = load_profile(args.profile) if args.profile else load_default_profile()
        if args.floor and args.input is not None:
            parser.error("--floor and positional INPUT are mutually exclusive")
        if not args.floor and args.input is None:
            parser.error(
                "convert requires either a positional INPUT or one or more --floor flags"
            )
        if args.floor:
            files = [
                _parse_floor_arg(v, default_index=i) for i, v in enumerate(args.floor)
            ]
            convert(
                files=files,
                output_path=args.output,
                profile=profile,
                schema=args.schema.upper(),
                energy_specs_path=args.energy_specs,
                magicad_ifc_path=args.magicad_ifc,
            )
        else:
            convert_dxf(
                dxf_path=args.input,
                output_path=args.output,
                profile=profile,
                schema=args.schema.upper(),
                energy_specs_path=args.energy_specs,
                floor_elevation_mm=args.floor_elevation,
                magicad_ifc_path=args.magicad_ifc,
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
