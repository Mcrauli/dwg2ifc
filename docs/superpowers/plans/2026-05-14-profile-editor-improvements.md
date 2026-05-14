# Profile Editor Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the GUI profile editor usable — a searchable rule table with a clear scrollbar, a complete IFC-type dropdown, and per-user persistence of the active profile that auto-loads on startup.

**Architecture:** Three independent pieces. (1) A single `SUPPORTED_IFC_TYPES` constant in `builders.py` feeds the rule dialog's dropdown. (2) A new `profiles/store.py` module persists the active profile to a per-user `%APPDATA%` file; the main window auto-loads it. (3) `profile_editor.py` is rewritten to wrap its table model in a `QSortFilterProxyModel` driven by a search box, and its Save button writes to the store instead of opening a file dialog.

**Tech Stack:** Python 3.12, PySide6 (Qt), pydantic v2, pytest + pytest-qt, TOML (`tomllib` / `tomli_w`).

**Spec:** `docs/superpowers/specs/2026-05-14-profile-editor-improvements-design.md`

**Test runner:** `.venv/Scripts/python.exe -m pytest` — use the PowerShell tool or `./.venv/Scripts/python.exe` from bash. GUI tests need `QT_QPA_PLATFORM=offscreen` (test files set this themselves).

---

## Task 1: `SUPPORTED_IFC_TYPES` constant — single source of truth

The rule dialog hard-codes only 11 IFC types; the writer dispatches ~29. Add one canonical tuple in `builders.py` (where the equipment frozensets already live) and a drift test that pins it to the orchestrator's actual dispatch set.

**Files:**
- Modify: `src/dxf2ifc/core/ifc_writer/builders.py` (add constant after `_DISTRIBUTION_ELEMENT_CLASSES`, ~line 1182)
- Test: `tests/test_supported_ifc_types.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_supported_ifc_types.py`:

```python
"""SUPPORTED_IFC_TYPES must stay in sync with the orchestrator dispatch.

The profile editor's IFC-type dropdown is sourced from this tuple. If a
type is offered in the GUI but the orchestrator has no branch for it, a
rule using it would silently produce nothing — so the tuple is pinned
to exactly the set the dispatch loop handles.
"""

from __future__ import annotations


def test_supported_ifc_types_matches_orchestrator_dispatch():
    from dxf2ifc.core.ifc_writer.builders import (
        SUPPORTED_IFC_TYPES,
        _COOLING_EQUIPMENT_CLASSES,
        _DISTRIBUTION_ELEMENT_CLASSES,
    )

    base = {
        "IfcWall",
        "IfcSlab",
        "IfcDoor",
        "IfcWindow",
        "IfcPipeSegment",
        "IfcCableCarrierSegment",
        "IfcFurniture",
        "IfcBuildingElementProxy",
    }
    expected = (
        base
        | set(_COOLING_EQUIPMENT_CLASSES)
        | {"IfcTank", "IfcFlowController"}
        | set(_DISTRIBUTION_ELEMENT_CLASSES)
    )
    assert set(SUPPORTED_IFC_TYPES) == expected


def test_supported_ifc_types_has_no_duplicates():
    from dxf2ifc.core.ifc_writer.builders import SUPPORTED_IFC_TYPES

    assert len(SUPPORTED_IFC_TYPES) == len(set(SUPPORTED_IFC_TYPES))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_supported_ifc_types.py -q`
Expected: FAIL — `ImportError: cannot import name 'SUPPORTED_IFC_TYPES'`.

- [ ] **Step 3: Add the constant**

