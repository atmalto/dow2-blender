"""Filesystem discovery of DoW2 game assets under ``DATA_ROOT/art``.

Pure filesystem logic (no ``bpy``) so it can be unit-tested and reused by both
the suite and the Phase-A test-data generator.

Sourcing rules (see working/test_plan.md §12):
  - Models live under ``art/race_<name>/...`` and ``art/world_objects/...``.
  - Meshes are typically in ``troops_wargear`` / ``structures`` / ``world_objects``;
    ``troops`` folders usually hold ``.model`` + ``.hkanim`` with no mesh.
  - Animations: ``.hkanim`` (batch-unpacked to ``.hkx``); loose ``.hkx`` sit under
    a model's ``animations/`` subfolder. ``.anim`` is out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ART_SUBDIR = "art"


@dataclass(frozen=True)
class ModelAsset:
    path: Path
    category: str  # 'mesh' | 'troops' | 'world_object' | 'other'


@dataclass(frozen=True)
class CollisionAsset:
    path: Path
    category: str  # 'sim' | 'walkable' | 'other'
    model_path: Path | None
    sibling_models: tuple[Path, ...]


@dataclass(frozen=True)
class PhysicsAsset:
    path: Path
    category: str  # 'physics' | 'rubble'
    model_path: Path


@dataclass(frozen=True)
class RagdollAsset:
    path: Path
    category: str  # race/source bucket, e.g. 'race_chaos' | 'world_objects' | 'other'
    model_path: Path


def _art_root(data_root: Path) -> Path:
    return data_root / ART_SUBDIR


def classify_model(path: Path) -> str:
    parts = {p.lower() for p in path.parts}
    if "world_objects" in parts:
        return "world_object"
    if "troops_wargear" in parts or "structures" in parts:
        return "mesh"
    if "troops" in parts:
        return "troops"
    return "other"


def find_models(data_root: Path, limit: int | None = None) -> list[ModelAsset]:
    """Return ``.model`` assets under ``art/``, deterministically ordered, capped at ``limit``.

    Ordering favors variety by interleaving categories (mesh / world_object /
    troops / other) so a small scope still exercises different shader families.
    """
    art = _art_root(data_root)
    if not art.is_dir():
        return []

    buckets: dict[str, list[ModelAsset]] = {"mesh": [], "world_object": [], "troops": [], "other": []}
    for model_path in sorted(art.rglob("*.model")):
        asset = ModelAsset(model_path, classify_model(model_path))
        buckets[asset.category].append(asset)

    # Round-robin interleave for category variety.
    order = ["mesh", "world_object", "troops", "other"]
    interleaved: list[ModelAsset] = []
    idx = 0
    while any(buckets[c] for c in order):
        cat = order[idx % len(order)]
        if buckets[cat]:
            interleaved.append(buckets[cat].pop(0))
        idx += 1

    return interleaved if limit is None else interleaved[:limit]


def _classify_collision(path: Path) -> str:
    stem = path.stem.lower()
    if stem.endswith("_sim"):
        return "sim"
    if stem.endswith("_walkable"):
        return "walkable"
    return "other"


def _preferred_model_for_collision(path: Path, sibling_models: tuple[Path, ...]) -> Path | None:
    if not sibling_models:
        return None
    stem = path.stem
    for suffix in ("_sim", "_walkable", "_collision"):
        if stem.lower().endswith(suffix):
            candidate = path.with_name(stem[: -len(suffix)] + ".model")
            if candidate in sibling_models:
                return candidate
    same_stem = path.with_suffix(".model")
    if same_stem in sibling_models:
        return same_stem
    return sibling_models[0]


def find_collisions(data_root: Path, limit: int | None = None) -> list[CollisionAsset]:
    """Return ``.collision`` assets under ``art/`` with sibling model pairing.

    Ordering interleaves sim/walkable/other so small scope covers both full-object
    collision and walkable surfaces deterministically.
    """
    art = _art_root(data_root)
    if not art.is_dir():
        return []

    buckets: dict[str, list[CollisionAsset]] = {"sim": [], "walkable": [], "other": []}
    for collision_path in sorted(art.rglob("*.collision")):
        category = _classify_collision(collision_path)
        sibling_models = tuple(sorted(collision_path.parent.glob("*.model")))
        asset = CollisionAsset(
            path=collision_path,
            category=category,
            model_path=_preferred_model_for_collision(collision_path, sibling_models),
            sibling_models=sibling_models,
        )
        buckets[category].append(asset)

    order = ["sim", "walkable", "other"]
    interleaved: list[CollisionAsset] = []
    idx = 0
    while any(buckets[c] for c in order):
        category = order[idx % len(order)]
        if buckets[category]:
            interleaved.append(buckets[category].pop(0))
        idx += 1

    return interleaved if limit is None else interleaved[:limit]


def find_animations(data_root: Path, limit: int | None = None) -> list[Path]:
    """Return ``.hkanim`` files under ``art/``, deterministically ordered, capped at ``limit``."""
    art = _art_root(data_root)
    if not art.is_dir():
        return []
    hkanims = sorted(art.rglob("*.hkanim"))
    return hkanims if limit is None else hkanims[:limit]


def find_loose_hkx(model_dir: Path) -> list[Path]:
    """Return loose ``.hkx`` files under ``<model_dir>/animations/`` (extracted clips)."""
    anim_dir = model_dir / "animations"
    if not anim_dir.is_dir():
        return []
    return sorted(anim_dir.glob("*.hkx"))


def _classify_physics(path: Path) -> str:
    return "rubble" if path.stem.lower().endswith("_rubble_physics") else "physics"


def _preferred_model_for_physics(path: Path) -> Path | None:
    stem = path.stem
    lower = stem.lower()
    if lower.endswith("_rubble_physics"):
        candidate = path.with_name(stem[: -len("_rubble_physics")] + "_rubble.model")
        return candidate if candidate.is_file() else None
    if lower.endswith("_physics"):
        candidate = path.with_name(stem[: -len("_physics")] + ".model")
        return candidate if candidate.is_file() else None
    return None


def find_physics(data_root: Path, limit: int | None = None) -> list[PhysicsAsset]:
    """Return exact-paired ``*_physics.hkx`` assets under ``art/``.

    This phase deliberately keeps pairing strict: only same-folder canonical
    ``foo_physics.hkx -> foo.model`` and ``foo_rubble_physics.hkx -> foo_rubble.model``
    matches are included. Odd corpus exceptions are left for later phases.
    Placeholder helper assets under ``art/defaults`` and ``art/fx`` are skipped.
    """
    art = _art_root(data_root)
    if not art.is_dir():
        return []

    buckets: dict[str, list[PhysicsAsset]] = {"physics": [], "rubble": []}
    for physics_path in sorted(art.rglob("*.hkx")):
        lower = physics_path.name.lower()
        if not lower.endswith("_physics.hkx"):
            continue
        rel_parts = {part.lower() for part in physics_path.relative_to(art).parts}
        if "defaults" in rel_parts or "fx" in rel_parts:
            continue
        model_path = _preferred_model_for_physics(physics_path)
        if model_path is None:
            continue
        asset = PhysicsAsset(
            path=physics_path,
            category=_classify_physics(physics_path),
            model_path=model_path,
        )
        buckets[asset.category].append(asset)

    order = ["physics", "rubble"]
    interleaved: list[PhysicsAsset] = []
    idx = 0
    while any(buckets[category] for category in order):
        category = order[idx % len(order)]
        if buckets[category]:
            interleaved.append(buckets[category].pop(0))
        idx += 1

    return interleaved if limit is None else interleaved[:limit]


def _classify_ragdoll(data_root: Path, path: Path) -> str:
    """Bucket a ragdoll by its top-level ``art`` source folder (race_* / world_objects)."""
    rel_parts = [p.lower() for p in path.relative_to(_art_root(data_root)).parts]
    for part in rel_parts:
        if part.startswith("race_"):
            return part
    if "world_objects" in rel_parts:
        return "world_objects"
    return "other"


def _preferred_model_for_ragdoll(path: Path) -> Path | None:
    """Resolve the source ``.model`` for a ragdoll.

    DoW2 ragdolls live at ``.../troops/<unit>/animations/<clip>/ragdoll.hkx`` and
    the source skeleton is ``.../troops/<unit>/<unit>.model``. Walk up the
    ancestors until a directory contains a ``.model``; prefer one whose stem
    matches the unit directory name, else the first available.
    """
    for ancestor in path.parents:
        models = sorted(ancestor.glob("*.model"))
        if not models:
            continue
        named = ancestor / f"{ancestor.name}.model"
        if named in models:
            return named
        return models[0]
    return None


def find_ragdolls(data_root: Path, limit: int | None = None) -> list[RagdollAsset]:
    """Return ``ragdoll.hkx`` assets under ``art/`` paired with their source model.

    Only ragdolls with a resolvable sibling/ancestor ``.model`` are returned.
    Ordering interleaves by source race/world bucket so a small scope still
    exercises different unit families deterministically.
    """
    art = _art_root(data_root)
    if not art.is_dir():
        return []

    buckets: dict[str, list[RagdollAsset]] = {}
    order: list[str] = []
    for ragdoll_path in sorted(art.rglob("*.hkx")):
        if ragdoll_path.name.lower() != "ragdoll.hkx":
            continue
        model_path = _preferred_model_for_ragdoll(ragdoll_path)
        if model_path is None:
            continue
        category = _classify_ragdoll(data_root, ragdoll_path)
        asset = RagdollAsset(path=ragdoll_path, category=category, model_path=model_path)
        if category not in buckets:
            buckets[category] = []
            order.append(category)
        buckets[category].append(asset)

    order.sort()
    interleaved: list[RagdollAsset] = []
    idx = 0
    while any(buckets[category] for category in order):
        category = order[idx % len(order)]
        if buckets[category]:
            interleaved.append(buckets[category].pop(0))
        idx += 1

    return interleaved if limit is None else interleaved[:limit]
