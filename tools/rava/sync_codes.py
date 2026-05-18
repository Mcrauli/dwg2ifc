"""Sync the four RAVA codesets from the official koodistot.suomi.fi
JSON API (Plan H Section 2 Task 5).

Each codeset becomes a JSON file under
``src/dwg2ifc/profiles/rava/<scheme_snakecase>.json``. Tests stub
``fetch_json`` so the real network call is only made when Lauri runs the
script manually.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_TARGET_DIR = REPO_ROOT / "src" / "dwg2ifc" / "profiles" / "rava"

CODESETS: tuple[str, ...] = (
    "LVI-TUOTEOSA",
    "LVI-JARJESTELMA",
    "TALOTEKNIIKKA-TUOTEOSA",
    "TALOTEKNIIKKA-JARJESTELMA",
)

API_URL_TEMPLATE = (
    "https://koodistot.suomi.fi/codelist-api/api/v1/coderegistries/rytj/"
    "codeschemes/{scheme}_Versio_1_0/codes"
)


def url_for_codeset(scheme: str) -> str:
    return API_URL_TEMPLATE.format(scheme=scheme)


def fetch_json(url: str) -> dict[str, Any]:
    """Real network fetch — replaced in tests via monkeypatch."""
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310 — trusted gov URL
        return json.loads(resp.read().decode("utf-8"))


def _filename_for(scheme: str) -> str:
    return scheme.lower().replace("-", "_") + ".json"


def sync(*, target_dir: Path = DEFAULT_TARGET_DIR) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for scheme in CODESETS:
        payload = fetch_json(url_for_codeset(scheme))
        path = target_dir / _filename_for(scheme)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(path)
    return written


def cli_main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.rava.sync_codes")
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=DEFAULT_TARGET_DIR,
        help="Where to write the codeset JSON files.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    sync(target_dir=args.target_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(cli_main())
