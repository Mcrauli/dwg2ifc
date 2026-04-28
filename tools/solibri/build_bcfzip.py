"""Build tools/solibri/dxf2ifc.bcfzip — the YTV 2012 + Talo2000 minimum
rule-set encoded as a BCF 2.1 archive with one Topic per rule.

Run from the repo root:

    python -m tools.solibri.build_bcfzip

The script is deterministic (fixed timestamps, fixed GUIDs) so the resulting
bcfzip can be committed and diffed reliably.
"""

from __future__ import annotations

import xml.sax.saxutils as xml_saxutils
import zipfile
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipInfo

BCFZIP_PATH = Path(__file__).resolve().parent / "dxf2ifc.bcfzip"
EPOCH = (2026, 4, 28, 0, 0, 0)
DETERMINISTIC_DATE = "2026-04-28T00:00:00Z"
AUTHOR = "Lauri Rekola (Radika Oy)"


def _esc(text: str) -> str:
    return xml_saxutils.escape(text)


@dataclass(frozen=True)
class Rule:
    guid: str
    title: str
    description: str
    reference: str


RULES: tuple[Rule, ...] = (
    Rule(
        guid="11111111-aaaa-4aaa-aaaa-111111111111",
        title="Units are millimetres",
        description=(
            "YTV 2012 osa 3 (Arkkitehtisuunnittelu) edellyttää että IFC-mallin "
            "pituusyksikkö on millimetri. Solibri-ruleset tarkistaa että "
            "IfcUnitAssignment sisältää SI-yksikön LENGTHUNIT prefixillä MILLI."
        ),
        reference="YTV 2012 osa 3, kohta 4.1.2",
    ),
    Rule(
        guid="22222222-bbbb-4bbb-bbbb-222222222222",
        title="Talo2000 classification coverage",
        description=(
            "Jokainen IfcWall, IfcSlab, IfcDoor ja IfcWindow tulee olla "
            "luokiteltu IfcRelAssociatesClassification-relaatiolla "
            "Talo2000-codesetiin. Sääntö sallii vain RT 10-10962 + YTV 2012 "
            "-mukaiset Talo2000-koodit."
        ),
        reference="RT 10-10962, YTV 2012 osa 3 + osa 4",
    ),
    Rule(
        guid="33333333-cccc-4ccc-cccc-333333333333",
        title="IfcSystem grouping for refrigeration networks",
        description=(
            "Kylmäaineputket (LT IMU, MT IMU, MT NESTE), viemäriputket "
            "(KYL-VIEMARI*), kaapelihyllyt sekä kylmälaitteet (höyrystin / "
            "lauhdutin / kompressori) tulee olla ryhmitelty IfcSystem-objektien "
            "alle IfcRelAssignsToGroup-relaatiolla. Jokaisella IfcSystemillä "
            "≥ 1 jäsen."
        ),
        reference="YTV 2012 osa 4 (TATE) + Plan C ryhmittelypäätös",
    ),
    Rule(
        guid="44444444-dddd-4ddd-dddd-444444444444",
        title="Cold-room panels emit IfcBuildingElementProxy 1352",
        description=(
            "Kylmähuone-elementit (KYL-LEVY*, KYL-NURKKA*) tulee olla "
            "IfcBuildingElementProxy ja luokitella Talo2000 1352. Solibri "
            "kommentoi mikäli paneeli on jätetty IfcWall:ksi."
        ),
        reference="YTV 2012 osa 3, RT 10-10962 koodi 1352",
    ),
    Rule(
        guid="55555555-eeee-4eee-eeee-555555555555",
        title="Cooling equipment uses MEP entity types",
        description=(
            "HOYRYSTIN-blokit kartoitetaan IfcEvaporator, LAUHDUTIN-blokit "
            "IfcCondenser ja KOMPRESSORI-blokit IfcCompressor. IfcFlowFitting "
            "tai IfcBuildingElementProxy ei kelpaa kylmälaitteelle."
        ),
        reference="IFC 4 MEP-skeema + Plan B Section 11",
    ),
)


def _version_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
        '<Version xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'VersionId="2.1">\n'
        "  <DetailedVersion>2.1</DetailedVersion>\n"
        "</Version>\n"
    )


def _markup_xml(rule: Rule) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
        "<Markup>\n"
        f'  <Topic Guid="{rule.guid}" TopicType="Rule" TopicStatus="Active">\n'
        f"    <ReferenceLink>{_esc(rule.reference)}</ReferenceLink>\n"
        f"    <Title>{_esc(rule.title)}</Title>\n"
        f"    <CreationDate>{DETERMINISTIC_DATE}</CreationDate>\n"
        f"    <CreationAuthor>{_esc(AUTHOR)}</CreationAuthor>\n"
        f"    <Description>{_esc(rule.description)}</Description>\n"
        "  </Topic>\n"
        "</Markup>\n"
    )


def _add_deterministic(zf: zipfile.ZipFile, name: str, payload: str) -> None:
    info = ZipInfo(filename=name, date_time=EPOCH)
    info.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(info, payload)


def build(output: Path = BCFZIP_PATH) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        _add_deterministic(zf, "bcf.version", _version_xml())
        for rule in RULES:
            _add_deterministic(zf, f"{rule.guid}/markup.bcf", _markup_xml(rule))
    return output


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path}")
