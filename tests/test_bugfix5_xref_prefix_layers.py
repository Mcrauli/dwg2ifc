"""Bugfix 5: xref-prefixed layer names like 'KCM Kauhajoki...|AR1241_US'
must match profile rules whose pattern targets the suffix part."""

from __future__ import annotations

from dxf2ifc.core.mapper import layer_matches


def test_layer_matches_strips_xref_prefix():
    # AutoCAD xref-imported layers are formatted '<xref>|<layer>'.
    assert layer_matches("AR1241_US", "KCM Kauhajoki|AR1241_US")
    assert layer_matches("KYL-ULKOSEINA", "Storage|KYL-ULKOSEINA")
    assert layer_matches("KAAPELIHYLLY*", "Project Foo|KAAPELIHYLLY-A")


def test_layer_matches_full_name_still_works():
    assert layer_matches("AR1241_US", "AR1241_US")
    assert layer_matches("KAAPELIHYLLY*", "KAAPELIHYLLY-A")
    assert not layer_matches("AR1241_US", "AR9999_FAKE")


def test_layer_matches_does_not_strip_when_no_pipe():
    # Sanity: hyphens are NOT pipes.
    assert not layer_matches("AR1241", "KCM-AR1241")


def test_layer_matches_pipe_with_wildcard_pattern():
    assert layer_matches("AR12*_US", "Block123|AR1241_US")
