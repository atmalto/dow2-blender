# DoW2 Ragdoll UI Implementation Plan

Current UI rework note:

The active UI/constraint-authoring direction now lives in `ragdoll/ui_rework_implementation.md`.
This older document remains useful as historical export/runtime context, but it is no longer the primary source for the category layout or template-loader behavior.

This document reanchors the current ragdoll implementation before UI authoring work expands into viewport interaction. It is intentionally tied to the verified export path and current addon wiring, not to a speculative future design.

## 1. Current Verified Export and Roundtrip Flow

### 1.1 Verified runtime path today

The currently verified path is:

1. Import a shipped `.model` in headless Blender.
2. Resolve a named selection profile and template id.
3. Build ragdoll data from the scene animation armature.
4. Write explicit ragdoll JSON.
5. Pass that JSON to the native Havok 4.5.1 exporter.
6. Convert both shipped and generated HKX to XML with `AssetCc1.exe`.
7. Normalize both inventories to logical body/constraint payloads.
8. Compare the normalized payloads for semantic equality.

The headless wrapper is in `ragdoll/export_ragdoll_json_from_model.py`.
The clean export orchestrator is in `ragdoll/exporter.py`.
The native HKX bridge is in `ragdoll/hkx.py`.
The verifier is in `tests/verify_ragdoll_roundtrip.py`.

### 1.2 What the roundtrip test is rechecking

The roundtrip verifier is not only checking that a file was produced. It rechecks four separate invariants:

1. Blender-side export succeeds using the real addon registration path.
2. Native HKX export is deterministic across repeated runs from the same JSON input.
3. Generated HKX matches shipped HKX semantically after XML normalization.
4. Frozen template coverage still matches the shipped reference asset it was frozen from.

### 1.3 What is compared semantically

The semantic comparison strips away packfile-level noise and compares the normalized logical payload.

For rigid bodies, the verifier compares:

- body names
- shape type
- motion type
- collision filter info
- quality type
- radius
- mass
- friction
- restitution
- linear damping
- angular damping
- vertex A
- vertex B
- half extents
- position
- rotation

For constraints, the verifier compares:

- constraint names
- constraint type
- entity name pair
- pivot A/B
- twist axis A/B
- plane axis A/B
- hinge min/max and friction torque for limited hinge
- twist min/max, cone angle, plane min/max, and friction torque for ragdoll

This is why the roundtrip test is useful as a regression test for UI work later: it verifies logical authoring output, not just byte-for-byte file identity.

### 1.4 How template-based flow is being tested today

The template-based path is currently tested in three ways.

1. The export path runs with an explicit template id, so all template overlays are active during JSON and HKX generation.
2. The verifier compares the generated logical body and constraint data to the shipped HKX reference for that same template target.
3. The verifier also asserts that the frozen template bundle still covers the exact body and constraint name set found in the shipped reference HKX.

That means the current tests verify both:

- template application behavior during export
- template library integrity relative to shipped source assets

### 1.5 Targets already verified

The current verifier covers at least these named targets:

- `space_marine`
- `scout_1`
- `boy`
- `hormagaunt`

`scout_1`, `boy`, and `hormagaunt` were verified end to end through Blender export, native HKX generation, AssetCc XML conversion, semantic normalization, and deterministic repeat generation.

## 2. Current Implementation Summary Under `ragdoll/`

The current `ragdoll/` package has two distinct layers:

1. a clean modular export core
2. a thin addon/runtime layer for template selection and export

### 2.1 Public package surface

`ragdoll/__init__.py` currently exposes:

- selection profiles
- field spec metadata
- template loading
- skeleton generation
- JSON export
- HKX export
- top-level ragdoll data build

This is a useful API boundary and should be preserved.

### 2.2 Core export modules

Current core responsibilities are already split reasonably well.

- `scene.py`: model import and armature lookup helpers
- `profiles.py`: named ragdoll bone-selection profiles
- `skeleton.py`: animation skeleton export, ragdoll bone mapping, ragdoll hierarchy inference, ragdoll reference pose generation
- `bodies.py`: heuristic rigid body generation plus template overlay
- `constraints.py`: heuristic constraint generation plus template overlay
- `templates.py`: frozen template library loading, normalization, bundle resolution, overlay application
- `field_specs.py`: UI-facing editable fields, template-driven fields, locked backend values, unit conversion helpers
- `hkx.py`: native bridge to `ragdoll_blender2hkx_451r.exe`
- `exporter.py`: top-level orchestrator that composes skeleton, bodies, constraints, templates, JSON output, and HKX output

