"""Bugfix 3: Preview & log paneeli näyttää DXF-yhteenvedon ja Convert-lokin."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_preview_log_panel_appends_info_lines(qtbot):
    from dxf2ifc.gui.preview_log import PreviewLogPanel

    panel = PreviewLogPanel()
    qtbot.addWidget(panel)
    panel.append_info("Reading simple_wall.dxf")
    panel.append_info("Done")
    text = panel.text()
    assert "Reading simple_wall.dxf" in text
    assert "Done" in text


def test_preview_log_panel_appends_success_and_error(qtbot):
    from dxf2ifc.gui.preview_log import PreviewLogPanel

    panel = PreviewLogPanel()
    qtbot.addWidget(panel)
    panel.append_success("Wrote out.ifc")
    panel.append_error("Failed: bad layer")
    text = panel.text()
    assert "Wrote out.ifc" in text
    assert "Failed: bad layer" in text


def test_preview_log_panel_set_dxf_summary_lists_layers(qtbot):
    from dxf2ifc.gui.preview_log import PreviewLogPanel

    panel = PreviewLogPanel()
    qtbot.addWidget(panel)
    panel.set_dxf_summary(
        path="/tmp/fake.dxf",
        entity_count=4,
        layer_counts={"KYL-ULKOSEINA": 2, "KYL-IKKUNA": 1, "KYL-OVET-ULKO": 1},
    )
    text = panel.text()
    assert "fake.dxf" in text
    assert "4 entities" in text
    assert "KYL-ULKOSEINA" in text and "2" in text
    assert "KYL-IKKUNA" in text


def test_preview_log_panel_clear_resets_buffer(qtbot):
    from dxf2ifc.gui.preview_log import PreviewLogPanel

    panel = PreviewLogPanel()
    qtbot.addWidget(panel)
    panel.append_info("noise")
    panel.clear()
    assert panel.text() == ""


def test_preview_log_panel_uses_jetbrains_mono(qtbot):
    from dxf2ifc.gui.preview_log import PreviewLogPanel

    panel = PreviewLogPanel()
    qtbot.addWidget(panel)
    family = panel.fontInfo().family() or panel.font().family()
    assert "Mono" in family or "JetBrains" in family
