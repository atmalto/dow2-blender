"""
Collision file reader/writer for Dawn of War 2 .collision files.

Format validated against SimEngine.dll (sub_10032040) from DOW2.exe.

File Structure:
    Relic Chunky Header (36 bytes):
        - char[16]: Signature "Relic Chunky\r\n\x1a\x00"
        - uint32: Version (3)
        - uint32: Unknown1 (1)
        - uint32: Unknown2 (36)
        - uint32: Unknown3 (28) - chunk header size
        - uint32: Unknown4 (1)
    
    FOLDCMSH Chunk (0x434D5348):
        - Chunk header (28 bytes)
        - Contains DATADATA chunk
    
    DATADATA Chunk (0x44415441):
        - Chunk header (28 bytes)  
        - unk1 field = 1 (required for DATA chunks)
        - Collision data payload

Collision Data Payload:
    Header:
        - uint32: num_meshes
        - uint32: first_mesh_state_id
    
    Per Mesh (validated against ByteStreamAdapter::ReadString and sub_10032520):
        - uint32: mesh_state_id (only for mesh_idx > 0)
        - uint32: name_length
        - char[name_length]: mesh_name (no null terminator)
                - uint32: header_field_0 (stored in-memory but not consulted by the
                    loader or the collision query methods inspected)
                - uint32: header_field_1 (legacy count field; determines how many
                    trailing uint32 values are preserved)
                - uint32[header_field_1]: trailing header values
        - uint32: vertex_count
        - float[vertex_count * 3]: vertices (x, y, z) - 12 bytes per vertex
        - uint32: index_count (number of uint16 indices, = num_triangles * 3)
        - uint16[index_count]: face indices - 6 bytes per triangle

Assembly References (SimEngine.dll):
    - CollisionModel vtable: 0x1005b684
    - Load function: sub_10032040
    - CollisionModel::AddMesh: 0x100302b0
    - Chunky::ReadFolderChunk with 0x434D5348 (CMSH)
    - Chunky::ReadDataChunk with 0x44415441 (DATA)
    - ByteStreamAdapter::ReadString for mesh names
    - sub_10032520: reads uint32 array (header fields)
    - sub_100325E0: reads uint16 array (face indices)

Validation: 83/83 collision files pass byte-identical round-trip test.

The second payload field and the repeated leading uint32 before later meshes are
treated here as a per-mesh state ID. In shipped assets these correlate strongly
with DoW2 damage-state bins:
    1 = Healthy_LOD
    2 = Light_LOD
    3 = HeavyDMG_LOD
    4 = Wreck_LOD

The post-name header vector is preserved for round-trip fidelity. SimEngine's
load path copies it into the in-memory mesh object, but the collision query
methods inspected here (GetAABB, QueryHeight, Query, GetOBB2f) branch on the
per-mesh state ID and geometry buffers rather than on these header values.
"""

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, BinaryIO


# Relic Chunky signature
CHUNKY_SIGNATURE = b'Relic Chunky\r\n\x1a\x00'
CHUNKY_VERSION = 3
CHUNKY_UNKNOWN1 = 1
CHUNKY_UNKNOWN2 = 1


@dataclass
class CollisionMesh:
    """A single collision mesh with vertices and faces."""
    name: str
    mesh_type: int  # Legacy count field for trailing header uint32 values
    state_id: int = 1
    vertices: List[Tuple[float, float, float]] = field(default_factory=list)
    faces: List[Tuple[int, int, int]] = field(default_factory=list)
    header_fields: List[int] = field(default_factory=list)  # Opaque header data preserved for round-trip fidelity
    
    def __repr__(self):
        return f"CollisionMesh('{self.name}', state={self.state_id}, type={self.mesh_type}, verts={len(self.vertices)}, faces={len(self.faces)})"


@dataclass  
class CollisionData:
    """Container for collision file data."""
    collision_type: int  # Backward-compatible alias for the first mesh state ID
    meshes: List[CollisionMesh] = field(default_factory=list)
    
    def __repr__(self):
        return f"CollisionData(type={self.collision_type}, meshes={len(self.meshes)})"


