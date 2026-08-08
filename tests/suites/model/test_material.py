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

    from dow2_tools.material.definitions import VAR_TYPE_BOOL, VAR_TYPE_FLOAT, VAR_TYPE_INT, VAR_TYPE_TEXTURE
    from dow2_tools.material.presets import SHADER_PRESET_CONFIG
    from dow2_tools.material.schema import get_shader_schema
    from framework import blender_env

    blender_env.reset_scene()
    problems: list[str] = []

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
        shader_name = config.get("shader", preset)
        schema = get_shader_schema(shader_name)
        schema_names = set(schema.names())
        if mat.get("dow2_shader") != shader_name:
            problems.append(f"{preset}: dow2_shader={mat.get('dow2_shader')!r}, expected {shader_name!r}")
        if not mat.get("dow2_is_relic_material", False):
            problems.append(f"{preset}: dow2_is_relic_material not set")

        shader_vars = str(mat.get("dow2_shader_vars", "") or "")
        if schema.variables and set(shader_vars.split(",")) != schema_names:
            problems.append(f"{preset}: dow2_shader_vars did not match shader schema")
        for slot in config.get("textures", []):
            if f"dow2_{slot}" not in mat:
                problems.append(f"{preset}: missing texture prop {slot}")
            if slot not in shader_vars.split(","):
                problems.append(f"{preset}: {slot} missing from dow2_shader_vars")
        for var in schema.variables:
            if var.var_type in {VAR_TYPE_BOOL, VAR_TYPE_INT, VAR_TYPE_FLOAT, VAR_TYPE_TEXTURE}:
                if f"dow2_{var.name}" not in mat:
                    problems.append(f"{preset}: missing schema prop {var.name}")
        for param, expected in config.get("params", {}).items():
            got = mat.get(f"dow2_{param}")
            if got != expected:
                problems.append(f"{preset}: {param}={got!r}, expected {expected!r}")

    if problems:
        ctx.fail(" | ".join(problems))


def test_shader_schema_param_types(ctx):
    """Material UI/export params are driven by shader variable_list declarations."""
    from dow2_tools.material.definitions import VAR_TYPE_BOOL, VAR_TYPE_FLOAT, VAR_TYPE_INT, VAR_TYPE_TEXTURE
    from dow2_tools.material.schema import get_shader_schema

    schema = get_shader_schema("dow2_unit")
    lookup = {var.name: var.var_type for var in schema.variables}
    expected = {
        "unitOcclusionFlag": VAR_TYPE_INT,
        "bHighlight": VAR_TYPE_BOOL,
        "dirtVisibility": VAR_TYPE_FLOAT,
        "alphaTest": VAR_TYPE_BOOL,
        "diffuseTex": VAR_TYPE_TEXTURE,
        "emissiveMultiplier": VAR_TYPE_FLOAT,
        "uOffset": VAR_TYPE_FLOAT,
        "vOffset": VAR_TYPE_FLOAT,
    }
    problems = [f"{name}: {lookup.get(name)!r} != {var_type!r}" for name, var_type in expected.items() if lookup.get(name) != var_type]
    if problems:
        ctx.fail(" | ".join(problems))


def test_imported_material_seeds_full_shader_schema(ctx):
    """Imported materials expose the full shader schema, not only XVARs present in a file."""
    import bpy  # type: ignore

    from dow2_tools.material.creator import RelicMaterialCreator
    from dow2_tools.material.data import MaterialVariable, RelicMaterialData
    from dow2_tools.material.definitions import VAR_TYPE_TEXTURE
    from dow2_tools.material.schema import get_shader_schema
    from framework import blender_env

    blender_env.reset_scene()
    mat_data = RelicMaterialData(
        name="relic.material.__partial_xvar_import",
        shader_name="dow2_unit",
        variables=[MaterialVariable("diffuseTex", VAR_TYPE_TEXTURE, "art/test/partial_diffuse")],
    )

    mat = RelicMaterialCreator(ctx.config.test_data_dir).create_material(mat_data)
    schema = get_shader_schema("dow2_unit")
    problems: list[str] = []

    if bpy.data.materials.get(mat.name) is not mat:
        problems.append("material was not registered in bpy.data")
    if set(str(mat.get("dow2_shader_vars", "") or "").split(",")) != set(schema.names()):
        problems.append("dow2_shader_vars did not contain full schema")
    for name in ("unitOcclusionFlag", "bHighlight", "dirtVisibility", "alphaTest", "emissiveMultiplier", "uOffset", "vOffset"):
        if f"dow2_{name}" not in mat:
            problems.append(f"missing seeded schema param {name}")
    if mat.get("dow2_diffuseTex") != "art/test/partial_diffuse":
        problems.append("imported XVAR did not override seeded texture default")

    if problems:
        ctx.fail(" | ".join(problems))


def test_load_shader_builds_shader_specific_node_graph(ctx):
    """Load Shader creates the shader-specific graph template, not a sparse prop rebuild."""
    import bpy  # type: ignore
    from pathlib import Path

    import dow2_tools.material.schema as schema_module
    from framework import blender_env

    blender_env.reset_scene()
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.object
    mat = bpy.data.materials.new("relic.material.__load_shader_unit_graph")
    obj.data.materials.append(mat)
    obj.active_material = mat

    shader_path = Path(schema_module.__file__).resolve().parent / "dow2_.asm_and_.shader" / "dow2_unit.shader"
    result = bpy.ops.dow2.load_shader(filepath=str(shader_path))
    if "FINISHED" not in result:
        ctx.fail(f"load shader failed: {result}")

    labels = {str(getattr(node, "label", "") or "") for node in mat.node_tree.nodes}
    problems: list[str] = []
    for label in ("Unit Surface + Specular", "Badge 1 UV Split", "Badge 1 Layer"):
        if label not in labels:
            problems.append(f"missing node label {label!r}")
    if mat.get("dow2_shader_profile") != "unit":
        problems.append(f"shader profile={mat.get('dow2_shader_profile')!r}, expected 'unit'")

    if problems:
        ctx.fail(" | ".join(problems))


