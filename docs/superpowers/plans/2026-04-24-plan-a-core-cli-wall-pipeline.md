# Plan A: Core CLI Pipeline — Wall Converter

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the complete DXF → IFC conversion pipeline end-to-end using the simplest viable element — an exterior wall (US). A CLI command `dxf2ifc convert input.dxf output.ifc` reads LINEs on a wall layer, extrudes them to 3D walls, and writes a valid IFC 4 file with correct Talo2000 classification. Plans B/C/D/E/F build on this foundation.

**Architecture:** Layered modules — `types.py` (dataclasses), `profiles/` (TOML schema + loader), `core/dxf_reader.py` (ezdxf), `core/mapper.py` (layer → IFC type), `core/geometry.py` (2D→3D extrude), `core/ifc_writer.py` (ifcopenshell), `cli.py` (argparse). TDD throughout, one pytest per module + integration test.

**Tech Stack:** Python 3.12, `ezdxf`, `ifcopenshell`, `pydantic`, `tomli`, `pytest`, `ruff`, managed with `uv`.

---

## Repository state before this plan

- `C:\Users\LauriRekola\work\dxf2ifc\` exists
- Contains `README.md`, `.gitignore`, and `docs/superpowers/specs/2026-04-24-dxf2ifc-design.md` (the approved design spec)
- Four prior commits on branch `main` (design iteration)
- No Python code, no `src/`, no dependencies installed yet
- Python is **not installed** on the system (per pre-work exploration)

## File structure (created during this plan)

```
dxf2ifc/
├── pyproject.toml                              [Task 2]
├── src/dxf2ifc/
│   ├── __init__.py                             [Task 3]
│   ├── __main__.py                             [Task 26]
│   ├── cli.py                                  [Task 24]
│   ├── core/
│   │   ├── __init__.py                         [Task 3]
│   │   ├── types.py                            [Task 5]
│   │   ├── dxf_reader.py                       [Task 11]
│   │   ├── mapper.py                           [Task 14]
│   │   ├── geometry.py                         [Task 16]
│   │   └── ifc_writer.py                       [Task 18]
│   └── profiles/
│       ├── __init__.py                         [Task 3]
│       ├── schema.py                           [Task 7]
│       ├── loader.py                           [Task 9]
│       └── default_kylmalaite_talo2000.toml    [Task 10]
└── tests/
    ├── __init__.py                             [Task 4]
    ├── conftest.py                             [Task 4]
    ├── test_types.py                           [Task 5]
    ├── test_profile_schema.py                  [Task 7]
    ├── test_profile_loader.py                  [Task 9]
    ├── test_dxf_reader.py                      [Task 12]
    ├── test_mapper.py                          [Task 14]
    ├── test_geometry.py                        [Task 16]
    ├── test_ifc_writer.py                      [Task 19]
    ├── test_cli.py                             [Task 25]
    ├── test_integration.py                     [Task 27]
    └── fixtures/
        └── simple_wall.dxf                     [Task 12]
```

### File responsibilities

- **`types.py`** — plain dataclasses only. No logic. `Point3D`, `LineGeometry`, `EntityRecord`, `MappedEntity`.
- **`profiles/schema.py`** — pydantic models validating the TOML profile. `Profile`, `Rule`.
- **`profiles/loader.py`** — load TOML → `Profile`, with built-in default resolution via `importlib.resources`.
- **`core/dxf_reader.py`** — `read_dxf(path) -> list[EntityRecord]`. Uses `ezdxf` to iterate model space.
- **`core/mapper.py`** — `apply_profile(entities, profile) -> list[MappedEntity]`. Glob-matches layer names against rules.
- **`core/geometry.py`** — `extrude_2d_line(line, height) -> IfcGeometryData`. For MVP only LINE → extruded wall; Plan B adds polyline / 3DSOLID / INSERT.
- **`core/ifc_writer.py`** — `write_ifc(mapped_entities, output_path, schema="IFC4")`. Builds `IfcProject/Site/Building/Storey` + `IfcWall` entities + `IfcClassificationReference` (Talo2000).
- **`cli.py`** — `argparse`-based CLI. `dxf2ifc convert <in.dxf> <out.ifc> [--profile ...]`.

---

## Task 1: Install Python 3.12 and uv

**Files:**
- No project files modified. System-level install.

- [ ] **Step 1: Install Python 3.12 via winget**

Run:
```
winget install --id Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
```
Expected: "Successfully installed". Restart the shell so the new `python` is on PATH.

- [ ] **Step 2: Verify python --version**

Run (in fresh shell):
```
python --version
```
Expected output: `Python 3.12.x` (any 3.12 patch version).

- [ ] **Step 3: Install uv**

Run:
```
winget install --id astral-sh.uv --silent --accept-source-agreements --accept-package-agreements
```
Expected: "Successfully installed". Restart shell.

- [ ] **Step 4: Verify uv --version**

Run:
```
uv --version
```
Expected output: `uv 0.x.y` (any recent version).

- [ ] **Step 5: No commit (environment task)**

---

## Task 2: Initialise pyproject.toml and dependencies

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: Create pyproject.toml**

Create file `pyproject.toml` at the project root with content:

```toml
[project]
name = "dxf2ifc"
version = "0.1.0"
description = "AutoCAD DXF to IFC 4 converter for Finnish refrigeration design (Talo2000 classification)"
readme = "README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
authors = [{ name = "Lauri Rekola" }]
dependencies = [
    "ezdxf>=1.3.0",
    "ifcopenshell>=0.8.0",
    "pydantic>=2.8.0",
    "tomli>=2.0.1 ; python_version<'3.11'",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.5.0",
]

[project.scripts]
dxf2ifc = "dxf2ifc.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/dxf2ifc"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py312"
```

- [ ] **Step 2: Create empty .python-version**

Create file `.python-version` at the project root with content:

```
3.12
```

- [ ] **Step 3: Create a virtual environment and install deps**

Run:
```
uv venv
uv pip install -e ".[dev]"
```
Expected: installs `ezdxf`, `ifcopenshell`, `pydantic`, `pytest`, `ruff` into `.venv/`. No errors.

- [ ] **Step 4: Verify Python imports the third-party libraries**

Run:
```
.venv\Scripts\python -c "import ezdxf; import ifcopenshell; import pydantic; print('ok')"
```
Expected output: `ok`

- [ ] **Step 5: Commit**

```
git add pyproject.toml .python-version
git commit -m "feat: initialise pyproject.toml with Python 3.12 and core dependencies"
```

---

## Task 3: Create package skeleton

**Files:**
- Create: `src/dxf2ifc/__init__.py`
- Create: `src/dxf2ifc/core/__init__.py`
- Create: `src/dxf2ifc/profiles/__init__.py`

- [ ] **Step 1: Create src/dxf2ifc/__init__.py**

Create file with content:

```python
"""dxf2ifc — AutoCAD DXF to IFC 4 converter for Finnish refrigeration design."""