### 2.3 Current addon layer

The addon integration added so far is intentionally small.

- `addon.py`: registers ragdoll properties and operators
- `properties.py`: scene-level template id, selection profile, JSON path, HKX path
- `operators.py`: export JSON and export HKX operators
- `ui/ragdoll_panels.py`: current sidebar panel for source/template selection and export buttons

This layer does not yet represent authored ragdoll state inside the scene. It only configures the export path.

### 2.4 Important current limitation

The current exporter is still animation-armature-driven.

It does **not** currently operate on:

- a dedicated authored ragdoll armature in the scene
- user-authored rigid body meshes
- user-authored constraints stored in Blender data
- persistent scene-side bone-to-ragdoll mapping assets

That distinction matters because the requested UI is not just a visualization layer on top of the current exporter. It requires a new authored scene model.

### 2.5 Current addon integration points outside `ragdoll/`

The current ragdoll addon wiring into the rest of the plugin is:

- root addon module registration in `__init__.py`
- UI aggregation in `ui/panels.py`
- runtime panel in `ui/ragdoll_panels.py`

This integration approach should remain unchanged: `ragdoll/` should own its data and operators, while `ui/` should stay as presentation and composition.

## 3. Architectural Reanchor for the Requested UI

The requested UI implies a shift from **derived export** to **scene-authored ragdoll authoring**.

The clean architectural split should become:

1. source animation skeleton discovery
2. authored ragdoll scene data model
3. export translation from authored scene data to canonical ragdoll JSON
4. optional template application and preset loading into authored state
5. viewport preview and gizmo rendering

The export core should stop treating generated bodies/constraints as temporary Python-only structures once authoring UI begins. Instead, those structures should become canonical scene-backed authored data that the exporter serializes.

## 4. Target User Workflow

The intended authored workflow should be formalized as follows.

### Phase A: setup

1. User selects animation bones on the imported animation armature.
2. User presses `Setup Ragdoll From Selected`.
3. Addon verifies the scene is saved; if not, prompt to save first.
4. Addon creates a dedicated ragdoll armature named `DoW2_Ragdoll_Armature`.
5. Addon creates and stores a persistent mapping between animation bones and ragdoll bones.
6. Addon writes mapping metadata to disk and also stores it in the `.blend` file.

### Phase B: authoring

1. User selects the ragdoll armature or ragdoll bone.
2. User creates or edits the rigid body for a bone.
3. User edits body properties and constraint properties.
4. User optionally loads values from a frozen template preset.
5. User previews geometric and scalar properties in the viewport.

### Phase C: export and validation

1. Exporter reads the authored ragdoll scene model.
2. Exporter resolves locked fields and optional template-driven fields.
3. Exporter writes canonical JSON.
4. Native backend writes HKX.
5. Roundtrip or custom-value tests validate the output.

## 5. Proposed Scene Data Model

The requested UI needs a real authored scene model. That model should live in Blender data, not only in transient Python dicts.

### 5.1 Core authored entities

We should introduce four primary authored entities.

1. Ragdoll rig session
2. Ragdoll bone mapping record
3. Ragdoll rigid body record
4. Ragdoll constraint record

### 5.2 Recommended ownership model

Use the `DoW2_Ragdoll_Armature` object as the anchor object for ragdoll state.

Recommended ownership:

- scene stores active ragdoll session pointer/reference
- ragdoll armature stores session metadata and mapping metadata
- each ragdoll rigid body mesh stores a `body_id`, related ragdoll bone name, and naming prefix marker
- each constraint record is stored as armature-attached property data keyed by child ragdoll bone name

### 5.3 Persistent storage strategy

Store data in two places by design.

1. In-file: Blender custom properties / property groups for normal authoring and undo support
2. On disk: mapping manifest JSON for portability, inspection, and recovery

Do not use CSV as the primary persistence format. JSON is a better fit because the mapping will quickly grow beyond flat columns once body ids, template ids, and preview flags are added.

