"""Material tests ; part of the model import/export pipeline (plan IDs MAT-1..MAT-7)."""

from __future__ import annotations

CATEGORY = "material"

_SEEDS = ("power_armour_common", "chaos_heavy_bolter_turret")


def _available_seeds(ctx):
    from framework import model_roundtrip

    return [
        (s, cfg)
        for s in _SEEDS
        if (cfg := model_roundtrip.load_seed_config(ctx.config.test_data_dir, s)) is not None
    ]


def _norm(path: str) -> str:
    v = str(path).replace("\\", "/").lower().strip()
    return v[:-4] if v.endswith(".dds") else v


def test_shader_presets(ctx):
    """MAT-1: each shader preset populates its expected TEXTURE_SLOTS + params."""
    import bpy  # type: ignore

    from dow2_tools.material.definitions import BOOL_PARAMS, FLOAT_PARAMS, INT_PARAMS
    from dow2_tools.material.presets import SHADER_PRESET_CONFIG
    from framework import blender_env

    blender_env.reset_scene()
    problems: list[str] = []
    bool_names = {name for name, _label in BOOL_PARAMS}
    int_names = {name for name, _label in INT_PARAMS}
    float_names = {name for name, _label, _default in FLOAT_PARAMS}
    all_param_names = bool_names | int_names | float_names

    for preset, config in SHADER_PRESET_CONFIG.items():
        mat_name = f"relic.material.__preset_{preset}"
        result = bpy.ops.dow2.create_relic_material(material_name=mat_name, shader_preset=preset)
        if "FINISHED" not in result:
            problems.append(f"{preset}: create operator returned {result}")
            continue
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            problems.append(f"{preset}: material not created")
            continue
        if mat.get("dow2_shader") != preset:
            problems.append(f"{preset}: dow2_shader={mat.get('dow2_shader')!r}")
        if not mat.get("dow2_is_relic_material", False):
            problems.append(f"{preset}: dow2_is_relic_material not set")

        shader_vars = str(mat.get("dow2_shader_vars", "") or "")
        for slot in config.get("textures", []):
            if f"dow2_{slot}" not in mat:
                problems.append(f"{preset}: missing texture prop {slot}")
            if slot not in shader_vars.split(","):
                problems.append(f"{preset}: {slot} missing from dow2_shader_vars")
        for param in all_param_names:
            if f"dow2_{param}" not in mat:
                problems.append(f"{preset}: missing param prop {param}")
        for param, expected in config.get("params", {}).items():
            got = mat.get(f"dow2_{param}")
            if got != expected:
                problems.append(f"{preset}: {param}={got!r}, expected {expected!r}")

    if problems:
        ctx.fail(" | ".join(problems))


def test_texture_path_resolution(ctx):
    """MAT-2: resolve textures relative to mod root (walk to art/); .dds appended when missing."""
    from dow2_tools.material.creator import RelicMaterialCreator
    from framework import fixtures

    with fixtures.scratch_dir(ctx.config, "material_path_resolution") as scratch:
        data_root = scratch / "Codex" / "Data"
        texture_dir = data_root / "art" / "race_test" / "materials"
        texture_dir.mkdir(parents=True, exist_ok=True)
        texture = texture_dir / "unit_diffuse.dds"
        texture.write_bytes(b"DDS ")

        nested_shader_path = data_root / "art" / "race_test" / "materials" / "shaders"
        nested_shader_path.mkdir(parents=True, exist_ok=True)
        creator = RelicMaterialCreator(str(nested_shader_path))

        problems: list[str] = []
        if creator.game_data_path != str(data_root):
            problems.append(f"game_data_path={creator.game_data_path!r}, expected {str(data_root)!r}")

        expected = str(texture.resolve()).replace("\\", "/").lower()
        without_ext = creator.find_texture_file("art/race_test/materials/unit_diffuse")
        with_ext = creator.find_texture_file("art/race_test/materials/unit_diffuse.dds")
        with_backslashes = creator.find_texture_file(r"art\race_test\materials\unit_diffuse")
        missing = creator.find_texture_file("art/race_test/materials/missing_texture")
        for label, got in (("without_ext", without_ext), ("with_ext", with_ext), ("with_backslashes", with_backslashes)):
            normalized = str(got or "").replace("\\", "/").lower()
            if normalized != expected:
                problems.append(f"{label}: {got!r} != {expected!r}")
        if missing is not None:
            problems.append(f"missing texture resolved unexpectedly: {missing!r}")

    if problems:
        ctx.fail(" | ".join(problems))


