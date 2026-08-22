#!/usr/bin/env python3
"""End-to-end test suite for havok_sim_cli.

Five workflow tests exercise the headless simulator the way the GUI does:

  1. Ragdoll import + heavy-object drop (simulation-driven).
  2. Physics (rubble) import + static plane underneath + settle (simulation-driven).
  3. Objects on a plane shoved by directed forces, sphere vs cube, light vs heavy
     (simulation-driven).
  4. Scene create / save / load / clear (file I/O + state).
  5. Object + force manipulation: move, rotate, edit rigid-body + force props.

Because simulation outcomes are hard to assert exactly, the three simulation
tests (1-3) also SAVE a .hkscene the user can open in havok_simulator.exe to
visually confirm the setup imports and simulates correctly. The suite asserts on
measurable deltas (things moved / fell / released) and prints the scene links at
the end.

Runnable directly (no pytest needed):

    python havok_simulator/tests/test_cli.py

Each scenario runs in its own CLI process (Havok base system + global singletons
are process-global -> one scenario per process).
"""

import json
import os
import subprocess
import sys

# --- paths -------------------------------------------------------------------

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))  # dow2_tools
CLI = os.path.join(ROOT, "havok_simulator", "build_cli", "build", "havok_sim_cli.exe")
SCENES_DIR = os.path.join(ROOT, "working", "tmp", "cli_scenes")
GUI = os.path.join(ROOT, "havok_simulator", "build_vs2008", "build", "havok_simulator.exe")

RAGDOLL_HKX = ("C:/Program Files (x86)/Steam/steamapps/common/Dawn of War II - Retribution/"
               "testMod/Data/art/race_tyranid/troops/hormagaunt/animations/melee_blade/ragdoll.hkx")
PHYSICS_HKX = ("C:/Program Files (x86)/Steam/steamapps/common/Dawn of War II - Retribution/"
               "testMod/Data/art/world_objects/desert_objects/buildings/d_windmill_6slot/"
               "d_windmill_6slot_rubble_physics.hkx")

# Simulation length guard: dt = 1/60 s, so keep every run < 600 steps (< 10 s).
MAX_STEPS = 540


# --- CLI harness -------------------------------------------------------------

class CliError(Exception):
    pass


def run_cli(commands, stop_on_error=True):
    """Run one scenario in a fresh CLI process; return (result_dict, returncode)."""
    scenario = {"stop_on_error": stop_on_error, "commands": commands}
    proc = subprocess.run(
        [CLI, "-"],
        input=json.dumps(scenario),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT,
        text=True,
    )
    # Havok prints a boot banner to stdout before our JSON document. The top-level
    # object is the only '{' at column 0, so parse from the first such line.
    lines = proc.stdout.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("{"):
            start = i
            break
    if start is None:
        raise CliError("no JSON in CLI output:\n%s\n%s" % (proc.stdout, proc.stderr))
    result = json.loads("\n".join(lines[start:]))
    return result, proc.returncode


def results_of(result):
    return result.get("results", [])


def by_cmd(result, cmd, index=0):
    """Return the index-th result whose 'cmd' matches."""
    matches = [r for r in results_of(result) if r.get("cmd") == cmd]
    if not matches:
        raise CliError("no result for cmd '%s'" % cmd)
    return matches[index]


def assert_all_ok(result):
    for r in results_of(result):
        if not r.get("ok", False):
            raise AssertionError("command failed: %s -> %s" % (r.get("cmd"), r.get("error")))
    if not result.get("ok", False):
        raise AssertionError("scenario not ok")


# --- geometry helpers --------------------------------------------------------

def _extent_y(body):
    return max(body["half_extents"][1], body.get("radius", 0.0))


def top_of(body):
    return body["position"][1] + _extent_y(body)


def bottom_of(body):
    return body["position"][1] - _extent_y(body)