### 5.4 Suggested disk artifacts

Suggested saved artifacts next to the `.blend` file:

- `*.dow2_ragdoll_mapping.json`
- `*.dow2_ragdoll_session.json` only if external session snapshots are later needed

The mapping file should at minimum contain:

- source armature object name
- ragdoll armature object name
- animation bone to ragdoll bone mapping
- ragdoll bone to body object name mapping
- template id last loaded

## 6. Naming Conventions

Naming must be deterministic and machine-recognizable.

### 6.1 Armature

- Ragdoll armature object name: `DoW2_Ragdoll_Armature`

### 6.2 Rigid body meshes

Rigid body meshes should use a dedicated prefix, similar to how collision and physics helpers are recognized elsewhere in the addon.

Recommended prefix:

- `RagdollBody::`

Recommended object name format:

- `RagdollBody::<ragdoll bone name>`

Example:

- `RagdollBody::Ragdoll_Bip01 L Calf01`

Meshes without the prefix should be ignored by the ragdoll addon logic.

### 6.3 Optional constraint pseudo-objects

Constraints do not need real Blender constraint objects if the exporter owns canonical serialization, but preview helpers may benefit from named helper empties or transient draw records.

If helper objects are needed, use:

- `RagdollConstraint::<ragdoll bone name>`

## 7. Target Module Split for the UI Implementation

The implementation should stay modular and testable. Do not let the current thin `properties.py` and `operators.py` grow into monoliths.

Recommended new module split under `ragdoll/`:

- `session.py`: session-level state and saved-scene detection
- `mapping.py`: animation bone <-> ragdoll bone mapping model, JSON read/write
- `setup.py`: setup operator logic for creating `DoW2_Ragdoll_Armature` and initial records
- `authoring_properties.py`: PropertyGroup definitions for bodies, constraints, sessions, preview flags
- `body_objects.py`: create/update/query rigid body mesh objects and prefix recognition
- `constraint_state.py`: canonical authored constraint records and preset-loading helpers
- `selection.py`: selection-context resolution for animation armature, ragdoll armature, ragdoll bone, rigid body object
- `presets.py`: load values from template bundles into authored scene state
- `serialization.py`: convert authored scene state into canonical export dicts
- `exporter_authored.py`: authored-scene exporter entry point, likely merged into `exporter.py` later via strategy selection
- `viewport_draw.py`: non-gizmo draw handlers for overlays and scalar visualizations
- `viewport_preview_state.py`: throttled preview caches and dirty-flag updates
- `operators_setup.py`: setup and scene authoring operators
- `operators_bodies.py`: create/update rigid body operators
- `operators_presets.py`: load preset/apply preset/reset preset operators
- `panels_authoring.py`: body/constraint/session UI sections for authored state

Existing modules that should remain mostly stable:

- `templates.py`
- `field_specs.py`
- `hkx.py`
- `profiles.py`

Existing modules that should be adapted rather than discarded:

- `exporter.py`
- `skeleton.py`
- `bodies.py`
- `constraints.py`

## 8. Planned Feature Areas

### 8.1 Ragdoll skeleton setup

#### Goal

Create a persistent scene-authored ragdoll rig anchored to a selected animation-bone subset.

#### Operator

- `dow2.setup_ragdoll_from_selected`

#### Behavior

1. Validate the scene is saved.
2. Validate there is a source animation armature.
3. Read selected source bones.
4. Resolve relic/havok ragdoll naming for those bones.
5. Create `DoW2_Ragdoll_Armature` if absent, or prompt to replace/update if present.
6. Build and store the mapping record.
7. Persist mapping in-file and to JSON.

#### Reuse from current implementation

Reuse from `skeleton.py`:

- name canonicalization approach
- hierarchy inference approach
- reference pose extraction approach

#### Important change from current implementation

Current `create_ragdoll_skeleton_from_armature()` returns transient exported data.
The new setup flow must create authored scene state first, then let export serialize from that state.

### 8.2 Rigid body creation

#### Goal

Let a user create a body per ragdoll bone either through raw endpoint coordinates or through capsule-friendly controls.

#### Supported editing modes

1. Endpoint mode: vertex A / vertex B XYZ
2. Capsule mode: radius / length / alignment axis

