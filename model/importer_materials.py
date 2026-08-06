from __future__ import annotations

from typing import TYPE_CHECKING, List

from ..chunk_lib import RelicChunk, find_chunks
from ..material.creator import get_material_creator
from ..material.reader import RelicMaterialReader

if TYPE_CHECKING:
    from .importer import DoW2ModelImporter


def import_materials(importer: DoW2ModelImporter, chunks: List[RelicChunk]):
    """Import all materials from MTRL chunks."""

    print("Importing materials...")
    mtrl_chunks = find_chunks("MTRL", chunks)
    mat_creator = get_material_creator(importer.data_path)

    for mtrl in mtrl_chunks:
        mat_data = RelicMaterialReader.read_material(importer.reader, mtrl, importer.data_path)
        mat = mat_creator.create_material(mat_data)
        importer.materials[mat_data.name] = mat
        print(f"  Imported material: {mat_data.name}")