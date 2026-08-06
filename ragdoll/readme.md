# Ragdoll Package

This package is the clean plugin-facing replacement for the legacy `ragdoll_workspace` exporter code. It keeps the old workspace artifacts as evidence and source data, but formalizes three concerns for later Blender UI work:

1. exporter logic is split into scene, skeleton, body, constraint, and template modules
2. templates are loaded from a frozen package-local library keyed by `race/unit/animation_set`
3. user-facing constraint fields have explicit unit and range conventions separate from backend/export storage
4. the clean package can export both JSON and native Havok 4.5.1 ragdoll HKX through the stable backend executable

For the current authored-UI implementation plan, roundtrip test reanchor, and module-by-module status summary, see `ragdoll/ui_implementation_plan.md`.

## Module Layout

- `scene.py`: Blender import helpers and armature lookup
- `profiles.py`: named ragdoll selection profiles used when generating a ragdoll skeleton from scene bones
- `skeleton.py`: animation skeleton export, ragdoll hierarchy inference, and ragdoll reference pose generation
- `bodies.py`: heuristic rigid body authoring and body template overlay
- `constraints.py`: heuristic constraint authoring and constraint template overlay
- `templates.py`: standardized template library loader using the frozen package-local template payload
- `hkx.py`: native ragdoll HKX backend bridge for `ragdoll_blender2hkx_451r.exe`
- `field_specs.py`: UI-facing field metadata, units, observed ranges, and hard limits
- `exporter.py`: top-level JSON export orchestration
- `data/template_library.json`: frozen normalized template library used at runtime

## Template Library Shape

Templates are standardized from the legacy shipped-file inventory at `ragdoll_workspace/working/ragdoll_workspace_old/analysis_outputs/ragdoll_batch_inventory.json` and then frozen into `ragdoll/data/template_library.json` for runtime use.

The runtime library shape is:

```python
{
    "version": 1,
    "tree": {
        "race_marine": {
            "space_marine": {
                "melee_axe_range_pistol": "race_marine/space_marine/melee_axe_range_pistol"
            }
        }
    },
    "templates": {
        "race_marine/space_marine/melee_axe_range_pistol": {
            "template_id": "race_marine/space_marine/melee_axe_range_pistol",
            "selection_profile": "space_marine",
            "bodies": {
                "Ragdoll_Bip01 L Calf01": {
                    "shape_type": "capsule",
                    "radius": 0.126045,
                    "vertex_a": [-0.42519, 0.001847, 0.008837],
                    "vertex_b": [-0.186709, 0.001847, 0.008837],
                    "position": [-0.31347, 0.853804, 0.03941],
                    "rotation": [x, y, z, w],
                    "mass": 100.0,
                    ...
                }
            },
            "constraints": {
                "Ragdoll_Bip01 L Calf01": {
                    "constraint_type": "limited_hinge",
                    "entity_names": ["Ragdoll_Bip01 L Calf01", "Ragdoll_Bip01 L Thigh01"],
                    "pivot_a": [0.0, 0.0, 0.0],
                    "twist_axis_a": [0.0, 1.0, 0.0],
                    "plane_axis_a": [-1.0, 0.0, 0.0],
                    "hinge_min": -0.471239,
                    "hinge_max": 1.570796,
                    "friction_torque": 20.0,
                }
            },
        }
    },
}
```

The tree is what the future Blender UI should browse. The frozen template payload remains in canonical export units so the backend path stays lossless and runtime loading no longer depends on the analysis workspace.

## Backend Export Path

The clean package exposes two export layers:

- `export_ragdoll_json(...)` writes explicit ragdoll JSON for inspection and debugging
- `export_ragdoll_hkx(...)` builds the same ragdoll payload and passes it to `blender_hkx/ragdoll_blender2hkx_451r.exe`

That keeps the stable backend writer as the single source of truth for final HKX generation while letting the plugin keep explicit JSON as an inspectable intermediate.

## Unit Conventions

The exporter stores canonical Havok/backend values.

- angular values are stored/exported in radians
- lengths are stored/exported in Havok length units already present in the shipped HKX data
- friction torque is stored/exported directly as Havok torque magnitude

The future UI should present exposed angular fields in degrees and convert to radians before export. This is the clean split between user ergonomics and backend fidelity.

## Exposed Field Conventions

The field specs in `field_specs.py` encode both hard limits and observed shipped ranges.

| Field | UI Unit | Export Unit | Hard Range | Observed Shipped Range |
|---|---|---|---|---|
| `twist_min` | degrees | radians | `[-180, 180]` | `[-180, 0]` |
| `twist_max` | degrees | radians | `[-180, 180]` | `[0, 180]` |
| `cone_angle` | degrees | radians | `[0, 180]` | `[0.3, 82.5]` |
| `plane_min` | degrees | radians | `[-180, 0]` | `[-75.0, 0]` |
| `plane_max` | degrees | radians | `[0, 180]` | `[2.4, 45.0]` |
| `hinge_min` | degrees | radians | `[-180, 0]` | `[-119.7, 0]` |
| `hinge_max` | degrees | radians | `[0, 180]` | `[4.0, 104.4]` |
| `friction_torque` | torque | torque | `[0, +inf)` | ragdoll `[0, 1000]`, hinge `[0, 60]` |
| `capsule_radius` | scene length | scene length | `[0, +inf)` | `[0.033516, 0.367357]` |
| `capsule_length` | scene length | scene length | `[0, +inf)` | `[0.005892, 2.835086]` |

## Evidence Basis

- Havok 5.5 docs describe ragdoll and limited hinge angular limits in radians and limited hinges defaulting to `[-pi, pi]`
- the shipped batch inventory across 55 HKX files provides the observed ranges above
- the legacy policy matrix in `ragdoll_workspace/working/ragdoll_workspace_old/analysis_outputs/RAGDOLL_EXPORTER_POLICY_MATRIX.md` captured the initial export/UI split and remains the audit trail

## Intended Workflow

The package is built around the intended plugin flow:

1. user selects scene bones and generates a ragdoll skeleton from the existing animation skeleton
2. user chooses a template from the standardized tree to populate exposed and preset-driven fields
3. user optionally overrides exposed fields in UI units
4. exporter converts UI-facing values to canonical export values and writes explicit JSON for the backend

Template-driven joint local frames do not move the bones themselves. They define the local constraint frames attached to the generated rigid bodies.