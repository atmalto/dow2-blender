# DoW2 Tools Blender Add-on

DoW2 Tools is a Blender add-on for working with Dawn of War II assets. It is built around the add-on panels in Blender's N-panel, and that is the intended way to use it.

## Setup

Download the latest release, then unpack the zip directly into:

```text
C:\Program Files\Blender Foundation\Blender <version>\<version>\scripts\addons_core
```

Example:

```text
C:\Program Files\Blender Foundation\Blender 4.3\4.3\scripts\addons_core
```

This should create a `dow2_tools` folder inside `addons_core`. Restart Blender after unpacking; the add-on should then show up in the N-panel.

Do not use Blender's normal add-on installer for this release layout. Unpack the folder directly into `addons_core` instead.

## What this add-on does
1. DoW2 `.model` import/export including meshes, materials, bones, and bounding volumes.
2. DoW2 `.hkx` import/export for animations, physics, and ragdolls.
3. DoW2 `.hkanim` pack/unpack for Relic-style animation sets.
4. DoW2 `.simbox` and `.coverbox` import/generation/export.
5. DoW2 `.markers` import/export.
6. DoW2 `.collision` import/export.
7. Santos Model Editor `.anim` import.
8. DoW2 batch animation processing and export.
9. QoL features:
   - Creation of DoW2 collsion meshes, physics bodies, ragdoll, bounding boxes and volumes, 
   - Badge placement editing for DoW2 Relic Materials.
   - Scene graph view of DoW2-relevant objects in the scene.
   - Export setup (LoD and health states) for DoW2 `.model`
   - Material preview controls for DoW2-shader team color, emissive, specularity intensity, and specularity tint.

## Functionality Notes

- The add-on uses bundled executables in the background for animation, physics, and ragdoll export (`dow2_tools\blender_hkx\havok_io_cli.exe`)
- **Physics, ragdoll, and map I/O** are experimental
  - Physics (`_physics.hkx`) is relatively stable but haven't been tested in game
  - Ragdoll (`ragdoll.hkx`) is experimental but hasn't been tested in game
  - Map I/O is in development
- The *rest-pose export* option exists, but it has not been thoroughly tested yet.
- *Smoothing groups, bounding volumes, and collision meshes* are heuristic. They are useful, but they may need manual checking.

## Usage Notes

- Use the N-panel UI for this add-on. Other Blender import/export menu paths are not the supported workflow.
- Most of the last-used configuration is saved and reused the next time Blender opens.
- Art assets are expected to exist relative to `<dow2-install-directory>/<mod-name>/data/art`.
- Badge placement editing is available under the model panel of the add-on, under the Relic Material tab. With the badge supporting material selected, click on change, edit, clear to modify the badge texture source, or edit it's position/orientation.
  - Mouse wheel: scale up / down
  - LMB: move badge
  - Q/E: rotate badge, CTRL + Q/E: rotate 90 degrees
  - Esc/Enter: cancel/apply changes
- Material preview controls include team color, emissive, specularity intensity, and specularity tint. These can also be controlled in the shader node panel, but they are for preview only.
- The add-on relies heavily on collections for LoDs and health bins, and on the armature name "DoW2_Armature" for model and animation export. If export fails or the output is wrong, check naming and collection layout first.
  - Note on LoD collections: since Blender only allows unique names for collections, multiple health bins require LoDs to have different names, hence the add-on processes them in an indexed fashion, ex: `healthy: lod0, light_damage: lod0.001, heavy_damage: lod0.002, wreck: lod0.003, etc`
    - in the example above, the each of the lod collections represents LoD level 0, the highest level of detail, and will strip out the additional suffixes when exporting to `.model`
    - **Ideally**, you should use the Model -> Model Export Setup as this will ensure proper collection naming under which meshes can be placed for safe export.
- Animation tools support editing `.rig` and `.tracks` files. Direct file editing is available from the rig and track settings panel, but editing from the panel itself is recommended.
- Animation batch processing does not currently show progress. Wait for Blender to unfreeze before assuming it failed.
- `write_all_animations.blend` imports all animation clips as a chain into one Blender scene file. It can take a while to generate.

## Utility Usage

1. **Intercept apply transform**: enable this so markers can properly transform with bones for DoW2 `.model` that are imported into Blender for editing through this add-on.
2. **Simbox / coverbox**: creates simbox and coverbox helpers that can be adjusted and exported.
3. **Model export setup**: creates the LoD and health-state collection presets supported by DoW2 and detected by this add-on. In the *Outliner* panel, place your meshes under those collections to prepare them for export.
4. **HKANIM pack / unpack**: packs and unpacks Relic-style `.hkanim` files, which are packed `.hkx` animation sets.
5. **Collision mesh generation**: generates collision meshes. **Simple (default)** meshes are created by default and are mainly used in-game for walkable surfaces. **Complex** meshes are used for projectile and unit nav collision, mainly for garrisonable buildings. 
   - Use *Decimate* to simplify collision geometry, 
   - Use *Walkable Angle* to limit walkable surface based on faces of selected mesh
   - Use *Use Selected Face* in object edit mode to limit collision mesh generation to only selected faces of the mesh for finegrained control of collision mesh generation.
6. **DoW2 Scene graph**: Shows scene objects detected by the add-on as DoW2-relevant objects. This helps organize your scene and find DoW2 supported objects.


## Supported Files

General:

- `.model`
- `.simbox`
- `.coverbox`
- `.markers`
- `.collision`
- `.dds`
- `ragdoll.hkx`
- `*_physics.hkx`

Animation:

- Santos Model Editor `.anim` import
- Havok `.hkx` import/export
- Relic `.hkanim` pack/unpack


Reach out to `sonofwilkin1337@gmail.com` with issues, or open an issue on the github repo. Pull requests are welcome, but please reach out first to discuss the change before submitting a PR.
