"""Plan D Task 13: end-to-end GUI roundtrip with the real convert_dxf."""

import os
from pathlib import Path

import ifcopenshell

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_gui_convert_simple_wall_writes_valid_ifc(qtbot, fixtures_dir: Path, tmp_path: Path):
    from dxf2ifc.gui.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    out = tmp_path / "simple_wall.ifc"
    window.file_panel.input_edit.setText(str(fixtures_dir / "simple_wall.dxf"))
    window.file_panel.output_edit.setText(str(out))

    with qtbot.waitSignal(window.convert_finished, timeout=10000) as sig:
        window.file_panel.convert_button.click()

    assert sig.args == [str(out)]
    assert out.is_file()

    ifc = ifcopenshell.open(str(out))
    assert ifc.schema == "IFC4"
    assert ifc.by_type("IfcWall"), "expected at least one IfcWall in the GUI-generated IFC"
    assert "Done" in window.statusBar().currentMessage()
