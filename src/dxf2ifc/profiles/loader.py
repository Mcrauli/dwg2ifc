"""Load and dump mapping profiles backed by TOML files."""

from __future__ import annotations

import tomllib
from importlib import resources
from pathlib import Path

import tomli_w

from dxf2ifc.profiles.schema import Profile

_DEFAULT_RESOURCE = "default_kylmalaite.toml"
_TATE_ONLY_RESOURCE = "default_kylmalaite_tate_only.toml"


def _parse_profile(toml_text: str) -> Profile:
    data = tomllib.loads(toml_text)
    merged = dict(data.get("profile", {}))
    merged["rules"] = data.get("rules", [])
    return Profile.model_validate(merged)


def load_profile(path: str | Path) -> Profile:
    """Load and validate a profile from a TOML file path."""
    return _parse_profile(Path(path).read_text(encoding="utf-8"))


def _load_packaged(resource: str) -> Profile:
    package_files = resources.files("dxf2ifc.profiles")
    return _parse_profile(package_files.joinpath(resource).read_text(encoding="utf-8"))


def load_default_profile() -> Profile:
    """Load the bundled Kylmälaite Talo2000 profile via importlib.resources."""
    return _load_packaged(_DEFAULT_RESOURCE)


def load_default_tate_only_profile() -> Profile:
    """Load the bundled TATE-only Kylmälaite profile (Bugfix 12).

    This profile drops every architectural rule (walls, slabs, doors,
    windows, panels, AR/K layers) so the converter only emits IFC for
    elements a Finnish refrigeration designer actually models — pipes,
    drains, cable carriers, shelving, and cooling equipment.
    """
    return _load_packaged(_TATE_ONLY_RESOURCE)


def dump_profile(profile: Profile, path: str | Path) -> None:
    """Serialize ``profile`` to ``path`` as TOML in the load_profile schema."""
    profile_data = profile.model_dump(exclude_none=True, exclude_defaults=False)
    rules = profile_data.pop("rules", [])
    document = {"profile": profile_data, "rules": rules}
    Path(path).write_bytes(tomli_w.dumps(document).encode("utf-8"))
