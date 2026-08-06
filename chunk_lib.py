# Relic Chunky File Library
import struct
from dataclasses import dataclass, field
from typing import List, Optional, BinaryIO
from mathutils import Matrix


@dataclass
class RelicChunk:
    chunk_kind: str = ""      # "FOLD" or "DATA"
    chunk_type: str = ""      # 4-char ID like "MTRL", "INFO", "VAR ", etc
    version: int = 0
    size: int = 0
    name: str = ""
    unk1: int = 0
    unk2: int = 0
    data_pos: int = 0
    children: List['RelicChunk'] = field(default_factory=list)


class ChunkReader:
    RELIC_CHUNKY_SIGNATURE = b'Relic Chunky\r\n\x1a\x00'
    
    def __init__(self, file: BinaryIO):
        self.file = file
        self.root_chunks: List[RelicChunk] = []
    
    def read_byte(self) -> int:
        return struct.unpack('B', self.file.read(1))[0]
    
    def read_short(self) -> int:
        return struct.unpack('<H', self.file.read(2))[0]
    
    def read_long(self, unsigned: bool = True) -> int:
        fmt = '<I' if unsigned else '<i'
        return struct.unpack(fmt, self.file.read(4))[0]
    
    def read_float(self) -> float:
        return struct.unpack('<f', self.file.read(4))[0]
    
    def read_str(self, length: int) -> str:
        return self.file.read(length).decode('utf-8', errors='replace').rstrip('\x00')
    
    def read_cstr(self) -> str:
        chars = []
        while True:
            c = self.file.read(1)
            if c == b'\x00' or not c:
                break
            chars.append(c)
        return b''.join(chars).decode('utf-8', errors='replace')
    
    def read_matrix(self) -> Matrix:
        """Read a 4x3 matrix (12 floats) from file - Relic format"""
        rows = []
        for _ in range(4):
            row = [self.read_float() for _ in range(3)]
            row.append(0.0 if len(rows) < 3 else 1.0)  # Add 4th column (i.e. 0,0,0,1)
            rows.append(row)
        return Matrix(rows).transposed()  # Transpose for column-major to row-major
    
    def read_matrix_4x4(self) -> Matrix:
        """Read a full 4x4 matrix (16 floats) from file"""
        rows = []
        for _ in range(4):
            row = [self.read_float() for _ in range(4)]
            rows.append(row)
        return Matrix(rows)
    
    def read_relic_chunky(self) -> bool:
        signature = self.file.read(16)
        if signature != self.RELIC_CHUNKY_SIGNATURE:
            return False
        self.read_long()
        self.read_long()
        self.read_long()
        return True
    
    def read_chunk_header(self) -> Optional[RelicChunk]:
        kind_bytes = self.file.read(4)
        if len(kind_bytes) < 4:
            return None
        chunk = RelicChunk()
        chunk.chunk_kind = kind_bytes.decode('utf-8', errors='replace')
        chunk.chunk_type = self.file.read(4).decode('utf-8', errors='replace')
        chunk.version = self.read_long()
        chunk.size = self.read_long()
        name_len = self.read_long()
        chunk.unk1 = self.read_long()
        chunk.unk2 = self.read_long()
        if name_len > 0:
            chunk.name = self.read_str(name_len)
        chunk.data_pos = self.file.tell()
        return chunk
    
    def read_chunks(self, parent: Optional[RelicChunk] = None, end_pos: int = -1) -> List[RelicChunk]:
        chunks = []
        if end_pos < 0:
            self.file.seek(0, 2)
            end_pos = self.file.tell()
            self.file.seek(36)  # Skip Relic Chunky header (36 bytes)
        while self.file.tell() < end_pos:
            chunk = self.read_chunk_header()
            if chunk is None:
                break
            if chunk.chunk_kind == "FOLD":
                chunk.children = self.read_chunks(chunk, chunk.data_pos + chunk.size)
            else:
                self.file.seek(chunk.data_pos + chunk.size)
            chunks.append(chunk)
            if parent:
                parent.children.append(chunk)
        if not parent:
            self.root_chunks = chunks
        return chunks
    
    def get_chunk(self, chunk_type: str, chunks: List[RelicChunk] = None) -> Optional[RelicChunk]:
        if chunks is None:
            chunks = self.root_chunks
        for chunk in chunks:
            if chunk.chunk_type == chunk_type:
                return chunk
            if chunk.children:
                result = self.get_chunk(chunk_type, chunk.children)
                if result:
                    return result
        return None
    
    def find_chunks(self, chunk_type: str, chunks: List[RelicChunk] = None) -> List[RelicChunk]:
        if chunks is None:
            chunks = self.root_chunks
        results = []
        for chunk in chunks:
            if chunk.chunk_type == chunk_type:
                results.append(chunk)
            if chunk.children:
                results.extend(self.find_chunks(chunk_type, chunk.children))
        return results
    
    def seek_chunk(self, chunk: RelicChunk):
        self.file.seek(chunk.data_pos)


