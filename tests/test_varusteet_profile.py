"""VARUSTEET-LISP-laitteiden layer-mappaus default-profiilissa.

Six new device blocks (CO2-anturi, CO2-sireeni, Huolto-PC, RK-JK10,
Säädinkeskus, Hätäseis) created in autocad-lisp-ohjeet/Laitteet/ and
inserted via the VARUSTEET LISP command. The default profile maps
their KYL-* layers to IFC4 distribution-element types with
T-LVI-01-01-999 (MUU - Lämmitys- ja jäähdytyslaitteistot) or
T-TATE-02-01-004 (Tilavaraus - keskus) RAVA codes.
"""

from __future__ import annotations

import pytest

from dwg2ifc.core.mapper import layer_matches
from dwg2ifc.profiles.loader import load_default_profile


@pytest.mark.parametrize(
    "layer, expected_ifc, expected_predef, expected_code",
    [
        ("KYL-CO2-ANTURI", "IfcSensor", "CO2SENSOR", "T-LVI-01-01-999"),
        ("KYL-CO2-SIREENI", "IfcAlarm", "SIREN", "T-LVI-01-01-999"),
        ("KYL-HUOLTO-PC", "IfcCommunicationsAppliance", "COMPUTER", "T-LVI-01-01-999"),
        ("KYL-RK-JK10", "IfcElectricDistributionBoard", "DISTRIBUTIONBOARD", "T-TATE-02-01-004"),
        ("KYL-SAADINKESKUS-KU", "IfcController", "PROGRAMMABLE", "T-TATE-02-01-004"),
        ("KYL-HATASEIS", "IfcSwitchingDevice", "EMERGENCYSTOP", "T-LVI-01-01-999"),
    ],
)
def test_varusteet_layer_maps_to_expected_ifc_type_and_rava_code(
    layer: str, expected_ifc: str, expected_predef: str, expected_code: str
) -> None:
    """Each VARUSTEET-LISP layer must resolve to the right IFC4 class +
    predefined type + RAVA tilavaraus-koodi when the default profile
    is loaded."""
    profile = load_default_profile()
    rule = next((r for r in profile.rules if layer_matches(r.layer_pattern, layer)), None)
    assert rule is not None, f"no rule matches {layer}"
    assert rule.ifc_type == expected_ifc
    assert rule.predefined_type == expected_predef
    code = rule.lvi_code or rule.talotekniikka_code
    assert code == expected_code
    assert rule.domain == "KYL"


def test_varusteet_layer_specific_rule_wins_over_generic_kyl_pattern():
    """Make sure the specific KYL-CO2-ANTURI / KYL-HATASEIS rules are
    matched before any generic KYL-* fallback (first-match-wins in
    profile.rules order). Regression guard if someone ever adds a
    catch-all KYL-* rule above these in the TOML."""
    profile = load_default_profile()
    for layer, expected in [
        ("KYL-CO2-ANTURI", "IfcSensor"),
        ("KYL-CO2-SIREENI", "IfcAlarm"),
        ("KYL-HATASEIS", "IfcSwitchingDevice"),
    ]:
        rule = next((r for r in profile.rules if layer_matches(r.layer_pattern, layer)), None)
        assert rule is not None and rule.ifc_type == expected, (
            f"{layer} mapped to {rule.ifc_type if rule else None}, expected {expected}"
        )


def test_existing_kyl_rk_pattern_still_matches_kyl_rk_jk_layers():
    """The new KYL-RK-JK10 layer is covered by the existing wildcard
    KYL-RK-* rule (we only updated its RAVA code, not its pattern).
    Verify the wildcard still matches a generic KYL-RK-JK7 too."""
    profile = load_default_profile()
    for layer in ("KYL-RK-JK10", "KYL-RK-JK7", "KYL-RK-PROJEKTI42"):
        rule = next((r for r in profile.rules if layer_matches(r.layer_pattern, layer)), None)
        assert rule is not None
        assert rule.ifc_type == "IfcElectricDistributionBoard"
        assert rule.talotekniikka_code == "T-TATE-02-01-004"


def test_existing_kyl_kk_pattern_uses_corrected_rava_code():
    """KYL-KK-* (Koneikkokeskus) — RAVA code was T-TATE-01-01-099
    (placeholder under Asennushyllyt) until alpha19. Should now be
    T-TATE-02-01-004 (Tilavaraus - keskus), the correct RAVA-konventio
    for kylmäsuunnittelijan keskuksia."""
    profile = load_default_profile()
    rule = next((r for r in profile.rules if layer_matches(r.layer_pattern, "KYL-KK-JK1")), None)
    assert rule is not None
    assert rule.ifc_type == "IfcElectricDistributionBoard"
    assert rule.talotekniikka_code == "T-TATE-02-01-004"


def test_varusteet_predefined_types_valid_in_ifc4_schema():
    """Spot-check that every PredefinedType used by VARUSTEET rules is
    a valid IFC4 enum member — guards against typos that would crash
    at convert_dxf time (IfcController.PROGRAMMABLECONTROLLER vs
    IFC4's actual PROGRAMMABLE)."""
    import ifcopenshell
    import ifcopenshell.api

    ifc = ifcopenshell.file(schema="IFC4")
    profile = load_default_profile()
    layers_under_test = [
        "KYL-CO2-ANTURI",
        "KYL-CO2-SIREENI",
        "KYL-HUOLTO-PC",
        "KYL-RK-JK10",
        "KYL-SAADINKESKUS-KU",
        "KYL-HATASEIS",
    ]
    for layer in layers_under_test:
        rule = next(r for r in profile.rules if layer_matches(r.layer_pattern, layer))
        ifcopenshell.api.run(
            "root.create_entity",
            ifc,
            ifc_class=rule.ifc_type,
            name=f"test-{layer}",
            predefined_type=rule.predefined_type,
        )