__version__ = "0.1.0"
```

- [ ] **Step 2: Create src/dxf2ifc/core/__init__.py**

Create file with content:

```python
"""Core conversion pipeline (DXF reader, mapper, geometry, IFC writer)."""
```

- [ ] **Step 3: Create src/dxf2ifc/profiles/__init__.py**

Create file with content:

```python
"""Profile schema and loader (layer to IFC type mapping rules)."""
```

- [ ] **Step 4: Verify package imports**

Run:
```
.venv\Scripts\python -c "import dxf2ifc; from dxf2ifc import core, profiles; print(dxf2ifc.__version__)"
```
Expected output: `0.1.0`

- [ ] **Step 5: Commit**

```
git add src/
git commit -m "feat: create package skeleton for dxf2ifc with core/ and profiles/"
```

---

## Task 4: Set up tests package with conftest

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create tests/__init__.py**

Create empty file.

- [ ] **Step 2: Create tests/conftest.py**

Create file with content:

```python
"""Shared pytest fixtures for dxf2ifc tests."""
from pathlib import Path
import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Absolute path to the tests/fixtures directory."""
    return Path(__file__).parent / "fixtures"
```

- [ ] **Step 3: Run pytest to verify collection**

Run:
```
.venv\Scripts\pytest
```
Expected: `collected 0 items` and exit code 0 (no tests yet, but no errors).

- [ ] **Step 4: Commit**

```
git add tests/
git commit -m "test: add tests/ package with fixtures_dir conftest fixture"
```

---

## Task 5: Implement and test core types

**Files:**
- Create: `src/dxf2ifc/core/types.py`
- Create: `tests/test_types.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_types.py`:

```python
"""Unit tests for core.types dataclasses."""
from dxf2ifc.core.types import Point3D, LineGeometry, EntityRecord


def test_point3d_stores_coords():
    p = Point3D(x=1.0, y=2.0, z=3.0)
    assert p.x == 1.0
    assert p.y == 2.0
    assert p.z == 3.0


def test_point3d_equality():
    assert Point3D(1.0, 2.0, 3.0) == Point3D(1.0, 2.0, 3.0)
    assert Point3D(1.0, 2.0, 3.0) != Point3D(1.0, 2.0, 3.1)


def test_line_geometry_from_two_points():
    start = Point3D(0.0, 0.0, 0.0)
    end = Point3D(1000.0, 0.0, 0.0)
    line = LineGeometry(start=start, end=end)
    assert line.start == start
    assert line.end == end


def test_entity_record_holds_layer_type_geometry():
    line = LineGeometry(start=Point3D(0, 0, 0), end=Point3D(1, 0, 0))
    rec = EntityRecord(
        layer="KYL-ULKOSEINA",
        dxf_type="LINE",
        geometry=line,
        attributes={},
        block_name=None,
        xform=None,
    )
    assert rec.layer == "KYL-ULKOSEINA"
    assert rec.dxf_type == "LINE"
    assert rec.geometry is line
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```
.venv\Scripts\pytest tests/test_types.py -v
```
Expected: `ModuleNotFoundError: No module named 'dxf2ifc.core.types'`

- [ ] **Step 3: Implement src/dxf2ifc/core/types.py**

Create file with content:

```python
"""Core dataclasses shared across the conversion pipeline.

No business logic in this module — only plain data containers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Point3D:
    """A point in 3D space. Coordinates are in millimetres (DXF WCS)."""

    x: float
    y: float
    z: float = 0.0


@dataclass(frozen=True)
class LineGeometry:
    """A straight line between two points."""

    start: Point3D
    end: Point3D


@dataclass
class EntityRecord:
    """One DXF entity as read from the source file.

    `geometry` is one of the geometry dataclasses defined in this module
    (currently only LineGeometry; Plan B extends with polyline/solid/block).
    `attributes` carries DXF-specific extras (color, linetype, thickness).
    `block_name` and `xform` are only populated for INSERT entities.
    """

    layer: str
    dxf_type: str
    geometry: Any
    attributes: dict[str, Any] = field(default_factory=dict)
    block_name: str | None = None
    xform: Any | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```
.venv\Scripts\pytest tests/test_types.py -v
```
Expected: `4 passed`

- [ ] **Step 5: Commit**

```
git add src/dxf2ifc/core/types.py tests/test_types.py
git commit -m "feat(core): add Point3D, LineGeometry, EntityRecord dataclasses"
```

---

## Task 6: Add MappedEntity dataclass

**Files:**
- Modify: `src/dxf2ifc/core/types.py`
- Modify: `tests/test_types.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_types.py`:

```python
def test_mapped_entity_extends_entity_record():
    from dxf2ifc.core.types import MappedEntity, LineGeometry

    line = LineGeometry(start=Point3D(0, 0, 0), end=Point3D(1000, 0, 0))
    mapped = MappedEntity(
        layer="KYL-ULKOSEINA",
        dxf_type="LINE",
        geometry=line,
        attributes={},
        block_name=None,
        xform=None,
        ifc_type="IfcWall",
        predefined_type="STANDARD",
        talo2000_code="1241",
        talo2000_name="Ulkoseinät",
        extra_props={"default_height_mm": 3000},
    )
    assert mapped.ifc_type == "IfcWall"
    assert mapped.talo2000_code == "1241"
    assert mapped.extra_props["default_height_mm"] == 3000
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```
.venv\Scripts\pytest tests/test_types.py::test_mapped_entity_extends_entity_record -v
```
Expected: `ImportError: cannot import name 'MappedEntity'`

- [ ] **Step 3: Add MappedEntity to types.py**

Append to `src/dxf2ifc/core/types.py`:

```python
@dataclass
class MappedEntity(EntityRecord):
    """An EntityRecord plus the IFC type and Talo2000 classification
    resolved by the profile mapper."""

    ifc_type: str = ""
    predefined_type: str | None = None
    talo2000_code: str = ""
    talo2000_name: str = ""
    extra_props: dict[str, Any] = field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```
.venv\Scripts\pytest tests/test_types.py -v
```
Expected: `5 passed`

- [ ] **Step 5: Commit**

```
git add src/dxf2ifc/core/types.py tests/test_types.py
git commit -m "feat(core): add MappedEntity dataclass extending EntityRecord"
```

---

## Task 7: Profile and Rule pydantic schemas

**Files:**
- Create: `src/dxf2ifc/profiles/schema.py`
- Create: `tests/test_profile_schema.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_profile_schema.py`:

```python
"""Unit tests for profiles.schema pydantic models."""
import pytest
from pydantic import ValidationError

from dxf2ifc.profiles.schema import Profile, Rule


def test_rule_requires_layer_pattern_and_ifc_type():
    rule = Rule(
        layer_pattern="KYL-ULKOSEINA*",
        ifc_type="IfcWall",
        talo2000_code="1241",
        talo2000_name="Ulkoseinät",
    )
    assert rule.layer_pattern == "KYL-ULKOSEINA*"
    assert rule.ifc_type == "IfcWall"


def test_rule_allows_predefined_type_and_defaults():
    rule = Rule(
        layer_pattern="KYL-ULKOSEINA*",
        ifc_type="IfcWall",
        predefined_type="STANDARD",
        talo2000_code="1241",
        talo2000_name="Ulkoseinät",
        default_height_mm=3000,
        default_thickness_mm=200,
    )
    assert rule.predefined_type == "STANDARD"
    assert rule.default_height_mm == 3000
    assert rule.default_thickness_mm == 200


def test_rule_rejects_missing_required():
    with pytest.raises(ValidationError):
        Rule(ifc_type="IfcWall", talo2000_code="1241")  # no layer_pattern


def test_profile_holds_rules():
    profile = Profile(
        name="test",
        ifc_schema="IFC4",
        rules=[
            Rule(
                layer_pattern="KYL-ULKOSEINA*",
                ifc_type="IfcWall",
                talo2000_code="1241",
                talo2000_name="Ulkoseinät",
            )
        ],
    )
    assert profile.name == "test"
    assert profile.ifc_schema == "IFC4"
    assert len(profile.rules) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```
