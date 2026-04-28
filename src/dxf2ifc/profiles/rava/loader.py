"""Load RAVA codesets from the bundled JSON files (Plan H Task 7).

The four codeset files (LVI-TUOTEOSA, LVI-JARJESTELMA,
TALOTEKNIIKKA-TUOTEOSA, TALOTEKNIIKKA-JARJESTELMA) ship under this
directory. ``load_rava_codes()`` returns a ``dict[str, RAVACode]``
keyed by ``codeValue`` so callers can look up the Finnish prefLabel
without re-parsing the JSON.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_RAVA_DIR = Path(__file__).resolve().parent

_FILE_TO_CODESET = {
    "lvi_tuoteosa.json": "LVI-TUOTEOSA",
    "lvi_jarjestelma.json": "LVI-JARJESTELMA",
    "talotekniikka_tuoteosa.json": "TALOTEKNIIKKA-TUOTEOSA",
    "talotekniikka_jarjestelma.json": "TALOTEKNIIKKA-JARJESTELMA",
}


@dataclass(frozen=True)
class RAVACode:
    """Single code in a RAVA codeset."""

    code: str
    name: str
    codeset: str


def load_rava_codes() -> dict[str, RAVACode]:
    """Return every committed RAVA code keyed by its ``codeValue``."""
    out: dict[str, RAVACode] = {}
    for filename, codeset in _FILE_TO_CODESET.items():
        path = _RAVA_DIR / filename
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data.get("results", []):
            code_value = entry.get("codeValue")
            if not code_value:
                continue
            label = entry.get("prefLabel", {})
            name = label.get("fi") or label.get("en") or ""
            out[code_value] = RAVACode(code=code_value, name=name, codeset=codeset)
    return out