class ChunkWriter:
    RELIC_CHUNKY_SIGNATURE = b'Relic Chunky\r\n\x1a\x00' # default relic chunky signature for .model to myunderstsanding
    
    def __init__(self, file: BinaryIO):
        self.file = file
    
    def write_byte(self, value: int):
        self.file.write(struct.pack('B', value & 0xFF))
    
    def write_short(self, value: int):
        self.file.write(struct.pack('<H', value & 0xFFFF))
    
    def write_long(self, value: int, unsigned: bool = True):
        if unsigned:
            self.file.write(struct.pack('<I', value & 0xFFFFFFFF))
        else:
            self.file.write(struct.pack('<i', value))
    
    def write_float(self, value: float):
        self.file.write(struct.pack('<f', value))
    
    def write_str(self, value: str):
        self.file.write(value.encode('utf-8'))
    
    def write_matrix(self, matrix: Matrix):
        """Write a 4x3 matrix (12 floats) - Relic format"""
        m = matrix.transposed()  # Row-major to column-major
        for row in range(4):
            for col in range(3):  # Only first 3 columns
                self.write_float(m[row][col])
    
    def write_matrix_4x4(self, matrix: Matrix):
        """Write a full 4x4 matrix (16 floats)"""
        for row in range(4):
            for col in range(4):
                self.write_float(matrix[row][col])
    
    def write_relic_chunky(self):
        """Write Relic Chunky file header"""
        self.file.write(self.RELIC_CHUNKY_SIGNATURE)  # 16 bytes
        self.write_long(3)    # 0x03
        self.write_long(1)    # 0x01  
        self.write_long(36)   # 0x24
        self.write_long(28)   # 0x1C
        self.write_long(1)    # 0x01
        # Total: 16 + 20 = 36 bytes
    
    def write_chunk_header(self, kind: str, chunk_type: str, version: int, 
                           size: int, name: Optional[str], flag: int) -> int:
        """Write chunk header
        
        Args:
            kind: "FOLD" or "DATA"
            chunk_type: 4-char type ID
            version: chunk version
            size: data size (0, will be updated later)
            name: chunk name or None
            flag: unk1 flag value (-1 becomes 0xFFFFFFFF)
        
        Returns:
            Position after header (where data starts)
        """
        self.write_str(kind)       # 4 bytes
        self.write_str(chunk_type) # 4 bytes
        self.write_long(version)   # 4 bytes
        self.write_long(size)      # 4 bytes - data size
        
        # Name length (+1 for null if name exists)
        if name and len(name) > 0:
            self.write_long(len(name) + 1)  # +1 for null terminator
        else:
            self.write_long(0)
        
        # Flags (unk1, unk2)
        self.write_long(flag if flag >= 0 else 0xFFFFFFFF)
        self.write_long(0)
        
        # Write chunk name with null terminator
        if name and len(name) > 0:
            self.write_str(name)
            self.write_byte(0)  # Null terminator
        
        return self.file.tell()
    
    def update_chunk_size(self, header_pos: int, data_start_pos: int):
        current_pos = self.file.tell()
        size = current_pos - data_start_pos
        self.file.seek(header_pos + 12)
        self.write_long(size)
        self.file.seek(current_pos)


def get_chunk(chunk_type: str, chunks: List[RelicChunk]) -> Optional[RelicChunk]:
    for chunk in chunks:
        if chunk.chunk_type == chunk_type:
            return chunk
        if chunk.children:
            result = get_chunk(chunk_type, chunk.children)
            if result:
                return result
    return None


def find_chunks(chunk_type: str, chunks: List[RelicChunk]) -> List[RelicChunk]:
    """Find all chunks of a type recursively (searches all descendants)"""
    results = []
    for chunk in chunks:
        if chunk.chunk_type == chunk_type:
            results.append(chunk)
        if chunk.children:
            results.extend(find_chunks(chunk_type, chunk.children))
    return results


def find_chunks_direct(chunk_type: str, chunks: List[RelicChunk]) -> List[RelicChunk]:
    """Find chunks of a type in direct children only (non-recursive)"""
    results = []
    for chunk in chunks:
        if chunk.chunk_type == chunk_type:
            results.append(chunk)
    return results
