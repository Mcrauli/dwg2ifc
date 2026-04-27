"""Plan D Task 19: RuleEditDialog form with pydantic validation."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _populate_valid_line_rule(dialog) -> None:
    dialog.layer_pattern_edit.setText("KYL-ULKOSEINA*")
    dialog.entity_kind_combo.setCurrentText("LINE")
    dialog.ifc_type_combo.setCurrentText("IfcWall")
    dialog.talo2000_code_edit.setText("1241")
    dialog.talo2000_name_edit.setText("Ulkoseinät")


def test_rule_edit_dialog_ok_button_disabled_for_invalid_insert(qtbot):
    from dxf2ifc.gui.rule_dialog import RuleEditDialog

    dialog = RuleEditDialog()
    qtbot.addWidget(dialog)
    dialog.layer_pattern_edit.setText("KYL-OVET*")
    dialog.entity_kind_combo.setCurrentText("INSERT")
    dialog.ifc_type_combo.setCurrentText("IfcDoor")
    dialog.talo2000_code_edit.setText("1243")
    dialog.talo2000_name_edit.setText("Ulko-ovet")
    dialog.block_name_edit.clear()
    dialog._refresh_validation()
    assert not dialog.ok_button.isEnabled()


def test_rule_edit_dialog_ok_button_enabled_for_valid_input(qtbot):
    from dxf2ifc.gui.rule_dialog import RuleEditDialog

    dialog = RuleEditDialog()
    qtbot.addWidget(dialog)
    _populate_valid_line_rule(dialog)
    dialog._refresh_validation()
    assert dialog.ok_button.isEnabled()
    rule = dialog.rule()
    assert rule is not None
    assert rule.layer_pattern == "KYL-ULKOSEINA*"
    assert rule.ifc_type == "IfcWall"
    assert rule.talo2000_code == "1241"


def test_rule_edit_dialog_prefills_existing_rule(qtbot):
    from dxf2ifc.gui.rule_dialog import RuleEditDialog
    from dxf2ifc.profiles.schema import Rule

    rule = Rule(
        layer_pattern="LT IMU",
        entity_kind="LINE",
        ifc_type="IfcPipeSegment",
        predefined_type="REFRIGERATION",
        talo2000_code="2151",
        talo2000_name="Putkiosat",
        system_name="Refrigeration LT",
    )
    dialog = RuleEditDialog(rule=rule)
    qtbot.addWidget(dialog)
    assert dialog.layer_pattern_edit.text() == "LT IMU"
    assert dialog.system_name_edit.text() == "Refrigeration LT"
    assert dialog.predefined_type_edit.text() == "REFRIGERATION"