def read_collision(filepath: str) -> CollisionData:
    """
    Read a .collision file and return CollisionData.
    
    Args:
        filepath: Path to the .collision file
        
    Returns:
        CollisionData object containing all meshes
        
    Raises:
        ValueError: If file format is invalid
    """
    with open(filepath, 'rb') as f:
        # Read and validate Relic Chunky header
        signature = f.read(16)
        if signature != CHUNKY_SIGNATURE:
            raise ValueError(f"Invalid file signature: expected Relic Chunky")
        
        # Skip chunky header (5 uint32s = 20 bytes: version, unk1, unk2, unk3, unk4)
        f.read(20)
        
        # Find FOLDCMSH chunk
        # Chunk header format: kind(4) + type(4) + version(4) + size(4) + name_len(4) + unk1(4) + unk2(4) = 28 bytes
        chunk_kind = f.read(4).decode('ascii')
        chunk_type = f.read(4).decode('ascii')
        chunk_version = struct.unpack('<I', f.read(4))[0] # _
        chunk_size = struct.unpack('<I', f.read(4))[0] # _
        name_len = struct.unpack('<I', f.read(4))[0]
        f.read(4)  # unk1
        f.read(4)  # unk2
        if name_len > 0:
            f.read(name_len)  # Skip chunk name
        
        if chunk_kind != 'FOLD' or chunk_type != 'CMSH':
            raise ValueError(f"Expected FOLDCMSH, got {chunk_kind}{chunk_type}")
        
        # Find DATADATA chunk inside FOLDCMSH
        chunk_kind = f.read(4).decode('ascii')
        chunk_type = f.read(4).decode('ascii')
        chunk_version = struct.unpack('<I', f.read(4))[0] # _
        data_size = struct.unpack('<I', f.read(4))[0]
        name_len = struct.unpack('<I', f.read(4))[0]
        f.read(4)  # unk1
        f.read(4)  # unk2
        if name_len > 0:
            f.read(name_len)  # Skip chunk name
        
        if chunk_kind != 'DATA' or chunk_type != 'DATA':
            raise ValueError(f"Expected DATADATA, got {chunk_kind}{chunk_type}")
        
        # Read collision data
        data = f.read(data_size)
        
    return _parse_collision_data(data)


def _parse_collision_data(data: bytes) -> CollisionData:
    """Parse the raw collision data bytes."""
    pos = 0
    
    # Header
    num_meshes = struct.unpack_from('<I', data, pos)[0]
    pos += 4
    first_mesh_state_id = struct.unpack_from('<I', data, pos)[0]
    pos += 4
    
    result = CollisionData(collision_type=first_mesh_state_id)
    
    for mesh_idx in range(num_meshes):
        if mesh_idx == 0:
            state_id = first_mesh_state_id
        else:
            state_id = struct.unpack_from('<I', data, pos)[0]
            pos += 4
        
        # Mesh name
        name_len = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        mesh_name = data[pos:pos+name_len].decode('utf-8').rstrip('\x00')
        pos += name_len
        
        # Preserve the opaque post-name header block exactly as stored.
        unk0 = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        mesh_type = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        
        # The second dword is just the count of trailing uint32 values.
        header_fields = [unk0, mesh_type]
        for _ in range(mesh_type):
            val = struct.unpack_from('<I', data, pos)[0]
            header_fields.append(val)
            pos += 4
        
        # Vertex count and vertices
        vertex_count = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        
        vertices = []
        for _ in range(vertex_count):
            x, y, z = struct.unpack_from('<fff', data, pos)
            vertices.append((x, y, z))
            pos += 12
        
        # Index count and face indices
        index_count = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        
        num_triangles = index_count // 3
        faces = []
        for _ in range(num_triangles):
            i0, i1, i2 = struct.unpack_from('<HHH', data, pos)
            faces.append((i0, i1, i2))
            pos += 6
        
        mesh = CollisionMesh(
            name=mesh_name,
            state_id=state_id,
            mesh_type=mesh_type,
            vertices=vertices,
            faces=faces,
            header_fields=header_fields
        )
        result.meshes.append(mesh)

    if result.meshes:
        result.collision_type = result.meshes[0].state_id
    
    return result


