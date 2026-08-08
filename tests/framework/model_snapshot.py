"""Comprehensive model snapshot + pairwise comparator (runs inside Blender).

``capture()`` records a plain-data snapshot of the current scene's DoW2 model:
per (state, lod, material) group it stores world-space vertex positions,
per-vertex normals and bone-weight maps; plus material params, bone rest
hierarchy, and markers. ``compare()`` diffs two snapshots.

Because the DoW2 export/import welds and reorders vertices, there is no stable
per-vertex index mapping. ``compare()`` therefore matches vertices by *world
position* via a KD-tree (nearest neighbour), then checks that each matched pair
agrees on normal direction and bone weights within tolerance. Materials, bones
and markers are compared by name/value (float tolerance on transforms).

Shared by the §14 round-trip and the MODEL-export tests (and reusable by the
import golden tests).
"""

from __future__ import annotations

import math

# -- tolerances (tunable) -------------------------------------------------
POS_FRAC = 0.005          # nearest-neighbour distance <= 0.5% of bbox diagonal
NORMAL_DEG = 8.0          # max normal angle deviation
WEIGHT_DELTA = 0.05       # max per-bone weight delta
PASS_FRAC = 0.99          # >= 99% of vertices must match within tolerance
PARAM_TOL = 1e-4          # numeric material-param tolerance


# =========================================================================
# capture (needs bpy)
# =========================================================================
def capture() -> dict:
    import bpy  # type: ignore

    from .blender_env import _group_lod_of

    meshes: dict = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        mesh = obj.data
        state, lod = _group_lod_of(obj)
        mat = mesh.materials[0].name if mesh.materials and mesh.materials[0] else None
        key = f"{state}|{lod}|{mat}"
        group = meshes.setdefault(
            key,
            {"material": mat, "positions": [], "normals": [], "weights": [],
             "triangles": 0, "uv_layers": 0, "objects": 0},
        )

        mw = obj.matrix_world
        nmat = mw.to_3x3()
        try:
            nmat = nmat.inverted().transposed()
        except ValueError:
            pass
        vg_names = {i: vg.name for i, vg in enumerate(obj.vertex_groups)}
        custom_normals = _per_vertex_custom_normals(mesh)

        for v in mesh.vertices:
            co = mw @ v.co
            group["positions"].append((co.x, co.y, co.z))
            local_n = custom_normals.get(v.index, v.normal)
            n = (nmat @ local_n)
            if n.length > 0:
                n = n.normalized()
            group["normals"].append((n.x, n.y, n.z))
            weights = {}
            for ge in v.groups:
                name = vg_names.get(ge.group)
                if name and ge.weight > 0.0:
                    weights[name] = ge.weight
            group["weights"].append(weights)

        group["triangles"] += sum(max(len(p.vertices) - 2, 0) for p in mesh.polygons)
        group["uv_layers"] = max(group["uv_layers"], len(mesh.uv_layers))
        group["objects"] += 1

    return {
        "meshes": meshes,
        "materials": _capture_materials(),
        "bones": _capture_bones(),
        "markers": _capture_markers(),
    }


def _per_vertex_custom_normals(mesh) -> dict:
    """Average the split (custom) loop normals per vertex.

    DoW2 stores one normal per vertex as a *custom* normal; ``vertex.normal`` is
    the auto-computed normal and ignores it, so we read the loop normals.
    """
    from mathutils import Vector  # type: ignore

    accum: dict = {}
    try:
        loops = mesh.loops
        for loop in loops:
            vec = loop.normal
            entry = accum.get(loop.vertex_index)
            if entry is None:
                accum[loop.vertex_index] = Vector((vec[0], vec[1], vec[2]))
            else:
                entry += Vector((vec[0], vec[1], vec[2]))
    except (AttributeError, RuntimeError):
        return {}
    for idx, vec in accum.items():
        if vec.length > 0:
            accum[idx] = vec.normalized()
    return accum


def _capture_materials() -> dict:
    import bpy  # type: ignore

    out: dict = {}
    for mat in bpy.data.materials:
        dow2_keys = [k for k in mat.keys() if k.startswith("dow2_")]
        if not dow2_keys:
            continue
        params: dict = {}
        for key in dow2_keys:
            short = key[len("dow2_"):]
            if short in ("shader", "shader_path"):
                continue
            params[short] = _jsonify(mat[key])
        out[mat.name] = {
            "shader": mat.get("dow2_shader", ""),
            "shader_path": mat.get("dow2_shader_path", ""),
            "params": params,
        }
    return out


