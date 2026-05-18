"""Plan D Task 15: LayerTable widget showing layer/IFC/Talo2000/system mapping."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")




def test_layer_table_uses_jetbrains_mono_for_layer_column(qtbot):
    from dwg2ifc.gui.layer_table import LayerTable
    from dwg2ifc.profiles.loader import load_default_profile

    table = LayerTable()
    qtbot.addWidget(table)
    table.set_layers(["LT IMU"], load_default_profile())
    assert table.item(0, 0).font().family() == "JetBrains Mono"
    assert table.item(0, 3).font().family() == "JetBrains Mono"
