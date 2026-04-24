"""Match DXF entities against profile rules and produce MappedEntity objects."""
from __future__ import annotations

from fnmatch import fnmatch


def layer_matches(pattern: str, layer: str) -> bool:
    """Case-insensitive glob match. '*' and '?' wildcards supported."""
    return fnmatch(layer.casefold(), pattern.casefold())
