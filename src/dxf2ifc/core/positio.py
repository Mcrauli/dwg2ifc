"""Read POSITIO numbering blocks from a DXF and link them to nearby
refrigeration equipment.

Lauri's drawing convention: every cooling-equipment INSERT
(KYL-HÖYRYSTIN, KYL-LAUHDUTIN, KYL-KOMPRESSORI) is paired with a
``positiov2`` INSERT carrying two text attributes:

* ``NUMERO`` — the unique position number (e.g. "1", "47")
* ``TEKSTI`` — the koneikko / compressor unit tag (e.g. "JK1", "JK3")

The Finnish FI_Komponentti PropertySet wants both:

* ``Laitetunnus`` ← TEKSTI (group / koneikko)
* ``Laitetunnus, yksilöllinen`` ← NUMERO (per-instance number)

This module is a small two-function helper: index every POSITIO marker
once at the start of a conversion, then find the nearest one (in 2D)
for each equipment INSERT placement. No changes to the IFC writer
itself — it just reads ``extras['laitetunnus']`` from the mapped entity.
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

import ezdxf


@dataclass(frozen=True)
class PositioMarker:
    """One POSITIO numbering block read from DXF model space."""

    insert_xy: tuple[float, float]
    numero: str
    teksti: str
    handle: str  # source DXF handle, only kept for diagnostics


def index_positio_markers(
    dxf_path: str | Path,
    *,
    block_pattern: str = "positiov2*",
) -> list[PositioMarker]:
    """Iterate model space and collect every POSITIO INSERT.

    ``block_pattern`` is a case-insensitive ``fnmatch`` glob against the
    INSERT's block name (group code 2). The default ``"positiov2*"``
    catches ``positiov2``, ``positiov2_alt`` etc. INSERTs without the
    expected ``NUMERO`` and ``TEKSTI`` attributes are silently skipped
    (broken / placeholder positios should never crash a conversion).
    """
    pattern = block_pattern.casefold()
    doc = ezdxf.readfile(str(dxf_path))
    markers: list[PositioMarker] = []
    for entity in doc.modelspace():
        if entity.dxftype() != "INSERT":
            continue
        if not fnmatch(entity.dxf.name.casefold(), pattern):
            continue
        if not entity.has_attrib:
            continue
        # Attribute TAG match is case-insensitive too — Lauri's positiov2
        # uses upper-case NUMERO / TEKSTI but a future variant might
        # differ. We extract by uppercased tag name.
        attribs: dict[str, str] = {}
        for att in entity.attribs:
            tag = (att.dxf.tag or "").upper().strip()
            text = (att.dxf.text or "").strip()
            if tag and text:
                attribs[tag] = text
        numero = attribs.get("NUMERO")
        teksti = attribs.get("TEKSTI")
        if not numero and not teksti:
            # Block is pure decoration without numbering data — skip.
            continue
        markers.append(
            PositioMarker(
                insert_xy=(float(entity.dxf.insert.x), float(entity.dxf.insert.y)),
                numero=numero or "",
                teksti=teksti or "",
                handle=str(entity.dxf.handle).upper(),
            )
        )
    return markers


def find_nearest_positio(
    target_xy: tuple[float, float],
    markers: list[PositioMarker],
    *,
    max_distance_mm: float = 3000.0,
) -> PositioMarker | None:
    """Return the closest marker within ``max_distance_mm`` in the XY plane.

    Z is ignored on purpose — POSITIOs are typically drawn at Z=0 while
    a ceiling-mounted evaporator sits at Z=2200; an XY-only match still
    pairs them correctly. ``None`` is returned when no marker is within
    the radius, leaving Laitetunnus fields blank instead of inventing a
    bogus tag from a far-away marker.
    """
    if not markers:
        return None
    tx, ty = target_xy
    best: PositioMarker | None = None
    best_d2 = max_distance_mm * max_distance_mm
    for m in markers:
        dx = m.insert_xy[0] - tx
        dy = m.insert_xy[1] - ty
        d2 = dx * dx + dy * dy
        if d2 < best_d2:
            best_d2 = d2
            best = m
    return best