.venv\Scripts\pytest tests/test_profile_schema.py -v
```
Expected: `ModuleNotFoundError: No module named 'dxf2ifc.profiles.schema'`

- [ ] **Step 3: Implement profiles/schema.py**

Create `src/dxf2ifc/profiles/schema.py`:

```python
"""Pydantic models validating the mapping profile TOML."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Rule(BaseModel):
    """One layer-pattern → IFC-type rule."""

    model_config = ConfigDict(extra="forbid")

    layer_pattern: str = Field(
        ...,
        description="Glob pattern matched against DXF layer name (case-insensitive).",
    )
    ifc_type: str = Field(..., description="IFC entity name, e.g. 'IfcWall'.")
    predefined_type: str | None = Field(
        default=None, description="IFC PredefinedType enumeration value, if applicable."
    )
    talo2000_code: str = Field(..., description="Talo2000 classification code.")
    talo2000_name: str = Field(..., description="Human-readable Talo2000 category name.")

    default_height_mm: float | None = Field(default=None, description="Extrusion height for 2D lines.")
    default_thickness_mm: float | None = Field(
        default=None, description="Default element thickness (wall, slab)."
    )
    block_handling: Literal["geometry_direct", "extrude"] | None = Field(
        default=None, description="How to handle INSERT entities on this layer."
    )
    system_name: str | None = Field(
        default=None, description="Optional IfcSystem grouping name."
    )


class Profile(BaseModel):
    """A complete mapping profile."""

    model_config = ConfigDict(extra="forbid")

    name: str
    ifc_schema: Literal["IFC4"]
    rules: list[Rule]
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```
.venv\Scripts\pytest tests/test_profile_schema.py -v
```
Expected: `4 passed`

- [ ] **Step 5: Commit**

```
git add src/dxf2ifc/profiles/schema.py tests/test_profile_schema.py
git commit -m "feat(profiles): add Profile and Rule pydantic schemas"
```

---

## Task 8: Default profile TOML (minimal MVP — one wall rule)

**Files:**
- Create: `src/dxf2ifc/profiles/default_kylmalaite_talo2000.toml`

- [ ] **Step 1: Create default profile TOML**

Create `src/dxf2ifc/profiles/default_kylmalaite_talo2000.toml`:

```toml
# Default "Kylmälaite Talo2000" profile.
# Plan A ships only the exterior wall rule. Plan B adds all other entity types.
# Talo2000 codes verified against Solibri Talo2000.classification and
# RT 10-10962 Talo 2000 Hankenimikkeistö (see design spec § "YTV 2012 sources reviewed").

[profile]
name = "Kylmälaite Talo2000 v1"
ifc_schema = "IFC4"

[[rules]]
layer_pattern = "KYL-ULKOSEINA*"
ifc_type = "IfcWall"
predefined_type = "STANDARD"
talo2000_code = "1241"
talo2000_name = "Ulkoseinät"
default_height_mm = 3000
default_thickness_mm = 200
```

- [ ] **Step 2: No test yet — loader is tested in Task 9**

- [ ] **Step 3: Commit**

```
git add src/dxf2ifc/profiles/default_kylmalaite_talo2000.toml
git commit -m "feat(profiles): add minimal default profile with exterior wall rule"
```

---

## Task 9: Profile loader

**Files:**
- Create: `src/dxf2ifc/profiles/loader.py`
- Create: `tests/test_profile_loader.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_profile_loader.py`:

```python
"""Unit tests for profiles.loader."""
from pathlib import Path

import pytest

from dxf2ifc.profiles.loader import load_profile, load_default_profile
from dxf2ifc.profiles.schema import Profile


def test_load_default_profile_returns_profile():
    profile = load_default_profile()
    assert isinstance(profile, Profile)
    assert profile.ifc_schema == "IFC4"
    assert len(profile.rules) >= 1


def test_load_default_profile_has_exterior_wall_rule():
    profile = load_default_profile()
    wall_rules = [r for r in profile.rules if r.ifc_type == "IfcWall"]
    assert len(wall_rules) >= 1
    assert wall_rules[0].talo2000_code == "1241"


def test_load_profile_from_file(tmp_path: Path):
    toml_content = """
[profile]
name = "Test"
ifc_schema = "IFC4"

[[rules]]
layer_pattern = "WALL*"
ifc_type = "IfcWall"
talo2000_code = "1241"
talo2000_name = "Ulkoseinät"
"""
    profile_file = tmp_path / "test.toml"
    profile_file.write_text(toml_content, encoding="utf-8")
    profile = load_profile(profile_file)
    assert profile.name == "Test"
    assert len(profile.rules) == 1
    assert profile.rules[0].layer_pattern == "WALL*"


def test_load_profile_rejects_invalid(tmp_path: Path):
    toml_content = """
[profile]
name = "Bad"
ifc_schema = "IFC4"

[[rules]]
# missing layer_pattern
ifc_type = "IfcWall"
talo2000_code = "1241"
talo2000_name = "Ulkoseinät"
"""
    profile_file = tmp_path / "bad.toml"
    profile_file.write_text(toml_content, encoding="utf-8")
    with pytest.raises(Exception):  # pydantic ValidationError
        load_profile(profile_file)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```
.venv\Scripts\pytest tests/test_profile_loader.py -v
```
Expected: `ModuleNotFoundError: No module named 'dxf2ifc.profiles.loader'`

- [ ] **Step 3: Implement profiles/loader.py**

Create `src/dxf2ifc/profiles/loader.py`:

```python
"""Load a mapping profile from a TOML file."""
from __future__ import annotations

import sys
from importlib import resources
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

from dxf2ifc.profiles.schema import Profile

_DEFAULT_RESOURCE = "default_kylmalaite_talo2000.toml"


def load_profile(path: str | Path) -> Profile:
    """Load and validate a profile from a TOML file path."""
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    # TOML [profile] + [[rules]] → flatten to single dict for pydantic
    merged = dict(data.get("profile", {}))
    merged["rules"] = data.get("rules", [])
    return Profile.model_validate(merged)


def load_default_profile() -> Profile:
    """Load the bundled Kylmälaite Talo2000 profile via importlib.resources."""
    package_files = resources.files("dxf2ifc.profiles")
    toml_text = package_files.joinpath(_DEFAULT_RESOURCE).read_text(encoding="utf-8")
    data = tomllib.loads(toml_text)
    merged = dict(data.get("profile", {}))
    merged["rules"] = data.get("rules", [])
    return Profile.model_validate(merged)
```

- [ ] **Step 4: Update package to expose default TOML as a data file**

Modify `pyproject.toml` to include the TOML in the built wheel. Add at the end of the existing `[tool.hatch.build.targets.wheel]` block:

```toml
[tool.hatch.build.targets.wheel.force-include]
"src/dxf2ifc/profiles/default_kylmalaite_talo2000.toml" = "dxf2ifc/profiles/default_kylmalaite_talo2000.toml"
```

- [ ] **Step 5: Reinstall package so TOML is picked up**

Run:
```
uv pip install -e ".[dev]"
```
Expected: reinstall completes without errors.

- [ ] **Step 6: Run test to verify it passes**

Run:
```
.venv\Scripts\pytest tests/test_profile_loader.py -v
```
Expected: `4 passed`

- [ ] **Step 7: Commit**

```
git add src/dxf2ifc/profiles/loader.py tests/test_profile_loader.py pyproject.toml
git commit -m "feat(profiles): add load_profile and load_default_profile"
```

---

## Task 10: Create minimal DXF fixture

**Files:**
- Create: `tests/fixtures/simple_wall.dxf`

- [ ] **Step 1: Write a helper script that creates the fixture**

Create `tests/fixtures/_build_simple_wall_dxf.py` (not committed; one-off generator):

```python
"""One-off helper: generate tests/fixtures/simple_wall.dxf using ezdxf.

