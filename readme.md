# DoW2 Tools Blender Add-on

DoW2 Tools is a Blender add-on for working with Dawn of War II assets. It is built around the add-on panels in Blender's N-panel.

Download from releases on GitHub https://github.com/atmalto/dow2-blender/releases 

Download from ModDB:

<a href="https://www.moddb.com/games/dawn-of-war-ii-retribution/downloads/dow-2-blender-tools" title="Download DoW 2 Blender Tools - ModDB" target="_blank"><img src="https://button.moddb.com/download/medium/314341.png" alt="DoW 2 Blender Tools" /></a>

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

**Note on binaries used**

The add-on uses an exe and a dll in the background for animation/physics/ragdoll import/export, their source code and build script can be found under [/blender_hkx/src ](https://github.com/atmalto/dow2-blender/tree/main/blender_hkx/src) , [/blender_hkx/build_all.sh ](https://github.com/atmalto/dow2-blender/blob/main/blender_hkx/build_all.sh).

- _Antivirus_ : You may use your antivirus software to scan and flag the add on.
- _Self-build .exe / .dll_  : If there are concerns, you'd be able to build your .exe / .dll files, as long as you have the accompanying havok sdk and compatible MSVC versions. Contact sonofwilkin1337@gmail.com for assistance on this.
- _AI Tools _: Ask AI to scan the binaries against the source code and match ( give the .dll + .exe + a zip of [/blender_hkx/src ](https://github.com/atmalto/dow2-blender/tree/main/blender_hkx/src)  and get an AI model like claude or codex to validate)

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
   - Havok simulation of DoW2 `.hkx` physics and ragdolls.
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
- Debugging physics and ragdoll is done through the Havok Simulator standalone app, which is included in the add-on.

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
- A more detailed usage guide will be provided fro havok and ragdoll authoring.

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
7. Import DoW2 ragdoll.hkx or _physics.hkx into havok_simulator.exe, add static planes, dynamic objects and force objects to simulate interaction with hkx rigid bodies and ragdolls.

## Supported Files

General:

- `.model`
- `.simbox`
- `.coverbox`
- `.markers`
- `.collision`
- `.dds`

Animation:

- Santos Model Editor `.anim` import
- Havok `.hkx` import/export
- Relic `.hkanim` pack/unpack

Physics:

- Ragdoll `.hkx`
- destruction physics `.hkx`

Reach out to `sonofwilkin1337@gmail.com` with issues, or open an issue on the github repo. Pull requests are welcome, but please reach out first to discuss the change before submitting a PR.
