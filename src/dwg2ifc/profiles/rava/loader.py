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
    short_name: str
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
            short_name = entry.get("shortName") or ""
            out[code_value] = RAVACode(
                code=code_value,
                name=name,
                short_name=short_name,
                codeset=codeset,
            )
    return out


@dataclass(frozen=True)
class TuoteosaHierarchy:
    """FI_Komponentti canonical fields derived from a RAVA tuoteosa code."""

    paaryhma: str
    alaryhma: str
    yleisnimi: str
    yleistunnus: str


_tuoteosa_cache: dict[str, TuoteosaHierarchy] | None = None


def load_tuoteosa_hierarchy() -> dict[str, TuoteosaHierarchy]:
    """Return paaryhma/alaryhma/yleisnimi/yleistunnus for every level-3 tuoteosa code.

    Navigates the broaderCode chain in the RAVA JSON (code → alaryhmä → paaryhma)
    so that FI_Komponentti fields are always consistent with what RAVA defines
    for a given code — which is what Solibri's tunnistaminen check verifies.

    Only TUOTEOSA files (not JÄRJESTELMÄ) contain the hierarchy needed here.
    """
    global _tuoteosa_cache
    if _tuoteosa_cache is not None:
        return _tuoteosa_cache

    tuoteosa_files = ("lvi_tuoteosa.json", "talotekniikka_tuoteosa.json")
    flat: dict[str, dict] = {}
    for filename in tuoteosa_files:
        path = _RAVA_DIR / filename
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data.get("results", []):
            cv = entry.get("codeValue")
            if cv:
                flat[cv] = entry

    result: dict[str, TuoteosaHierarchy] = {}
    for cv, entry in flat.items():
        if entry.get("hierarchyLevel", 0) != 3:
            continue
        label = entry.get("prefLabel", {})
        yleisnimi = label.get("fi") or label.get("en") or ""
        yleistunnus = entry.get("shortName") or ""

        b1 = entry.get("broaderCode") or {}
        alaryhma_cv = b1.get("codeValue", "")
        alaryhma_entry = flat.get(alaryhma_cv, {})
        alaryhma = (alaryhma_entry.get("prefLabel") or {}).get("fi") or ""

        b2 = (alaryhma_entry.get("broaderCode") or {})
        paaryhma_cv = b2.get("codeValue", "")
        paaryhma_entry = flat.get(paaryhma_cv, {})
        paaryhma = (paaryhma_entry.get("prefLabel") or {}).get("fi") or ""

        result[cv] = TuoteosaHierarchy(
            paaryhma=paaryhma,
            alaryhma=alaryhma,
            yleisnimi=yleisnimi,
            yleistunnus=yleistunnus,
        )

    _tuoteosa_cache = result
    return result
