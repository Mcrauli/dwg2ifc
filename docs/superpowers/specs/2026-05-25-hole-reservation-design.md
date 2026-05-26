# Reikavaraus / IfcProvisionForVoid design

## Goal

Add a new hole reservation workflow that starts in AutoCAD and exports to IFC as a real `IfcProvisionForVoid`.

The first version must:

- add a dedicated AutoCAD tool named `REIKAVARAUS`
- always place reservations on layer `KYL-REIKAVARAUS`
- store a persistent GUID on each reservation block
- export reservations as true `IfcProvisionForVoid` objects
- include reservations in normal exports by default
- add a GUI checkbox for "reservations only" export
- produce a reservations-only IFC that contains only the IFC skeleton and hole reservations

The reservation is not an `IfcOpeningElement`. It is an independent reservation object used by structural design later.

## Current state

- The DXF -> IFC pipeline already supports layer/profile mapping and block attribute routing.
- `KYL-REIKAVARAUS` is now recognized in profile mapping.
- Hole reservation block attributes are promoted only for `INSERT` entities on `KYL-REIKAVARAUS`.
- The current IFC tree is a normal spatial tree:
  - `IfcProject -> IfcSite -> IfcBuilding -> IfcBuildingStorey -> products`
- A basic worker implementation for hole reservations was attempted, but local IfcOpenShell/schema support does not currently expose `IfcProvisionForVoid`.
- A proxy fallback (`IfcBuildingElementProxy` with `ObjectType = "IfcProvisionForVoid"`) was tested and rejected as the final solution.

## Approved decisions

### IFC semantics

- Hole reservations must be exported as true `IfcProvisionForVoid`.
- Final implementation must not silently fall back to `IfcBuildingElementProxy`.
- If current writer/tooling cannot create `IfcProvisionForVoid`, the write path must be changed so the correct entity can be produced.

### Spatial tree and Solibri visibility

- Hole reservations stay in the normal IFC spatial tree under storeys.
- No separate branch or special model tree grouping is created for reservations.
- In Solibri they should appear with the rest of the model content under the normal building/storey structure.

### Export modes

- Normal export includes hole reservations together with the rest of the model.
- A GUI checkbox adds a new "reservations only" export mode.
- In "reservations only" mode, the IFC contains:
  - the normal IFC skeleton
  - only hole reservation objects from `KYL-REIKAVARAUS`
- Other products, systems, and geometry are omitted in this mode.
- Filtering is applied late in the pipeline, in the export/orchestration stage, not in the parser.

### CAD authoring model

- The AutoCAD tool is block-based.
- A dedicated reservation block carries geometry-driving parameters and all export metadata.
- The command name is `REIKAVARAUS`.
- The tool always inserts to layer `KYL-REIKAVARAUS`.
- A ribbon button named `Reikavaraus` must be added.
- A dedicated ribbon icon is needed.

### First geometry version

- First version supports a round reservation body only.
- The IFC geometry is a cylindrical or equivalent round extruded provision body.
- Users can later edit diameter or length.

### Orientation workflow

- At command start the user explicitly chooses:
  - `Lattia`
  - `Seina`
- No automatic orientation guessing is used in v1.

Suggested input flow:

- `Lattia`: center point, diameter, length/thickness, elevation
- `Seina`: center point or direction points, diameter, wall penetration length

### GUID strategy

- Each reservation block stores its own persistent `GUID` attribute.
- The CAD-side value should be a normal UUID string.
- Export converts that UUID to IFC `GlobalId` format.
- If the block has no GUID yet, the reservation creation tool generates one once and stores it on the block.
- The same edited reservation must keep the same GUID across exports.

## Required reservation data

The reservation block should contain at least these attributes in the first version:

- `GUID`
- `VARAUS_TYYPPI` (`LATTIA` or `SEINA`)
- `HALKAISIJA`
- `PITUUS`
- `KORKO`
- `TUNNUS`
- `VARAAJA`
- `KOMMENTTI`

This set is intended to cover the information that must remain visible in downstream model checking and Solibri usage.

## IFC mapping design

### Entity target

- Hole reservations map to `ifc_type = "IfcProvisionForVoid"`.
- They are not mapped to `IfcOpeningElement`.
- They are not modeled as a generic proxy in the final design.

### Builder responsibilities

The hole reservation builder must:

- create the reservation entity as `IfcProvisionForVoid`
- set a stable IFC `GlobalId` derived from block attribute `GUID`
- build round geometry from diameter and length
- place the object in the normal spatial structure
- attach the needed property sets / metadata so the reservation remains useful in Solibri and RAVA-oriented workflows

### Writer/tooling constraint

Because the currently verified local IfcOpenShell/schema path does not expose `IfcProvisionForVoid`, implementation must explicitly solve that tooling gap instead of masking it with a proxy fallback.

## GUI behavior

Add a checkbox in the GUI export settings for a reservations-only IFC.

Expected behavior:

- checkbox off:
  - export the normal model
  - include hole reservations with everything else
- checkbox on:
  - export only IFC skeleton + hole reservations

This is a GUI-level option that passes an export flag into the convert/orchestrator pipeline.

## Implementation boundaries

### Files likely affected

- AutoCAD tool / Lisp files for block insertion and ribbon command wiring
- ribbon/CUIX-related assets and icon resources
- profile mapping config
- block attribute promotion logic
- GUI export settings and convert call path
- export orchestrator filtering
- IFC builders / writer dispatch
- tests for mapper, builder, and reservations-only export mode

### Tests required

- normal export still includes reservations
- reservations-only export contains only skeleton + reservations
- reservations-only export does not change normal export behavior when disabled
- reservation GUID is stable across repeated exports of the same source block
- final writer path creates real `IfcProvisionForVoid`, not a proxy fallback

## Implementation order

1. Finalize CAD-side reservation data contract and block metadata.
2. Add GUI checkbox and late-stage orchestrator filtering for reservations-only export.
3. Implement a real IFC write path for `IfcProvisionForVoid` without proxy fallback.
4. Complete stable GUID handling end to end.
5. Add ribbon button and icon.
6. Add or update tests and documentation.

## Definition of done

The feature is done when:

- AutoCAD users can place a `REIKAVARAUS` block on `KYL-REIKAVARAUS`
- the block stores a persistent GUID and reservation metadata
- normal export includes reservations with the rest of the model
- GUI can export skeleton + reservations only
- exported reservations are true `IfcProvisionForVoid` entities
- no final proxy fallback remains in the writer path
