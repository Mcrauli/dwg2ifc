"""Match DXF entities against profile rules and produce MappedEntity objects."""

from __future__ import annotations

from fnmatch import fnmatch

from dwg2ifc.core.types import EntityRecord, MappedEntity
from dwg2ifc.profiles.schema import Profile, Rule


def layer_matches(pattern: str, layer: str) -> bool:
    """Case-insensitive glob match. ``*`` and ``?`` wildcards supported.

    AutoCAD-exported DXFs frequently carry xref-prefixed layer names of
    the form ``<xref>|<layer>`` (e.g. ``KCM Kauhajoki|AR1241_US``). When
    the pattern does not contain a pipe character but the candidate
    does, the pipe-prefix is stripped before matching so the rule
    targets the suffix layer name only.
    """
    if "|" in layer and "|" not in pattern:
        layer = layer.rsplit("|", 1)[-1]
    return fnmatch(layer.casefold(), pattern.casefold())


def apply_profile(entities: list[EntityRecord], profile: Profile) -> list[MappedEntity]:
    """Match each entity's layer against profile rules (first match wins)
    and return a list of MappedEntity.

    Entities whose layer matches no rule are skipped silently.
    """
    result: list[MappedEntity] = []
    for entity in entities:
        rule = _first_matching_rule(entity.layer, profile.rules)
        if rule is None:
            continue
        extras: dict[str, object] = {}
        if rule.default_height_mm is not None:
            extras["default_height_mm"] = rule.default_height_mm
        if rule.default_thickness_mm is not None:
            extras["default_thickness_mm"] = rule.default_thickness_mm
        if rule.system_name is not None:
            extras["system_name"] = rule.system_name
        if rule.block_handling is not None:
            extras["block_handling"] = rule.block_handling
        pipe_pset = rule.pset_overrides.get("Pset_PipeSegmentOccurrence")
        if pipe_pset and "NominalDiameter" in pipe_pset:
            extras["default_diameter_mm"] = float(pipe_pset["NominalDiameter"])
        result.append(
            MappedEntity(
                layer=entity.layer,
                dxf_type=entity.dxf_type,
                geometry=entity.geometry,
                attributes=entity.attributes,
                block_name=entity.block_name,
                xform=entity.xform,
                handle=entity.handle,
                # ``block_attribs`` carries the INSERT's ATTRIB tag→value
                # map. ``orchestrator._process_one_file`` calls
                # ``apply_block_attribs`` later which merges them into
                # ``fi_tekninen``; without propagating them here that
                # merge sees an empty dict and the user's per-device
                # tech-spec values never reach Solibri.
                block_attribs=dict(entity.block_attribs)
                if entity.block_attribs
                else {},
                ifc_type=rule.ifc_type,
                predefined_type=rule.predefined_type,
                domain=rule.domain,
                talo2000_code=rule.talo2000_code,
                talo2000_name=rule.talo2000_name,
                lvi_code=rule.lvi_code,
                talotekniikka_code=rule.talotekniikka_code,
                fi_komponentti=(
                    rule.fi_komponentti.model_dump(exclude_none=True)
                    if rule.fi_komponentti is not None
                    else None
                ),
                fi_tuote=(
                    rule.fi_tuote.model_dump(exclude_none=True)
                    if rule.fi_tuote is not None
                    else None
                ),
                fi_tekninen=dict(rule.fi_tekninen) if rule.fi_tekninen else None,
                fi_sijainti=dict(rule.fi_sijainti) if rule.fi_sijainti else None,
                extra_props=extras,
            )
        )
    return result


def _first_matching_rule(layer: str, rules: list[Rule]) -> Rule | None:
    for rule in rules:
        if layer_matches(rule.layer_pattern, layer):
            return rule
    return None
