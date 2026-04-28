"""IFC quality / validation gate (Plan F).

Wraps :mod:`ifcopenshell.validate` into a structured :class:`ValidationReport`
that the CLI and GUI can present uniformly. In addition to the upstream schema
checks the wrapper also runs YTV 2012 -specific checks — most importantly that
every IfcWall / IfcSlab / IfcDoor / IfcWindow is classified with a Talo2000
``IfcClassificationReference`` via ``IfcRelAssociatesClassification``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import ifcopenshell
import ifcopenshell.validate

TALO2000_REQUIRED_CLASSES: tuple[str, ...] = (
    "IfcWall",
    "IfcSlab",
    "IfcDoor",
    "IfcWindow",
)

RAVA_REQUIRED_CLASSES: tuple[str, ...] = (
    "IfcPipeSegment",
    "IfcCableCarrierSegment",
    "IfcEvaporator",
    "IfcCondenser",
    "IfcCompressor",
)

RAVA_SOURCE_NAMES: frozenset[str] = frozenset({"RAVA-LVI", "RAVA-TATE"})


@dataclass
class ValidationReport:
    """Structured result of an ifcopenshell.validate run."""

    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""


def _classified_products(
    ifc: ifcopenshell.file, *, source_names: frozenset[str] | set[str]
) -> set[int]:
    """Return ``id()``-based identifiers of products linked to an
    IfcClassificationReference whose ReferencedSource.Name is in
    ``source_names``."""
    classified: set[int] = set()
    for rel in ifc.by_type("IfcRelAssociatesClassification"):
        ref = rel.RelatingClassification
        if ref is None or not ref.is_a("IfcClassificationReference"):
            continue
        source = ref.ReferencedSource
        if source is None or getattr(source, "Name", None) not in source_names:
            continue
        if not getattr(ref, "Identification", None):
            continue
        for product in rel.RelatedObjects or ():
            classified.add(product.id())
    return classified


def _check_talo2000_classification(ifc: ifcopenshell.file) -> list[dict[str, Any]]:
    """Emit a warning for every IfcWall/IfcSlab/IfcDoor/IfcWindow whose
    Talo2000 classification link is missing (YTV 2012, ARK-domain)."""
    classified = _classified_products(ifc, source_names=frozenset({"Talo2000"}))
    warnings: list[dict[str, Any]] = []
    for ifc_class in TALO2000_REQUIRED_CLASSES:
        for product in ifc.by_type(ifc_class):
            if product.id() in classified:
                continue
            warnings.append(
                {
                    "level": "WARNING",
                    "type": "talo2000_classification",
                    "ifc_class": ifc_class,
                    "global_id": getattr(product, "GlobalId", None),
                    "name": getattr(product, "Name", None),
                    "message": (
                        f"missing Talo2000 classification on {ifc_class} "
                        f"{getattr(product, 'Name', None)!r}"
                    ),
                }
            )
    return warnings


def _check_rava_classification(ifc: ifcopenshell.file) -> list[dict[str, Any]]:
    """Emit a warning for every TATE-domain product (pipes, cable carriers,
    cooling equipment) that lacks a RAVA-LVI / RAVA-TATE classification."""
    classified = _classified_products(ifc, source_names=RAVA_SOURCE_NAMES)
    warnings: list[dict[str, Any]] = []
    for ifc_class in RAVA_REQUIRED_CLASSES:
        for product in ifc.by_type(ifc_class):
            if product.id() in classified:
                continue
            warnings.append(
                {
                    "level": "WARNING",
                    "type": "rava_classification",
                    "ifc_class": ifc_class,
                    "global_id": getattr(product, "GlobalId", None),
                    "name": getattr(product, "Name", None),
                    "message": (
                        f"missing RAVA classification on {ifc_class} "
                        f"{getattr(product, 'Name', None)!r}"
                    ),
                }
            )
    return warnings


def validate_ifc(path: str | Path) -> ValidationReport:
    """Validate an IFC file on disk and return a structured report.

    Errors and warnings are extracted from the json_logger statements
    emitted by :func:`ifcopenshell.validate.validate`. YTV 2012 -specific
    Talo2000 classification checks are appended to ``warnings``. The
    summary string captures the schema and counts so the CLI can print a
    one-liner.
    """
    ifc_path = Path(path)
    ifc = ifcopenshell.open(str(ifc_path))

    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, logger=logger)

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for statement in logger.statements:
        level = statement.get("level", "").upper()
        if level == "ERROR":
            errors.append(statement)
        elif level == "WARNING":
            warnings.append(statement)

    warnings.extend(_check_talo2000_classification(ifc))
    warnings.extend(_check_rava_classification(ifc))

    summary = f"{ifc.schema}: {len(errors)} errors, {len(warnings)} warnings ({ifc_path.name})"
    return ValidationReport(errors=errors, warnings=warnings, summary=summary)