def write_collision(collision_data: CollisionData, filepath: str):
    """
    Write CollisionData to a .collision file.
    
    Args:
        collision_data: CollisionData object to write
        filepath: Output path for the .collision file
    """
    # Build collision data first
    data_content = _build_collision_data(collision_data)
    
    with open(filepath, 'wb') as f:
        # Write Relic Chunky header (36 bytes = 16 + 4*5)
        f.write(CHUNKY_SIGNATURE)  # 16 bytes
        f.write(struct.pack('<I', CHUNKY_VERSION))  # version = 3
        f.write(struct.pack('<I', 1))  # unknown1 = 1
        f.write(struct.pack('<I', 36))  # unknown2 = 36 (seems constant)
        f.write(struct.pack('<I', 28))  # unknown3 = 28 (chunk header size?)
        f.write(struct.pack('<I', 1))   # unknown4 = 1
        
        # Calculate sizes
        data_chunk_size = len(data_content)
        # DATA chunk header: 28 bytes
        fold_chunk_size = data_chunk_size + 28
        
        # Write FOLDCMSH chunk header (28 bytes: kind(4) + type(4) + ver(4) + size(4) + namelen(4) + unk1(4) + unk2(4))
        f.write(b'FOLD')
        f.write(b'CMSH')
        f.write(struct.pack('<I', 1))  # version
        f.write(struct.pack('<I', fold_chunk_size))  # size
        f.write(struct.pack('<I', 0))  # name_len = 0
        f.write(struct.pack('<I', 0))  # unk1 = 0
        f.write(struct.pack('<I', 0))  # unk2 = 0
        
        # Write DATADATA chunk header (28 bytes)
        f.write(b'DATA')
        f.write(b'DATA')
        f.write(struct.pack('<I', 1))  # version
        f.write(struct.pack('<I', data_chunk_size))  # size
        f.write(struct.pack('<I', 0))  # name_len = 0
        f.write(struct.pack('<I', 1))  # unk1 = 1 (seems constant for DATA chunks)
        f.write(struct.pack('<I', 0))  # unk2 = 0
        
        # Write collision data
        f.write(data_content)


def _build_collision_data(collision_data: CollisionData) -> bytes:
    """Build the raw collision data bytes from CollisionData."""
    parts = []
    
    # Header
    parts.append(struct.pack('<I', len(collision_data.meshes)))
    first_mesh_state_id = collision_data.meshes[0].state_id if collision_data.meshes else collision_data.collision_type
    parts.append(struct.pack('<I', first_mesh_state_id))
    
    for mesh_idx, mesh in enumerate(collision_data.meshes):
        if mesh_idx > 0:
            parts.append(struct.pack('<I', mesh.state_id))
        
        # Mesh name (NO null terminator in original format)
        name_bytes = mesh.name.encode('utf-8')
        parts.append(struct.pack('<I', len(name_bytes)))
        parts.append(name_bytes)
        
        # Header fields
        for val in mesh.header_fields:
            parts.append(struct.pack('<I', val))
        
        # Vertices
        parts.append(struct.pack('<I', len(mesh.vertices)))
        for x, y, z in mesh.vertices:
            parts.append(struct.pack('<fff', x, y, z))
        
        # Face indices
        index_count = len(mesh.faces) * 3
        parts.append(struct.pack('<I', index_count))
        for i0, i1, i2 in mesh.faces:
            parts.append(struct.pack('<HHH', i0, i1, i2))
    
    return b''.join(parts)


def collision_info(collision_data: CollisionData) -> str:
    """Return a human-readable summary of collision data."""
    lines = []
    lines.append(f"First Mesh State: {collision_data.collision_type}")
    lines.append(f"Number of Meshes: {len(collision_data.meshes)}")
    
    for i, mesh in enumerate(collision_data.meshes):
        lines.append(f"\nMesh {i}: '{mesh.name}'")
        lines.append(f"  State: {mesh.state_id}")
        lines.append(f"  Type: {mesh.mesh_type}")
        lines.append(f"  Vertices: {len(mesh.vertices)}")
        lines.append(f"  Faces: {len(mesh.faces)}")
        lines.append(f"  Header: {mesh.header_fields}")
    
    return '\n'.join(lines)