In `src/dxf2ifc/core/ifc_writer/builders.py`, immediately after the `_DISTRIBUTION_ELEMENT_CLASSES` frozenset closes (after its closing `})`, add:

```python
# Every IFC type the orchestrator dispatch loop knows how to build. The
# profile editor's "IFC type" dropdown is sourced from this tuple so the
# GUI can never offer a type the writer would silently drop. Ordered for
# readability: ARK/structural base types, refrigeration plant, tanks &
# flow control, then distribution elements. Pinned to the dispatch loop
# by tests/test_supported_ifc_types.py.
SUPPORTED_IFC_TYPES: tuple[str, ...] = (
    # Structural / ARK base types
    "IfcWall",
    "IfcSlab",
    "IfcDoor",
    "IfcWindow",
    # TATE/KYL geometry primitives
    "IfcPipeSegment",
    "IfcCableCarrierSegment",
    "IfcFurniture",
    "IfcBuildingElementProxy",
    # Refrigeration plant (_COOLING_EQUIPMENT_CLASSES)
    "IfcEvaporator",
    "IfcCondenser",
    "IfcCompressor",
    "IfcChiller",
    "IfcUnitaryEquipment",
    "IfcCoil",
    # Tanks & flow control
    "IfcTank",
    "IfcFlowController",
    # Distribution elements (_DISTRIBUTION_ELEMENT_CLASSES)
    "IfcSensor",
    "IfcValve",
    "IfcPump",
    "IfcWasteTerminal",
    "IfcInterceptor",
    "IfcElectricDistributionBoard",
    "IfcController",
    "IfcAlarm",
    "IfcSwitchingDevice",
    "IfcCommunicationsAppliance",
    "IfcDuctSegment",
    "IfcDuctFitting",
    "IfcAirTerminal",
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_supported_ifc_types.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/dxf2ifc/core/ifc_writer/builders.py tests/test_supported_ifc_types.py
git commit -m "feat(builders): SUPPORTED_IFC_TYPES — single source for the GUI IFC-type list"
```

---

## Task 2: Grouped IFC-type dropdown in the rule dialog

Replace `rule_dialog.py`'s 11-item `_IFC_TYPES` with the full set, displayed in labelled groups with separators so ~29 types stay scannable.

**Files:**
- Modify: `src/dxf2ifc/gui/rule_dialog.py:11-23` (`_IFC_TYPES` definition) and `:52-53` (combo population)
- Test: `tests/test_gui_rule_dialog.py` (append new tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_gui_rule_dialog.py`:

```python
def test_rule_edit_dialog_offers_full_ifc_type_set(qtbot):
    from dxf2ifc.core.ifc_writer.builders import SUPPORTED_IFC_TYPES
    from dxf2ifc.gui.rule_dialog import RuleEditDialog

    dialog = RuleEditDialog()
    qtbot.addWidget(dialog)
    combo = dialog.ifc_type_combo
    items = {combo.itemText(i) for i in range(combo.count())}
    for ifc_type in SUPPORTED_IFC_TYPES:
        assert ifc_type in items, f"{ifc_type} missing from IFC type dropdown"


def test_ifc_type_groups_cover_supported_types_exactly(qtbot):
    from dxf2ifc.core.ifc_writer.builders import SUPPORTED_IFC_TYPES
    from dxf2ifc.gui.rule_dialog import _IFC_TYPE_GROUPS

    grouped = [t for _label, types in _IFC_TYPE_GROUPS for t in types]
    assert set(grouped) == set(SUPPORTED_IFC_TYPES)
    assert len(grouped) == len(set(grouped)), "a type appears in two groups"


def test_rule_edit_dialog_accepts_a_distribution_type(qtbot):
    """A newly-exposed type (e.g. IfcSensor) must round-trip through the
    dialog — previously it was not selectable at all."""
    from dxf2ifc.gui.rule_dialog import RuleEditDialog

    dialog = RuleEditDialog()
    qtbot.addWidget(dialog)
    dialog.domain_combo.setCurrentText("KYL")
    dialog.layer_pattern_edit.setText("KYL-CO2-ANTURI*")
    dialog.entity_kind_combo.setCurrentText("INSERT")
    dialog.block_name_edit.setText("CO2-anturi")
    dialog.ifc_type_combo.setCurrentText("IfcSensor")
    dialog.lvi_code_combo.setCurrentText("")
    dialog.talotekniikka_code_combo.setCurrentText("T-TATE-02-01-003")
    dialog._refresh_validation()
    assert dialog.ok_button.isEnabled()
    rule = dialog.rule()
    assert rule is not None
    assert rule.ifc_type == "IfcSensor"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_gui_rule_dialog.py -q -k "full_ifc_type_set or ifc_type_groups or distribution_type"`
Expected: FAIL — `_IFC_TYPE_GROUPS` does not exist; `IfcSensor` not in the combo.

- [ ] **Step 3: Replace `_IFC_TYPES` with grouped definition**

In `src/dxf2ifc/gui/rule_dialog.py`, replace the `_IFC_TYPES` block (lines 11-23, the tuple from `_IFC_TYPES = (` through its closing `)`) with:

```python
from dxf2ifc.core.ifc_writer.builders import SUPPORTED_IFC_TYPES

# Display grouping for the IFC type dropdown — labelled groups with
# separators keep the ~29-type list scannable. Every name here must be
# in SUPPORTED_IFC_TYPES (enforced by test_gui_rule_dialog).
_IFC_TYPE_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Jäähdytyslaitteet",
        (
            "IfcEvaporator",
            "IfcCondenser",
            "IfcCompressor",
            "IfcChiller",
            "IfcUnitaryEquipment",
            "IfcCoil",
        ),
    ),
    (
        "Putket & hyllyt",
        (
            "IfcPipeSegment",
            "IfcCableCarrierSegment",
        ),
    ),
    (
        "Säiliöt & virtaus",
        (
            "IfcTank",
            "IfcFlowController",
        ),
    ),
    (
        "Sähkö- & jakelulaitteet",
        (
            "IfcSensor",
            "IfcValve",
            "IfcPump",
            "IfcWasteTerminal",
            "IfcInterceptor",
            "IfcElectricDistributionBoard",
            "IfcController",
            "IfcAlarm",
            "IfcSwitchingDevice",
            "IfcCommunicationsAppliance",
            "IfcDuctSegment",
            "IfcDuctFitting",
            "IfcAirTerminal",
        ),
    ),
    (
        "Rakenne / ARK",
        (
            "IfcWall",
            "IfcSlab",
            "IfcDoor",
            "IfcWindow",
            "IfcBuildingElementProxy",
            "IfcFurniture",
        ),
    ),
)
```

Keep `SUPPORTED_IFC_TYPES` imported even though `_IFC_TYPE_GROUPS` is what populates the combo — the test imports it from `builders`, not from here, so no extra change is needed; but leaving the import documents the contract. (If a linter flags it unused, reference it in a module-level `assert set(t for _l, ts in _IFC_TYPE_GROUPS for t in ts) == set(SUPPORTED_IFC_TYPES)` — a cheap import-time guard.)

Add the import-time guard right after `_IFC_TYPE_GROUPS`:

```python
# Import-time guard: the display groups and the writer's supported set
# must not drift apart.
assert {t for _label, _types in [(l, ts) for l, ts in _IFC_TYPE_GROUPS] for t in _types} == set(
    SUPPORTED_IFC_TYPES
)
```

(Simpler equivalent — use whichever reads cleaner; the test covers it regardless.)

- [ ] **Step 4: Populate the combo from the groups**

In `src/dxf2ifc/gui/rule_dialog.py`, replace lines 52-53:

```python
        self.ifc_type_combo = QtWidgets.QComboBox()
        self.ifc_type_combo.addItems(_IFC_TYPES)
```

with:

```python
        self.ifc_type_combo = QtWidgets.QComboBox()
        for group_index, (_group_label, group_types) in enumerate(_IFC_TYPE_GROUPS):
            if group_index > 0:
                self.ifc_type_combo.insertSeparator(self.ifc_type_combo.count())
            self.ifc_type_combo.addItems(group_types)
```

- [ ] **Step 5: Run the rule-dialog tests**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_gui_rule_dialog.py -q`
Expected: PASS — the 3 new tests plus all pre-existing rule-dialog tests (IfcWall / IfcDoor are still in the list, so the old tests still pass).

- [ ] **Step 6: Commit**

```bash
git add src/dxf2ifc/gui/rule_dialog.py tests/test_gui_rule_dialog.py
git commit -m "feat(gui): complete, grouped IFC-type dropdown in the rule dialog"
```

---

## Task 3: `profiles/store.py` — per-user active-profile persistence

