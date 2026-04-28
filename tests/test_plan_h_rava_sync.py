"""Plan H Task 5: tools/rava/sync_codes.py fetches the four RAVA codesets
from koodistot.suomi.fi and persists them as JSON under
src/dxf2ifc/profiles/rava/."""

from __future__ import annotations

import json
from pathlib import Path

from tools.rava import sync_codes


def test_codeset_names_constant_lists_four_schemes():
    assert set(sync_codes.CODESETS) == {
        "LVI-TUOTEOSA",
        "LVI-JARJESTELMA",
        "TALOTEKNIIKKA-TUOTEOSA",
        "TALOTEKNIIKKA-JARJESTELMA",
    }


def test_url_for_codeset_targets_official_api():
    url = sync_codes.url_for_codeset("LVI-TUOTEOSA")
    assert url.startswith("https://koodistot.suomi.fi/codelist-api/api/v1/coderegistries/rytj/")
    assert "LVI-TUOTEOSA_Versio_1_0/codes" in url


def test_sync_codes_writes_one_json_per_codeset(monkeypatch, tmp_path: Path):
    fake_payloads = {
        scheme: {
            "results": [{"codeValue": f"{scheme}-001", "prefLabel": {"fi": f"{scheme} dummy 1"}}]
        }
        for scheme in sync_codes.CODESETS
    }

    def fake_fetch(url: str) -> dict:
        for scheme in sync_codes.CODESETS:
            if scheme in url:
                return fake_payloads[scheme]
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(sync_codes, "fetch_json", fake_fetch)
    written = sync_codes.sync(target_dir=tmp_path)
    assert sorted(p.name for p in written) == sorted(
        f"{name.lower().replace('-', '_')}.json" for name in sync_codes.CODESETS
    )
    for path in written:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "results" in data
        assert isinstance(data["results"], list)


def test_sync_codes_default_target_is_profiles_rava(monkeypatch, tmp_path: Path):
    captured: dict[str, Path] = {}

    def fake_sync(*, target_dir: Path) -> list[Path]:
        captured["target_dir"] = target_dir
        return []

    monkeypatch.setattr(sync_codes, "sync", fake_sync)
    sync_codes.cli_main([])
    assert captured["target_dir"].name == "rava"
    assert captured["target_dir"].parent.name == "profiles"