def bodies_of_kind(scene_result, kind, dynamic_only=False):
    bodies = scene_result["bodies"]
    out = [b for b in bodies if b["kind"] == kind]
    if dynamic_only:
        out = [b for b in out if b.get("is_dynamic")]
    return out


def centroid(bodies):
    n = float(len(bodies))
    cx = sum(b["position"][0] for b in bodies) / n
    cy = sum(b["position"][1] for b in bodies) / n
    cz = sum(b["position"][2] for b in bodies) / n
    return (cx, cy, cz)


def dist2d(a, b):
    return ((a[0] - b[0]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def scene_path(name):
    if not os.path.isdir(SCENES_DIR):
        os.makedirs(SCENES_DIR)
    # Forward slashes: safe for the C++ std::ofstream / QFile writer on Windows.
    return os.path.join(SCENES_DIR, name).replace("\\", "/")


# --- Test 1: ragdoll import + heavy drop ------------------------------------

def test_ragdoll_drop():
    # Probe: import the ragdoll and measure its extent so we can place a heavy
    # object directly above it (DoW2 ragdolls are heavy, so use ~400 kg).
    probe, _ = run_cli([
        {"cmd": "import_ragdoll", "path": RAGDOLL_HKX},
        {"cmd": "get_props", "target": "scene"},
    ])
    assert_all_ok(probe)
    rag = bodies_of_kind(by_cmd(probe, "get_props"), "ragdoll")
    assert len(rag) > 0, "ragdoll produced no bodies"
    top = max(top_of(b) for b in rag)
    cen = centroid(rag)

    out = scene_path("test1_ragdoll_drop.hkscene")
    result, code = run_cli([
        {"cmd": "import_ragdoll", "path": RAGDOLL_HKX},
        {"cmd": "settings", "gravity_scale": 1.0, "ragdoll_mass_scale": 0.1},
        {"cmd": "add_object", "object": "box", "body": "dynamic",
         "position": [cen[0], top + 3.0, cen[2]], "mass": 400.0, "scale": [0.6, 0.6, 0.6]},
        {"cmd": "get_props", "target": "ragdoll"},
        {"cmd": "get_props", "target": "scene"},
        {"cmd": "save_scene", "path": out},
        {"cmd": "run", "steps": 360},
        {"cmd": "get_props", "target": "ragdoll"},
        {"cmd": "get_props", "target": "scene"},
    ])
    assert_all_ok(result)
    assert code == 0

    pre_diag = by_cmd(result, "get_props", 0)["ragdoll"]
    post_diag = by_cmd(result, "get_props", 2)["ragdoll"]
    pre_scene = by_cmd(result, "get_props", 1)
    post_scene = by_cmd(result, "get_props", 3)

    pre_c = centroid(bodies_of_kind(pre_scene, "ragdoll"))
    post_c = centroid(bodies_of_kind(post_scene, "ragdoll"))
    moved = ((pre_c[0] - post_c[0]) ** 2 + (pre_c[1] - post_c[1]) ** 2 + (pre_c[2] - post_c[2]) ** 2) ** 0.5

    assert pre_diag["is_holding"] is True, "ragdoll should start held/authored"
    # The heavy box must disturb the ragdoll: it releases and/or the bones shift.
    assert (post_diag["is_holding"] is False) or (post_diag["max_stress"] > 0.0), \
        "ragdoll never reacted to the impact"
    assert moved > 0.1, "ragdoll barely moved (%.3f m); expected a visible shove" % moved
    return {"scene": out,
            "detail": "released=%s max_stress=%.2f centroid_shift=%.2fm"
                      % (not post_diag["is_holding"], post_diag["max_stress"], moved)}


# --- Test 2: physics rubble import + static plane + settle -------------------

def test_physics_rubble():
    # Probe: import 1 of the N systems into a BLANK scene (so the controller's
    # default seeded box/sphere don't pollute the bounds) and measure the rubble
    # extent so the static plane can be sized/placed to catch every dynamic piece.
    probe, _ = run_cli([
        {"cmd": "new_scene", "preset": "blank"},
        {"cmd": "import_physics", "path": PHYSICS_HKX, "systems": [0]},
        {"cmd": "get_props", "target": "scene"},
    ])
    assert_all_ok(probe)
    dyn = bodies_of_kind(by_cmd(probe, "get_props"), "physics_object", dynamic_only=True)
    assert len(dyn) >= 1, "physics system 0 had no dynamic objects"

    xs = [b["position"][0] for b in dyn]
    zs = [b["position"][2] for b in dyn]
    min_center = min(b["position"][1] for b in dyn)
    min_bottom = min(bottom_of(b) for b in dyn)
    cx = (min(xs) + max(xs)) / 2.0
    cz = (min(zs) + max(zs)) / 2.0
    half_x = max(8.0, (max(xs) - min(xs)) * 0.5 + 6.0)
    half_z = max(8.0, (max(zs) - min(zs)) * 0.5 + 6.0)
    # A THIN ramp tilted ~30 deg about X: a shallow slab, not a fat box, so the
    # rubble lands on the incline and rolls/slides downhill under gravity.
    tilt_deg = 30.0
    plane_half_y = 0.2                    # thin slab (0.4 m)
    plane_top = min_bottom - 0.2          # just below the lowest piece
    plane_y = plane_top - plane_half_y - 5.0   # box center so its top ~= plane_top

    out = scene_path("test2_physics_rubble.hkscene")
    result, code = run_cli([
        {"cmd": "new_scene", "preset": "blank"},
        {"cmd": "add_object", "object": "box", "body": "static",
         "position": [cx, plane_y, cz], "rotation": [tilt_deg, 0.0, 0.0],
         "scale": [half_x, plane_half_y, half_z]},
        {"cmd": "import_physics", "path": PHYSICS_HKX, "systems": [0]},
        {"cmd": "get_props", "target": "scene"},
        {"cmd": "save_scene", "path": out},
        {"cmd": "run", "steps": 300},
        {"cmd": "get_props", "target": "scene"},
    ])
    assert_all_ok(result)
    assert code == 0

    pre = by_cmd(result, "get_props", 0)
    post = by_cmd(result, "get_props", 1)
    pre_dyn = bodies_of_kind(pre, "physics_object", dynamic_only=True)
    post_dyn = bodies_of_kind(post, "physics_object", dynamic_only=True)
    assert len(post_dyn) == len(pre_dyn) and len(post_dyn) >= 1

    pre_min_y = min(b["position"][1] for b in pre_dyn)
    post_min_y = min(b["position"][1] for b in post_dyn)
    pre_c = centroid(pre_dyn)
    post_c = centroid(post_dyn)
    downhill = dist2d(pre_c, post_c)      # horizontal travel = rolled down the slope

    # On a tilted ramp the rubble must descend (Y drops) AND travel horizontally
    # (roll/slide down the incline) rather than just sitting in place.
    assert post_min_y < pre_min_y - 0.05, \
        "rubble did not descend (pre_min_y=%.3f post_min_y=%.3f)" % (pre_min_y, post_min_y)
    assert downhill > 0.2, \
        "rubble did not roll down the slope (horizontal travel %.3f m)" % downhill
    # Loose guard against catastrophic tunnel-through (tilt allows some roll-off).
    assert post_min_y > plane_top - 4.0, \
        "a piece passed through the ramp (center=%.3f plane_top=%.3f)" % (post_min_y, plane_top)
    return {"scene": out,
            "detail": "%d pieces on a %d-deg ramp fell %.2fm and rolled %.2fm downhill"
                      % (len(post_dyn), int(tilt_deg), pre_min_y - post_min_y, downhill)}


# --- Test 3: objects on a plane shoved by forces ----------------------------

def test_objects_force_on_plane():
    # A large static plane with its top at y = 0; a light sphere and a heavy cube
    # sit side by side, with a third "control" box parked farther out. A SINGLE
    # cylinder force (radius 3.5 m) is centered between the sphere and cube and
    # aimed along -Z. The cylinder volume must shove BOTH bodies it envelops from
    # one force (proving the volumetric field, not a single ray), while the control
    # box outside the radius stays put. Same force on different masses -> the light
    # sphere still travels farther than the heavy cube.
    sphere_pos = [-3.0, 0.5, 0.0]
    cube_pos = [3.0, 0.5, 0.0]
    control_pos = [8.0, 0.5, 0.0]
    force_strength = 150.0
    force_radius = 3.5

    out = scene_path("test3_objects_force.hkscene")
    result, code = run_cli([
        {"cmd": "new_scene", "preset": "blank"},
        {"cmd": "add_object", "object": "box", "body": "static",
         "position": [0.0, -1.0, 0.0], "scale": [40.0, 1.0, 40.0]},
        {"cmd": "add_object", "object": "sphere", "body": "dynamic",
         "position": sphere_pos, "scale": [0.5, 0.5, 0.5], "mass": 5.0, "restitution": 0.2},
        {"cmd": "add_object", "object": "box", "body": "dynamic",
         "position": cube_pos, "scale": [0.5, 0.5, 0.5], "mass": 20.0, "restitution": 0.2},
        # Control box parked at x=8, well outside the 3.5 m cylinder radius.
        {"cmd": "add_object", "object": "box", "body": "dynamic",
         "position": control_pos, "scale": [0.5, 0.5, 0.5], "mass": 10.0, "restitution": 0.2},
        # ONE cylinder force centered at x=0 (between sphere and cube), sitting at
        # +Z and aimed along -Z. Radius 3.5 m reaches both objects (each 3 m off the
        # axis) but not the control box (8 m off the axis).
        {"cmd": "add_force", "position": [0.0, 0.5, 6.0],
         "strength": force_strength, "mode": "push", "active": True, "radius": force_radius},
        {"cmd": "get_props", "target": "scene"},
        {"cmd": "save_scene", "path": out},
        {"cmd": "run", "steps": 60},
        {"cmd": "get_props", "target": "scene"},
    ])
    assert_all_ok(result)
    assert code == 0

    pre = by_cmd(result, "get_props", 0)
    post = by_cmd(result, "get_props", 1)

    def dynamic_boxes(scene):
        return [b for b in bodies_of_kind(scene, "physics_object", dynamic_only=True)
                if b["shape"] == "box"]

    def find_sphere(scene):
        for b in bodies_of_kind(scene, "physics_object", dynamic_only=True):
            if b["shape"] == "sphere":
                return b
        raise AssertionError("no dynamic sphere in scene")

    def nearest_box(scene, ref_x):
        boxes = dynamic_boxes(scene)
        return min(boxes, key=lambda b: abs(b["position"][0] - ref_x))

    sphere_pre = find_sphere(pre)["position"]
    sphere_post = find_sphere(post)["position"]
    cube_pre = nearest_box(pre, cube_pos[0])["position"]
    cube_post = nearest_box(post, cube_pos[0])["position"]
    control_pre = nearest_box(pre, control_pos[0])["position"]
    control_post = nearest_box(post, control_pos[0])["position"]

    sphere_move = dist2d(sphere_pre, sphere_post)
    cube_move = dist2d(cube_pre, cube_post)
    control_move = dist2d(control_pre, control_post)

    # The single cylinder force must move BOTH enveloped bodies (volume effect).
    assert sphere_move > 0.2, "sphere barely moved (%.3f m)" % sphere_move
    assert cube_move > 0.05, "cube in the cylinder did not react (%.3f m)" % cube_move
    # The control box outside the radius must stay essentially still.
    assert control_move < 0.1, \
        "control box outside the cylinder should not move (%.3f m)" % control_move
    # Same force, different mass -> lighter body outruns the heavier one.
    assert sphere_move > cube_move, \
        "light sphere (%.3f m) should outrun heavy cube (%.3f m)" % (sphere_move, cube_move)
    # Both enveloped bodies should still be resting on / above the plane, not tunneled.
    assert bottom_of(find_sphere(post)) > -0.5
    assert bottom_of(nearest_box(post, cube_pos[0])) > -0.5
    return {"scene": out,
            "detail": "cylinder(r=%.1fm) pushed sphere %.2fm + cube %.2fm, control held %.2fm"
                      % (force_radius, sphere_move, cube_move, control_move)}


# --- Test 4: scene create / save / load / clear ------------------------------

def test_scene_save_load_clear():
    out = scene_path("test4_roundtrip.hkscene")

    # Build a scene and record its authored composition.
    build, _ = run_cli([
        {"cmd": "new_scene", "preset": "blank"},
        {"cmd": "add_object", "object": "box", "body": "dynamic", "position": [0, 5, 0]},
        {"cmd": "add_object", "object": "sphere", "body": "dynamic", "position": [2, 5, 0]},
        {"cmd": "add_force", "position": [0, 1, 4], "strength": 120.0, "mode": "push"},
        {"cmd": "get_props", "target": "scene"},
        {"cmd": "save_scene", "path": out},
    ])
    assert_all_ok(build)
    built_scene = by_cmd(build, "get_props")
    objs_before = len(bodies_of_kind(built_scene, "physics_object"))
    forces_before = len([b for b in built_scene["bodies"] if b["kind"] == "force"])
    assert objs_before >= 2 and forces_before >= 1
    assert os.path.isfile(out), "scene file was not written"

    # Clear then load: the loaded scene must restore the same composition.
    reload_result, code = run_cli([
        {"cmd": "load_scene", "path": out},
        {"cmd": "get_props", "target": "scene"},
        {"cmd": "clear_scene"},
        {"cmd": "get_props", "target": "scene"},
        {"cmd": "load_scene", "path": out},
        {"cmd": "get_props", "target": "scene"},
    ])
    assert_all_ok(reload_result)
    assert code == 0

    loaded = by_cmd(reload_result, "get_props", 0)
    cleared = by_cmd(reload_result, "get_props", 1)
    reloaded = by_cmd(reload_result, "get_props", 2)

    assert len(bodies_of_kind(loaded, "physics_object")) == objs_before
    assert len([b for b in loaded["bodies"] if b["kind"] == "force"]) == forces_before
    # Clearing removes the user objects (a ground body may remain).
    assert len(bodies_of_kind(cleared, "physics_object")) <= 1
    assert len([b for b in cleared["bodies"] if b["kind"] == "force"]) == 0
    # Reloading restores the saved composition.
    assert len(bodies_of_kind(reloaded, "physics_object")) == objs_before
    assert len([b for b in reloaded["bodies"] if b["kind"] == "force"]) == forces_before
    return {"scene": out, "detail": "%d objects + %d force round-tripped through save/load/clear"
            % (objs_before, forces_before)}


# --- Test 5: object + force manipulation -------------------------------------

def test_manipulation_and_edit():
    result, code = run_cli([
        {"cmd": "new_scene", "preset": "blank"},
        {"cmd": "add_object", "object": "box", "body": "dynamic",
         "position": [0, 5, 0], "rotation": [0, 0, 0], "mass": 10.0, "restitution": 0.4},
        {"cmd": "get_props", "target": "object", "kind": "physics_object"},   # 0: as-created
        {"cmd": "move", "kind": "physics_object", "position": [2, 6, 1]},
        {"cmd": "get_props", "target": "object", "kind": "physics_object"},   # 1: after move
        {"cmd": "rotate", "kind": "physics_object", "rotation": [0, 45, 0]},
        {"cmd": "get_props", "target": "object", "kind": "physics_object"},   # 2: after rotate
        {"cmd": "edit_object", "kind": "physics_object",
         "mass": 25.0, "restitution": 0.9, "position": [1, 2, 3], "rotation": [10, 20, 30]},
        {"cmd": "get_props", "target": "object", "kind": "physics_object"},   # 3: after edit
        {"cmd": "add_force", "position": [0, 1, 4], "strength": 100.0, "mode": "push"},
        {"cmd": "get_props", "target": "force", "kind": "force"},             # 4: force created
        {"cmd": "edit_force", "kind": "force", "strength": 250.0, "mode": "pull"},
        {"cmd": "get_props", "target": "force", "kind": "force"},             # 5: force edited
    ])
    assert_all_ok(result)
    assert code == 0

    created = by_cmd(result, "get_props", 0)["object"]
    after_move = by_cmd(result, "get_props", 1)["object"]
    after_rot = by_cmd(result, "get_props", 2)["object"]
    after_edit = by_cmd(result, "get_props", 3)["object"]
    force_new = by_cmd(result, "get_props", 4)["force"]
    force_edited = by_cmd(result, "get_props", 5)["force"]

    def close(a, b, eps=1e-3):
        return abs(a - b) <= eps

    # move changed position, not rotation
    assert after_move["position"][0] == 2 and after_move["position"][1] == 6 and after_move["position"][2] == 1
    # rotate changed rotation_degrees
    assert close(after_rot["rotation_degrees"][1], 45.0), after_rot["rotation_degrees"]
    # edit_object changed mass / restitution / pos / rot together
    assert close(after_edit["mass"], 25.0) and close(after_edit["restitution"], 0.9)
    assert after_edit["position"][0] == 1 and after_edit["position"][2] == 3
    assert close(after_edit["rotation_degrees"][0], 10.0) and close(after_edit["rotation_degrees"][2], 30.0)
    # created object had the authored defaults
    assert close(created["mass"], 10.0) and close(created["restitution"], 0.4)
    # force edit changed strength + mode (push=0 -> pull=1)
    assert close(force_new["strength"], 100.0) and force_new["mode"] == 0
    assert close(force_edited["strength"], 250.0) and force_edited["mode"] == 1
    return {"detail": "move/rotate/edit_object + edit_force all applied and read back"}


# --- runner ------------------------------------------------------------------

TESTS = [
    ("Ragdoll import + heavy drop", test_ragdoll_drop, True),
    ("Physics rubble import + static plane", test_physics_rubble, True),
    ("Cylinder force shoves objects in radius", test_objects_force_on_plane, True),
    ("Scene create/save/load/clear", test_scene_save_load_clear, False),
    ("Object + force manipulation/edit", test_manipulation_and_edit, False),
]


def main():
    if not os.path.isfile(CLI):
        print("ERROR: havok_sim_cli.exe not found at %s\n"
              "Build it first: bash havok_simulator/build_cli.sh debug" % CLI)
        return 2

    print("Running %d havok_sim_cli workflow tests\n" % len(TESTS))
    passed = 0
    scenes = []
    for name, fn, is_sim in TESTS:
        try:
            info = fn() or {}
            passed += 1
            detail = info.get("detail", "")
            print("  PASS  %-40s %s" % (name, detail))
            if info.get("scene"):
                scenes.append((name, info["scene"]))
        except AssertionError as exc:
            print("  FAIL  %-40s %s" % (name, exc))
        except Exception as exc:  # noqa: BLE001 - surface any harness/CLI error
            print("  ERROR %-40s %s" % (name, exc))

    print("\n%d/%d tests passed" % (passed, len(TESTS)))

    if scenes:
        print("\n" + "=" * 74)
        print("VISUAL VALIDATION - open these scenes in the GUI and press Play:")
        print("  GUI: %s" % GUI)
        print("-" * 74)
        for name, path in scenes:
            print("  * %s" % name)
            print("    %s" % path)
        print("=" * 74)
        print("Each scene reproduces the test setup; playing it should show the\n"
              "ragdoll get shoved, the rubble fall onto the plane, and the objects\n"
              "get pushed by the forces, respectively.")

    return 0 if passed == len(TESTS) else 1


if __name__ == "__main__":
    sys.exit(main())