A new module that saves/loads the active profile to a fixed per-user path under `%APPDATA%`. Atomic writes; corrupt files degrade to "no saved profile" rather than crashing.

**Files:**
- Create: `src/dxf2ifc/profiles/store.py`
- Test: `tests/test_profile_store.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_profile_store.py`:

```python
"""Per-user active-profile store (profiles/store.py)."""

from __future__ import annotations

import pytest

from dxf2ifc.profiles.loader import load_default_profile
from dxf2ifc.profiles.store import (
    active_profile_path,
    clear_active_profile,
    load_active_profile,
    save_active_profile,
)


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    """Redirect %APPDATA% so the store writes inside the test's tmp dir."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def test_active_profile_path_lives_under_appdata(appdata):
    assert active_profile_path() == appdata / "Mcrauli" / "dxf2ifc" / "active_profile.toml"


def test_save_then_load_round_trips(appdata):
    profile = load_default_profile()
    assert load_active_profile() is None
    save_active_profile(profile)
    loaded = load_active_profile()
    assert loaded is not None
    assert loaded.name == profile.name
    assert len(loaded.rules) == len(profile.rules)


def test_save_creates_parent_dirs(appdata):
    assert not active_profile_path().parent.exists()
    save_active_profile(load_default_profile())
    assert active_profile_path().is_file()


def test_load_returns_none_when_missing(appdata):
    assert load_active_profile() is None


def test_load_returns_none_for_corrupt_file(appdata):
    path = active_profile_path()
    path.parent.mkdir(parents=True)
    path.write_text("this is not = valid [toml\n", encoding="utf-8")
    assert load_active_profile() is None


def test_clear_removes_saved_profile(appdata):
    save_active_profile(load_default_profile())
    assert active_profile_path().is_file()
    clear_active_profile()
    assert not active_profile_path().is_file()


def test_clear_is_noop_when_nothing_saved(appdata):
    clear_active_profile()  # must not raise


def test_save_leaves_no_temp_files_behind(appdata):
    save_active_profile(load_default_profile())
    leftovers = list(active_profile_path().parent.glob(".active_profile_*"))
    assert leftovers == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_profile_store.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'dxf2ifc.profiles.store'`.

- [ ] **Step 3: Create the module**

Create `src/dxf2ifc/profiles/store.py`:

```python
"""Per-user persistence of the active GUI mapping profile.

The profile editor saves the user's edited profile here instead of to a
file the user has to remember and re-load. The path is per-Windows-user
(under ``%APPDATA%``), writable without admin rights, and created on
demand — it never touches shared/global state, the registry (beyond the
existing QSettings), or the user's AutoCAD profile.

The CLI is unaffected: it still takes an explicit ``--profile`` TOML path
and falls back to the bundled default. This store is GUI-only.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from dxf2ifc.profiles.loader import dump_profile, load_profile
from dxf2ifc.profiles.schema import Profile

_log = logging.getLogger(__name__)

_ORG = "Mcrauli"
_APP = "dxf2ifc"
_FILENAME = "active_profile.toml"


def _app_data_root() -> Path:
    """Per-user writable config root.

    ``%APPDATA%`` on Windows (always set for an interactive user); a
    ``~/.config`` style fallback elsewhere so the test suite and any
    non-Windows dev machine still work.
    """
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata)
    return Path.home() / ".config"


def active_profile_path() -> Path:
    """Fixed per-user path of the saved active profile."""
    return _app_data_root() / _ORG / _APP / _FILENAME


def save_active_profile(profile: Profile) -> None:
    """Persist ``profile`` to :func:`active_profile_path`, atomically.

    Writes to a temp file in the target directory and ``os.replace``s it
    over the destination, so a crash mid-write can never leave a
    half-written profile behind. Raises ``OSError`` on IO failure — the
    caller (the editor dialog) surfaces that to the user.
    """
    target = active_profile_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(target.parent), prefix=".active_profile_", suffix=".tmp"
    )
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        dump_profile(profile, tmp_path)
        os.replace(tmp_path, target)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def load_active_profile() -> Profile | None:
    """Return the saved active profile, or ``None``.

    ``None`` means *use the bundled default*: either nothing has been
    saved yet, or the saved file is unreadable / fails schema validation
    (logged, never raised — a corrupt file must not block startup).
    """
    path = active_profile_path()
    if not path.is_file():
        return None
    try:
        return load_profile(path)
    except Exception:  # noqa: BLE001 — corrupt file must not crash startup
        _log.exception("Saved active profile at %s is unreadable", path)
        return None


def clear_active_profile() -> None:
    """Delete the saved active profile if it exists (no-op otherwise)."""
    active_profile_path().unlink(missing_ok=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_profile_store.py -q`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add src/dxf2ifc/profiles/store.py tests/test_profile_store.py
git commit -m "feat(profiles): per-user active-profile store with atomic writes"
```

---

## Task 4: Restyle the vertical scrollbar

The default scrollbar handle is low-contrast — the user can't tell at a glance whether they're at the top or bottom of the 49-row table. Make the vertical scrollbar wider with a high-contrast amber handle (existing locked accent colour — no new colours).

**Files:**
- Modify: `src/dxf2ifc/gui/style.qss:180-191` (the `QScrollBar` block)
- Test: `tests/test_gui_style.py` (append one test)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_gui_style.py`:

```python
def test_style_qss_gives_vertical_scrollbar_a_visible_handle():
    """The 49-row profile table needs a scrollbar whose handle is wide
    and high-contrast enough to read position at a glance."""
    qss = _load_qss()
    assert "QScrollBar:vertical" in qss
    # widened track + a minimum handle length so the thumb never shrinks
    # to an invisible sliver on a long table
    assert "width: 14px" in qss
    assert "min-height: 36px" in qss
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_gui_style.py -q -k vertical_scrollbar`
Expected: FAIL — `width: 14px` / `min-height: 36px` not present.

- [ ] **Step 3: Replace the `QScrollBar` block**

In `src/dxf2ifc/gui/style.qss`, replace the three `QScrollBar` rules (lines 180-191, from `QScrollBar:vertical, QScrollBar:horizontal {` through the closing `}` of the `:hover` rule) with:

