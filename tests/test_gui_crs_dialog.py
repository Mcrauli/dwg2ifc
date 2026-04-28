"""Plan G Task 15: ``CRSDialog`` lets the user pick EPSG + enter
Eastings/Northings/OrthogonalHeight; OK emits a ``CRSConfig`` to the
caller (MainWindow assigns it to the current profile)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_crs_dialog_default_fields_zero(qtbot):
    from dxf2ifc.gui.crs_dialog import CRSDialog

    dialog = CRSDialog(crs=None)
    qtbot.addWidget(dialog)
    values = dialog.current_values()
    assert values["epsg"] == "EPSG:3067"
    assert values["eastings_mm"] == 0.0
    assert values["northings_mm"] == 0.0
    assert values["orthogonal_height_mm"] == 0.0


def test_crs_dialog_seeds_existing_crs(qtbot):
    from dxf2ifc.gui.crs_dialog import CRSDialog
    from dxf2ifc.profiles.schema import CRSConfig

    crs = CRSConfig(
        eastings_mm=25_496_000.0,
        northings_mm=6_672_000.0,
        orthogonal_height_mm=15_000.0,
    )
    dialog = CRSDialog(crs=crs)
    qtbot.addWidget(dialog)
    values = dialog.current_values()
    assert values["eastings_mm"] == 25_496_000.0
    assert values["northings_mm"] == 6_672_000.0
    assert values["orthogonal_height_mm"] == 15_000.0


def test_crs_dialog_ok_emits_crs_config(qtbot):
    from dxf2ifc.gui.crs_dialog import CRSDialog
    from dxf2ifc.profiles.schema import CRSConfig

    dialog = CRSDialog(crs=None)
    qtbot.addWidget(dialog)
    dialog._eastings_edit.setText("25496000")
    dialog._northings_edit.setText("6672000")
    dialog._orth_height_edit.setText("0")

    received: list = []
    dialog.crs_accepted.connect(received.append)
    dialog._on_accept()

    assert len(received) == 1
    assert isinstance(received[0], CRSConfig)
    assert received[0].epsg_code == "EPSG:3067"
    assert received[0].eastings_mm == 25_496_000.0
    assert received[0].name == "ETRS-TM35FIN"
    assert received[0].geodetic_datum == "ETRS89"


def test_main_window_profile_menu_has_set_crs_action(qtbot):
    from dxf2ifc.gui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    assert window._set_crs_action.text() == "Set CRS…"