Run once to create the fixture. The DXF is committed; this script is not.
"""
from pathlib import Path

import ezdxf

doc = ezdxf.new(dxfversion="R2010", setup=True)
msp = doc.modelspace()
doc.layers.add("KYL-ULKOSEINA")
# One 5000 mm wall along +X
msp.add_line(start=(0, 0, 0), end=(5000, 0, 0), dxfattribs={"layer": "KYL-ULKOSEINA"})
out = Path(__file__).parent / "simple_wall.dxf"
doc.saveas(out)
print(f"Wrote {out}")
```

- [ ] **Step 2: Run the helper to produce the DXF**

Run:
```
.venv\Scripts\python tests\fixtures\_build_simple_wall_dxf.py
```
Expected output: `Wrote ...\tests\fixtures\simple_wall.dxf`. File `tests/fixtures/simple_wall.dxf` exists.

- [ ] **Step 3: Delete the helper script (keep only the committed DXF)**

Run:
```
del tests\fixtures\_build_simple_wall_dxf.py
```

- [ ] **Step 4: Verify the DXF is valid**

Run:
```
.venv\Scripts\python -c "import ezdxf; d=ezdxf.readfile('tests/fixtures/simple_wall.dxf'); print(list(d.layers.names()))"
```
Expected output includes `KYL-ULKOSEINA`.

- [ ] **Step 5: Commit**

```
git add tests/fixtures/simple_wall.dxf
git commit -m "test(fixtures): add simple_wall.dxf with one 5000 mm KYL-ULKOSEINA line"
```

---

## Task 11: DXF reader — read LINE entities

**Files:**
- Create: `src/dxf2ifc/core/dxf_reader.py`

- [ ] **Step 1: No new test file yet — tested in Task 12**

- [ ] **Step 2: Implement dxf_reader.py**

Create `src/dxf2ifc/core/dxf_reader.py`:

```python
"""Read a DXF file and produce a list of EntityRecord objects.