def test_schema_material_variables_are_strict(ctx):
    """Only shader-schema variables are exportable, and their schema type wins."""
    import bpy  # type: ignore

    from dow2_tools.material.definitions import VAR_TYPE_BOOL, VAR_TYPE_FLOAT, VAR_TYPE_INT
    from dow2_tools.material.schema import ensure_material_schema_properties, get_shader_schema, schema_material_variables
    from framework import blender_env

    blender_env.reset_scene()
    mat = bpy.data.materials.new("relic.material.__schema_strict")
    mat["dow2_shader"] = "dow2_unit"
    ensure_material_schema_properties(mat, get_shader_schema("dow2_unit"))
    mat["dow2_unitOcclusionFlag"] = 7
    mat["dow2_dirtVisibility"] = 0.25
    mat["dow2_alphaTest"] = True
    mat["dow2_notInShader"] = 123

    exported = {var.name: var for var in schema_material_variables(mat)}
    problems: list[str] = []
    if "notInShader" in exported:
        problems.append("unsupported custom variable was exportable")
    expected = {
        "unitOcclusionFlag": (VAR_TYPE_INT, 7),
        "dirtVisibility": (VAR_TYPE_FLOAT, 0.25),
        "alphaTest": (VAR_TYPE_BOOL, True),
    }
    for name, (var_type, value) in expected.items():
        got = exported.get(name)
        if got is None:
            problems.append(f"{name}: missing")
        elif got.var_type != var_type or got.value != value:
            problems.append(f"{name}: {(got.var_type, got.value)!r} != {(var_type, value)!r}")

    if problems:
        ctx.fail(" | ".join(problems))


def test_material_param_panel_draw_is_read_only(ctx):
    """The material params panel must not write ID props while Blender draws UI."""
    import bpy  # type: ignore
    from types import SimpleNamespace

    from dow2_tools.material.schema import ensure_material_schema_properties, get_shader_schema
    from dow2_tools.ui.material.panels_params import DOW2_PT_material_params
    from framework import blender_env

    class _FakeLayout:
        enabled = True

        def box(self):
            return self

        def row(self):
            return self

        def label(self, **_kwargs):
            return None

        def prop(self, *_args, **_kwargs):
            return None

    blender_env.reset_scene()
    mat = bpy.data.materials.new("relic.material.__panel_read_only")
    mat["dow2_shader"] = "dow2_unit"
    ensure_material_schema_properties(mat, get_shader_schema("dow2_unit"))
    before = {key: mat[key] for key in mat.keys()}

    fake_context = SimpleNamespace(
        object=SimpleNamespace(active_material=mat),
        preferences=SimpleNamespace(addons={}),
    )
    fake_panel = SimpleNamespace(layout=_FakeLayout())
    DOW2_PT_material_params.draw(fake_panel, fake_context)

    after = {key: mat[key] for key in mat.keys()}
    if after != before:
        ctx.fail(f"panel draw mutated material props: before={before!r} after={after!r}")


def test_schema_param_edit_roundtrip(ctx):
    """Edited bool/int/float shader params survive model export/import round-trip."""
    import bpy  # type: ignore

    from framework import blender_env, fixtures, model_snapshot

    blender_env.reset_scene()
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.object
    obj.name = "schema_param_cube"
    obj["dow2_group"] = "healthy"
    obj["dow2_lod"] = 0

    mat = bpy.data.materials.new("relic.material.__schema_param_roundtrip")
    mat["dow2_shader"] = "dow2_unit"
    mat["dow2_diffuseTex"] = "art/test/schema_param_diffuse"
    mat["dow2_normalMap"] = "art/test/schema_param_normal"
    mat["dow2_specularTex"] = "art/test/schema_param_specular"
    mat["dow2_teamTex"] = "art/test/schema_param_team"
    mat["dow2_unitOcclusionFlag"] = 3
    mat["dow2_dirtVisibility"] = 0.375
    mat["dow2_alphaTest"] = True
    mat["dow2_notInShader"] = 99
    obj.data.materials.append(mat)

    with fixtures.scratch_dir(ctx.config, "schema_param_roundtrip") as scratch:
        out_model = scratch / "schema_param_roundtrip.model"
        result = blender_env.export_model(out_model, export_bones=False, export_markers=False)
        if "FINISHED" not in result:
            ctx.fail(f"export failed: {result}")

        blender_env.reset_scene()
        imported = blender_env.import_model(out_model, import_bones=False, import_markers=False)
        if "FINISHED" not in imported:
            ctx.fail(f"import failed: {imported}")

        snapshot = model_snapshot.capture()

    got = snapshot["materials"].get("relic.material.__schema_param_roundtrip")
    if got is None:
        ctx.fail("round-tripped material missing")
    params = got["params"]
    problems: list[str] = []
    expected = {
        "unitOcclusionFlag": 3,
        "dirtVisibility": 0.375,
        "alphaTest": True,
    }
    for name, value in expected.items():
        got_value = params.get(name)
        if got_value != value:
            problems.append(f"{name}: {got_value!r} != {value!r}")
    if "notInShader" in params:
        problems.append("unsupported custom variable survived export")

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

