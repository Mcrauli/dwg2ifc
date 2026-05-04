"""Tests for the energy-spec loader (Excel + CSV → FI_Tekninen lookup)."""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest

from dxf2ifc.core.energy_specs import (
    EnergySpec,
    load_energy_specs,
    lookup_spec,
)


def _write_csv(path: Path, rows: list[list[str]]) -> None:
    import csv

    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


def _write_xlsx(path: Path, rows: list[list[object]]) -> None:
    wb = openpyxl.Workbook()
    sheet = wb.active
    for row in rows:
        sheet.append(row)
    wb.save(str(path))


class TestLoadEnergySpecsCSV:
    def test_basic_lookup(self, tmp_path: Path) -> None:
        path = tmp_path / "specs.csv"
        _write_csv(
            path,
            [
                ["Koneikko", "Laitetunnus", "Jäähdytysteho [kW]", "Sähköteho [kW]"],
                ["JK1", "5", "5.2", "0.45"],
                ["JK2", "12", "8.1", "0.7"],
            ],
        )
        specs = load_energy_specs(path)
        assert ("jk1", "5") in specs
        spec = specs[("jk1", "5")]
        assert spec.fields == {"Jäähdytysteho": "5.2", "Sähköteho": "0.45"}
        assert spec.koneikko == "JK1"
        assert spec.laitetunnus == "5"

    def test_handles_semicolon_delimiter(self, tmp_path: Path) -> None:
        path = tmp_path / "specs.csv"
        # European Excel default — sniffer should pick up the semicolon.
        path.write_text(
            "Koneikko;Laitetunnus;Jäähdytysteho [kW]\n"
            "JK1;5;5,2\n",
            encoding="utf-8",
        )
        specs = load_energy_specs(path)
        assert ("jk1", "5") in specs

    def test_empty_rows_skipped(self, tmp_path: Path) -> None:
        path = tmp_path / "specs.csv"
        _write_csv(
            path,
            [
                ["Koneikko", "Laitetunnus", "Jäähdytysteho"],
                [],
                ["JK1", "5", "5.2"],
                ["", "", ""],
                ["JK2", "12", "8.1"],
            ],
        )
        specs = load_energy_specs(path)
        assert len(specs) == 2

    def test_alias_columns_resolved(self, tmp_path: Path) -> None:
        # Common variants the user might type.
        path = tmp_path / "specs.csv"
        _write_csv(
            path,
            [
                ["Koneryhmä", "Pos.", "Cooling capacity [kW]", "Refrigerant"],
                ["JK1", "5", "5.2", "R454C"],
            ],
        )
        specs = load_energy_specs(path)
        spec = specs[("jk1", "5")]
        assert spec.fields == {
            "Jäähdytysteho": "5.2",
            "Kylmäaine": "R454C",
        }


class TestLoadEnergySpecsXLSX:
    def test_basic_xlsx(self, tmp_path: Path) -> None:
        path = tmp_path / "specs.xlsx"
        _write_xlsx(
            path,
            [
                ["Koneikko", "Laitetunnus", "Jäähdytysteho [kW]", "Kylmäaine"],
                ["JK1", 5, 5.2, "R454C"],
                ["JK2", 12, 8.1, "R454C"],
            ],
        )
        specs = load_energy_specs(path)
        spec = specs[("jk1", "5")]
        # Numeric laitetunnus 5 in Excel matches "5" string from POSITIO.
        assert spec.fields == {"Jäähdytysteho": "5.2", "Kylmäaine": "R454C"}

    def test_xlsx_skips_title_rows(self, tmp_path: Path) -> None:
        # User often has a title row (or two) above the table.
        path = tmp_path / "specs.xlsx"
        _write_xlsx(
            path,
            [
                ["Energialista 2026"],
                [None],
                ["Koneikko", "Laitetunnus", "Jäähdytysteho", "Kylmäaine"],
                ["JK1", 5, 5.2, "R454C"],
            ],
        )
        specs = load_energy_specs(path)
        assert ("jk1", "5") in specs

    def test_xlsx_integer_floats_render_clean(self, tmp_path: Path) -> None:
        path = tmp_path / "specs.xlsx"
        _write_xlsx(
            path,
            [
                ["Koneikko", "Laitetunnus", "Sähköteho"],
                ["JK1", 5, 1.0],  # Excel often stores ints as floats
            ],
        )
        spec = load_energy_specs(path)[("jk1", "5")]
        assert spec.fields["Sähköteho"] == "1"


class TestKeyDetection:
    def test_missing_keys_returns_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "no_keys.csv"
        _write_csv(
            path,
            [
                ["Some", "Other", "Columns"],
                ["a", "b", "c"],
            ],
        )
        assert load_energy_specs(path) == {}

    def test_blank_key_rows_skipped(self, tmp_path: Path) -> None:
        path = tmp_path / "blank.csv"
        _write_csv(
            path,
            [
                ["Koneikko", "Laitetunnus", "Jäähdytysteho"],
                ["", "", "5.2"],
                ["JK1", "", "5.2"],
                ["JK1", "5", "5.2"],
            ],
        )
        specs = load_energy_specs(path)
        assert list(specs.keys()) == [("jk1", "5")]

    def test_unsupported_extension_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "x.json"
        path.write_text("{}")
        with pytest.raises(ValueError, match="Unsupported"):
            load_energy_specs(path)


class TestLookupSpec:
    def test_case_insensitive_and_whitespace_tolerant(self) -> None:
        specs = {
            ("jk1", "5"): EnergySpec(
                koneikko="JK1", laitetunnus="5", fields={"Jäähdytysteho": "5.2"}
            )
        }
        assert lookup_spec(specs, koneikko="JK1", laitetunnus="5") is not None
        assert lookup_spec(specs, koneikko="jk1", laitetunnus="5") is not None
        assert lookup_spec(specs, koneikko=" Jk1 ", laitetunnus=" 5 ") is not None

    def test_missing_returns_none(self) -> None:
        specs = {
            ("jk1", "5"): EnergySpec(
                koneikko="JK1", laitetunnus="5", fields={"Jäähdytysteho": "5.2"}
            )
        }
        assert lookup_spec(specs, koneikko="JK1", laitetunnus="9") is None
        assert lookup_spec(specs, koneikko=None, laitetunnus="5") is None
        assert lookup_spec(specs, koneikko="JK1", laitetunnus=None) is None
