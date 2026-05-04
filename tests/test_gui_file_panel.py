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
    # Energy-spec path is the third element; empty when not picked.
    assert sig.args == [
        str(tmp_path / "in.dxf"),
        str(tmp_path / "out.ifc"),
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
    ]