Plan A handles only LINE entities. Plan B extends with LWPOLYLINE, 3DSOLID, INSERT.
"""
from __future__ import annotations

from pathlib import Path

import ezdxf

from dxf2ifc.core.types import EntityRecord, LineGeometry, Point3D


def read_dxf(path: str | Path) -> list[EntityRecord]:
    """Parse a DXF and return every supported entity in model space."""
    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()
    records: list[EntityRecord] = []
    for entity in msp:
        if entity.dxftype() == "LINE":
            start = Point3D(*entity.dxf.start)
            end = Point3D(*entity.dxf.end)
            records.append(
                EntityRecord(
                    layer=entity.dxf.layer,
                    dxf_type="LINE",
                    geometry=LineGeometry(start=start, end=end),
                    attributes={},
                )
            )
    return records
```

- [ ] **Step 3: Commit**

```
git add src/dxf2ifc/core/dxf_reader.py
git commit -m "feat(core): add dxf_reader.read_dxf handling LINE entities"
```

---

## Task 12: Tests for DXF reader

**Files:**
- Create: `tests/test_dxf_reader.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_dxf_reader.py`:

```python
"""Unit tests for core.dxf_reader."""
from pathlib import Path

from dxf2ifc.core.dxf_reader import read_dxf
from dxf2ifc.core.types import EntityRecord, LineGeometry, Point3D


def test_read_simple_wall_returns_one_entity(fixtures_dir: Path):
    records = read_dxf(fixtures_dir / "simple_wall.dxf")
    assert len(records) == 1


def test_read_simple_wall_captures_layer(fixtures_dir: Path):
    records = read_dxf(fixtures_dir / "simple_wall.dxf")
    assert records[0].layer == "KYL-ULKOSEINA"


def test_read_simple_wall_is_line(fixtures_dir: Path):
    records = read_dxf(fixtures_dir / "simple_wall.dxf")
    rec = records[0]
    assert rec.dxf_type == "LINE"
    assert isinstance(rec.geometry, LineGeometry)


def test_read_simple_wall_line_endpoints(fixtures_dir: Path):
    records = read_dxf(fixtures_dir / "simple_wall.dxf")
    line = records[0].geometry
    assert line.start == Point3D(0.0, 0.0, 0.0)
    assert line.end == Point3D(5000.0, 0.0, 0.0)
```

- [ ] **Step 2: Run test to verify it passes**

Run:
```
.venv\Scripts\pytest tests/test_dxf_reader.py -v
```
Expected: `4 passed`

- [ ] **Step 3: Commit**

```
git add tests/test_dxf_reader.py
git commit -m "test(core): verify dxf_reader reads LINE entity and layer from fixture"
```

---

## Task 13: Layer glob matching helper

**Files:**
- Create: `src/dxf2ifc/core/mapper.py` (just the helper; `apply_profile` comes in Task 14)

- [ ] **Step 1: Write a failing test**

Create `tests/test_mapper.py`:

```python
"""Unit tests for core.mapper."""
import pytest

from dxf2ifc.core.mapper import layer_matches


@pytest.mark.parametrize(
    "pattern,layer,expected",
    [
        ("KYL-ULKOSEINA*", "KYL-ULKOSEINA", True),
        ("KYL-ULKOSEINA*", "KYL-ULKOSEINA-200", True),
        ("KYL-ULKOSEINA*", "KYL-VALISEINA", False),
        ("KYL-*", "KYL-LEVYHYLLY", True),
        ("KYL-*", "WALL", False),
        ("LT IMU", "LT IMU", True),
        ("LT IMU", "lt imu", True),  # case-insensitive
    ],
)
def test_layer_matches(pattern: str, layer: str, expected: bool):
    assert layer_matches(pattern, layer) is expected
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```
.venv\Scripts\pytest tests/test_mapper.py -v
```
Expected: `ModuleNotFoundError: No module named 'dxf2ifc.core.mapper'`

- [ ] **Step 3: Implement layer_matches**

Create `src/dxf2ifc/core/mapper.py`:

```python
"""Match DXF entities against profile rules and produce MappedEntity objects."""
from __future__ import annotations

from fnmatch import fnmatch


def layer_matches(pattern: str, layer: str) -> bool:
    """Case-insensitive glob match. '*' and '?' wildcards supported."""
    return fnmatch(layer.casefold(), pattern.casefold())
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```
.venv\Scripts\pytest tests/test_mapper.py -v
```
Expected: `7 passed`

- [ ] **Step 5: Commit**

```
git add src/dxf2ifc/core/mapper.py tests/test_mapper.py
git commit -m "feat(core): add mapper.layer_matches helper"
```

---

## Task 14: apply_profile mapper

**Files:**
- Modify: `src/dxf2ifc/core/mapper.py`
- Modify: `tests/test_mapper.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_mapper.py`:

```python
from dxf2ifc.core.mapper import apply_profile
from dxf2ifc.core.types import EntityRecord, LineGeometry, Point3D
from dxf2ifc.profiles.schema import Profile, Rule


def _simple_profile():
    return Profile(
        name="test",
        ifc_schema="IFC4",
        rules=[
            Rule(
                layer_pattern="KYL-ULKOSEINA*",
                ifc_type="IfcWall",
                predefined_type="STANDARD",
                talo2000_code="1241",
                talo2000_name="Ulkoseinät",
                default_height_mm=3000,
                default_thickness_mm=200,
            ),
        ],
    )


def _sample_line_record(layer: str = "KYL-ULKOSEINA") -> EntityRecord:
    return EntityRecord(
        layer=layer,
        dxf_type="LINE",
        geometry=LineGeometry(start=Point3D(0, 0, 0), end=Point3D(5000, 0, 0)),
    )


def test_apply_profile_returns_mapped_entity_for_matching_rule():
    entities = [_sample_line_record()]
    mapped = apply_profile(entities, _simple_profile())
    assert len(mapped) == 1
    assert mapped[0].ifc_type == "IfcWall"
    assert mapped[0].predefined_type == "STANDARD"
    assert mapped[0].talo2000_code == "1241"
    assert mapped[0].extra_props["default_height_mm"] == 3000
    assert mapped[0].extra_props["default_thickness_mm"] == 200


def test_apply_profile_skips_unmatched_layer():
    entities = [_sample_line_record(layer="RANDOM-LAYER")]
    mapped = apply_profile(entities, _simple_profile())
    assert mapped == []


def test_apply_profile_uses_first_matching_rule_by_order():
    profile = Profile(
        name="order",
        ifc_schema="IFC4",
        rules=[
            Rule(
                layer_pattern="KYL-*",
                ifc_type="IfcWall",
                predefined_type="PARTITIONING",
                talo2000_code="1311",
                talo2000_name="Väliseinät",
            ),
            Rule(
                layer_pattern="KYL-ULKOSEINA*",
                ifc_type="IfcWall",
                predefined_type="STANDARD",
                talo2000_code="1241",
                talo2000_name="Ulkoseinät",
            ),
        ],
    )
    mapped = apply_profile([_sample_line_record()], profile)
    # First match wins → PARTITIONING (because KYL-* matches first)
    assert mapped[0].predefined_type == "PARTITIONING"
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```
.venv\Scripts\pytest tests/test_mapper.py -v
```
Expected: `ImportError: cannot import name 'apply_profile'`

- [ ] **Step 3: Implement apply_profile**

Append to `src/dxf2ifc/core/mapper.py`:

```python
from dxf2ifc.core.types import EntityRecord, MappedEntity
from dxf2ifc.profiles.schema import Profile, Rule


def apply_profile(
    entities: list[EntityRecord], profile: Profile
) -> list[MappedEntity]:
    """Match each entity's layer against profile rules (first match wins)
    and return a list of MappedEntity.

    Entities whose layer matches no rule are skipped silently.
    """
    result: list[MappedEntity] = []
    for entity in entities:
        rule = _first_matching_rule(entity.layer, profile.rules)
        if rule is None:
            continue
        extras: dict[str, object] = {}
        if rule.default_height_mm is not None:
            extras["default_height_mm"] = rule.default_height_mm
        if rule.default_thickness_mm is not None:
            extras["default_thickness_mm"] = rule.default_thickness_mm
        if rule.system_name is not None:
            extras["system_name"] = rule.system_name
        if rule.block_handling is not None:
            extras["block_handling"] = rule.block_handling
        result.append(
            MappedEntity(
                layer=entity.layer,
                dxf_type=entity.dxf_type,
                geometry=entity.geometry,
                attributes=entity.attributes,
                block_name=entity.block_name,
                xform=entity.xform,
                ifc_type=rule.ifc_type,
                predefined_type=rule.predefined_type,
                talo2000_code=rule.talo2000_code,
                talo2000_name=rule.talo2000_name,
                extra_props=extras,
            )
        )
    return result


def _first_matching_rule(layer: str, rules: list[Rule]) -> Rule | None:
    for rule in rules:
        if layer_matches(rule.layer_pattern, layer):
            return rule
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```
.venv\Scripts\pytest tests/test_mapper.py -v
```
Expected: `10 passed`

- [ ] **Step 5: Commit**

```
git add src/dxf2ifc/core/mapper.py tests/test_mapper.py
git commit -m "feat(core): add apply_profile mapping DXF entities to MappedEntity"
```

---

## Task 15: Geometry — extrude a 2D line into a wall profile

**Files:**
- Create: `src/dxf2ifc/core/geometry.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_geometry.py`:

```python
"""Unit tests for core.geometry."""
from dxf2ifc.core.geometry import WallExtrusion, line_to_wall_extrusion
from dxf2ifc.core.types import LineGeometry, Point3D


def test_line_to_wall_extrusion_length():
    line = LineGeometry(start=Point3D(0, 0, 0), end=Point3D(5000, 0, 0))
    w = line_to_wall_extrusion(line, thickness_mm=200, height_mm=3000)
    assert isinstance(w, WallExtrusion)
    assert w.length_mm == 5000.0


def test_line_to_wall_extrusion_dims():
    line = LineGeometry(start=Point3D(0, 0, 0), end=Point3D(5000, 0, 0))
    w = line_to_wall_extrusion(line, thickness_mm=200, height_mm=3000)
    assert w.thickness_mm == 200.0
    assert w.height_mm == 3000.0


def test_line_to_wall_extrusion_angle_zero_for_x_axis_line():
    line = LineGeometry(start=Point3D(0, 0, 0), end=Point3D(5000, 0, 0))
    w = line_to_wall_extrusion(line, thickness_mm=200, height_mm=3000)
    assert w.angle_rad == 0.0


def test_line_to_wall_extrusion_anchor_is_start_point():
    line = LineGeometry(start=Point3D(100, 200, 300), end=Point3D(5100, 200, 300))
    w = line_to_wall_extrusion(line, thickness_mm=200, height_mm=3000)
    assert w.anchor == Point3D(100, 200, 300)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```
.venv\Scripts\pytest tests/test_geometry.py -v
```
Expected: `ModuleNotFoundError: No module named 'dxf2ifc.core.geometry'`

- [ ] **Step 3: Implement geometry.py**

Create `src/dxf2ifc/core/geometry.py`:

```python
"""Convert DXF geometry into IFC geometry parameters.

Plan A: 2D line → WallExtrusion (length, thickness, height, rotation, anchor).
Plan B adds polyline → slab, 3DSOLID pass-through, block placement.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from dxf2ifc.core.types import LineGeometry, Point3D


@dataclass(frozen=True)
class WallExtrusion:
    """Parameters sufficient to create an IfcWall with IfcExtrudedAreaSolid.

    - anchor: start point of the wall centreline (XY of bottom)
    - angle_rad: rotation around Z from world +X to the wall's length axis
    - length_mm / thickness_mm / height_mm: wall dimensions
    """

    anchor: Point3D
    angle_rad: float
    length_mm: float
    thickness_mm: float
    height_mm: float


