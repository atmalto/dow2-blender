# Ragdoll UI Rework Implementation

## Purpose

This document replaces the earlier mixed UI direction with a clear constraint/body authoring plan.

The goal is to rework the ragdoll UI and constraint-update flow without disturbing the parts that already work:

- ragdoll skeleton creation logic stays as-is
- rigid body creation logic stays as-is
- viewport/body sync fixes are deferred to a later pass

This document is only about how the authoring UI should be organized and how template loading should update authored data.

## Core Decision

The UI is anchored on the selected rigid body, not on the selected bone.

Why:

- the user is editing the physical thing they can see
- the linked ragdoll bone can be shown from the rigid body mapping
- the linked constraint can be inferred from the rigid body relationship

## Target Editing Rule

When rigid body `B` is selected:

- the `Body` editor edits the authored rigid-body data for `B`
- the `Constraint` editor edits the authored constraint between `B` and its parent rigid body

Root rigid body behavior:

- body fields remain available
- constraint fields are disabled or empty
- the UI must state clearly that the root body has no parent constraint

## Scope Boundary

This rework does not change:

- skeleton generation operators
- ragdoll armature creation flow
- rigid body creation operators
- viewport sync and live capsule update behavior

The current issue where UI values and viewport capsule state are not fully synchronized is explicitly deferred.

## UI Layout

### Header

The top of the authoring UI should show the active target context.

Required header items:

- active rigid body name
- linked ragdoll bone name
- parent rigid body name, if any
- current constraint type, if any

This header is read-only context, not an edit surface.

### Main Sections

The authoring UI is divided into exactly three sections:

- `Basic`
- `Advanced`
- `Templated`

Each section contains exactly two blocks:

- `Body`
- `Constraint`

This keeps the shared rigid-body-centered workflow while still preserving the structural difference between rigid-body data and constraint data.

## Category Definitions

### Basic

`Basic` contains user-editable fields that should be quick to tune.

#### Basic Body

- `shape_type`
- `capsule_radius`
- `capsule_length`

#### Basic Constraint

- `twist_min`
- `twist_max`
- `cone_angle`
- `plane_min`
- `plane_max`
- `hinge_min`
- `hinge_max`
- `friction_torque`

Notes:

- hinge-only fields are unavailable for non-hinge constraints
- ragdoll angular fields are unavailable for limited-hinge constraints
- UI widgets must respect field type, such as enum vs numeric input

### Advanced

`Advanced` contains user-editable fields that are lower-level or harder to reason about directly.

#### Advanced Body

- `vertex_a`
- `vertex_b`
- `half_extents`
- `mass`
- `position`
- `rotation`

#### Advanced Constraint

- `constraint_type`
- `pivot_a`
- `pivot_b`
- `twist_axis_a`
- `twist_axis_b`
- `plane_axis_a`
- `plane_axis_b`

Notes:

- these are still editable by the user
- templates may override them, but only through the `Advanced` section loader

### Templated

`Templated` contains fields that are not manually edited in normal UI and are instead chosen by template selection.

#### Templated Body

- `friction`
- `motion_type`
- `linear_damping`
- `angular_damping`
- `collision_filter_info`
- `quality_type`
- `restitution` if kept template-only

#### Templated Constraint

This block is reserved for any constraint fields intentionally kept template-only.

Important current observation:

- the exported constraint payload is already mostly covered by `Basic` and `Advanced`
- if there are no true template-only constraint fields, the `Templated Constraint` block should either be empty or hidden until such fields are explicitly designated

## Field State Model

Every field shown in the UI must have one clear state:

- editable here
- not available for the current body or constraint type
- template-driven only

This is mandatory. Without it, the UI will become ambiguous.

Examples:

- `hinge_min` and `hinge_max` are not available for ragdoll constraints
- `twist_min`, `twist_max`, `cone_angle`, `plane_min`, and `plane_max` are not available for limited-hinge constraints
- template-driven-only fields must render as read-only summaries or template-owned values, not editable widgets

## Template Loader Design

Every category includes its own `Load from Template` area.

Required controls:

- `model` dropdown
- `folder` dropdown
- `bone name` dropdown
- `Load Preset` button

Important distinction:

- selected rigid body is the target being edited
- selected template bone name is the source entry inside the chosen `model | folder` template bundle

This means the loader is not "use the selected scene bone name".
It is "copy the chosen template bone entry onto the currently selected rigid body / inferred constraint target".

## Template Load Scope Rules

Load scope must be strict.

Rules:

- `Basic > Load Preset` only updates `Basic Body` and `Basic Constraint` fields
- `Advanced > Load Preset` only updates `Advanced Body` and `Advanced Constraint` fields
- `Templated > Load Preset` only updates template-driven fields

No category is allowed to overwrite another category's fields.

This is a hard rule because the three-section organization becomes meaningless if loaders leak across sections.

## Constraint Inference Rules

Constraint editing is inferred from the selected rigid body.

Rules:

- selected rigid body identifies the active ragdoll bone/body target
- the editable constraint is the constraint between that rigid body and its parent rigid body
- if there is no parent rigid body, no constraint is available
- the UI must never guess among multiple candidate constraints

## Common Interface Definition

The authoring surface is one shared rigid-body-centered interface, but it edits two kinds of data:

- rigid-body data
- constraint data

That means the UI should feel like one editor, not two separate workflows, but the data blocks remain visibly separate inside each category.

## Non-Goals For This Pass

Do not solve these in the same rework:

- live capsule mesh sync from edited UI values
- back-propagating object transforms into authored values
- skeleton creation redesign
- body creation redesign
- exporter backend redesign

Those are separate steps after the UI structure is corrected.

## Recommended Implementation Sequence

1. Replace the current mixed constraint UI with the new `Basic / Advanced / Templated` section layout.
2. Keep the existing skeleton and body creation operators intact.
3. Keep selection anchored on the active rigid body.
4. Add the shared header context for selected rigid body, linked bone, parent rigid body, and constraint type.
5. Add `Body` and `Constraint` blocks inside each category.
6. Add category-scoped template loaders with `model | folder | bone name` source selection.
7. Enforce the field-state model for editable, unavailable, and template-driven-only fields.
8. Add root-body empty-state handling for the constraint blocks.
9. Only after the new UI is stable, return to viewport capsule sync and body-update behavior.

## Short Form

The intended UI model is:

- selection target = active rigid body
- body target = selected rigid body
- constraint target = selected rigid body's parent joint
- layout = `Basic`, `Advanced`, `Templated`
- structure inside each = `Body` block + `Constraint` block
- template source = `model | folder | bone name`
- template load scope = only the currently selected category
- skeleton/body creation logic = preserved
- viewport body sync = deferred
