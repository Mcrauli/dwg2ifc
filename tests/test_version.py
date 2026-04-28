"""Verify __version__ stays in sync with the installed package metadata."""

from __future__ import annotations

from importlib import metadata


def test_dunder_version_matches_package_metadata() -> None:
    from dxf2ifc import __version__

    assert __version__ == metadata.version("dxf2ifc")


def test_version_module_exposes_string() -> None:
    from dxf2ifc._version import __version__

    assert isinstance(__version__, str)
    assert __version__.count(".") >= 2