def line_to_wall_extrusion(
    line: LineGeometry, *, thickness_mm: float, height_mm: float
) -> WallExtrusion:
    """Treat the line as the wall's centreline at the given thickness and height."""
    dx = line.end.x - line.start.x
    dy = line.end.y - line.start.y
    length = math.hypot(dx, dy)
    angle = math.atan2(dy, dx)
    return WallExtrusion(
        anchor=line.start,
        angle_rad=angle,
        length_mm=length,
        thickness_mm=thickness_mm,
        height_mm=height_mm,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```
.venv\Scripts\pytest tests/test_geometry.py -v
```
Expected: `4 passed`

- [ ] **Step 5: Commit**

```
git add src/dxf2ifc/core/geometry.py tests/test_geometry.py
git commit -m "feat(core): add WallExtrusion and line_to_wall_extrusion"
```

---

## Task 16: IFC writer — project hierarchy skeleton

**Files:**
- Create: `src/dxf2ifc/core/ifc_writer.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ifc_writer.py`:

```python
"""Unit tests for core.ifc_writer."""
from pathlib import Path

import ifcopenshell

from dxf2ifc.core.ifc_writer import build_ifc_project_skeleton, write_ifc


def test_build_project_creates_ifc4_file_with_hierarchy(tmp_path: Path):
    ifc = build_ifc_project_skeleton(
        project_name="Test Project", site_name="Site", building_name="Cold Store"
    )
    # Schema
    assert ifc.schema == "IFC4"
    # Required hierarchy
    assert len(ifc.by_type("IfcProject")) == 1
    assert len(ifc.by_type("IfcSite")) == 1
    assert len(ifc.by_type("IfcBuilding")) == 1
    assert len(ifc.by_type("IfcBuildingStorey")) == 1


def test_build_project_uses_millimetres():
    ifc = build_ifc_project_skeleton(project_name="MM Test")
    project = ifc.by_type("IfcProject")[0]
    length_units = [
        u for u in project.UnitsInContext.Units
        if u.is_a("IfcSIUnit") and u.UnitType == "LENGTHUNIT"
    ]
    assert len(length_units) == 1
    assert length_units[0].Prefix == "MILLI"
    assert length_units[0].Name == "METRE"


def test_write_ifc_produces_file(tmp_path: Path):
    ifc = build_ifc_project_skeleton(project_name="Write Test")
    out = tmp_path / "out.ifc"
    write_ifc(ifc, out)
    assert out.exists()
    assert out.stat().st_size > 0
    reloaded = ifcopenshell.open(str(out))
    assert len(reloaded.by_type("IfcProject")) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```
.venv\Scripts\pytest tests/test_ifc_writer.py -v
```
Expected: `ModuleNotFoundError: No module named 'dxf2ifc.core.ifc_writer'`

- [ ] **Step 3: Implement ifc_writer.py skeleton**

Create `src/dxf2ifc/core/ifc_writer.py`:

```python
"""Generate an IFC file from MappedEntity objects.

Plan A covers: IfcProject/Site/Building/Storey hierarchy, IfcUnitAssignment
(millimetres), single IfcWall creation with classification reference.
Plan B extends with slabs, doors, windows, pipes, furniture, etc.
"""
from __future__ import annotations

from pathlib import Path

import ifcopenshell
import ifcopenshell.api


def build_ifc_project_skeleton(
    *,
    project_name: str = "Untitled",
    site_name: str = "Default Site",
    building_name: str = "Default Building",
    storey_name: str = "Ground Floor",
) -> ifcopenshell.file:
    """Create a minimal IFC 4 file with IfcProject → Site → Building → Storey,
    with millimetre length units set via IfcUnitAssignment.
    """
    ifc = ifcopenshell.api.run("project.create_file", version="IFC4")

    project = ifcopenshell.api.run(
        "root.create_entity", ifc, ifc_class="IfcProject", name=project_name
    )

    # Units: millimetre length, radian angle
    ifcopenshell.api.run(
        "unit.assign_unit",
        ifc,
        length={"is_metric": True, "raw": "MILLIMETERS"},
        angle={"is_metric": True, "raw": "RADIANS"},
    )

    context = ifcopenshell.api.run(
        "context.add_context", ifc, context_type="Model"
    )
    ifcopenshell.api.run(
        "context.add_context",
        ifc,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=context,
    )

    site = ifcopenshell.api.run(
        "root.create_entity", ifc, ifc_class="IfcSite", name=site_name
    )
    building = ifcopenshell.api.run(
        "root.create_entity", ifc, ifc_class="IfcBuilding", name=building_name
    )
    storey = ifcopenshell.api.run(
        "root.create_entity", ifc, ifc_class="IfcBuildingStorey", name=storey_name
    )
    ifcopenshell.api.run("aggregate.assign_object", ifc, products=[site], relating_object=project)
    ifcopenshell.api.run("aggregate.assign_object", ifc, products=[building], relating_object=site)
    ifcopenshell.api.run("aggregate.assign_object", ifc, products=[storey], relating_object=building)
    return ifc


def write_ifc(ifc: ifcopenshell.file, output_path: str | Path) -> None:
    """Write the IFC file to disk."""
    ifc.write(str(output_path))
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```
.venv\Scripts\pytest tests/test_ifc_writer.py -v
```
Expected: `3 passed`

- [ ] **Step 5: Commit**

```
git add src/dxf2ifc/core/ifc_writer.py tests/test_ifc_writer.py
git commit -m "feat(core): add IFC 4 project skeleton with millimetre units"
```

---

## Task 17: Add IfcWall creation + Talo2000 classification

**Files:**
- Modify: `src/dxf2ifc/core/ifc_writer.py`
- Modify: `tests/test_ifc_writer.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_ifc_writer.py`:

```python
from dxf2ifc.core.geometry import WallExtrusion, line_to_wall_extrusion
from dxf2ifc.core.ifc_writer import add_wall, add_talo2000_classification
from dxf2ifc.core.types import LineGeometry, MappedEntity, Point3D


def _wall_mapped_entity() -> MappedEntity:
    line = LineGeometry(start=Point3D(0, 0, 0), end=Point3D(5000, 0, 0))
    return MappedEntity(
        layer="KYL-ULKOSEINA",
        dxf_type="LINE",
        geometry=line,
        ifc_type="IfcWall",
        predefined_type="STANDARD",
        talo2000_code="1241",
        talo2000_name="Ulkoseinät",
        extra_props={"default_height_mm": 3000, "default_thickness_mm": 200},
    )


def test_add_wall_creates_ifcwall():
    ifc = build_ifc_project_skeleton(project_name="Wall Test")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    wall = add_wall(ifc, _wall_mapped_entity(), parent_storey=storey)
    assert wall.is_a("IfcWall")
    assert wall.PredefinedType == "STANDARD"
    assert wall.Name == "KYL-ULKOSEINA"


def test_add_wall_placed_under_storey():
    ifc = build_ifc_project_skeleton(project_name="Wall Test")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    wall = add_wall(ifc, _wall_mapped_entity(), parent_storey=storey)
    walls = ifc.by_type("IfcWall")
    assert len(walls) == 1
    rels = [
        r
        for r in ifc.by_type("IfcRelContainedInSpatialStructure")
        if r.RelatingStructure == storey
    ]
    assert any(wall in rel.RelatedElements for rel in rels)


def test_add_talo2000_classification_attaches_reference():
    ifc = build_ifc_project_skeleton(project_name="Class Test")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    wall = add_wall(ifc, _wall_mapped_entity(), parent_storey=storey)
    add_talo2000_classification(ifc, wall, code="1241", name="Ulkoseinät")

    refs = ifc.by_type("IfcClassificationReference")
    assert any(r.Identification == "1241" for r in refs)
    classifications = ifc.by_type("IfcClassification")
    assert any(c.Name == "Talo2000" for c in classifications)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```
.venv\Scripts\pytest tests/test_ifc_writer.py -v
```
Expected: `ImportError: cannot import name 'add_wall'`

- [ ] **Step 3: Implement add_wall and add_talo2000_classification**

Append to `src/dxf2ifc/core/ifc_writer.py`:

```python
import math

from dxf2ifc.core.geometry import line_to_wall_extrusion
from dxf2ifc.core.types import LineGeometry, MappedEntity


def add_wall(ifc, mapped: MappedEntity, *, parent_storey) -> object:
    """Create an IfcWall entity from a MappedEntity whose geometry is a
    LineGeometry. Adds extruded area solid representation and places it under
    parent_storey via IfcRelContainedInSpatialStructure.
    """
    if not isinstance(mapped.geometry, LineGeometry):
        raise TypeError(f"add_wall expects LineGeometry, got {type(mapped.geometry).__name__}")

    height = float(mapped.extra_props.get("default_height_mm", 3000.0))
    thickness = float(mapped.extra_props.get("default_thickness_mm", 200.0))
    ext = line_to_wall_extrusion(mapped.geometry, thickness_mm=thickness, height_mm=height)

    wall = ifcopenshell.api.run(
        "root.create_entity",
        ifc,
        ifc_class="IfcWall",
        name=mapped.layer,
        predefined_type=mapped.predefined_type,
    )

    # Placement: anchor the wall at its line-start, rotated around Z by angle_rad.
    matrix = _z_rotation_matrix(ext.anchor.x, ext.anchor.y, ext.anchor.z, ext.angle_rad)
    ifcopenshell.api.run(
        "geometry.edit_object_placement",
        ifc,
        product=wall,
        matrix=matrix,
    )

    # Representation: rectangular extruded solid, length × thickness × height.
    model_ctx = [
        c for c in ifc.by_type("IfcGeometricRepresentationSubContext")
        if c.ContextIdentifier == "Body"
    ][0]
    rect = ifc.create_entity(
        "IfcRectangleProfileDef",
        ProfileType="AREA",
        ProfileName=None,
        Position=ifc.create_entity(
            "IfcAxis2Placement2D",
            Location=ifc.create_entity("IfcCartesianPoint", Coordinates=(ext.length_mm / 2.0, 0.0)),
        ),
        XDim=ext.length_mm,
        YDim=ext.thickness_mm,
    )
    extruded = ifc.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=rect,
        Position=ifc.create_entity(
            "IfcAxis2Placement3D",
            Location=ifc.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0)),
        ),
        ExtrudedDirection=ifc.create_entity(
            "IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)
        ),
        Depth=ext.height_mm,
    )
    shape = ifc.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=model_ctx,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extruded],
    )
    product_definition = ifc.create_entity(
        "IfcProductDefinitionShape", Representations=[shape]
    )
    wall.Representation = product_definition

    ifcopenshell.api.run(
        "spatial.assign_container",
        ifc,
        products=[wall],
        relating_structure=parent_storey,
    )
    return wall


