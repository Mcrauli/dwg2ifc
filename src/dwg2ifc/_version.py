"""Single source of truth for the dwg2ifc version string.

Kept in sync manually with `pyproject.toml`. PyInstaller's VSVersionInfo
resource and the GitHub release-workflow read this at build time.
"""

from __future__ import annotations

__version__ = "0.3.0a27"
