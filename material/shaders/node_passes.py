from __future__ import annotations

import bpy

from typing import Any, Optional, Sequence


class BaseColorNodePasses:
    _PALETTE_LABELS = (
        'Palette 1',
        'Palette 2',
        'Palette 3',
        'Palette 4',
    )

    @staticmethod
    def pop_socket_source(links: Any, node: Any, socket_name: str) -> Optional[Any]:
        current = None
        for link in list(links):
            if link.to_socket.name == socket_name and link.to_node == node:
                current = link.from_socket
                links.remove(link)
                break
        return current

    @classmethod
    def pop_base_color_source(cls, links: Any, principled: Any) -> Optional[Any]:
        return cls.pop_socket_source(links, principled, 'Base Color')

    @staticmethod
    def apply_legacy_specular_metalness(
        nodes: Any,
        links: Any,
        principled: Any,
        specular_tex_node: Any,
    ) -> Optional[Any]:
        if specular_tex_node is None:
            return None

        specular_color_socket = specular_tex_node.outputs['Color']

        if 'Specular Tint' in principled.inputs:
            links.new(specular_color_socket, principled.inputs['Specular Tint'])

        separate_spec = nodes.new('ShaderNodeSeparateColor')
        separate_spec.location = (specular_tex_node.location.x + 180, specular_tex_node.location.y - 140)
        separate_spec.label = 'Specular Channels'
        links.new(specular_color_socket, separate_spec.inputs['Color'])

        max_rg = nodes.new('ShaderNodeMath')
        max_rg.operation = 'MAXIMUM'
        max_rg.location = (specular_tex_node.location.x + 360, specular_tex_node.location.y - 200)
        links.new(separate_spec.outputs['Red'], max_rg.inputs[0])
        links.new(separate_spec.outputs['Green'], max_rg.inputs[1])

        max_rgb = nodes.new('ShaderNodeMath')
        max_rgb.operation = 'MAXIMUM'
        max_rgb.location = (specular_tex_node.location.x + 540, specular_tex_node.location.y - 200)
        links.new(max_rg.outputs['Value'], max_rgb.inputs[0])
        links.new(separate_spec.outputs['Blue'], max_rgb.inputs[1])

        remove_dielectric = nodes.new('ShaderNodeMath')
        remove_dielectric.operation = 'SUBTRACT'
        remove_dielectric.location = (specular_tex_node.location.x + 720, specular_tex_node.location.y - 200)
        remove_dielectric.inputs[1].default_value = 0.04
        links.new(max_rgb.outputs['Value'], remove_dielectric.inputs[0])

        normalize_metal = nodes.new('ShaderNodeMath')
        normalize_metal.operation = 'MULTIPLY'
        normalize_metal.location = (specular_tex_node.location.x + 900, specular_tex_node.location.y - 200)
        normalize_metal.inputs[1].default_value = 1.0 / 0.96
        normalize_metal.use_clamp = True
        links.new(remove_dielectric.outputs['Value'], normalize_metal.inputs[0])

        if 'Metallic' in principled.inputs:
            links.new(normalize_metal.outputs['Value'], principled.inputs['Metallic'])

        gloss_to_roughness = nodes.new('ShaderNodeMath')
        gloss_to_roughness.operation = 'SUBTRACT'
        gloss_to_roughness.use_clamp = True
        gloss_to_roughness.location = (specular_tex_node.location.x + 360, specular_tex_node.location.y)
        gloss_to_roughness.label = 'Spec Alpha To Roughness'
        gloss_to_roughness.inputs[0].default_value = 1.0
        links.new(specular_tex_node.outputs['Alpha'], gloss_to_roughness.inputs[1])

        has_existing_roughness = any(
            link.to_node == principled and link.to_socket.name == 'Roughness'
            for link in links
        )
        if 'Roughness' in principled.inputs and not has_existing_roughness:
            links.new(gloss_to_roughness.outputs['Value'], principled.inputs['Roughness'])

        return normalize_metal.outputs['Value']

    @classmethod
    def apply_reflective_specular(
        cls,
        nodes: Any,
        links: Any,
        output: Any,
        principled: Any,
        specular_tex_node: Any,
        normal_socket: Any = None,
    ) -> None:
        if specular_tex_node is None:
            return

        cls.pop_socket_source(links, principled, 'Metallic')
        cls.pop_socket_source(links, principled, 'Roughness')

        if 'Metallic' in principled.inputs:
            principled.inputs['Metallic'].default_value = 0.0
        if 'Specular IOR Level' in principled.inputs:
            principled.inputs['Specular IOR Level'].default_value = 0.0

        gloss_to_roughness = nodes.new('ShaderNodeMath')
        gloss_to_roughness.operation = 'SUBTRACT'
        gloss_to_roughness.use_clamp = True
        gloss_to_roughness.location = (principled.location.x - 620, principled.location.y - 520)
        gloss_to_roughness.label = 'Spec Alpha To Roughness'
        gloss_to_roughness.inputs[0].default_value = 0.65
        links.new(specular_tex_node.outputs['Alpha'], gloss_to_roughness.inputs[1])

        if 'Roughness' in principled.inputs:
            links.new(gloss_to_roughness.outputs['Value'], principled.inputs['Roughness'])

        glossy_node = nodes.new('ShaderNodeBsdfGlossy')
        glossy_node.location = (principled.location.x + 260, principled.location.y - 420)
        glossy_node.label = 'Reflective Specular'
        if hasattr(glossy_node, 'distribution'):
            glossy_node.distribution = 'GGX'
        links.new(specular_tex_node.outputs['Color'], glossy_node.inputs['Color'])
        links.new(gloss_to_roughness.outputs['Value'], glossy_node.inputs['Roughness'])
        if normal_socket is not None and 'Normal' in glossy_node.inputs:
            links.new(normal_socket, glossy_node.inputs['Normal'])

        surface_socket = cls.pop_socket_source(links, output, 'Surface')
        if surface_socket is None:
            surface_socket = principled.outputs['BSDF']

        add_shader = nodes.new('ShaderNodeAddShader')
        add_shader.location = (output.location.x - 160, output.location.y - 40)
        add_shader.label = 'Unit Surface + Specular'
        links.new(surface_socket, add_shader.inputs[0])
        links.new(glossy_node.outputs['BSDF'], add_shader.inputs[1])
        links.new(add_shader.outputs['Shader'], output.inputs['Surface'])

    @staticmethod
    def apply_overlay(nodes: Any, links: Any, principled: Any, base_source: Any, overlay_node: Any) -> Any:
        if base_source is None or overlay_node is None:
            return base_source

        overlay_mix = nodes.new('ShaderNodeMix')
        overlay_mix.data_type = 'RGBA'
        overlay_mix.blend_type = 'MIX'
        overlay_mix.clamp_factor = True
        overlay_mix.location = (principled.location.x - 650, principled.location.y + 220)
        overlay_mix.label = "Diffuse + Overlay"
        links.new(base_source, overlay_mix.inputs['A'])
        links.new(overlay_node.outputs['Color'], overlay_mix.inputs['B'])
        links.new(overlay_node.outputs['Alpha'], overlay_mix.inputs['Factor'])
        return overlay_mix.outputs['Result']

    @staticmethod
    def apply_ao(nodes: Any, links: Any, principled: Any, base_source: Any, ao_tex_node: Any) -> Any:
        if base_source is None or ao_tex_node is None:
            return base_source

        ao_mul = nodes.new('ShaderNodeMix')
        ao_mul.data_type = 'RGBA'
        ao_mul.blend_type = 'MULTIPLY'
        ao_mul.location = (principled.location.x - 450, principled.location.y + 180)
        ao_mul.label = "Base * AO"
        ao_mul.inputs['Factor'].default_value = 1.0
        links.new(base_source, ao_mul.inputs['A'])
        links.new(ao_tex_node.outputs['Color'], ao_mul.inputs['B'])
        return ao_mul.outputs['Result']

    @staticmethod
    def apply_damage_scarring(nodes: Any, links: Any, principled: Any, mat: Any, base_source: Any, damage_diffuse_node: Any, scar_mask_node: Any) -> Any:
        enable_scarring = bool(mat.get("dow2_enableScarring", False))
        scar_texture_path = str(mat.get("dow2_scarTexture", "")).lower()

        if (
            base_source is None or
            not enable_scarring or
            not damage_diffuse_node or
            not scar_mask_node or
            "defaulttexture" in scar_texture_path
        ):
            return base_source

        mask_to_bw = nodes.new('ShaderNodeRGBToBW')
        mask_to_bw.location = (principled.location.x - 480, principled.location.y - 20)
        mask_to_bw.label = "Scar Mask"
        links.new(scar_mask_node.outputs['Color'], mask_to_bw.inputs['Color'])

        damage_mix = nodes.new('ShaderNodeMix')
        damage_mix.data_type = 'RGBA'
        damage_mix.blend_type = 'MIX'
        damage_mix.clamp_factor = True
        damage_mix.location = (principled.location.x - 250, principled.location.y + 60)
        damage_mix.label = "Damage Blend"
        links.new(mask_to_bw.outputs['Val'], damage_mix.inputs['Factor'])
        links.new(base_source, damage_mix.inputs['A'])
        links.new(damage_diffuse_node.outputs['Color'], damage_mix.inputs['B'])
        return damage_mix.outputs['Result']

    @staticmethod
    def ensure_palette_properties(mat: Any, palette_defaults: Sequence[Sequence[float]]) -> Sequence[Sequence[float]]:
        keys = [
            "dow2_display_palette1",
            "dow2_display_palette2",
            "dow2_display_palette3",
            "dow2_display_palette4",
        ]
        palette_values = list(BaseColorNodePasses.get_global_palette_values(palette_defaults))
        for key, value in zip(keys, palette_values):
            mat[key] = list(value)
        return tuple(palette_values)

    @staticmethod
    def get_global_palette_values(palette_defaults: Sequence[Sequence[float]]) -> Sequence[Sequence[float]]:
        scene = getattr(bpy.context, 'scene', None)
        palette_settings = getattr(scene, 'dow2_global_palettes', None) if scene is not None else None
        if palette_settings is None:
            return palette_defaults

        palette_values = []
        for index, default_value in enumerate(palette_defaults, start=1):
            attr_name = f'palette{index}'
            raw_value = getattr(palette_settings, attr_name, default_value)
            palette_values.append(tuple(raw_value))
        return tuple(palette_values)

    @classmethod
    def attach_palette_driver(cls, palette_node: Any, palette_index: int, palette_value: Sequence[float]) -> None:
        palette_node.outputs['Color'].default_value = palette_value

        for channel_index in range(4):
            try:
                palette_node.outputs['Color'].driver_remove('default_value', channel_index)
            except (TypeError, RuntimeError):
                pass

    @classmethod
    def sync_global_palette_nodes(cls, scene: Any) -> None:
        palette_settings = getattr(scene, 'dow2_global_palettes', None)
        if palette_settings is None:
            return

        palette_values = [
            tuple(getattr(palette_settings, f'palette{index}'))
            for index in range(1, 5)
        ]

        for material in bpy.data.materials:
            if material is None or not material.use_nodes or material.node_tree is None:
                continue

            for index, palette_value in enumerate(palette_values, start=1):
                material[f'dow2_display_palette{index}'] = list(palette_value)

            for node in material.node_tree.nodes:
                if node.bl_idname != 'ShaderNodeRGB':
                    continue
                for index, label in enumerate(cls._PALETTE_LABELS, start=1):
                    if str(getattr(node, 'label', '')).startswith(label):
                        cls.attach_palette_driver(node, index, palette_values[index - 1])
                        break

    @classmethod
    def _build_team_tint_chain(
        cls,
        nodes: Any,
        links: Any,
        chain_input: Any,
        team_tex_node: Any,
        palette_defaults: Sequence[Sequence[float]],
    ) -> Any:
        palette_defaults = tuple(cls.get_global_palette_values(palette_defaults))

        separate_node = nodes.new('ShaderNodeSeparateColor')
        separate_node.location = (team_tex_node.location.x + 200, team_tex_node.location.y)
        separate_node.label = "Team Mask Channels"
        links.new(team_tex_node.outputs['Color'], separate_node.inputs['Color'])

        team_x = chain_input.node.location.x + 350
        team_y = chain_input.node.location.y - 100

        palette_channels = ['Red', 'Green', 'Blue']
        palette_labels = ["Palette 1 (R)", "Palette 2 (G)", "Palette 3 (B)"]

        for i, (label, channel, color) in enumerate(zip(palette_labels, palette_channels, palette_defaults[:3])):
            palette_node = nodes.new('ShaderNodeRGB')
            palette_node.location = (team_x, team_y - i * 250)
            palette_node.label = label
            cls.attach_palette_driver(palette_node, i + 1, color)

            mult_node = nodes.new('ShaderNodeMix')
            mult_node.data_type = 'RGBA'
            mult_node.blend_type = 'MULTIPLY'
            mult_node.location = (team_x + 200, team_y - i * 250)
            mult_node.label = f"Diffuse * {label}"
            mult_node.inputs['Factor'].default_value = 1.0
            links.new(chain_input, mult_node.inputs['A'])
            links.new(palette_node.outputs['Color'], mult_node.inputs['B'])

            scale_node = nodes.new('ShaderNodeVectorMath')
            scale_node.operation = 'SCALE'
            scale_node.location = (team_x + 400, team_y - i * 250)
            scale_node.label = "x2 (mid-grey neutral)"
            scale_node.inputs['Scale'].default_value = 2.0
            links.new(mult_node.outputs['Result'], scale_node.inputs['Vector'])

            lerp_node = nodes.new('ShaderNodeMix')
            lerp_node.data_type = 'RGBA'
            lerp_node.blend_type = 'MIX'
            lerp_node.location = (team_x + 600, team_y - i * 250)
            lerp_node.label = f"Apply {label}"
            lerp_node.clamp_factor = True
            links.new(separate_node.outputs[channel], lerp_node.inputs['Factor'])
            links.new(chain_input, lerp_node.inputs['A'])
            links.new(scale_node.outputs['Vector'], lerp_node.inputs['B'])
            chain_input = lerp_node.outputs['Result']

        palette4_node = nodes.new('ShaderNodeRGB')
        palette4_node.location = (team_x, team_y - 3 * 250)
        palette4_node.label = "Palette 4 (A)"
        cls.attach_palette_driver(palette4_node, 4, palette_defaults[3])

        mult4_node = nodes.new('ShaderNodeMix')
        mult4_node.data_type = 'RGBA'
        mult4_node.blend_type = 'MULTIPLY'
        mult4_node.location = (team_x + 200, team_y - 3 * 250)
        mult4_node.label = "Diffuse * Palette 4"
        mult4_node.inputs['Factor'].default_value = 1.0
        links.new(chain_input, mult4_node.inputs['A'])
        links.new(palette4_node.outputs['Color'], mult4_node.inputs['B'])

        scale4_node = nodes.new('ShaderNodeVectorMath')
        scale4_node.operation = 'SCALE'
        scale4_node.location = (team_x + 400, team_y - 3 * 250)
        scale4_node.label = "x2 (mid-grey neutral)"
        scale4_node.inputs['Scale'].default_value = 2.0
        links.new(mult4_node.outputs['Result'], scale4_node.inputs['Vector'])

        lerp4_node = nodes.new('ShaderNodeMix')
        lerp4_node.data_type = 'RGBA'
        lerp4_node.blend_type = 'MIX'
        lerp4_node.location = (team_x + 600, team_y - 3 * 250)
        lerp4_node.label = "Apply Palette 4"
        lerp4_node.clamp_factor = True
        links.new(team_tex_node.outputs['Alpha'], lerp4_node.inputs['Factor'])
        links.new(chain_input, lerp4_node.inputs['A'])
        links.new(scale4_node.outputs['Vector'], lerp4_node.inputs['B'])
        return lerp4_node.outputs['Result']

    @classmethod
    def _build_team_tint_factor(
        cls,
        nodes: Any,
        links: Any,
        team_tex_node: Any,
        palette_defaults: Sequence[Sequence[float]],
    ) -> Any:
        white_node = nodes.new('ShaderNodeRGB')
        white_node.location = (team_tex_node.location.x - 240, team_tex_node.location.y + 500)
        white_node.label = "Team Tint Factor Seed"
        white_node.outputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
        return cls._build_team_tint_chain(
            nodes,
            links,
            white_node.outputs['Color'],
            team_tex_node,
            palette_defaults,
        )

    @classmethod
    def _apply_tint_factor_to_socket(
        cls,
        nodes: Any,
        links: Any,
        principled: Any,
        socket_name: str,
        tint_factor_socket: Any,
        fallback_source_socket: Any,
    ) -> None:
        current_source = cls.pop_socket_source(links, principled, socket_name)
        if current_source is None:
            current_source = fallback_source_socket
        if current_source is None:
            return

        tint_mul = nodes.new('ShaderNodeMix')
        tint_mul.data_type = 'RGBA'
        tint_mul.blend_type = 'MULTIPLY'
        tint_mul.inputs['Factor'].default_value = 1.0
        tint_mul.location = (principled.location.x - 320, principled.location.y + (120 if socket_name == 'Base Color' else -120))
        tint_mul.label = f"{socket_name} * TeamTint"
        links.new(current_source, tint_mul.inputs['A'])
        links.new(tint_factor_socket, tint_mul.inputs['B'])
        links.new(tint_mul.outputs['Result'], principled.inputs[socket_name])

    @classmethod
    def apply_team_colors_shared(
        cls,
        nodes: Any,
        links: Any,
        principled: Any,
        mat: Any,
        team_tex_node: Any,
        diffuse_tex_node: Any,
        emissive_tex_node: Any,
        palette_defaults: Sequence[Sequence[float]],
    ) -> None:
        if not team_tex_node:
            return

        palette_defaults = cls.ensure_palette_properties(mat, palette_defaults)
        tint_factor_socket = cls._build_team_tint_factor(
            nodes,
            links,
            team_tex_node,
            palette_defaults,
        )

        diffuse_fallback = diffuse_tex_node.outputs['Color'] if diffuse_tex_node else None
        emissive_fallback = emissive_tex_node.outputs['Color'] if emissive_tex_node else None

        cls._apply_tint_factor_to_socket(
            nodes,
            links,
            principled,
            'Base Color',
            tint_factor_socket,
            diffuse_fallback,
        )
        cls._apply_tint_factor_to_socket(
            nodes,
            links,
            principled,
            'Emission Color',
            tint_factor_socket,
            emissive_fallback,
        )

    @classmethod
    def apply_metal_base_blend(
        cls,
        nodes: Any,
        links: Any,
        principled: Any,
        specular_color_socket: Any,
        metallic_socket: Any,
    ) -> None:
        if not specular_color_socket or not metallic_socket:
            return

        current_color_source = cls.pop_base_color_source(links, principled)
        if current_color_source is None:
            return

        metal_base_mix = nodes.new('ShaderNodeMix')
        metal_base_mix.data_type = 'RGBA'
        metal_base_mix.blend_type = 'MIX'
        metal_base_mix.location = (principled.location.x - 250, principled.location.y - 220)
        metal_base_mix.label = "Base/Spec Metal Blend"
        metal_base_mix.clamp_factor = True

        links.new(metallic_socket, metal_base_mix.inputs['Factor'])
        links.new(current_color_source, metal_base_mix.inputs['A'])
        links.new(specular_color_socket, metal_base_mix.inputs['B'])
        links.new(metal_base_mix.outputs['Result'], principled.inputs['Base Color'])

    @staticmethod
    def apply_badge_decal(nodes: Any, links: Any, principled: Any, base_source: Any, badge_tex_node: Any, label: str) -> Any:
        if base_source is None or badge_tex_node is None:
            return base_source

        badge_mix = nodes.new('ShaderNodeMix')
        badge_mix.data_type = 'RGBA'
        badge_mix.blend_type = 'MIX'
        badge_mix.clamp_factor = True
        badge_mix.location = (principled.location.x - 260, principled.location.y - 360)
        badge_mix.label = label
        links.new(base_source, badge_mix.inputs['A'])
        links.new(badge_tex_node.outputs['Color'], badge_mix.inputs['B'])
        links.new(badge_tex_node.outputs['Alpha'], badge_mix.inputs['Factor'])
        return badge_mix.outputs['Result']

    @staticmethod
    def apply_dirt_layer(nodes: Any, links: Any, principled: Any, base_source: Any, dirt_tex_node: Any, dirt_visibility: float) -> Any:
        if base_source is None or dirt_tex_node is None or dirt_visibility <= 0.0:
            return base_source

        dirt_visibility_node = nodes.new('ShaderNodeValue')
        dirt_visibility_node.location = (principled.location.x - 680, principled.location.y - 520)
        dirt_visibility_node.label = 'Dirt Visibility'
        dirt_visibility_node.outputs['Value'].default_value = dirt_visibility

        dirt_factor = nodes.new('ShaderNodeMath')
        dirt_factor.operation = 'MULTIPLY'
        dirt_factor.use_clamp = True
        dirt_factor.location = (principled.location.x - 470, principled.location.y - 520)
        dirt_factor.label = 'Dirt Blend Factor'
        links.new(dirt_tex_node.outputs['Alpha'], dirt_factor.inputs[0])
        links.new(dirt_visibility_node.outputs['Value'], dirt_factor.inputs[1])

        dirt_mix = nodes.new('ShaderNodeMix')
        dirt_mix.data_type = 'RGBA'
        dirt_mix.blend_type = 'MIX'
        dirt_mix.clamp_factor = True
        dirt_mix.location = (principled.location.x - 260, principled.location.y - 520)
        dirt_mix.label = 'Dirt Layer'
        links.new(dirt_factor.outputs['Value'], dirt_mix.inputs['Factor'])
        links.new(base_source, dirt_mix.inputs['A'])
        links.new(dirt_tex_node.outputs['Color'], dirt_mix.inputs['B'])
        return dirt_mix.outputs['Result']

    @staticmethod
    def apply_color_tint(nodes: Any, links: Any, principled: Any, base_source: Any, tint_rgba: Sequence[float], label: str) -> Any:
        if base_source is None:
            return base_source

        tint_node = nodes.new('ShaderNodeRGB')
        tint_node.location = (principled.location.x - 700, principled.location.y - 680)
        tint_node.label = f'{label} Color'
        tint_node.outputs['Color'].default_value = tint_rgba

        tint_mix = nodes.new('ShaderNodeMix')
        tint_mix.data_type = 'RGBA'
        tint_mix.blend_type = 'MULTIPLY'
        tint_mix.inputs['Factor'].default_value = 1.0
        tint_mix.location = (principled.location.x - 430, principled.location.y - 680)
        tint_mix.label = label
        links.new(base_source, tint_mix.inputs['A'])
        links.new(tint_node.outputs['Color'], tint_mix.inputs['B'])
        return tint_mix.outputs['Result']

    @staticmethod
    def apply_alpha_factor(nodes: Any, links: Any, principled: Any, alpha_source: Any, alpha_factor: float, label: str) -> Any:
        if alpha_source is None and alpha_factor >= 0.999:
            return None

        factor_node = nodes.new('ShaderNodeValue')
        factor_node.location = (principled.location.x - 700, principled.location.y - 780)
        factor_node.label = f'{label} Factor'
        factor_node.outputs['Value'].default_value = alpha_factor

        if alpha_source is None:
            return factor_node.outputs['Value']

        alpha_mul = nodes.new('ShaderNodeMath')
        alpha_mul.operation = 'MULTIPLY'
        alpha_mul.use_clamp = True
        alpha_mul.location = (principled.location.x - 430, principled.location.y - 780)
        alpha_mul.label = label
        links.new(alpha_source, alpha_mul.inputs[0])
        links.new(factor_node.outputs['Value'], alpha_mul.inputs[1])
        return alpha_mul.outputs['Value']

    @staticmethod
    def apply_dual_scar_blend(nodes: Any, links: Any, principled: Any, base_source: Any, dual_scar_tex_node: Any, scar_mask_node: Any, label: str) -> Any:
        if base_source is None or dual_scar_tex_node is None or scar_mask_node is None:
            return base_source

        # The building_brick_scar_dual pixel shader uses the scar mask as the
        # blend factor for the alternate scar diffuse set, so we mirror that
        # relationship directly instead of treating it like the regular damage
        # overlay path.
        scar_mask_bw = nodes.new('ShaderNodeRGBToBW')
        scar_mask_bw.location = (principled.location.x - 720, principled.location.y - 420)
        scar_mask_bw.label = 'Dual Scar Mask'
        links.new(scar_mask_node.outputs['Color'], scar_mask_bw.inputs['Color'])

        dual_scar_mix = nodes.new('ShaderNodeMix')
        dual_scar_mix.data_type = 'RGBA'
        dual_scar_mix.blend_type = 'MIX'
        dual_scar_mix.clamp_factor = True
        dual_scar_mix.location = (principled.location.x - 430, principled.location.y - 420)
        dual_scar_mix.label = label
        links.new(scar_mask_bw.outputs['Val'], dual_scar_mix.inputs['Factor'])
        links.new(base_source, dual_scar_mix.inputs['A'])
        links.new(dual_scar_tex_node.outputs['Color'], dual_scar_mix.inputs['B'])
        return dual_scar_mix.outputs['Result']

    @staticmethod
    def apply_terrain_slope_blend(nodes: Any, links: Any, principled: Any, cliff_tex_node: Any, grass_tex_node: Any, label: str) -> Any:
        cliff_source = cliff_tex_node.outputs['Color'] if cliff_tex_node else None
        grass_source = grass_tex_node.outputs['Color'] if grass_tex_node else None

        if cliff_source is None and grass_source is None:
            return None
        if cliff_source is None:
            cliff_source = grass_source
        if grass_source is None:
            grass_source = cliff_source

        # The terrain object shader is not a simple single-diffuse material; it
        # carries separate cliff and grass texture variables. We approximate the
        # engine's terrain weighting with a slope-derived blend so users can see
        # why both texture families are present even when the exact terrain data
        # set is not available in Blender.
        geometry_node = nodes.new('ShaderNodeNewGeometry')
        geometry_node.location = (principled.location.x - 950, principled.location.y - 560)
        geometry_node.label = 'Terrain Geometry'

        separate_normal = nodes.new('ShaderNodeSeparateXYZ')
        separate_normal.location = (principled.location.x - 740, principled.location.y - 560)
        separate_normal.label = 'Terrain Normal Split'
        links.new(geometry_node.outputs['Normal'], separate_normal.inputs['Vector'])

        slope_factor = nodes.new('ShaderNodeMath')
        slope_factor.operation = 'ABSOLUTE'
        slope_factor.use_clamp = True
        slope_factor.location = (principled.location.x - 530, principled.location.y - 560)
        slope_factor.label = 'Terrain Grass Factor'
        links.new(separate_normal.outputs['Z'], slope_factor.inputs[0])

        terrain_mix = nodes.new('ShaderNodeMix')
        terrain_mix.data_type = 'RGBA'
        terrain_mix.blend_type = 'MIX'
        terrain_mix.clamp_factor = True
        terrain_mix.location = (principled.location.x - 300, principled.location.y - 560)
        terrain_mix.label = label
        links.new(slope_factor.outputs['Value'], terrain_mix.inputs['Factor'])
        links.new(cliff_source, terrain_mix.inputs['A'])
        links.new(grass_source, terrain_mix.inputs['B'])
        return terrain_mix.outputs['Result']
