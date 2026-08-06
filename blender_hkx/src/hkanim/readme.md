# hkanim_packer_451r

Standalone pack/unpack tool for Dawn of War II `.hkanim` containers.

This tool does not rebuild Havok animation data. It wraps existing 4.5.1-compatible `.hkx` animation files into the Relic Chunky `.hkanim` container format used by ModelEditor and the game.

## Proven Container Layout

- Relic Chunky file header: `Relic Chunky\r\n\x1a\x00`
- Root chunk: `FOLD/HAAS`, version `1`
- One child per animation set: `DATA/HAWS`, version `1`, chunk name = set name
- `HAWS` payload:
  - `u32` animation count
  - repeated `u32 byte_len + raw bytes` animation names, no null terminator
  - repeated `u32 blob_size + raw hkx bytes`

Observed game assets sort set folders alphabetically, sort `.hkx` files alphabetically within each set, and append an empty `set\\ragdoll` entry with a zero-size blob.

## Usage

```text
hkanim_packer_451r.exe pack <input_folder> <output.hkanim> [--set-name <name>] [--no-ragdoll-placeholder]
hkanim_packer_451r.exe unpack <input.hkanim> <output_folder>
```

- `pack` walks the selected root plus one level of subfolders.
- Root-level `.hkx` files become one set named after the root folder unless `--set-name` is supplied.
- Each child subfolder with `.hkx` files becomes one additional set named after that subfolder.
- `--set-name` overrides the single-set name when packing one folder directly.
- `--no-ragdoll-placeholder` disables the default empty `ragdoll` slot.
- `unpack` creates `.hkx` files beneath the output folder using the stored set names as subfolders.

## Integration Use

The reusable APIs are in `hkanim_packer.h` and `hkanim_unpacker.h`:

- `buildHkAnimSetsFromDirectory(...)`
- `writeHkAnimContainer(...)`
- `packHkAnimFromDirectory(...)`
- `readHkAnimContainer(...)`
- `unpackHkAnimToDirectory(...)`

This is intended to be callable from the Blender exporter after individual `.hkx` files have already been generated.