Capsule mode should not be a separate export format. It should only be a higher-level UI over canonical `vertex_a`, `vertex_b`, and `radius`.

#### Operator behavior

- create or replace the rigid body mesh for the selected ragdoll bone
- assign the naming prefix
- assign related custom properties linking it to the ragdoll bone record
- store canonical authored values in property groups

#### Recommendation

The authoritative stored data should still be canonical values:

- `shape_type`
- `radius`
- `vertex_a`
- `vertex_b`

Derived UI fields like `length` and `alignment` should be recomputed helpers, not the only stored form.

### 8.3 Rigid body modification

#### Goal

Selecting a recognized ragdoll rigid body mesh should expose authoring UI and keep the canonical body record synchronized.

#### Supported modification sources

1. Numeric editing in the panel
2. Transform editing on the mesh object
3. Optional geometry editing if shape remains representable

#### Recommendation on transforms

Treat the canonical authored body record as authoritative and synchronize object transforms from it. When the user transforms the mesh object directly, the addon should detect the change and update canonical body values.

#### Safe scope for first implementation

Support object transform sync first.
Do not support arbitrary edit-mode mesh deformation as authoritative input in the first pass.

Reason: freeform mesh editing quickly decouples the scene object from the canonical capsule/sphere/box exporter model.

### 8.4 Constraint and property editing

#### Goal

Selecting a ragdoll bone or rigid body should expose the correct body and constraint controls, grouped by editability.

#### Required groups

1. Main editable fields
2. Locked backend fields
3. Template preset fields

#### Group semantics

Main editable fields:

- backed by `EXPOSED_FIELD_SPECS`
- editable widgets
- include `Load From Preset`

Locked backend fields:

- backed by `LOCKED_BACKEND_FIELDS`
- display only
- muted styling

Template preset fields:

- backed by `TEMPLATE_DRIVEN_FIELDS`
- display current resolved values
- not editable directly
- include a visible `Select Preset` action

#### Recommendation on source of truth

Template fields should resolve into explicit authored values at load time, but their provenance should be tracked.

Suggested per-field provenance states:

- `locked`
- `template`
- `user`

That provenance will make UI rendering and future diffs much easier.

## 9. Viewport Preview Plan

Viewport preview is important, but it must be treated as a separate layer over authored state.

### 9.1 Preview categories

1. Rigid body preview geometry
2. Constraint angular preview geometry
3. Scalar heatmap previews
4. Constraint type text / label previews

### 9.2 Recommended rendering split

#### Use real scene objects for

- rigid body meshes

#### Use draw handlers or gizmo groups for

- cone / plane preview
- twist / hinge arc preview
- text overlays
- friction and mass color overlays if live object tinting is not practical

### 9.3 Update policy

Preview geometry should update on release or via a deferred dirty-flag refresh, not continuously on every drag step.

Recommended pattern:

- property update marks preview state dirty
- timer or depsgraph handler rebuilds preview once interaction settles

### 9.4 Specific preview recommendations

Cone + plane preview:

- render a moderate-resolution cone section
- plane min/max should clip the cone section
- use stable local-joint-frame basis, not world guesswork

Twist and hinge preview:

- render disc or ring sectors around the joint axis
- min/max values shown as arc boundaries

Constraint type preview:

- optional 2D viewport label near the joint
- do not make this a blocker for first authoring pass

Friction or mass preview:

- use a simple gradient palette on body preview objects or overlay wireframes
- keep the scalar normalization explicit and documented

## 10. Export Architecture After UI Work Starts

The exporter should support two modes explicitly.

### Mode 1: derived/template export

Current mode.
Input is an animation armature plus template and optional selection profile.

### Mode 2: authored-scene export

Target mode for the UI.
Input is the authored ragdoll session rooted at `DoW2_Ragdoll_Armature` plus its linked body and constraint records.

### Recommendation

Do not delete the current derived/template path.
Keep it as:

- a baseline reference path
- a fast verifier path
- a useful fallback for generating initial authored state

The exporter entry point should eventually dispatch based on explicit mode, not by guessing from object selection.

## 11. Testability Strategy

Viewport rendering itself will remain mostly visual/manual, but the rest must stay testable.

### 11.1 What should stay fully testable

