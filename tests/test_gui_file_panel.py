"""Multi-floor file panel: file/label/elevation table + add/remove/edit."""

import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_panel_starts_empty_and_disabled(qtbot):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    assert panel.files_table.rowCount() == 0
    assert not panel.convert_button.isEnabled()


def test_add_file_appends_row_with_defaults(qtbot, tmp_path):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    path = tmp_path / "1krs.dwg"
    path.write_bytes(b"")
    with patch(
        "dxf2ifc.gui.file_panel.QtWidgets.QFileDialog.getOpenFileNames",
        return_value=([str(path)], "AutoCAD-piirustukset (*.dxf *.dwg)"),
    ):
        panel.add_files_button.click()
    assert panel.files_table.rowCount() == 1
    assert panel.files_table.item(0, 0).text() == str(path)
    assert panel.files_table.item(0, 1).text() == "1.krs"
    assert panel.files_table.item(0, 2).text() == "0"


def test_add_multiple_files_auto_increments_label(qtbot, tmp_path):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    p1, p2, p3 = (tmp_path / f"{n}.dwg" for n in ("a", "b", "c"))
    for p in (p1, p2, p3):
        p.write_bytes(b"")
    with patch(
        "dxf2ifc.gui.file_panel.QtWidgets.QFileDialog.getOpenFileNames",
        return_value=([str(p1), str(p2), str(p3)], "*"),
    ):
        panel.add_files_button.click()
    labels = [panel.files_table.item(i, 1).text() for i in range(3)]
    assert labels == ["1.krs", "2.krs", "3.krs"]


def test_remove_button_drops_selected_row(qtbot, tmp_path):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    p1, p2 = (tmp_path / f"{n}.dwg" for n in ("a", "b"))
    for p in (p1, p2):
        p.write_bytes(b"")
    with patch(
        "dxf2ifc.gui.file_panel.QtWidgets.QFileDialog.getOpenFileNames",
        return_value=([str(p1), str(p2)], "*"),
    ):
        panel.add_files_button.click()
    panel.files_table.selectRow(0)
    panel.remove_button.click()
    assert panel.files_table.rowCount() == 1


def test_duplicate_label_disables_convert(qtbot, tmp_path):
    from PySide6 import QtWidgets

    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    panel.output_edit.setText(str(tmp_path / "out.ifc"))
    p1, p2 = (tmp_path / f"{n}.dwg" for n in ("a", "b"))
    for p in (p1, p2):
        p.write_bytes(b"")
    with patch(
        "dxf2ifc.gui.file_panel.QtWidgets.QFileDialog.getOpenFileNames",
        return_value=([str(p1), str(p2)], "*"),
    ):
        panel.add_files_button.click()
    assert panel.convert_button.isEnabled()
    panel.files_table.setItem(1, 1, QtWidgets.QTableWidgetItem("1.krs"))
    assert not panel.convert_button.isEnabled()


def test_convert_button_enables_after_add_and_output(qtbot, tmp_path):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    p1 = tmp_path / "1krs.dwg"
    p1.write_bytes(b"")
    with patch(
        "dxf2ifc.gui.file_panel.QtWidgets.QFileDialog.getOpenFileNames",
        return_value=([str(p1)], "*"),
    ):
        panel.add_files_button.click()
    # Files present, output still empty → still disabled.
    assert not panel.convert_button.isEnabled()
    panel.output_edit.setText(str(tmp_path / "out.ifc"))
    assert panel.convert_button.isEnabled()


def test_convert_requested_emits_file_entries(qtbot, tmp_path):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    panel.output_edit.setText(str(tmp_path / "out.ifc"))
    p1 = tmp_path / "1krs.dwg"
    p1.write_bytes(b"")
    with patch(
        "dxf2ifc.gui.file_panel.QtWidgets.QFileDialog.getOpenFileNames",
        return_value=([str(p1)], "*"),
    ):
        panel.add_files_button.click()

    received: list[dict] = []
    panel.convert_requested.connect(lambda payload: received.append(payload))
    panel.convert_button.click()
    assert len(received) == 1
    payload = received[0]
    assert payload["output_path"] == str(tmp_path / "out.ifc")
    assert payload["energy_specs_path"] == ""
    assert payload["magicad_ifc_path"] == ""
    assert len(payload["files"]) == 1
    fe = payload["files"][0]
    assert fe.path == Path(p1)
    assert fe.floor_label == "1.krs"
    assert fe.elevation_mm == 0.0


def test_convert_requested_emits_energy_and_magicad_paths(qtbot, tmp_path):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    panel.output_edit.setText(str(tmp_path / "out.ifc"))
    panel.energy_edit.setText(str(tmp_path / "energy.xlsx"))
    panel.magicad_ifc_edit.setText(str(tmp_path / "magicad.ifc"))
    p1 = tmp_path / "1krs.dwg"
    p1.write_bytes(b"")
    with patch(
        "dxf2ifc.gui.file_panel.QtWidgets.QFileDialog.getOpenFileNames",
        return_value=([str(p1)], "*"),
    ):
        panel.add_files_button.click()

    received: list[dict] = []
    panel.convert_requested.connect(lambda payload: received.append(payload))
    panel.convert_button.click()
    assert received[0]["energy_specs_path"] == str(tmp_path / "energy.xlsx")
    assert received[0]["magicad_ifc_path"] == str(tmp_path / "magicad.ifc")


def test_table_row_z_is_editable(qtbot, tmp_path):
    from PySide6 import QtWidgets

    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    p1 = tmp_path / "1krs.dwg"
    p1.write_bytes(b"")
    with patch(
        "dxf2ifc.gui.file_panel.QtWidgets.QFileDialog.getOpenFileNames",
        return_value=([str(p1)], "*"),
    ):
        panel.add_files_button.click()
    panel.files_table.setItem(0, 2, QtWidgets.QTableWidgetItem("3500"))
    panel.output_edit.setText(str(tmp_path / "out.ifc"))

    received: list[dict] = []
    panel.convert_requested.connect(lambda payload: received.append(payload))
    panel.convert_button.click()
    assert received[0]["files"][0].elevation_mm == 3500.0


def test_browse_output_fills_line_edit(qtbot, tmp_path):
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


def test_browse_energy_fills_line_edit(qtbot, tmp_path):
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


def test_browse_magicad_ifc_fills_line_edit(qtbot, tmp_path):
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
