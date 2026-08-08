"""Simbox / Coverbox tests (plan IDs S-1..S-2)."""

from __future__ import annotations

CATEGORY = "model/simbox_coverbox"

_TODO = "scaffold ; not implemented yet"

_SEEDS = ("power_armour_common", "chaos_heavy_bolter_turret")
_TOL = 1e-2


def _available_seeds(ctx):
    from framework import model_roundtrip

    return [
        (s, cfg)
        for s in _SEEDS
        if (cfg := model_roundtrip.load_seed_config(ctx.config.test_data_dir, s)) is not None
    ]


def test_simbox_coverbox_roundtrip(ctx):
    """S-1: create simbox/coverbox -> export -> import; dims + position preserved."""
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore

    from dow2_tools.model import utils as model_utils  # type: ignore
    from framework import blender_env, fixtures

    ctx.require_data()
    seeds = _available_seeds(ctx)
    if not seeds:
        ctx.skip("no test-data seeds present (run: python tests/run.py --build-test-data)")
    seed, cfg = seeds[0]
    seed_dir = ctx.config.test_data_dir / seed

    boxes = {
        "simbox": (Vector((0.3, -0.4, 1.1)), Vector((1.2, 0.8, 1.5)), True),
        "coverbox": (Vector((0.1, 0.2, 0.9)), Vector((2.0, 1.0, 0.5)), False),
    }
    problems: list[str] = []

    with fixtures.scratch_dir(ctx.config, f"simbox_{seed}") as scratch:
        with fixtures.staged_textures(ctx.config, cfg.get("textures", {}), seed_dir):
            blender_env.reset_scene()
            blender_env.import_glb(seed_dir / cfg["glb"])
            blender_env.apply_config_to_scene(cfg)

            armature = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
            for box_type, (loc, scale, maintain) in boxes.items():
                model_utils.create_or_update_bounding_box_object(
                    bpy.context.scene, box_type, model_name="",
                    location=loc, scale=scale, maintain_contour=maintain, armature_obj=armature,
                )

            out_model = scratch / f"{seed}.model"
            result = blender_env.export_model(out_model, export_simbox=True, export_coverbox=True)
            if "FINISHED" not in result:
                ctx.fail(f"{seed}: export failed ({result})")

            for box_type in boxes:
                if not (scratch / f"{seed}.{box_type}").is_file():
                    problems.append(f"{seed}: no .{box_type} lua written")

            blender_env.reset_scene()
            imported = blender_env.import_model(out_model, import_simbox=True, import_coverbox=True)
            if "FINISHED" not in imported:
                ctx.fail(f"{seed}: re-import failed ({imported})")

            for box_type, (loc, scale, _m) in boxes.items():
                obj = model_utils.find_bounding_box_object(bpy.context.scene, box_type, "")
                if obj is None:
                    problems.append(f"{seed}: {box_type} not imported")
                    continue
                if (obj.location - loc).length > _TOL:
                    problems.append(f"{seed}: {box_type} location {tuple(obj.location)} != {tuple(loc)}")
                if (obj.scale - scale).length > _TOL:
                    problems.append(f"{seed}: {box_type} scale {tuple(obj.scale)} != {tuple(scale)}")

    if problems:
        ctx.fail(" | ".join(problems))


def test_simbox_coverbox_naming(ctx):
    """S-2: naming conventions + object props; legacy all-caps fallback detection."""
    import bpy  # type: ignore

    from dow2_tools.model import utils as model_utils  # type: ignore
    from framework import blender_env

    blender_env.reset_scene()

    problems: list[str] = []
    created = []

    def _empty(name: str):
        obj = bpy.data.objects.new(name, None)
        bpy.context.scene.collection.objects.link(obj)
        created.append(obj)
        return obj

    conv_sim = _empty("DoW2_Simbox::power_armour_common")
    conv_cov = _empty("DoW2_Coverbox::power_armour_common")
    legacy_sim = _empty("SIMBOX")
    plain = _empty("just_an_empty")

    for obj, label in ((conv_sim, "convention simbox"), (conv_cov, "convention coverbox"), (legacy_sim, "legacy SIMBOX")):
        if not model_utils.is_bounding_box_object(obj):
            problems.append(f"{label} not detected as bounding box")
    if model_utils.is_bounding_box_object(plain):
        problems.append("plain empty wrongly detected as bounding box")

    if model_utils.find_bounding_box_object(bpy.context.scene, "simbox", "power_armour_common") is not conv_sim:
        problems.append("find_bounding_box_object did not resolve convention simbox by name")
    if model_utils.find_bounding_box_object(bpy.context.scene, "coverbox", "power_armour_common") is not conv_cov:
        problems.append("find_bounding_box_object did not resolve convention coverbox by name")

    for obj in created:
        bpy.data.objects.remove(obj, do_unlink=True)

    if problems:
        ctx.fail(" | ".join(problems))

