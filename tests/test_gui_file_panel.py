"""Plan D Task 10: FilePanel widget for DXF input + IFC output + Convert."""

import os
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_file_panel_browse_input_fills_line_edit(qtbot, tmp_path):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)

    fake_path = str(tmp_path / "input.dxf")
    with patch(
        "dxf2ifc.gui.file_panel.QtWidgets.QFileDialog.getOpenFileName",
        return_value=(fake_path, "DXF files (*.dxf)"),
    ):
        panel.browse_input_button.click()

    assert panel.input_edit.text() == fake_path


def test_file_panel_browse_output_fills_line_edit(qtbot, tmp_path):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)

    fake_path = str(tmp_path / "output.ifc")
    with patch(
        "dxf2ifc.gui.file_panel.QtWidgets.QFileDialog.getSaveFileName",
        return_value=(fake_path, "IFC files (*.ifc)"),
    ):
        panel.browse_output_button.click()

    assert panel.output_edit.text() == fake_path


def test_file_panel_convert_button_emits_signal_with_paths(qtbot, tmp_path):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    panel.input_edit.setText(str(tmp_path / "in.dxf"))
    panel.output_edit.setText(str(tmp_path / "out.ifc"))

    with qtbot.waitSignal(panel.convert_requested, timeout=500) as sig:
        panel.convert_button.click()
    # (dxf, ifc, energy_specs="" empty when not picked, floor_elevation_mm=0.0,
    # quick_convert=False)
    assert sig.args == [
        str(tmp_path / "in.dxf"),
        str(tmp_path / "out.ifc"),
        "",
        0.0,
        False,
        True,
        "",
    ]


def test_file_panel_floor_elevation_default_is_zero(qtbot):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    assert panel.floor_elevation_edit.value() == 0.0


def test_file_panel_floor_elevation_checkbox_default_is_checked(qtbot):
    """Default-on because the floor-relative drawing workflow is the
    common case in Finnish refrigeration design — Lauri's absolute-coord
    workflow is the minority and is opted into by unticking once."""
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    assert panel.floor_elevation_enabled_checkbox.isChecked() is True
    assert panel.floor_elevation_edit.isEnabled() is True


def test_file_panel_unchecking_disables_spinbox(qtbot):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    panel.floor_elevation_enabled_checkbox.setChecked(False)
    assert panel.floor_elevation_edit.isEnabled() is False


def test_file_panel_emits_zero_when_checkbox_unchecked(qtbot, tmp_path):
    """When the user unticks 1.krs korko, DXF Z passes through to IFC
    unchanged — the panel must emit 0.0 regardless of the spinbox value
    (which we keep around so re-enabling restores the last typed number)."""
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    panel.input_edit.setText(str(tmp_path / "in.dxf"))
    panel.output_edit.setText(str(tmp_path / "out.ifc"))
    panel.floor_elevation_edit.setValue(12000.0)
    panel.floor_elevation_enabled_checkbox.setChecked(False)

    with qtbot.waitSignal(panel.convert_requested, timeout=500) as sig:
        panel.convert_button.click()
    assert sig.args == [
        str(tmp_path / "in.dxf"),
        str(tmp_path / "out.ifc"),
        "",
        0.0,
        False,
        True,
        "",
    ]


def test_file_panel_emits_floor_elevation_with_convert(qtbot, tmp_path):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    panel.input_edit.setText(str(tmp_path / "in.dxf"))
    panel.output_edit.setText(str(tmp_path / "out.ifc"))
    panel.floor_elevation_edit.setValue(12000.0)

    with qtbot.waitSignal(panel.convert_requested, timeout=500) as sig:
        panel.convert_button.click()
    assert sig.args == [
        str(tmp_path / "in.dxf"),
        str(tmp_path / "out.ifc"),
        "",
        12000.0,
        False,
        True,
        "",
    ]


def test_file_panel_browse_energy_fills_line_edit(qtbot, tmp_path):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)

    fake_path = str(tmp_path / "energy.xlsx")
    with patch(
        "dxf2ifc.gui.file_panel.QtWidgets.QFileDialog.getOpenFileName",
        return_value=(fake_path, "Excel & CSV (*.xlsx *.xlsm *.csv *.tsv)"),
    ):
        panel.browse_energy_button.click()

    assert panel.energy_edit.text() == fake_path


def test_file_panel_convert_with_energy_specs_path(qtbot, tmp_path):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    panel.input_edit.setText(str(tmp_path / "in.dxf"))
    panel.output_edit.setText(str(tmp_path / "out.ifc"))
    panel.energy_edit.setText(str(tmp_path / "energy.xlsx"))

    with qtbot.waitSignal(panel.convert_requested, timeout=500) as sig:
        panel.convert_button.click()
    assert sig.args == [
        str(tmp_path / "in.dxf"),
        str(tmp_path / "out.ifc"),
        str(tmp_path / "energy.xlsx"),
        0.0,
        False,
        True,
        "",
    ]


def test_file_panel_browse_magicad_ifc_fills_line_edit(qtbot, tmp_path):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)

    fake_path = str(tmp_path / "magicad.ifc")
    with patch(
        "dxf2ifc.gui.file_panel.QtWidgets.QFileDialog.getOpenFileName",
        return_value=(fake_path, "IFC-tiedostot (*.ifc)"),
    ):
        panel.browse_magicad_ifc_button.click()

    assert panel.magicad_ifc_edit.text() == fake_path


def test_file_panel_convert_emits_magicad_ifc_path(qtbot, tmp_path):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    panel.input_edit.setText(str(tmp_path / "in.dxf"))
    panel.output_edit.setText(str(tmp_path / "out.ifc"))
    panel.magicad_ifc_edit.setText(str(tmp_path / "magicad.ifc"))

    with qtbot.waitSignal(panel.convert_requested, timeout=500) as sig:
        panel.convert_button.click()
    assert sig.args == [
        str(tmp_path / "in.dxf"),
        str(tmp_path / "out.ifc"),
        "",
        0.0,
        False,
        True,
        str(tmp_path / "magicad.ifc"),
    ]
