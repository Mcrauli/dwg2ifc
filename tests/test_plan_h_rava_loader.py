"""Plan H Task 7: profiles.rava.loader.load_rava_codes returns the
codes from the four committed JSON files keyed by codeValue."""

from __future__ import annotations

from dwg2ifc.profiles.rava.loader import RAVACode, load_rava_codes


def test_load_rava_codes_returns_dict_of_ravacode():
    codes = load_rava_codes()
    assert isinstance(codes, dict)
    assert codes
    assert all(isinstance(v, RAVACode) for v in codes.values())


def test_load_rava_codes_indexes_by_code_value():
    codes = load_rava_codes()
    hoyrystin = codes["T-LVI-01-01-023"]
    assert hoyrystin.code == "T-LVI-01-01-023"
    assert hoyrystin.name == "Höyrystin"
    assert hoyrystin.codeset == "LVI-TUOTEOSA"


def test_load_rava_codes_covers_every_decision_log_code():
    codes = load_rava_codes()
    for code in (
        "T-LVI-01-01-023",  # Höyrystin
        "T-LVI-01-01-018",  # Lauhdutin
        "T-LVI-01-01-017",  # Kompressori
        "T-LVI-01-01-005",  # Jäähdytyskompressorikoneikko
        "T-LVI-01-01-019",  # Kompressorilauhdutin
        "T-LVI-01-01-024",  # Välijäähdytin
        "T-LVI-01-01-003",  # Vedenjäähdytyskone
        "T-LVI-01-01-004",  # Kylmävesiasema
        "T-LVI-03-07-012",  # Kylmäainevaraajasäiliö
        "T-LVI-04-01-001",  # Viemäriputki
        "T-LVI-02",  # Putkiosat-yleiskategoria
        "T-TATE-01-01-001",  # Kaapelihylly
        "T-TATE-01-02",  # Asennuskanavat
    ):
        assert code in codes, f"missing RAVA code: {code}"


def test_ravacode_dataclass_shape():
    code = RAVACode(code="T-LVI-X", name="Test", codeset="LVI-TUOTEOSA", short_name="TX")
    assert code.code == "T-LVI-X"
    assert code.name == "Test"
    assert code.codeset == "LVI-TUOTEOSA"
    assert code.short_name == "TX"
