"""Match DXF entities against profile rules and produce MappedEntity objects."""
from __future__ import annotations

from fnmatch import fnmatch

from dxf2ifc.core.types import EntityRecord, MappedEntity
from dxf2ifc.profiles.schema import Profile, Rule


def layer_matches(pattern: str, layer: str) -> bool:
    """Case-insensitive glob match. '*' and '?' wildcards supported."""
    return fnmatch(layer.casefold(), pattern.casefold())


def apply_profile(
    entities: list[EntityRecord], profile: Profile
) -> list[MappedEntity]:
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
        result.append(
            MappedEntity(
                layer=entity.layer,
                dxf_type=entity.dxf_type,
                geometry=entity.geometry,
                attributes=entity.attributes,
                block_name=entity.block_name,
                xform=entity.xform,
                ifc_type=rule.ifc_type,
                predefined_type=rule.predefined_type,
                talo2000_code=rule.talo2000_code,
                talo2000_name=rule.talo2000_name,
                extra_props=extras,
            )
        )
    return result


def _first_matching_rule(layer: str, rules: list[Rule]) -> Rule | None:
    for rule in rules:
        if layer_matches(rule.layer_pattern, layer):
            return rule
    return None
