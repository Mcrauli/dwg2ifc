"""Plan D Task 15: LayerTable widget showing layer/IFC/Talo2000/system mapping."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_layer_table_columns_and_default_profile_rows(qtbot):
    from dxf2ifc.gui.layer_table import LayerTable
    from dxf2ifc.profiles.loader import load_default_profile

    table = LayerTable()
    qtbot.addWidget(table)
    assert [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())] == [
        "Layer",
        "IFC type",
        "Domain",
        "Code",
        "System",
    ]

    table.set_layers(["LT IMU", "KYL-ULKOSEINA", "UNKNOWN-LAYER"], load_default_profile())
    assert table.rowCount() == 3

    rows: dict[str, list[str]] = {}
    for r in range(table.rowCount()):
        rows[table.item(r, 0).text()] = [
            table.item(r, c).text() for c in range(table.columnCount())
        ]

    # LT IMU is a TATE-domain pipe rule after Plan H — code comes from
    # LVI-TUOTEOSA, not Talo2000.
    assert rows["LT IMU"][1] == "IfcPipeSegment"
    assert rows["LT IMU"][2] == "RAVA-LVI"
    assert rows["LT IMU"][3].startswith("T-LVI-")
    assert rows["LT IMU"][4] == "Refrigeration LT"

    assert rows["KYL-ULKOSEINA"][1] == "IfcWall"
    assert rows["KYL-ULKOSEINA"][2] == "Talo2000"
    assert rows["KYL-ULKOSEINA"][3] == "1241"
    assert rows["KYL-ULKOSEINA"][4] == "—"

    assert rows["UNKNOWN-LAYER"] == ["UNKNOWN-LAYER", "—", "—", "—", "—"]


def test_layer_table_uses_jetbrains_mono_for_layer_column(qtbot):
    from dxf2ifc.gui.layer_table import LayerTable
    from dxf2ifc.profiles.loader import load_default_profile

    table = LayerTable()
    qtbot.addWidget(table)
    table.set_layers(["LT IMU"], load_default_profile())
    assert table.item(0, 0).font().family() == "JetBrains Mono"
    assert table.item(0, 3).font().family() == "JetBrains Mono"