def _capture_bones() -> dict:
    import bpy  # type: ignore

    out: dict = {}
    for obj in bpy.data.objects:
        if obj.type != "ARMATURE":
            continue
        mw = obj.matrix_world
        for bone in obj.data.bones:
            head = mw @ bone.head_local
            out[bone.name] = {
                "parent": bone.parent.name if bone.parent else None,
                "head": (head.x, head.y, head.z),
            }
    return out


def _capture_markers() -> dict:
    import bpy  # type: ignore

    out: dict = {}
    for obj in bpy.data.objects:
        if obj.type != "EMPTY":
            continue
        loc = obj.matrix_world.translation
        out[obj.name] = {
            "parent": obj.parent.name if obj.parent else None,
            "parent_bone": obj.parent_bone or None,
            "loc": (loc.x, loc.y, loc.z),
        }
    return out


def _jsonify(value):
    if hasattr(value, "to_list"):
        return value.to_list()
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    if isinstance(value, bool):
        return int(value)
    try:
        if isinstance(value, float):
            return value
        if isinstance(value, int):
            return value
        return str(value)
    except Exception:
        return str(value)


# =========================================================================
# compare (needs mathutils.kdtree; runs inside Blender)
# =========================================================================
def compare(before: dict, after: dict) -> list[tuple[str, str]]:
    """Return a list of ``(category, message)`` problems (empty == match)."""
    problems: list[tuple[str, str]] = []
    problems += _compare_meshes(before.get("meshes", {}), after.get("meshes", {}))
    problems += _compare_materials(before.get("materials", {}), after.get("materials", {}))
    problems += _compare_bones(before.get("bones", {}), after.get("bones", {}))
    problems += _compare_markers(before.get("markers", {}), after.get("markers", {}))
    return problems


def _bbox_diagonal(positions: list) -> float:
    if not positions:
        return 0.0
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]
    zs = [p[2] for p in positions]
    dx = max(xs) - min(xs)
    dy = max(ys) - min(ys)
    dz = max(zs) - min(zs)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _angle_deg(a, b) -> float:
    dot = a[0] * b[0] + a[1] * b[1] + b[2] * a[2]
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.acos(dot))


def _dominant_bone(weights: dict):
    return max(weights, key=weights.get) if weights else None


def _compare_meshes(before: dict, after: dict) -> list:
    from mathutils.kdtree import KDTree  # type: ignore

    problems: list = []
    for key in sorted(set(before) | set(after)):
        if key not in after:
            problems.append(("model_mesh", f"group '{key}' missing after round-trip"))
            continue
        if key not in before:
            problems.append(("model_mesh", f"unexpected group '{key}' after round-trip"))
            continue

        b, a = before[key], after[key]
        if b["triangles"] != a["triangles"]:
            problems.append(
                ("model_mesh", f"{key}: triangles {a['triangles']} != {b['triangles']}")
            )
        if b["uv_layers"] != a["uv_layers"]:
            problems.append(
                ("model_mesh", f"{key}: uv layers {a['uv_layers']} != {b['uv_layers']}")
            )

        a_pos = a["positions"]
        if not a_pos or not b["positions"]:
            continue

        kd = KDTree(len(a_pos))
        for i, p in enumerate(a_pos):
            kd.insert(p, i)
        kd.balance()

        pos_tol = POS_FRAC * (_bbox_diagonal(b["positions"]) or 1.0)
        total = len(b["positions"])
        matched = pos_fail = normal_fail = weight_fail = 0

        for i, p in enumerate(b["positions"]):
            # At hard edges / UV seams several vertices share a position but carry
            # different normals; gather every co-located candidate and treat the
            # source vertex as preserved if any candidate agrees.
            hits = kd.find_range(p, pos_tol)
            if not hits:
                pos_fail += 1
                continue
            matched += 1
            bn, bw = b["normals"][i], b["weights"][i]
            if not any(_angle_deg(bn, a["normals"][idx]) <= NORMAL_DEG for _c, idx, _d in hits):
                normal_fail += 1
            if not any(_weights_match(bw, a["weights"][idx]) for _c, idx, _d in hits):
                weight_fail += 1

        if total and matched / total < PASS_FRAC:
            problems.append(
                ("model_mesh", f"{key}: only {matched}/{total} verts matched within {pos_tol:.4f}")
            )
        if matched and normal_fail / matched > (1.0 - PASS_FRAC):
            problems.append(
                ("model_normal", f"{key}: {normal_fail}/{matched} normals exceed {NORMAL_DEG}deg")
            )
        if matched and weight_fail / matched > (1.0 - PASS_FRAC):
            problems.append(
                ("model_weight", f"{key}: {weight_fail}/{matched} verts weight-mismatch")
            )
    return problems


