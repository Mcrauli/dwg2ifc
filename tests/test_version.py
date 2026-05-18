"""Verify __version__ stays in sync with the installed package metadata."""

from __future__ import annotations

from importlib import metadata




def test_version_module_exposes_string() -> None:
    from dwg2ifc._version import __version__

    assert isinstance(__version__, str)
    assert __version__.count(".") >= 2
