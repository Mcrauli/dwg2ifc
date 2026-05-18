"""IFC surface styling — write ``IfcStyledItem`` for the AutoCAD palette.

Every product the orchestrator emits is coloured with the same hue
(currently AutoCAD ACI 175, a slate-purple) so refrigeration models
arrive in Solibri / MagiCAD with a consistent visual identity. A single
``IfcSurfaceStyle`` is created per file and reused via a cached lookup,
so the styled-items chain stays compact even for a few hundred products.

Why all-elements-same-colour: per Lauri's feedback (2026-05-05), the
default DXF layer palette is too noisy for BIM consumers and a uniform
ACI 175 makes the cooling network instantly recognisable in Solibri's
3D view. If per-rule colouring becomes useful later, this module is
the natural place to thread a ``rule.color_aci`` field.
"""

from __future__ import annotations

import ezdxf.colors

# Lauri's chosen palette index. ezdxf.colors.aci2rgb returns 0–255 ints
# per channel; IFC wants 0..1 floats so we normalise once at module load.
DEFAULT_ACI = 175
_R, _G, _B = ezdxf.colors.aci2rgb(DEFAULT_ACI)
DEFAULT_RGB = (_R / 255.0, _G / 255.0, _B / 255.0)

_STYLE_CACHE_ATTR = "_dwg2ifc_surface_style"


def _ensure_surface_style(ifc) -> object:
    """Create or fetch the file-wide ``IfcSurfaceStyle`` for ACI 175.

    We cache by attribute on the ifc file object — ``ifcopenshell.file``
    accepts arbitrary Python attribute assignment and re-using a single
    style across hundreds of products keeps the IFC compact.
    """
    cached = getattr(ifc, _STYLE_CACHE_ATTR, None)
    if cached is not None:
        return cached

    colour = ifc.create_entity(
        "IfcColourRgb",
        Name=f"AutoCAD ACI {DEFAULT_ACI}",
        Red=DEFAULT_RGB[0],
        Green=DEFAULT_RGB[1],
        Blue=DEFAULT_RGB[2],
    )
    shading = ifc.create_entity(
        "IfcSurfaceStyleShading",
        SurfaceColour=colour,
    )
    style = ifc.create_entity(
        "IfcSurfaceStyle",
        Name=f"dwg2ifc_aci_{DEFAULT_ACI}",
        Side="POSITIVE",
        Styles=[shading],
    )
    setattr(ifc, _STYLE_CACHE_ATTR, style)
    return style


def _representation_items(product) -> list[object]:
    """Walk product.Representation -> Representations[*].Items[*].

    Empty list when the product has no representation yet. Builders are
    expected to call this only after wiring representation, so the
    empty-list path is a defensive no-op rather than an error.
    """
    rep = getattr(product, "Representation", None)
    if rep is None:
        return []
    items: list[object] = []
    for representation in (rep.Representations or []):
        for item in (representation.Items or []):
            items.append(item)
    return items


def apply_color_to_product(ifc, product) -> None:
    """Attach the cached ``IfcSurfaceStyle`` to every geometry item of
    ``product`` via per-item ``IfcStyledItem`` records.

    No-op when the product has no representation — used by orchestrator
    in a generic loop where some IFC entity types (e.g. proxies during
    early dispatch) may not have a Body context yet.

    Idempotent: re-applying to the same product appends new
    ``IfcStyledItem`` records without de-duplicating, but the overhead
    is small and downstream consumers tolerate the redundancy. Builders
    should call once per product.
    """
    style = _ensure_surface_style(ifc)
    for item in _representation_items(product):
        ifc.create_entity(
            "IfcStyledItem",
            Item=item,
            Styles=[style],
            Name=None,
        )
