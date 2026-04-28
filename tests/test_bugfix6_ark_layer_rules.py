"""Bugfix 6: default profile recognises common AutoCAD ARK-prefix layer
names that already encode their Talo2000 code in the layer name."""

from __future__ import annotations

from dxf2ifc.profiles.loader import load_default_profile


def _ifc_for_layer(layer: str) -> tuple[str | None, str | None, str | None]:
    """Return (ifc_type, talo2000_code, predefined_type) for the first
    rule whose layer_pattern matches *layer*."""
    profile = load_default_profile()
    from dxf2ifc.core.mapper import layer_matches

    for rule in profile.rules:
        if layer_matches(rule.layer_pattern, layer):
            return rule.ifc_type, rule.talo2000_code, rule.predefined_type
    return None, None, None


def test_ar1241_us_maps_to_ifcwall_standard_1241():
    ifc, code, pre = _ifc_for_layer("AR1241_US")
    assert ifc == "IfcWall"
    assert code == "1241"
    assert pre in {None, "STANDARD"}


def test_ar1242_ikkuna_maps_to_ifcwindow_1242():
    ifc, code, _ = _ifc_for_layer("AR1242_IKKUNA")
    assert ifc == "IfcWindow"
    assert code == "1242"


def test_ar1245_lasius_maps_to_ifcwall_standard_1241():
    ifc, code, _ = _ifc_for_layer("AR1245_LASIUS")
    assert ifc == "IfcWall"
    # Lasi-US falls back to ulkoseinät 1241 (LASIUS = lasinen ulkoseinä).
    assert code == "1241"


def test_ar1311_vs_maps_to_ifcwall_partitioning_1311():
    ifc, code, pre = _ifc_for_layer("AR1311_VS")
    assert ifc == "IfcWall"
    assert code == "1311"
    assert pre == "PARTITIONING"


def test_ar1233_pilari_maps_to_ifccolumn():
    ifc, _, _ = _ifc_for_layer("AR1233_PILARI")
    assert ifc == "IfcColumn"


def test_ar1314_kaide_maps_to_ifcrailing():
    ifc, _, _ = _ifc_for_layer("AR1314_KAIDE")
    assert ifc == "IfcRailing"


def test_ar1317_tilaportaat_maps_to_ifcstair():
    ifc, _, _ = _ifc_for_layer("AR1317_TILAPORTAAT")
    assert ifc == "IfcStair"


def test_ar1331_kiinto_maps_to_ifcfurniture_1331():
    ifc, code, _ = _ifc_for_layer("AR1331_KIINTO")
    assert ifc == "IfcFurniture"
    assert code == "1331"


def test_k_ovet_maps_to_ifcdoor():
    ifc, _, _ = _ifc_for_layer("K-OVET")
    assert ifc == "IfcDoor"


def test_k_seinat_valiseinat_maps_to_ifcwall_partitioning():
    ifc, _, pre = _ifc_for_layer("K-SEINÄT_VÄLISEINÄT")
    assert ifc == "IfcWall"
    assert pre == "PARTITIONING"


def test_k_kalusteet_variants_map_to_ifcfurniture():
    for layer in ("K-KALUSTEET", "K-KIINTOKALUSTEET", "K-RST-KALUSTEET"):
        ifc, _, _ = _ifc_for_layer(layer)
        assert ifc == "IfcFurniture", layer


def test_k_valaistus_maps_to_ifclightfixture():
    ifc, _, _ = _ifc_for_layer("K-VALAISTUS")
    assert ifc == "IfcLightFixture"


def test_xref_prefixed_ar_layers_still_match():
    ifc, code, _ = _ifc_for_layer("KCM Kauhajoki|AR1241_US")
    assert ifc == "IfcWall"
    assert code == "1241"
