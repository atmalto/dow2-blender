# Havok Simulator

This a Qt 4.8 + Havok 5.5 (VS2008) sand box app I wrote that I used to import Dawn of War II ragdoll and physics HKX files, dropping/pushing rigid bodies, and watching them simulate to validate blender import/export behavior. It is not a general-purpose Havok tool, but could be generalized, it does have a headless CLI mode that can be used to automate tests.

There are two build targets that share the same engine core (`sim_core.pri`):

- **`havok_simulator.exe`** — the interactive GUI app.
- **`havok_sim_cli.exe`** — a headless, scriptable driver used by the test suite.

The package is released in a separate zip with it's dedicated guide.

## GUI app

Release build - lightweight:

```bash
./build.sh release
```

Debug build:

```bash
./build.sh debug
```

Specify the Havok SDK path explicitly (otherwise it defaults to the path under
`~/Desktop/Reverse Engineering/...`):

```bash
./build.sh release "/c/Users/YourName/Desktop/Reverse Engineering/DoW2_Mod_tools/dow2_tools_working/working/havok_sdk_5_5_x"
```

The GUI executable is written to `build_vs2008/build/havok_simulator.exe` (debug)
or `build_vs2008/release/` (release).

## Headless CLI (`havok_sim_cli`)

`havok_sim_cli` boots the same `SimulationController` thatthe GUI uses (i.e no window, no OpenGL) and replays a JSON command scenario, printing a JSON result document. Its' the automation entry point for testing simulator behaviour.

Build it the same way as the GUI (ie same SDK path rules):

```bash
./build_cli.sh debug
# or: ./build_cli.sh release [sdk-path]
```

The executable is written to `build_cli/build/havok_sim_cli.exe` (debug) or
`build_cli/release/`.

### Running a scenario

Pass a scenario file, or `-` to read one from `stdin`:

```bash
./build_cli/build/havok_sim_cli.exe scenario.json
echo '{ ... }' | ./build_cli/build/havok_sim_cli.exe -
```

A scenario is an ordered list of commands; the CLI executes them against one
controller and prints `{ "ok": <bool>, "results": [ ... ] }`. Exit code is `0`
if every command succeeded, `1` if any failed, `2` on bad input.

```json
{
  "stop_on_error": true,
  "commands": [
    { "cmd": "new_scene", "preset": "blank" },
    { "cmd": "add_object", "object": "box", "body": "dynamic",
      "position": [0, 5, 0], "mass": 10.0 },
    { "cmd": "import_ragdoll", "path": "C:/path/to/ragdoll.hkx" },
    { "cmd": "run", "steps": 120 },
    { "cmd": "get_props", "target": "ragdoll" }
  ]
}
```

Create commands (`add_object`, `add_force`, `import_ragdoll`, `duplicate`) return
the new entity's `id` and `kind`. Editing/query commands (`edit_object`,
`edit_force`, `move`, `rotate`, `delete`, `duplicate`, `get_props`) take an `id`
plus `kind` and select that entity internally.

### Command reference

| Command | Purpose |
|---|---|
| `new_scene` `{preset}` | Reset to a preset (`blank`, `flat_plane_with_force`, `diagonal_plane`) |
| `clear_scene` | Remove all user entities |
| `save_scene` / `load_scene` `{path}` | Write / read a `.hkscene` file |
| `add_object` | Spawn a `box`/`sphere`/`wedge`/`hull`, `dynamic` or `static` |
| `add_force` `{mode: push\|pull}` | Add a directional force emitter |
| `import_ragdoll` `{path}` | Load a ragdoll HKX |
| `import_physics` `{path, systems:[i]}` | Load rigid bodies from a physics HKX |
| `run` `{steps}` / `reset` | Step the simulation / reset to the authored state |
| `settings` `{gravity_scale, ragdoll_mass_scale}` | Global sim knobs (applied on reset) |
| `edit_object` / `edit_force` | Change rigid-body / force properties |
| `move` `{position}` / `rotate` `{rotation}` | Reposition / reorient an entity |
| `delete` / `duplicate` | Remove / copy the target entity |
| `get_props` `{target: scene\|object\|force\|ragdoll}` | Read state / diagnostics |

Notes:
- **Authoring after running:** `run`/`step` puts the world out of sync with the
  authored scene, so add/edit/move/rotate/delete/duplicate are rejected until you
  `reset` (same rule as the GUI). Query commands still work.
- **Geometry:** a box's half-extents equal its `scale`; a sphere's radius equals
  `scale[0]`. A force ray-casts from its position along its local -Z (rotated by
  its Euler `rotation`) and pushes the first dynamic body it hits.

## Tests

`tests/test_cli.py` is a runner exercises
five common workflows end-to-end through `havok_sim_cli`:

Tests meant to produce a custom serialized hkscene for visual inspection in the GUI, these test actual DoW2-intended hkx assets :
  1. Ragdoll import + heavy-object drop on the ragdoll to simulate ragdoll stress/collision behaviour
  2. Physics (rubble) import onto a tilted static ramp to simulate rigid bodies collision

Tests mainly used as a validation for the base app, nothing DoW2 specific here:
   1. Objects on a plane shoved by directed forces (sphere vs cube, light vs heavy) 
   2. Scene create / save / load / clear
   3. Object + force manipulation (move, rotate, edit rigid-body & force props).


Build the CLI first, then run:

```bash
python tests/test_cli.py
```

The three simulation tests also save a `.hkscene` under
`working/tmp/cli_scenes/`; the runner prints their paths so you can open them in
`havok_simulator.exe` and press Play to visually confirm the setup imports and
simulates correctly. Each scenario runs in its own CLI process (the Havok base
system and global settings are process-global).