def test_shader_node_graphs(ctx):
    """MAT-6: supported shader presets build an approximate node graph with texture inputs."""
    import bpy  # type: ignore

    from dow2_tools.material.presets import SHADER_PRESET_CONFIG
    from dow2_tools.material.service import configure_relic_material
    from framework import blender_env

    blender_env.reset_scene()
    problems: list[str] = []

    for preset, config in SHADER_PRESET_CONFIG.items():
        mat = bpy.data.materials.new(f"relic.material.__graph_{preset}")
        shader_vars = list(config.get("textures", []))
        configure_relic_material(
            bpy.context,
            mat,
            shader_name=preset,
            shader_vars=shader_vars,
            param_overrides=config.get("params", {}),
        )

        if not mat.use_nodes or mat.node_tree is None:
            problems.append(f"{preset}: node tree was not enabled")
            continue
        nodes = list(mat.node_tree.nodes)
        node_types = {node.bl_idname for node in nodes}
        if "ShaderNodeOutputMaterial" not in node_types:
            problems.append(f"{preset}: missing Material Output node")
        if "ShaderNodeBsdfPrincipled" not in node_types:
            problems.append(f"{preset}: missing Principled BSDF node")

        image_labels = {str(node.label or node.name) for node in nodes if node.bl_idname == "ShaderNodeTexImage"}
        for slot in shader_vars:
            if slot not in image_labels:
                problems.append(f"{preset}: missing image texture node for {slot}")

        linked_surface = any(
            link.to_node.bl_idname == "ShaderNodeOutputMaterial" and link.to_socket.name == "Surface"
            for link in mat.node_tree.links
        )
        if not linked_surface:
            problems.append(f"{preset}: no linked material surface")

    if problems:
        ctx.fail(" | ".join(problems))


def test_roundtrip_slots_and_params(ctx):
    """MAT-3..MAT-4: TEXTURE_SLOTS + BOOL/INT/FLOAT params preserved round-trip."""
    from framework import model_roundtrip, model_snapshot

    ctx.require_data()
    seeds = _available_seeds(ctx)
    if not seeds:
        ctx.skip("no test-data seeds present (run: python tests/run.py --build-test-data)")

    problems: list[str] = []
    for seed, cfg in seeds:
        before, after, error = model_roundtrip.run(ctx.config, seed, cfg)
        if error:
            problems.append(f"{seed}: {error}")
            continue
        for category, message in model_snapshot.compare(before, after):
            if category in ("material_param", "model_texture"):
                problems.append(f"{seed} [{category}] {message}")

    if problems:
        ctx.fail(" | ".join(problems))


def test_relic_detection_and_nodegraph(ctx):
    """MAT-5: relic-material detection via dow2_shader / dow2_is_relic_material."""
    import bpy  # type: ignore

    from dow2_tools.model.export_utils import is_relic_material  # type: ignore

    problems: list[str] = []

    relic = bpy.data.materials.new("relic.material.__test_relic")
    relic["dow2_shader"] = "dow2_unit"
    if not is_relic_material(relic):
        problems.append("material with dow2_shader not detected as relic")

    flagged = bpy.data.materials.new("__test_flagged")
    flagged["dow2_is_relic_material"] = True
    if not is_relic_material(flagged):
        problems.append("material with dow2_is_relic_material not detected as relic")

    plain = bpy.data.materials.new("__test_plain")
    if is_relic_material(plain):
        problems.append("plain material wrongly detected as relic")

    if is_relic_material(None):
        problems.append("None wrongly detected as relic")

    for mat in (relic, flagged, plain):
        bpy.data.materials.remove(mat)

    if problems:
        ctx.fail(" | ".join(problems))


def test_rebuild_material_from_test_data(ctx):
    """MAT-7: rebuild material from test_data config -> export -> import; texture paths valid."""
    from framework import model_roundtrip

    ctx.require_data()
    seeds = _available_seeds(ctx)
    seed, cfg = next(((s, c) for s, c in seeds if s == "chaos_heavy_bolter_turret"), (None, None))
    if seed is None:
        if not seeds:
            ctx.skip("no test-data seeds present (run: python tests/run.py --build-test-data)")
        seed, cfg = seeds[0]

    _before, after, error = model_roundtrip.run(ctx.config, seed, cfg)
    if error:
        ctx.fail(f"{seed}: {error}")

    problems: list[str] = []
    for mat_name, entry in cfg.get("materials", {}).items():
        got = after["materials"].get(mat_name)
        if got is None:
            problems.append(f"{seed}: material '{mat_name}' missing after round-trip")
            continue
        for slot, path in entry.get("textures", {}).items():
            got_path = got["params"].get(slot)
            if got_path is None:
                problems.append(f"{seed}: {mat_name}.{slot} missing after round-trip")
            elif _norm(got_path) != _norm(path):
                problems.append(f"{seed}: {mat_name}.{slot} {got_path!r} != {path!r}")

    if problems:
        ctx.fail(" | ".join(problems))