def _z_rotation_matrix(x: float, y: float, z: float, angle: float) -> list[list[float]]:
    c, s = math.cos(angle), math.sin(angle)
    return [
        [c, -s, 0.0, x],
        [s,  c, 0.0, y],
        [0.0, 0.0, 1.0, z],
        [0.0, 0.0, 0.0, 1.0],
    ]


def add_talo2000_classification(ifc, product, *, code: str, name: str) -> object:
    """Attach a Talo2000 IfcClassificationReference to the given product.

    Creates (once per file) an IfcClassification named 'Talo2000', then
    references it from an IfcClassificationReference tied to the product.
    """
    existing = [c for c in ifc.by_type("IfcClassification") if c.Name == "Talo2000"]
    if existing:
        classification = existing[0]
    else:
        classification = ifc.create_entity(
            "IfcClassification",
            Source="Rakennustieto Oy",
            Edition="Talo 2000",
            Name="Talo2000",
        )

    reference = ifc.create_entity(
        "IfcClassificationReference",
        Identification=code,
        Name=name,
        ReferencedSource=classification,
    )
    ifc.create_entity(
        "IfcRelAssociatesClassification",
        GlobalId=ifcopenshell.guid.new(),
        RelatedObjects=[product],
        RelatingClassification=reference,
    )
    return reference
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```
.venv\Scripts\pytest tests/test_ifc_writer.py -v
```
Expected: `6 passed` (3 previous + 3 new).

- [ ] **Step 5: Commit**

```
git add src/dxf2ifc/core/ifc_writer.py tests/test_ifc_writer.py
git commit -m "feat(core): add IfcWall creation with Talo2000 classification"
```

---

## Task 18: convert_dxf end-to-end orchestrator function

**Files:**
- Modify: `src/dxf2ifc/core/ifc_writer.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_ifc_writer.py`:

```python
from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.profiles.loader import load_default_profile


def test_convert_dxf_produces_ifc_with_wall(fixtures_dir: Path, tmp_path: Path):
    output = tmp_path / "out.ifc"
    convert_dxf(
        dxf_path=fixtures_dir / "simple_wall.dxf",
        output_path=output,
        profile=load_default_profile(),
    )
    assert output.exists()
    reloaded = ifcopenshell.open(str(output))
    walls = reloaded.by_type("IfcWall")
    assert len(walls) == 1
    # Classification attached
    refs = reloaded.by_type("IfcClassificationReference")
    assert any(r.Identification == "1241" for r in refs)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```
.venv\Scripts\pytest tests/test_ifc_writer.py::test_convert_dxf_produces_ifc_with_wall -v
```
Expected: `ImportError: cannot import name 'convert_dxf'`

- [ ] **Step 3: Implement convert_dxf**

Append to `src/dxf2ifc/core/ifc_writer.py`:

```python
from pathlib import Path

from dxf2ifc.core.dxf_reader import read_dxf
from dxf2ifc.core.mapper import apply_profile
from dxf2ifc.profiles.schema import Profile


