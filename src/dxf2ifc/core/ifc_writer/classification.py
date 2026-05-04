"""IfcClassification + IfcClassificationReference helpers
(Talo2000, RAVA-LVI, RAVA-TATE, suunnittelualat)."""

from __future__ import annotations

import ifcopenshell
import ifcopenshell.guid


_CLASSIFICATION_SOURCES: dict[str, dict[str, str]] = {
    "Talo2000": {"Source": "Rakennustieto Oy", "Edition": "Talo 2000"},
    "RAVA-LVI": {"Source": "Rakennustietojärjestelmä RYTJ", "Edition": "LVI-TUOTEOSA v1.0"},
    "RAVA-TATE": {
        "Source": "Rakennustietojärjestelmä RYTJ",
        "Edition": "TALOTEKNIIKKA-TUOTEOSA v1.0",
    },
}


def _classification_name_for(domain: str, code: str) -> str:
    """Resolve the IfcClassification.Name for a (domain, code) pair."""
    if domain == "ARK":
        return "Talo2000"
    if domain in ("TATE", "KYL"):
        if code.startswith("T-LVI"):
            return "RAVA-LVI"
        if code.startswith("T-TATE"):
            return "RAVA-TATE"
    raise ValueError(f"Cannot resolve classification source for domain={domain!r}, code={code!r}")


def add_classification(
    ifc, product, *, domain: str, code: str | None, name: str | None = None
) -> object | None:
    """Attach a discipline-aware IfcClassificationReference to ``product``.

    domain="ARK" emits IfcClassification "Talo2000".
    domain="TATE" emits "RAVA-LVI" for T-LVI-… codes and "RAVA-TATE" for
    T-TATE-… codes. Returns ``None`` and does nothing if ``code`` is empty.
    Each IfcClassification entity is created at most once per file and
    reused across products.
    """
    if not code:
        return None
    classification_name = _classification_name_for(domain, code)
    existing = [c for c in ifc.by_type("IfcClassification") if c.Name == classification_name]
    if existing:
        classification = existing[0]
    else:
        meta = _CLASSIFICATION_SOURCES[classification_name]
        classification = ifc.create_entity(
            "IfcClassification",
            Source=meta["Source"],
            Edition=meta["Edition"],
            Name=classification_name,
        )

    reference = ifc.create_entity(
        "IfcClassificationReference",
        Identification=code,
        Name=name,
        ReferencedSource=classification,
    )
    ifc.create_entity(
        "IfcRelAssociatesClassification",
        GlobalId=ifcopenshell.guid.new(),
        RelatedObjects=[product],
        RelatingClassification=reference,
    )
    return reference


def add_discipline_classification(
    ifc, product, *, domain: str
) -> object | None:
    """Attach an explicit ``suunnittelualat`` classification per discipline.

    Solibri's rule engine otherwise infers every product as ARK from
    its IFC entity type (yes, even IfcEvaporator), which is wrong for
    refrigeration products. By emitting an explicit ``IfcClassification``
    named ``suunnittelualat`` with reference ``ARK`` / ``TATE`` / ``KYL``,
    the discipline appears in the "Luokittelusäännöistä" tab as
    authoritative and Solibri's heuristic no longer overrides it.

    Refrigeration items use ``KYL`` rather than the more generic ``TATE``
    so cold-room equipment shows up under the right design discipline.

    The IfcClassification entity is created once per file and reused
    across products (same dedup pattern as :func:`add_classification`).
    """
    if domain not in ("ARK", "TATE", "KYL"):
        return None
    existing = [c for c in ifc.by_type("IfcClassification") if c.Name == "suunnittelualat"]
    if existing:
        classification = existing[0]
    else:
        classification = ifc.create_entity(
            "IfcClassification",
            Source="dxf2ifc",
            Edition="1.0",
            Name="suunnittelualat",
        )
    reference = ifc.create_entity(
        "IfcClassificationReference",
        Identification=domain,
        Name=domain,
        ReferencedSource=classification,
    )
    ifc.create_entity(
        "IfcRelAssociatesClassification",
        GlobalId=ifcopenshell.guid.new(),
        RelatedObjects=[product],
        RelatingClassification=reference,
    )
    return reference


def add_talo2000_classification(
    ifc, product, *, code: str | None, name: str | None
) -> object | None:
    """Backwards-compatible wrapper around :func:`add_classification` (ARK domain).

    Returns ``None`` and does nothing for products without a Talo2000 code
    (TATE-domain rules use ``add_classification`` directly with their RAVA code).
    """
    return add_classification(ifc, product, domain="ARK", code=code, name=name)
