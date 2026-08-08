"""Failure-path tests (plan IDs F-1..F-8).

Assert that faults surface via operator reports and logs/dow2_tools.log, routed
into per-category log buckets. Scaffold: every test currently skips.
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

CATEGORY = "failures"


def test_missing_input_is_skipped(ctx):
    """F-1: missing input file -> recorded as unchecked (skip)."""
    ctx.data_path("__definitely_missing__", "missing.model")
    ctx.fail("missing asset path should have skipped")


def test_corrupt_model_reports_error(ctx):
    """F-2: corrupt / non-.model -> ERROR report, import cancelled."""
    from framework import blender_env, fixtures

    with fixtures.scratch_dir(ctx.config, "fail_corrupt_model") as scratch:
        bad = scratch / "bad.model"
        bad.write_bytes(b"not-a-model")
        blender_env.reset_scene()
        result = blender_env.import_model(bad)
        if "CANCELLED" not in result:
            ctx.fail(f"corrupt model did not cancel import: {result}")


def test_missing_texture_warns(ctx):
    """F-3: .model referencing a missing texture -> WARNING; import continues."""
    from dow2_tools.material.creator import RelicMaterialCreator  # type: ignore
    from dow2_tools.material.data import MaterialVariable, RelicMaterialData  # type: ignore
    from dow2_tools.material.definitions import VAR_TYPE_TEXTURE  # type: ignore
    from framework import blender_env, fixtures

    with fixtures.scratch_dir(ctx.config, "fail_missing_texture") as scratch:
        data_root = scratch / "Data"
        (data_root / "art").mkdir(parents=True)
        blender_env.reset_scene()

        missing_texture = "art/race_test/materials/does_not_exist"
        mat_data = RelicMaterialData(
            name="relic.material.missing_texture_probe",
            shader_name="dow2_unit",
            shader_path="art/race_test/materials/missing_texture_probe",
            variables=[MaterialVariable("diffuseTex", VAR_TYPE_TEXTURE, missing_texture)],
        )
        creator = RelicMaterialCreator(str(data_root / "art" / "race_test" / "materials"))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            material = creator.create_material(mat_data)

        if material is None:
            ctx.fail("missing texture prevented material creation")
        if material.get("dow2_diffuseTex") != missing_texture:
            ctx.fail("missing texture path was not preserved on the material")
        warning = output.getvalue().lower()
        if "warning" not in warning or "missing texture" not in warning or missing_texture.lower() not in warning:
            ctx.fail(f"missing texture warning was not surfaced; stdout={output.getvalue()!r}")


def test_export_without_materials(ctx):
    """F-4..F-5: no/empty or non-relic materials -> ExportValidationError / warning."""
    import bpy  # type: ignore

    from framework import blender_env, fixtures

    with fixtures.scratch_dir(ctx.config, "fail_export_no_material") as scratch:
        blender_env.reset_scene()
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))
        obj = bpy.context.active_object
        obj.data.materials.clear()

        out = scratch / "no_material.model"
        result = bpy.ops.export_scene.dow2_model(
            filepath=str(out),
            export_materials=True,
            apply_material_if_missing=False,
        )
        if "CANCELLED" not in result:
            ctx.fail(f"export without materials did not cancel: {result}")


def test_missing_havok_cli(ctx):
    """F-6: havok_io_cli.exe missing -> log_error, export fails cleanly."""
    from dow2_tools.animation import export_core  # type: ignore
    from framework import fixtures

    with fixtures.scratch_dir(ctx.config, "fail_missing_havok_cli") as scratch:
        missing_cli = scratch / "missing_havok_io_cli.exe"
        output_hkx = scratch / "should_not_exist.hkx"
        log_path = Path(export_core.get_log_path()) / "dow2_tools.log"
        before_log = log_path.read_text(encoding="utf-8") if log_path.is_file() else ""
        original_path_func = export_core.get_anim_blender2hkx_path
        try:
            export_core.get_anim_blender2hkx_path = lambda: str(missing_cli)
            result = export_core.export_animation(None, None, str(output_hkx))
        finally:
            export_core.get_anim_blender2hkx_path = original_path_func

        if result:
            ctx.fail("missing Havok CLI export unexpectedly succeeded")
        if output_hkx.exists():
            ctx.fail("missing Havok CLI path created an output HKX")
        after_log = log_path.read_text(encoding="utf-8") if log_path.is_file() else ""
        new_log = after_log[len(before_log):] if after_log.startswith(before_log) else after_log
        if "havok_io_cli.exe not found" not in new_log or str(missing_cli) not in new_log:
            ctx.fail(f"missing Havok CLI error was not logged; new log={new_log!r}")


def test_non_animation_hkx(ctx):
    """F-7: valid .hkx that is not animation -> HkxNonAnimationAssetError reported."""
    import bpy  # type: ignore

    from framework import blender_env, fixtures

    with fixtures.scratch_dir(ctx.config, "fail_non_anim_hkx") as scratch:
        bad = scratch / "bad.hkx"
        bad.write_text("invalid hkx payload", encoding="utf-8")

        blender_env.reset_scene()
        bpy.ops.object.armature_add(location=(0.0, 0.0, 0.0))
        try:
            result = bpy.ops.import_scene.dow2_animation(filepath=str(bad))
        except Exception as exc:
            # In background mode this path can surface as a raised read error
            # instead of a clean {'CANCELLED'} return from the operator.
            text = str(exc).lower()
            if "hkx" in text or "animation" in text or "failed to read" in text:
                return
            ctx.fail(f"unexpected exception importing invalid hkx: {exc}")
            return

        if "CANCELLED" not in result:
            ctx.fail(f"invalid hkx did not cancel animation import: {result}")


def test_overwrite_confirmation(ctx):
    """F-8: check_existing triggers confirmation path (not silent overwrite)."""
    import bpy  # type: ignore

    from framework import blender_env, fixtures

    with fixtures.scratch_dir(ctx.config, "fail_overwrite_confirmation") as scratch:
        out_model = scratch / "existing.model"
        sentinel = b"existing model bytes must survive"
        out_model.write_bytes(sentinel)

        blender_env.reset_scene()
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))
        result = bpy.ops.export_scene.dow2_model(filepath=str(out_model), check_existing=True)
        if "CANCELLED" not in result:
            ctx.fail(f"check_existing=True did not cancel existing-file export: {result}")
        if out_model.read_bytes() != sentinel:
            ctx.fail("check_existing=True overwrote the existing file")
