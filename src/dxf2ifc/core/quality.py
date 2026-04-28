"""IFC quality / validation gate (Plan F).

Wraps :mod:`ifcopenshell.validate` into a structured :class:`ValidationReport`
that the CLI and GUI can present uniformly. The wrapper accepts either an open
:class:`ifcopenshell.file` or a path on disk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import ifcopenshell
import ifcopenshell.validate


@dataclass
class ValidationReport:
    """Structured result of an ifcopenshell.validate run."""

    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""


def validate_ifc(path: str | Path) -> ValidationReport:
    """Validate an IFC file on disk and return a structured report.

    Errors and warnings are extracted from the json_logger statements
    emitted by :func:`ifcopenshell.validate.validate`. The summary string
    captures the schema and counts so the CLI can print a one-liner.
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

    summary = (
        f"{ifc.schema}: {len(errors)} errors, {len(warnings)} warnings "
        f"({ifc_path.name})"
    )
    return ValidationReport(errors=errors, warnings=warnings, summary=summary)
