"""Plan D Task 21: about dialog shows dxf2ifc + version + GitHub URL."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")




def test_show_about_dialog_is_modal_qdialog(qtbot):
    from PySide6 import QtWidgets

    from dxf2ifc.gui.about import show_about

    dialog = show_about(parent=None)
    qtbot.addWidget(dialog)
    assert isinstance(dialog, QtWidgets.QDialog)
    assert dialog.isModal()