def _weights_match(wb: dict, wa: dict) -> bool:
    if not wb and not wa:
        return True
    if _dominant_bone(wb) != _dominant_bone(wa):
        return False
    for bone in set(wb) | set(wa):
        if abs(wb.get(bone, 0.0) - wa.get(bone, 0.0)) > WEIGHT_DELTA:
            return False
    return True


def _norm_param(value):
    """Normalize a material param value for tolerant comparison."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, str):
        v = value.replace("\\", "/").lower().strip()
        if v.endswith(".dds"):
            v = v[:-4]
        return v
    if isinstance(value, (list, tuple)):
        return [_norm_param(v) for v in value]
    return value


def _params_equal(vb, va) -> bool:
    vb, va = _norm_param(vb), _norm_param(va)
    if isinstance(vb, list) and isinstance(va, list):
        if len(vb) != len(va):
            return False
        return all(_params_equal(x, y) for x, y in zip(vb, va))
    if isinstance(vb, (int, float)) and isinstance(va, (int, float)):
        return abs(float(vb) - float(va)) <= PARAM_TOL
    return vb == va


def _compare_materials(before: dict, after: dict) -> list:
    problems: list = []
    for name in sorted(before):
        if name not in after:
            problems.append(("material_param", f"material '{name}' missing after round-trip"))
            continue
        b, a = before[name], after[name]
        if b["shader"] != a["shader"]:
            problems.append(
                ("material_param", f"{name}: shader '{a['shader']}' != '{b['shader']}'")
            )
        for pkey in sorted(b["params"]):
            if pkey not in a["params"]:
                problems.append(("material_param", f"{name}: param '{pkey}' missing after"))
                continue
            if not _params_equal(b["params"][pkey], a["params"][pkey]):
                category = "model_texture" if _looks_like_texture(pkey) else "material_param"
                problems.append(
                    (category, f"{name}.{pkey}: {a['params'][pkey]!r} != {b['params'][pkey]!r}")
                )
    return problems


def _looks_like_texture(pkey: str) -> bool:
    low = pkey.lower()
    return low.endswith("tex") or low.endswith("map")


def _compare_bones(before: dict, after: dict) -> list:
    problems: list = []
    missing = set(before) - set(after)
    if missing:
        problems.append(("model_bone", f"bones missing after round-trip: {sorted(missing)}"))

    shared = sorted(set(before) & set(after))
    tol = POS_FRAC * (_bbox_diagonal([b["head"] for b in before.values()]) or 1.0)
    for name in shared:
        b, a = before[name], after[name]
        if b["parent"] != a["parent"]:
            problems.append(
                ("model_bone", f"{name}: parent '{a['parent']}' != '{b['parent']}'")
            )
        if _distance(b["head"], a["head"]) > tol:
            problems.append(
                ("model_bone", f"{name}: head moved {_distance(b['head'], a['head']):.5f} > {tol:.5f}")
            )
    return problems


def _compare_markers(before: dict, after: dict) -> list:
    problems: list = []
    tol = POS_FRAC * (_bbox_diagonal([m["loc"] for m in before.values()]) or 1.0)
    for name in sorted(before):
        if name not in after:
            problems.append(("model_marker", f"marker '{name}' missing after round-trip"))
            continue
        b, a = before[name], after[name]
        if b["parent_bone"] != a["parent_bone"]:
            problems.append(
                ("model_marker", f"{name}: parent bone '{a['parent_bone']}' != '{b['parent_bone']}'")
            )
        if _distance(b["loc"], a["loc"]) > tol:
            problems.append(
                ("model_marker", f"{name}: moved {_distance(b['loc'], a['loc']):.5f} > {tol:.5f}")
            )
    return problems


def _distance(a, b) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)
