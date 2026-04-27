"""Plan D Task 4: bundled font assets and license documentation."""

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"

EXPECTED_FONTS = [
    "Inter-Regular.ttf",
    "Inter-Medium.ttf",
    "Inter-SemiBold.ttf",
    "Inter-Bold.ttf",
    "SpaceGrotesk-Medium.ttf",
    "SpaceGrotesk-Bold.ttf",
    "JetBrainsMono-Medium.ttf",
]


def test_all_required_font_files_present():
    missing = [name for name in EXPECTED_FONTS if not (ASSETS_DIR / name).is_file()]
    assert not missing, f"missing font files: {missing}"


def test_font_files_have_non_trivial_size():
    for name in EXPECTED_FONTS:
        size = (ASSETS_DIR / name).stat().st_size
        assert size > 50_000, f"{name} suspiciously small ({size} bytes)"


def test_licenses_md_documents_open_font_license():
    licenses = (ASSETS_DIR / "LICENSES.md").read_text(encoding="utf-8")
    assert "SIL Open Font License" in licenses
    for family in ("Inter", "Space Grotesk", "JetBrains Mono"):
        assert family in licenses
