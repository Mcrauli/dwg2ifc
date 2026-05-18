"""Plan H Task 6: committed RAVA codeset JSONs cover the verified codes."""

from __future__ import annotations

import json
from pathlib import Path

RAVA_DIR = Path(__file__).resolve().parent.parent / "src" / "dwg2ifc" / "profiles" / "rava"


def _load(name: str) -> dict:
    return json.loads((RAVA_DIR / name).read_text(encoding="utf-8"))


def test_all_four_codeset_files_exist():
    for name in (
        "lvi_tuoteosa.json",
        "lvi_jarjestelma.json",
        "talotekniikka_tuoteosa.json",
        "talotekniikka_jarjestelma.json",
    ):
        assert (RAVA_DIR / name).is_file(), f"missing {name}"


def test_lvi_tuoteosa_contains_verified_cooling_codes():
    data = _load("lvi_tuoteosa.json")
    codes = {c["codeValue"]: c["prefLabel"]["fi"] for c in data["results"]}
    # Labels from koodistot.suomi.fi/codelist-api after sync_codes.py
    # ran (Plan H Task 6 completion). Mismatch versus historical stub
    # is normal — official RYTJ labels are the canonical truth.
    assert codes["T-LVI-01-01-023"] == "Höyrystin"
    assert codes["T-LVI-01-01-018"] == "Lauhdutin"
    assert codes["T-LVI-01-01-017"] == "Kompressori"
    assert codes["T-LVI-01-01-005"] == "Jäähdytyskompressorikoneikko"
    assert codes["T-LVI-01-01-019"] == "Kompressorilauhdutin"
    assert codes["T-LVI-01-01-024"] == "Välijäähdytin"
    assert codes["T-LVI-01-01-003"] == "Vedenjäähdytyskone"
    assert codes["T-LVI-01-01-004"] == "Kylmävesiasema"
    assert codes["T-LVI-03-07-012"] == "Kylmäainevaraajasäiliö"
    assert codes["T-LVI-04-01-001"] == "Viemäriputki"
    assert codes["T-LVI-02"] == "PUTKISTOT"


def test_talotekniikka_tuoteosa_contains_cable_carrier_codes():
    data = _load("talotekniikka_tuoteosa.json")
    codes = {c["codeValue"]: c["prefLabel"]["fi"] for c in data["results"]}
    assert codes["T-TATE-01-01-001"] == "Asennushylly"
    assert codes["T-TATE-01-02"] == "ASENNUSKANAVAT JA -KANAVAOSAT"


def test_talotekniikka_tuoteosa_contains_space_reservation_codes():
    """Sähkölaite-tilavaraukset käytetään VARUSTEET-LISP:n laitteille
    (CO2-anturi, sireeni, Huolto-PC, RK, säädinkeskus, hätäseis) —
    kylmäsuunnittelija varaa tilan, sähkösuunnittelija korvaa."""
    data = _load("talotekniikka_tuoteosa.json")
    codes = {c["codeValue"]: c["prefLabel"]["fi"] for c in data["results"]}
    assert codes["T-TATE-02-01-003"] == "Tilavaraus - laitteisto"
    assert codes["T-TATE-02-01-004"] == "Tilavaraus - keskus"