def convert_dxf(
    *,
    dxf_path: str | Path,
    output_path: str | Path,
    profile: Profile,
    project_name: str | None = None,
) -> None:
    """Orchestrate DXF → IFC conversion end-to-end for Plan A (walls only)."""
    name = project_name or Path(dxf_path).stem
    entities = read_dxf(dxf_path)
    mapped = apply_profile(entities, profile)
    ifc = build_ifc_project_skeleton(project_name=name)
    storey = ifc.by_type("IfcBuildingStorey")[0]
    for m in mapped:
        if m.ifc_type == "IfcWall":
            wall = add_wall(ifc, m, parent_storey=storey)
            add_talo2000_classification(ifc, wall, code=m.talo2000_code, name=m.talo2000_name)
        # Plan B adds slabs, doors, windows, pipes, etc.
    write_ifc(ifc, output_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```
.venv\Scripts\pytest tests/test_ifc_writer.py -v
```
Expected: `7 passed`.

- [ ] **Step 5: Commit**

```
git add src/dxf2ifc/core/ifc_writer.py tests/test_ifc_writer.py
git commit -m "feat(core): add convert_dxf orchestrator for DXF to IFC end-to-end"
```

---

## Task 19: CLI — convert command

**Files:**
- Create: `src/dxf2ifc/cli.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cli.py`:

```python
"""Unit tests for CLI entry point."""
import subprocess
import sys
from pathlib import Path

import ifcopenshell
import pytest


def _run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "dxf2ifc", *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def test_cli_no_args_prints_help():
    r = _run_cli()
    assert r.returncode != 0
    assert "usage" in (r.stdout + r.stderr).lower()


def test_cli_convert_default_profile(fixtures_dir: Path, tmp_path: Path):
    out = tmp_path / "out.ifc"
    r = _run_cli("convert", str(fixtures_dir / "simple_wall.dxf"), str(out))
    assert r.returncode == 0, r.stderr
    assert out.exists()
    ifc = ifcopenshell.open(str(out))
    assert len(ifc.by_type("IfcWall")) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```
.venv\Scripts\pytest tests/test_cli.py -v
```
Expected: fails because `python -m dxf2ifc` is not runnable yet (no `__main__.py`).

- [ ] **Step 3: Implement cli.py**

Create `src/dxf2ifc/cli.py`:

```python
"""Command-line interface for dxf2ifc."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dxf2ifc import __version__
from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.profiles.loader import load_default_profile, load_profile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dxf2ifc",
        description="Convert AutoCAD DXF drawings to IFC 4 with Talo2000 classification.",
    )
    parser.add_argument("--version", action="version", version=f"dxf2ifc {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    convert = subparsers.add_parser("convert", help="Convert a DXF file to IFC.")
    convert.add_argument("input", type=Path, help="Path to the DXF input file.")
    convert.add_argument("output", type=Path, help="Path for the IFC output file.")
    convert.add_argument(
        "--profile",
        type=Path,
        default=None,
        help="Custom profile TOML. Omit to use the shipped Kylmälaite Talo2000 profile.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "convert":
        profile = load_profile(args.profile) if args.profile else load_default_profile()
        convert_dxf(
            dxf_path=args.input,
            output_path=args.output,
            profile=profile,
        )
        print(f"Wrote {args.output}", file=sys.stderr)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Create __main__.py so `python -m dxf2ifc` works**

Create `src/dxf2ifc/__main__.py`:

```python
"""Entry point for `python -m dxf2ifc`."""
from dxf2ifc.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run CLI tests**

Run:
```
.venv\Scripts\pytest tests/test_cli.py -v
```
Expected: `2 passed`.

- [ ] **Step 6: Commit**

```
git add src/dxf2ifc/cli.py src/dxf2ifc/__main__.py tests/test_cli.py
git commit -m "feat(cli): add convert subcommand and python -m dxf2ifc entry"
```

---

## Task 20: Integration test — DXF to IFC end-to-end

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write the integration test**

Create `tests/test_integration.py`:

```python
"""End-to-end integration test: DXF → CLI → IFC validated by ifcopenshell."""
import subprocess
import sys
from pathlib import Path

import ifcopenshell
import ifcopenshell.validate


def test_simple_wall_roundtrip(fixtures_dir: Path, tmp_path: Path):
    dxf = fixtures_dir / "simple_wall.dxf"
    out = tmp_path / "simple_wall.ifc"

    result = subprocess.run(
        [sys.executable, "-m", "dxf2ifc", "convert", str(dxf), str(out)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    ifc = ifcopenshell.open(str(out))

    # Structural assertions
    assert ifc.schema == "IFC4"
    walls = ifc.by_type("IfcWall")
    assert len(walls) == 1, f"expected 1 wall, got {len(walls)}"
    wall = walls[0]
    assert wall.PredefinedType == "STANDARD"

    # Classification attached with Talo2000 1241
    refs = ifc.by_type("IfcClassificationReference")
    talo = [r for r in refs if r.Identification == "1241"]
    assert len(talo) >= 1
    assert talo[0].ReferencedSource.Name == "Talo2000"

    # Wall has a representation
    assert wall.Representation is not None

    # IFC-level schema validation: should not raise
    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, logger=logger)
    errors = [e for e in logger.statements if e.get("level") == "ERROR"]
    assert errors == [], f"IFC validation errors: {errors}"
```

- [ ] **Step 2: Run the integration test**

Run:
```
.venv\Scripts\pytest tests/test_integration.py -v
```
Expected: `1 passed`.

- [ ] **Step 3: Run the full test suite**

Run:
```
.venv\Scripts\pytest -v
```
Expected: all tests pass (types, profile schema, profile loader, dxf reader, mapper, geometry, ifc writer, cli, integration).

- [ ] **Step 4: Commit**

```
git add tests/test_integration.py
git commit -m "test(integration): verify DXF to IFC roundtrip with schema validation"
```

---

## Task 21: CI-ready ruff lint + full suite check

**Files:**
- No new files. Quality gate.

- [ ] **Step 1: Run ruff**

Run:
```
.venv\Scripts\ruff check src tests
```
Expected: `All checks passed!`. If any issues, fix them in a follow-up commit and re-run.

- [ ] **Step 2: Run ruff format --check**

Run:
```
.venv\Scripts\ruff format --check src tests
```
Expected: `X files already formatted`. If any files would reformat, run `ruff format src tests`, commit with message `style: ruff format`.

- [ ] **Step 3: Run full pytest with coverage**

Run:
```
.venv\Scripts\pytest --cov=dxf2ifc --cov-report=term-missing
```
Expected: all tests pass, coverage of each module reported.

- [ ] **Step 4: Tag the milestone if desired**

Optional. Leave as-is if Plan B will land soon.

---

## Self-review checklist (before handing off)

**Spec coverage**: Plan A covers only the exterior wall path from the MVP list of 11 entity types in the spec. Remaining 10 groups (partition walls, slabs, doors, windows, refrigerant pipes, drainage pipes, shelves, cold room shells, refrigeration equipment, cable trays) are addressed in Plan B.

**Placeholder scan**: Tasks contain concrete code. Comments that say "Plan B adds..." are forward-references to a separate plan — not TODOs within this plan.

**Type consistency**: `Point3D`, `LineGeometry`, `EntityRecord`, `MappedEntity`, `Profile`, `Rule`, `WallExtrusion` defined once and reused consistently. `convert_dxf` signature fixed in Task 18 and called with the same keywords in Task 19 and Task 20.

**Task granularity**: every step is one concrete action. Tests show full code. Commits grouped per task.

## Execution notes

- Plan A should take roughly half a day to a day depending on familiarity with `ezdxf` and `ifcopenshell`.
- The `ifcopenshell.api.run("project.create_file", ...)` path used in Task 16 is the 0.8.x API; if the installed ifcopenshell is 0.7.x (older), the API uses `ifcopenshell.file(schema="IFC4")` — adjust accordingly.
- After Plan A is merged and working, Plan B reuses the same `convert_dxf` orchestrator and adds branches for each new `ifc_type`.