1. setup mapping generation
2. mapping persistence and reload
3. rigid body canonicalization from UI values
4. constraint canonicalization from UI values
5. preset loading into authored state
6. export serialization from authored state
7. authored-scene JSON output sanity
8. native HKX roundtrip from authored-scene JSON

### 11.2 Test categories to add

#### A. Pure Python unit-style tests

- mapping normalization
- naming and prefix recognition
- field provenance resolution
- `length` / `alignment` <-> `vertex_a` / `vertex_b` conversion
- preset-load merge semantics

#### B. Headless Blender tests

- setup operator creates `DoW2_Ragdoll_Armature`
- setup operator writes mapping JSON
- rigid body operator creates recognized prefixed mesh
- selection-context resolution works for ragdoll armature, ragdoll bone, and rigid body object
- authored-scene export writes canonical JSON

#### C. Roundtrip tests against shipped assets

- same pattern as current `tests/verify_ragdoll_roundtrip.py`
- use authored-scene export instead of only derived export

#### D. Custom-value sanity tests

These are especially important for the requested workflow.

Add tests that:

1. build a ragdoll setup from a non-shipped selected subset
2. author custom body dimensions and masses
3. author custom editable constraint values
4. export JSON
5. assert the JSON and generated HKX remain structurally sane

For custom-value tests, sanity should include:

- no missing body/constraint references
- valid parent/child indices
- finite numeric values
- legal angle ranges
- no negative radii or invalid capsule lengths
- no exporter/backend failure

### 11.3 Suggested test file split

Recommended additions under `tests/`:

- `test_ragdoll_setup_mapping.py`
- `test_ragdoll_body_authoring.py`
- `test_ragdoll_constraint_authoring.py`
- `test_ragdoll_preset_loading.py`
- `test_ragdoll_authored_export_json.py`
- `test_ragdoll_authored_roundtrip.py`
- `test_ragdoll_custom_value_sanity.py`

## 12. Implementation Phases

### Phase 1: authored scene data foundation

Deliverables:

- session model
- mapping model
- saved-scene enforcement
- setup operator
- `DoW2_Ragdoll_Armature` creation
- mapping JSON persistence

Success criteria:

- setup is repeatable
- mapping survives save/reload
- no viewport preview required yet

### Phase 2: rigid body authored state

Deliverables:

- body property groups
- rigid body creation operator
- prefix recognition
- endpoint and capsule editing modes
- body selection-context UI

Success criteria:

- body state is scene-backed
- mesh object and canonical body state stay synchronized

### Phase 3: constraint authored state and preset integration

Deliverables:

- constraint property groups
- locked/template/user group rendering
- load-from-preset behavior
- per-field provenance tracking

Success criteria:

- template load is explicit and reversible
- authored editable values remain distinct from locked and template-only values

### Phase 4: authored export path

Deliverables:

- serialize authored scene state to canonical export dicts
- authored JSON export
- authored HKX export
- authored roundtrip tests

Success criteria:

- authored path exports through the same native HKX backend
- current shipped-target roundtrip style remains available

### Phase 5: viewport previews

Deliverables:

- rigid body preview synchronization
- cone/plane preview
- twist/hinge preview
- optional scalar overlays

Success criteria:

- previews are performant enough for normal authoring
- preview code is isolated from export logic

## 13. Immediate Design Decisions Recommended Before Coding

These decisions should be locked before implementation starts.

1. Use JSON, not CSV, for the mapping sidecar.
2. Treat authored scene data as canonical once UI authoring begins.
3. Keep the current derived/template export path as a separate supported mode.
4. Use deterministic name prefixes for recognized ragdoll helper objects.
5. Store canonical body values as `radius`, `vertex_a`, and `vertex_b`, even if the UI offers `length` and `alignment` helpers.
6. Separate preview code from export code from the start.
7. Track field provenance so locked/template/user sections stay coherent.

## 14. Immediate Next Coding Order

When implementation begins, the safest order is:

1. session and mapping foundation
2. setup operator and saved-scene enforcement
3. authored body data model and rigid body creation
4. selection-context resolution
5. authored constraint data model and preset loading
6. authored export serialization
7. authored roundtrip and custom-value tests
8. viewport preview layer

This order keeps non-viewport work testable first and prevents the viewport layer from becoming the place where data ownership is accidentally defined.
