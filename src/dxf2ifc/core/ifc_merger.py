"""Merge a MagiCAD-exported IFC into the master IFC dxf2ifc just wrote.

Why this module exists
----------------------

dxf2ifc's DWG-pipeline (see :mod:`dxf2ifc.core.dwg_preconvert`) gets
MagiCAD geometry by ``MAGIEXPLODE`` + ``EXPLODE`` + ``STLOUT`` —
mesh-tessellated bodies that land in the IFC as ``IfcFacetedBrep``
under whichever ``IfcBuildingElementProxy`` / ``IfcPipeSegment`` /
``IfcCooler`` / etc. type the layer profile picks. That works on a
FULL-MagiCAD-licensed machine, but the result is *just geometry* —
no MagiCAD product types (``IfcDuctSegment``, ``IfcAirTerminal``…),
no MagiCAD propertysets, no semantic IFC.

When the colleague has FULL MagiCAD, they can run ``-MAGIIFCCD`` (the
command-line / dialog-free variant of ``MAGIIFCEXPORT``) themselves
and get a much higher-fidelity IFC for the MagiCAD parts. This module
merges that MagiCAD-exported IFC *into* the master IFC that dxf2ifc
just wrote for Lauri's KYL-LISP shelves / refrigeration equipment. The result is a single IFC that carries:

* Lauri's KYL-* refrigeration parts (Brep, RAVA-classified, FI_*-PSets)
* Colleague's MagiCAD parts (MagiCAD-native IFC types + MagiCAD-PSets)
* All under the same ``IfcSite`` → ``IfcBuilding`` → ``IfcBuildingStorey``

How it works
------------

Uses ``ifcopenshell.api.project.append_asset`` which copies an IfcProduct
from a library file into the master file, intelligently transplanting
geometric contexts, materials, styles, and propertysets. We then use
``ifcopenshell.api.spatial.assign_container`` to place each appended
product in the master's first storey.

Spatial-structure entities (``IfcSite``, ``IfcBuilding``,
``IfcBuildingStorey``, ``IfcSpace``) and project/library entities are
never copied — the master's hierarchy stays canonical.

Returns
-------

A counts dict for diagnostics:

::

    {
        "products_appended": 47,
        "products_skipped": 0,
        "products_total_in_magicad_ifc": 47,
        "ifc_types": {"IfcDuctSegment": 24, "IfcAirTerminal": 12, ...}
    }
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Callable

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.project
import ifcopenshell.api.spatial


# IFC entity types that describe spatial structure or project metadata —
# never copied. Anything else that descends from IfcProduct gets merged.
_SPATIAL_STRUCTURE_TYPES = frozenset({
    "IfcProject",
    "IfcSite",
    "IfcBuilding",
    "IfcBuildingStorey",
    "IfcSpace",
    "IfcSpatialZone",
    "IfcExternalSpatialElement",
})


def merge_magicad_ifc(
    master_path: str | Path,
    magicad_ifc_path: str | Path,
    *,
    output_path: str | Path | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict:
    """Merge MagiCAD-exported IFC products into ``master_path``.

    ``master_path``: IFC dxf2ifc just wrote (Lauri's KYL parts).
    ``magicad_ifc_path``: IFC produced by colleague's ``MAGIIFCEXPORT``.
    ``output_path``: where the merged IFC is written. Defaults to
    overwriting ``master_path`` in place.
    ``progress``: optional callback receiving short status strings,
    invoked during reading + per-batch append + save.

    Returns a counts dict (see module docstring).

    Raises ``ValueError`` if the master IFC has no ``IfcBuildingStorey``
    (i.e. the skeleton was not built), or if the MagiCAD IFC cannot be
    opened.
    """
    master_path = Path(master_path)
    magicad_ifc_path = Path(magicad_ifc_path)
    output_path = Path(output_path) if output_path is not None else master_path

    if not master_path.is_file():
        raise FileNotFoundError(f"Master IFC ei löydy: {master_path}")
    if not magicad_ifc_path.is_file():
        raise FileNotFoundError(f"MagiCAD-IFC ei löydy: {magicad_ifc_path}")

    if progress:
        progress(f"Avataan MagiCAD-IFC ({magicad_ifc_path.stat().st_size // 1024} kB)…")
    library = ifcopenshell.open(str(magicad_ifc_path))

    if progress:
        progress("Avataan master-IFC ja etsitään storey…")
    master = ifcopenshell.open(str(master_path))

    storeys = master.by_type("IfcBuildingStorey")
    if not storeys:
        raise ValueError(
            "Master-IFC ei sisällä IfcBuildingStoreyta — merge ei voi "
            "linkittää MagiCAD-osia mihinkään spatiaaliseen rakenteeseen."
        )
    target_storey = storeys[0]

    # Gather the products to merge. Anything descending from IfcProduct
    # except spatial structure containers themselves.
    candidates = [
        p for p in library.by_type("IfcProduct")
        if p.is_a() not in _SPATIAL_STRUCTURE_TYPES
    ]

    if progress:
        progress(f"MagiCAD-IFC: {len(candidates)} tuotetta merge-jonossa")

    appended: list[ifcopenshell.entity_instance] = []
    skipped: int = 0
    type_counts: Counter[str] = Counter()
    # Reuse map cuts duplication of shared dependencies (geometric
    # contexts, materials, styles) across the whole batch.
    reuse: dict[int, ifcopenshell.entity_instance] = {}

    for product in candidates:
        try:
            new_product = ifcopenshell.api.project.append_asset(
                file=master,
                library=library,
                element=product,
                reuse_identities=reuse,
            )
        except Exception as exc:  # noqa: BLE001 — surface to progress, keep going
            if progress:
                progress(
                    f"VAROITUS: append_asset epäonnistui "
                    f"{product.is_a()}#{product.id()}: {exc}"
                )
            skipped += 1
            continue
        appended.append(new_product)
        type_counts[new_product.is_a()] += 1

    if progress:
        progress(
            f"Linkitetään {len(appended)} tuotetta "
            f"storey:hin {target_storey.Name or '(nimetön)'}…"
        )

    # Containment: place every appended product under the master's storey.
    # assign_container takes a list, so do it in one call to avoid N
    # IfcRelContainedInSpatialStructure relations.
    if appended:
        ifcopenshell.api.spatial.assign_container(
            file=master,
            products=appended,
            relating_structure=target_storey,
        )

    if progress:
        progress(f"Tallennetaan yhdistetty IFC → {output_path.name}…")
    master.write(str(output_path))

    return {
        "products_appended": len(appended),
        "products_skipped": skipped,
        "products_total_in_magicad_ifc": len(candidates),
        "ifc_types": dict(type_counts),
    }
