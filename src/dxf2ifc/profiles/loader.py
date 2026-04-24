"""Load a mapping profile from a TOML file."""
from __future__ import annotations

import tomllib
from importlib import resources
from pathlib import Path

from dxf2ifc.profiles.schema import Profile

_DEFAULT_RESOURCE = "default_kylmalaite_talo2000.toml"


def _parse_profile(toml_text: str) -> Profile:
    data = tomllib.loads(toml_text)
    merged = dict(data.get("profile", {}))
    merged["rules"] = data.get("rules", [])
    return Profile.model_validate(merged)


def load_profile(path: str | Path) -> Profile:
    """Load and validate a profile from a TOML file path."""
    return _parse_profile(Path(path).read_text(encoding="utf-8"))


def load_default_profile() -> Profile:
    """Load the bundled Kylmälaite Talo2000 profile via importlib.resources."""
    package_files = resources.files("dxf2ifc.profiles")
    toml_text = package_files.joinpath(_DEFAULT_RESOURCE).read_text(encoding="utf-8")
    return _parse_profile(toml_text)