```css
QScrollBar:vertical {
    background-color: rgba(15, 23, 42, 0.55);
    border: none;
    width: 14px;
    margin: 0;
}

QScrollBar:horizontal {
    background-color: rgba(15, 23, 42, 0.4);
    border: none;
    height: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: rgba(245, 158, 11, 0.55);
    border-radius: 5px;
    min-height: 36px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: rgba(245, 158, 11, 0.85);
}

QScrollBar::handle:horizontal {
    background-color: rgba(148, 163, 184, 0.3);
    border-radius: 3px;
    min-width: 24px;
}

QScrollBar::handle:horizontal:hover {
    background-color: rgba(245, 158, 11, 0.4);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    height: 0;
    width: 0;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
}
```

- [ ] **Step 4: Run the style tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_gui_style.py -q`
Expected: PASS — the new test plus all pre-existing style tests (brand colours `#f59e0b` / `#60a5fa` / `#0f172a` / `#020617` and the font families are untouched elsewhere in the file).

- [ ] **Step 5: Commit**

```bash
git add src/dxf2ifc/gui/style.qss tests/test_gui_style.py
git commit -m "style(gui): wider, high-contrast vertical scrollbar handle"
```

---

## Task 5: Searchable profile editor + persistence wiring

The big one — rewrite `profile_editor.py` to its final form (search box + `QSortFilterProxyModel` + row-count label + Save-to-store, no file dialogs), then wire `main_window.py` to the store and remove the now-dead `last_profile_path` from `recent_files.py`. These change one contract together (the editor's `profile_saved` signal and the main window that consumes it), so they ship as one task.

**Files:**
- Modify (full rewrite): `src/dxf2ifc/gui/profile_editor.py`
- Modify: `src/dxf2ifc/gui/main_window.py` (import line ~23, `__init__` ~39-40 and end, `_on_edit_profile` / `_on_reset_profile` / `_load_initial_profile` / `apply_profile_from_path` ~115-147)
- Modify: `src/dxf2ifc/gui/recent_files.py` (remove `last_profile_path`)
- Test (full rewrite): `tests/test_gui_profile_editor.py`
- Test: `tests/test_gui_recent_files.py` (remove 2 obsolete tests)
- Test (create): `tests/test_gui_main_window_profile.py`

- [ ] **Step 1: Rewrite the profile-editor test file**

Replace the entire contents of `tests/test_gui_profile_editor.py` with:

```python
"""ProfileEditorDialog: searchable rule table + Save-to-store.

The editor no longer has file-path Load/Save dialogs — Save persists to
the per-user store (profiles/store.py) and emits the edited Profile.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6 import QtWidgets


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def test_profile_editor_lists_all_default_rules(qtbot):
    from dxf2ifc.gui.profile_editor import ProfileEditorDialog
    from dxf2ifc.profiles.loader import load_default_profile

    profile = load_default_profile()
    dialog = ProfileEditorDialog(profile)
    qtbot.addWidget(dialog)
    table = dialog.findChild(QtWidgets.QTableView)
    assert table is not None
    assert table.model().rowCount() == len(profile.rules)
    assert table.model().columnCount() == 7


def test_search_filters_rows_and_updates_count(qtbot):
    from dxf2ifc.gui.profile_editor import ProfileEditorDialog
    from dxf2ifc.profiles.loader import load_default_profile

    profile = load_default_profile()
    dialog = ProfileEditorDialog(profile)
    qtbot.addWidget(dialog)
    total = dialog._model.rowCount()
    assert dialog.row_count_label.text() == f"{total} riviä"

    dialog.search_edit.setText("zzz-nonexistent-zzz")
    assert dialog._proxy.rowCount() == 0
    assert dialog.row_count_label.text() == f"0 / {total} riviä"

    dialog.search_edit.setText("")
    assert dialog._proxy.rowCount() == total
    assert dialog.row_count_label.text() == f"{total} riviä"


def test_search_matches_ifc_type_column(qtbot):
    from dxf2ifc.gui.profile_editor import ProfileEditorDialog
    from dxf2ifc.profiles.loader import load_default_profile

    profile = load_default_profile()
    dialog = ProfileEditorDialog(profile)
    qtbot.addWidget(dialog)
    dialog.search_edit.setText("evaporator")
    shown = dialog._proxy.rowCount()
    assert 0 < shown < dialog._model.rowCount()
    for proxy_row in range(shown):
        src = dialog._proxy.mapToSource(dialog._proxy.index(proxy_row, 0)).row()
        assert "evaporator" in dialog._model.rules[src].ifc_type.lower()


def test_remove_drops_correct_rule_when_filtered(qtbot):
    """With the table filtered, Remove must delete the source rule that
    backs the selected proxy row — not whatever sits at that source index."""
    from dxf2ifc.gui.profile_editor import ProfileEditorDialog
    from dxf2ifc.profiles.loader import load_default_profile

    profile = load_default_profile()
    dialog = ProfileEditorDialog(profile)
    qtbot.addWidget(dialog)
    dialog.search_edit.setText("evaporator")
    first_src = dialog._proxy.mapToSource(dialog._proxy.index(0, 0)).row()
    target_pattern = dialog._model.rules[first_src].layer_pattern
    initial = dialog._model.rowCount()

    dialog.table.selectRow(0)
    dialog.remove_button.click()

    assert dialog._model.rowCount() == initial - 1
    assert target_pattern not in [r.layer_pattern for r in dialog._model.rules]


def test_save_persists_to_store_and_emits_profile(qtbot, appdata):
    from dxf2ifc.gui.profile_editor import ProfileEditorDialog
    from dxf2ifc.profiles.loader import load_default_profile
    from dxf2ifc.profiles.store import active_profile_path, load_active_profile

    profile = load_default_profile()
    dialog = ProfileEditorDialog(profile)
    qtbot.addWidget(dialog)
    dialog.table.selectRow(0)
    dialog.remove_button.click()  # make one edit

    received = []
    dialog.profile_saved.connect(received.append)
    dialog.save_button.click()

    assert active_profile_path().is_file()
    assert len(received) == 1
    assert len(received[0].rules) == len(profile.rules) - 1
    saved = load_active_profile()
    assert saved is not None
    assert len(saved.rules) == len(profile.rules) - 1


def test_save_failure_shows_error_and_keeps_dialog_open(qtbot, appdata):
    from unittest.mock import patch

    from dxf2ifc.gui.profile_editor import ProfileEditorDialog
    from dxf2ifc.profiles.loader import load_default_profile

    dialog = ProfileEditorDialog(load_default_profile())
    qtbot.addWidget(dialog)
    received = []
    dialog.profile_saved.connect(received.append)

    with (
        patch(
            "dxf2ifc.gui.profile_editor.save_active_profile",
            side_effect=OSError("disk full"),
        ),
        patch(
            "dxf2ifc.gui.profile_editor.QtWidgets.QMessageBox.critical"
        ) as msgbox,
    ):
        dialog.save_button.click()

    assert msgbox.called
    assert received == []
    assert dialog.result() != QtWidgets.QDialog.DialogCode.Accepted


def test_close_button_rejects_without_saving(qtbot, appdata):
    from dxf2ifc.gui.profile_editor import ProfileEditorDialog
    from dxf2ifc.profiles.loader import load_default_profile
    from dxf2ifc.profiles.store import active_profile_path

    dialog = ProfileEditorDialog(load_default_profile())
    qtbot.addWidget(dialog)
    dialog.table.selectRow(0)
    dialog.remove_button.click()
    dialog.close_button.click()

    assert dialog.result() == QtWidgets.QDialog.DialogCode.Rejected
    assert not active_profile_path().is_file()
```

- [ ] **Step 2: Run the editor tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_gui_profile_editor.py -q`
Expected: FAIL — `dialog.search_edit` / `dialog._proxy` / `dialog.close_button` don't exist; `save_active_profile` not importable from `profile_editor`.

- [ ] **Step 3: Rewrite `profile_editor.py`**

Replace the entire contents of `src/dxf2ifc/gui/profile_editor.py` with:

```python
"""Dialog for inspecting and tweaking the active mapping profile.

The edited profile is persisted to the per-user store (profiles.store)
via the Save button — there is no file-path picker. A search box backed
by a QSortFilterProxyModel makes the ~49-rule table navigable; Add / Edit
/ Remove map the selected proxy row back to the source model so they hit
the right rule even while the table is filtered.
"""

from __future__ import annotations

import logging
from copy import deepcopy

from PySide6 import QtCore, QtGui, QtWidgets

from dxf2ifc.profiles.schema import Profile, Rule
from dxf2ifc.profiles.store import save_active_profile

_log = logging.getLogger(__name__)

_HEADERS = (
    "Layer pattern",
    "IFC type",
    "Predefined",
    "Domain",
    "Code",
    "Name",
    "System",
)


def _row_for(rule: Rule) -> tuple[str, str, str, str, str, str, str]:
    if rule.domain == "ARK":
        code = rule.talo2000_code or ""
        name = rule.talo2000_name or ""
    else:
        code = rule.lvi_code or rule.talotekniikka_code or ""
        name = ""
    return (
        rule.layer_pattern,
        rule.ifc_type,
        rule.predefined_type or "",
        rule.domain,
        code,
        name,
        rule.system_name or "",
    )


class _RuleTableModel(QtCore.QAbstractTableModel):
    def __init__(self, rules: list[Rule], parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._rules = list(rules)

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self._rules)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(_HEADERS)

    def data(
        self,
        index: QtCore.QModelIndex,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if not index.isValid() or role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None
        rule = self._rules[index.row()]
        return _row_for(rule)[index.column()]

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == QtCore.Qt.Orientation.Horizontal:
            return _HEADERS[section]
        return section + 1

    def remove_row(self, row: int) -> None:
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        del self._rules[row]
        self.endRemoveRows()

    def append_rule(self, rule: Rule) -> None:
        row = len(self._rules)
        self.beginInsertRows(QtCore.QModelIndex(), row, row)
        self._rules.append(rule)
        self.endInsertRows()

    def replace_rule(self, row: int, rule: Rule) -> None:
        self._rules[row] = rule
        top_left = self.index(row, 0)
        bottom_right = self.index(row, len(_HEADERS) - 1)
        self.dataChanged.emit(top_left, bottom_right)

    @property
    def rules(self) -> list[Rule]:
        return list(self._rules)


class ProfileEditorDialog(QtWidgets.QDialog):
    # Emitted after a successful Save-to-store, carrying the edited
    # Profile object so the main window can adopt it without re-reading
    # anything from disk.
    profile_saved = QtCore.Signal(object)

    def __init__(
        self,
        profile: Profile,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Profile editor")
        self.resize(820, 520)
        self._profile = deepcopy(profile)
        self._model = _RuleTableModel(self._profile.rules, self)
        self._proxy = QtCore.QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(
            QtCore.Qt.CaseSensitivity.CaseInsensitive
        )
        self._proxy.setFilterKeyColumn(-1)  # match against every column

        layout = QtWidgets.QVBoxLayout(self)

        # --- search row -------------------------------------------------
        search_row = QtWidgets.QHBoxLayout()
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText(
            "Hae sääntöjä (layer, IFC-tyyppi, domain, koodi…)"
        )
        self.search_edit.setClearButtonEnabled(True)
        self.row_count_label = QtWidgets.QLabel()
        self.row_count_label.setProperty("role", "caption")
        search_row.addWidget(self.search_edit, stretch=1)
        search_row.addWidget(self.row_count_label)
        layout.addLayout(search_row)

        # --- table ------------------------------------------------------
        self.table = QtWidgets.QTableView()
        self.table.setModel(self._proxy)
        self.table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.table.setVerticalScrollMode(
            QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        layout.addWidget(self.table)

        # --- toolbar ----------------------------------------------------
        toolbar = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton("Add")
        self.add_button.setProperty("secondary", "true")
        self.edit_button = QtWidgets.QPushButton("Edit…")
        self.edit_button.setProperty("secondary", "true")
        self.remove_button = QtWidgets.QPushButton("Remove")
        self.remove_button.setProperty("secondary", "true")
        self.close_button = QtWidgets.QPushButton("Sulje")
        self.close_button.setProperty("secondary", "true")
        self.save_button = QtWidgets.QPushButton("Tallenna")
        self.save_button.setProperty("primary", "true")
        for button in (self.add_button, self.edit_button, self.remove_button):
            toolbar.addWidget(button)
        toolbar.addStretch(1)
        toolbar.addWidget(self.close_button)
        toolbar.addWidget(self.save_button)
        layout.addLayout(toolbar)

        self.add_button.clicked.connect(self._on_add)
        self.edit_button.clicked.connect(self._on_edit)
        self.remove_button.clicked.connect(self._on_remove)
        self.close_button.clicked.connect(self.reject)
        self.save_button.clicked.connect(self._on_save)
        self.search_edit.textChanged.connect(self._on_search_changed)
        self._model.rowsInserted.connect(self._update_row_count)
        self._model.rowsRemoved.connect(self._update_row_count)
        self._update_row_count()

    def current_rules(self) -> list[Rule]:
        return self._model.rules

    def _on_search_changed(self, text: str) -> None:
        self._proxy.setFilterFixedString(text)
        self._update_row_count()

    def _update_row_count(self) -> None:
        total = self._model.rowCount()
        shown = self._proxy.rowCount()
        if shown == total:
            self.row_count_label.setText(f"{total} riviä")
        else:
            self.row_count_label.setText(f"{shown} / {total} riviä")

    def _selected_source_row(self) -> int | None:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        return self._proxy.mapToSource(indexes[0]).row()

    def _on_add(self) -> None:
        from dxf2ifc.gui.rule_dialog import RuleEditDialog

        dialog = RuleEditDialog(parent=self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            rule = dialog.rule()
            if rule is not None:
                self._model.append_rule(rule)

    def _on_edit(self) -> None:
        row = self._selected_source_row()
        if row is None:
            return
        from dxf2ifc.gui.rule_dialog import RuleEditDialog

        dialog = RuleEditDialog(rule=self._model.rules[row], parent=self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            rule = dialog.rule()
            if rule is not None:
                self._model.replace_rule(row, rule)

    def _on_remove(self) -> None:
        row = self._selected_source_row()
        if row is None:
            return
        self._model.remove_row(row)

    def _on_save(self) -> None:
        updated = self._profile.model_copy(update={"rules": self._model.rules})
        try:
            save_active_profile(updated)
        except OSError as exc:  # disk full, permission, …
            _log.exception("Failed to save the active profile")
            QtWidgets.QMessageBox.critical(
                self,
                "Profiilin tallennus epäonnistui",
                f"Profiilia ei voitu tallentaa:\n\n{type(exc).__name__}: {exc}",
            )
            return
        self._profile = updated
        self.profile_saved.emit(updated)
        self.accept()


# QtGui is imported for downstream consumers expecting it from this module.
__all__ = ["ProfileEditorDialog"]
_ = QtGui
```

- [ ] **Step 4: Run the editor tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_gui_profile_editor.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Wire `main_window.py` to the store**

In `src/dxf2ifc/gui/main_window.py`:

(a) Replace the loader import line (~line 23):

```python
from dxf2ifc.profiles.loader import load_default_profile, load_profile
```

with:

```python
from dxf2ifc.profiles.loader import load_default_profile
from dxf2ifc.profiles.store import (
    active_profile_path,
    clear_active_profile,
    load_active_profile,
)
```

(b) In `__init__`, immediately before the line `self._profile = self._load_initial_profile()` (~line 40), add:

```python
        self._startup_profile_warning: str | None = None
```

(c) At the very end of `__init__`, after `self.set_status("Ready")`, add:

```python
        if self._startup_profile_warning:
            self.set_status(self._startup_profile_warning, level="error")
```

(d) Replace `_on_edit_profile` (~lines 115-120) with:

```python
    def _on_edit_profile(self) -> None:
        from dxf2ifc.gui.profile_editor import ProfileEditorDialog

        dialog = ProfileEditorDialog(self._profile, parent=self)
        dialog.profile_saved.connect(self._on_profile_saved)
        dialog.exec()

    def _on_profile_saved(self, profile: object) -> None:
        """ProfileEditorDialog persisted the edited profile to the
        per-user store and handed us the in-memory copy — adopt it and
        refresh the layer preview."""
        self._profile = profile
        self._refresh_layer_table()
        self.set_status("Profiili tallennettu", level="success")
```

(e) Replace `_on_reset_profile` (~lines 123-130) with:

```python
    def _on_reset_profile(self) -> None:
        """Delete the saved active profile and reload the bundled
        default, so the next launch starts clean too."""
        clear_active_profile()
        self._profile = load_default_profile()
        self._refresh_layer_table()
        self.set_status("Profile reset to bundled default", level="success")
```

(f) Replace `_load_initial_profile` (~lines 132-141) with:

```python
    def _load_initial_profile(self):
        """Load the user's saved active profile, or the bundled default.

        The profile editor's Save button persists to a per-user file
        (see ``profiles.store``); we auto-load it here so edits stick
        across launches with no manual re-loading. A saved file that is
        present but unreadable falls back to the bundled default and
        stashes a warning, surfaced once the status bar exists (see the
        end of ``__init__``)."""
        stored = load_active_profile()
        if stored is not None:
            return stored
        if active_profile_path().is_file():
            self._startup_profile_warning = (
                "Tallennettu profiili oli viallinen — "
                "palautettiin oletusprofiili"
            )
        return load_default_profile()
```

(g) Delete the `apply_profile_from_path` method entirely (~lines 143-147):

```python
    def apply_profile_from_path(self, path: str) -> None:
        self._profile = load_profile(path)
        self._recent_files.last_profile_path = path
        self._refresh_layer_table()
        self.set_status(f"Profile loaded: {path}", level="success")
```

- [ ] **Step 6: Remove `last_profile_path` from `recent_files.py`**

In `src/dxf2ifc/gui/recent_files.py`:

(a) Delete the line `_LAST_PROFILE_KEY = "last_profile_path"` (line 8).

(b) Delete the entire `last_profile_path` property and setter (lines 32-43):

```python
    @property
    def last_profile_path(self) -> str | None:
        raw = self._settings.value(_LAST_PROFILE_KEY, None)
        return str(raw) if raw else None

    @last_profile_path.setter
    def last_profile_path(self, path: str | None) -> None:
        if path is None:
            self._settings.remove(_LAST_PROFILE_KEY)
        else:
            self._settings.setValue(_LAST_PROFILE_KEY, path)
        self._settings.sync()
```

The class keeps `list` / `add` / `clear` for the DXF MRU list.

- [ ] **Step 7: Remove the obsolete recent-files tests**

In `tests/test_gui_recent_files.py`, delete the two tests that exercise `last_profile_path` (around lines 45-58):
`test_recent_files_last_profile_path_round_trips` and
`test_recent_files_last_profile_path_clears_on_none`.

- [ ] **Step 8: Write the main-window profile tests**

Create `tests/test_gui_main_window_profile.py`:

```python
"""MainWindow startup-profile behaviour: auto-load from the store, with
a bundled-default fallback when nothing is saved or the file is corrupt."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def test_main_window_loads_saved_profile_on_startup(qtbot, appdata):
    from dxf2ifc.gui.main_window import MainWindow
    from dxf2ifc.profiles.schema import Profile, Rule
    from dxf2ifc.profiles.store import save_active_profile

    custom = Profile(
        name="custom-test-profile",
        ifc_schema="IFC4",
        rules=[
            Rule(
                layer_pattern="X",
                ifc_type="IfcWall",
                predefined_type="STANDARD",
                domain="ARK",
                talo2000_code="1241",
                talo2000_name="Ulkoseinät",
            )
        ],
    )
    save_active_profile(custom)

    window = MainWindow()
    qtbot.addWidget(window)
    assert window._profile.name == "custom-test-profile"


def test_main_window_falls_back_to_default_when_nothing_saved(qtbot, appdata):
    from dxf2ifc.gui.main_window import MainWindow
    from dxf2ifc.profiles.loader import load_default_profile

    window = MainWindow()
    qtbot.addWidget(window)
    assert window._profile.name == load_default_profile().name


def test_main_window_warns_on_corrupt_saved_profile(qtbot, appdata):
    from dxf2ifc.gui.main_window import MainWindow
    from dxf2ifc.profiles.loader import load_default_profile
    from dxf2ifc.profiles.store import active_profile_path

    path = active_profile_path()
    path.parent.mkdir(parents=True)
    path.write_text("not = valid [toml\n", encoding="utf-8")

    window = MainWindow()
    qtbot.addWidget(window)
    # fell back to the bundled default …
    assert window._profile.name == load_default_profile().name
    # … and surfaced a warning in the status bar
    assert "viallinen" in window.statusBar().currentMessage().lower()
```

- [ ] **Step 9: Run the full GUI + profile test set to verify everything passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_gui_profile_editor.py tests/test_gui_recent_files.py tests/test_gui_main_window_profile.py tests/test_gui_smoke.py tests/test_gui_integration.py -q`
Expected: PASS — editor tests, the trimmed recent-files tests, the 3 new main-window tests, smoke + integration all green.

- [ ] **Step 10: Run the whole suite to catch regressions**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: all green except the 2 known pre-existing unrelated failures (`test_convert_dxf_links_positio_to_evaporator`, `test_hoyrystin_roundtrip_produces_ifcevaporator_with_talo2000_2510`). If anything else fails, stop and investigate before committing.

- [ ] **Step 11: Commit**

```bash
git add src/dxf2ifc/gui/profile_editor.py src/dxf2ifc/gui/main_window.py src/dxf2ifc/gui/recent_files.py tests/test_gui_profile_editor.py tests/test_gui_recent_files.py tests/test_gui_main_window_profile.py
git commit -m "feat(gui): searchable profile editor, persisted to a per-user store"
```

---

## Task 6: Docs + version bump (alpha34)

Bump the version and bring the user-facing docs in line with the new profile-editor workflow.

**Files:**
- Modify: `src/dxf2ifc/_version.py`, `pyproject.toml`, `build/version_info.py`, `README.md`, `CHANGELOG.md`, `PROGRESS.md`, `CLAUDE.md`

- [ ] **Step 1: Bump the version to `0.2.0a34`**

- `src/dxf2ifc/_version.py`: `__version__ = "0.2.0a32"` → `__version__ = "0.2.0a34"` (current value is whatever the latest release left — replace with `0.2.0a34`).
- `pyproject.toml`: `version = "..."` → `version = "0.2.0a34"`.
- `build/version_info.py`: both `StringStruct("FileVersion", "...")` and `StringStruct("ProductVersion", "...")` → `"0.2.0a34"`.
- `README.md`: the `Nykyinen versio: **v0.2.0-alphaNN**` line → `**v0.2.0-alpha34**`.

- [ ] **Step 2: Add the CHANGELOG entry**

In `CHANGELOG.md`, directly under the `## Unreleased` line, insert:

```markdown
## v0.2.0-alpha34 — 2026-05-14 (profiilieditori: haku, täysi IFC-lista, tallennus sovellukseen)

**Profiilieditori käyttökelpoisemmaksi** — kolme käyttäjäpalautteen
kipupistettä korjattu:

- **Hakukenttä + selkeä scrollipalkki**: sääntötaulukon yläpuolella
  hakukenttä joka suodattaa rivit elävästi (layer pattern / IFC-tyyppi /
  domain / koodi). Vieressä "N / 49 riviä" -laskuri. Pystyscrollipalkki
  leveämpi ja korkeakontrastinen amber-vetimellä — näkee yhdellä
  silmäyksellä missä kohtaa listaa ollaan. Add/Edit/Remove osuvat oikeaan
  sääntöön myös suodatettuna.
- **Täysi IFC-tyyppivalikko**: pudotusvalikossa oli vain 11 tyyppiä,
  vaikka writer tukee ~29:ää. Nyt kaikki — jäähdytyslaitteet, säiliöt,
  sähkö- ja jakelulaitteet — ryhmiteltynä erottimin. Lista tulee yhdestä
  `SUPPORTED_IFC_TYPES`-vakiosta jota testi pitää synkassa orchestratorin
  kanssa.
- **Tallennus sovelluksen muistiin**: "Tallenna" kirjoittaa profiilin
  per-käyttäjä-tiedostoon (`%APPDATA%\Mcrauli\dxf2ifc\active_profile.toml`)
  ja se latautuu automaattisesti käynnistyessä — ei enää TOML-tiedoston
  etsimistä ja lataamista joka kerta. Atominen kirjoitus; vioittunut
  tiedosto putoaa siististi oletusprofiiliin. "Reset to bundled default"
  poistaa tallennetun profiilin. Editorin Load/Save-tiedostodialogit
  poistettu. CLI:n `--profile` toimii ennallaan.
```

- [ ] **Step 3: Update `PROGRESS.md`**

Update the `## Current state — v0.2.0-alphaNN` heading and "Tuorein julkaistu" line to `v0.2.0-alpha34`, the package filenames to `0.2.0a34`, and the "Alpha8–NN" range. Add a bullet at the top of the alpha summary list:

```markdown
- **alpha34** (2026-05-14): **Profiilieditori käyttökelpoisemmaksi** —
  hakukenttä + rivilaskuri + selkeä scrollipalkki sääntötaulukkoon,
  täysi IFC-tyyppivalikko (`SUPPORTED_IFC_TYPES`, 11 → ~29 tyyppiä,
  ryhmitelty), ja "Tallenna" persistoi profiilin per-käyttäjä-tiedostoon
  joka autolatautuu käynnistyessä. Editorin TOML-tiedostodialogit pois.
```

In `PROGRESS.md`'s "Open todos" section, remove or update the line
`- [ ] **GUI Profile Editor** ei näytä FI_*-kenttiä (TOML-edit toimii käsin).`
only if it is now inaccurate — leave it if FI_* fields are still not shown
(this plan does not add them). Leave it as-is.

- [ ] **Step 4: Update `CLAUDE.md`**

In `CLAUDE.md`'s "Tärkeät tiedostot" table, add a row (after the
`profiles/default_kylmalaite.toml` row):

```markdown
| `src/dxf2ifc/profiles/store.py` | Aktiivisen profiilin per-käyttäjä-persistointi (GUI:n "Tallenna") |
```

In the "Komennot" / GUI section or "Working rules", no change is needed —
but if there is a sentence describing profile loading as file-based,
update it to: "GUI:n profiilieditori tallentaa profiilin sovelluksen
omaan per-käyttäjä-muistiin (`%APPDATA%\Mcrauli\dxf2ifc\`), autolataa sen
käynnistyessä; CLI käyttää yhä `--profile`-TOML-polkua."

- [ ] **Step 5: Verify the version is consistent and the suite is green**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: green except the 2 known pre-existing unrelated failures.

Run: `./.venv/Scripts/python.exe -c "from dxf2ifc._version import __version__; print(__version__)"`
Expected: `0.2.0a34`

- [ ] **Step 6: Commit**

```bash
git add src/dxf2ifc/_version.py pyproject.toml build/version_info.py README.md CHANGELOG.md PROGRESS.md CLAUDE.md
git commit -m "docs: alpha34 — profile editor improvements (changelog, progress, version)"
```

---

## Release (after all tasks complete)

Not a task — the release is driven by pushing the tag, per the project's
established flow (see `project_dxf2ifc.md` memory / PROGRESS release notes):

```bash
git push origin master
git tag v0.2.0-alpha34
git push origin v0.2.0-alpha34
```

`release.yml` builds the exe + installer and publishes the pre-release.
Then notify the user that the GUI self-update banner will offer alpha34.

---

## Self-Review

**1. Spec coverage:**
- Spec Osa 1 (navigation: search box, row-count label, styled scrollbar, proxy selection mapping) → Task 4 (scrollbar) + Task 5 (search box, proxy, row count, mapToSource). ✓
- Spec Osa 2 (`SUPPORTED_IFC_TYPES` constant, grouped dropdown, drift test) → Task 1 + Task 2. ✓
- Spec Osa 3 (`profiles/store.py`, per-user `%APPDATA%` path, atomic write, editor Save→store + Tallenna/Sulje, main_window auto-load + corrupt fallback + reset clears store, recent_files cleanup, CLI untouched) → Task 3 + Task 5. ✓
- Spec error handling (corrupt profile fallback + status, atomic write, save IO error surfaced, drift test) → Task 3 (`load_active_profile` returns None on corrupt; atomic write), Task 5 (`_load_initial_profile` warning; `_on_save` OSError → QMessageBox), Task 1 (drift test). ✓
- Spec testing section → covered across Task 1/2/3/5 test steps. ✓
- Spec "muutettavat tiedostot" table → every file appears in a task. ✓

**2. Placeholder scan:** No "TBD"/"TODO"/"handle edge cases" — every code step has complete code. Task 6 Step 1 says "current value is whatever the latest release left" but gives the exact target value `0.2.0a34`, which is unambiguous. ✓

**3. Type consistency:**
- `profile_saved` signal: defined `QtCore.Signal(object)` in Task 5 Step 3; consumed by `_on_profile_saved(self, profile: object)` in Task 5 Step 5(d). ✓
- `save_active_profile` / `load_active_profile` / `active_profile_path` / `clear_active_profile`: defined in Task 3 Step 3, imported in Task 5 Step 3 (`save_active_profile`) and Step 5(a) (`active_profile_path`, `clear_active_profile`, `load_active_profile`). ✓
- `SUPPORTED_IFC_TYPES`: defined Task 1, imported in Task 2 (rule_dialog) and referenced in tests. ✓
- `_IFC_TYPE_GROUPS`: defined Task 2 Step 3, used Task 2 Step 4 and tested Task 2 Step 1. ✓
- Editor attributes used by tests (`search_edit`, `row_count_label`, `_proxy`, `_model`, `table`, `add_button`/`edit_button`/`remove_button`/`close_button`/`save_button`, `current_rules`, `profile_saved`) all defined in Task 5 Step 3. ✓

No issues found.
