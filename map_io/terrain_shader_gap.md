Terrain Tile Runtime Model

This note captures the verified executable-side terrain tile path from the live Retribution IDB.

Verified load path:
- `TerrainTextureLoad::Load`
- `RenderComposite::Load`
- `RenderCompositeTiles::Load`
- `RenderTiles`
- `UpdateShaderParams`

What `RenderCompositeTiles::Load` reads:
- `RCTI/HEAD` for the layer and mask counts
- `RCTI/LAYR` for the layer records
- `RCTI/MASK` for the two mask textures
- `RCTI/USAG` for the per-chunk active-layer byte grid
- older data without `USAG` falls back to a fully active grid filled with `0xFF`

What the data block contains:
- `+0x28/+0x30/+0x38` vector storage for 72-byte layer records
- `+0x40/+0x48` the two mask texture pointers
- `+0x68` the usage-grid pointer
- `+0x70` the usage-grid dimensions and stride
- `+0xB0..+0xCC` shader keys for `layerTexture0..7`
- `+0xD0/+0xD4` shader keys for `maskTexture0/1`
- `+0xD8` shader key for `layerActive`
- `+0xE0` active-layer count `8`
- `+0xE8` bool type info
- `+0x100` `MeshShaderGeometry*`

What `RenderTiles` does:
- reads one usage byte per chunk using `x + stride*y`
- expands bits `0..7` into the eight active-layer booleans
- passes those booleans directly to `MeshShaderGeometry::SetActiveLayers`

What `UpdateShaderParams` uploads:
- `layerTexture0..7` from each 72-byte layer record
- `maskTexture0/1` from the loaded mask textures
- a mask-UV transform matrix derived from the terrain bounds rect and `0.5` offsets

Shader-side shading model from `terrain_tileongeometry_full.asm`:
- the file contains multiple terrain pixel-shader variants with the same structure and shifted register bindings
- each variant declares `mask0Select[8]`, `mask1Select[8]`, and `maskUVMatrix`
- the selector bindings move across variants, for example `mask0Select`/`mask1Select` appear at windows like `c165/c168`, `c167/c169`, `c173/c180`, or `c173/c181`, with `maskUVMatrix` following after them
- the shader body repeatedly does `texld` / `dp4` / `if_lt` / `texldl` / `mad` blocks per layer, using the selector vectors to turn the two sampled mask textures into layer weights
- the selector arrays are variant-local constant blocks, not runtime chunk data; only the chunk usage byte controls which layers are active
- the mask textures are sampled once, then dotted against selector vectors with `dp4`
- per-layer contributions are gated with `if_lt` threshold checks
- the selectors are not the chunk usage bits themselves; they are shader constants used to turn the sampled mask channels into layer selection weights
- the register layout shifts between variants, but the shape is consistent: two mask selector arrays plus a 2x4 mask UV matrix

Layer record layout confirmed from live IDA:
- two stored names
- layer texture at `+48`
- ground texture at `+56`
- cliff texture at `+64`

What this means for the importer:
- the active-layer model is chunk-local, not a global RGBA channel map
- the loader uses real layer records plus two mask textures and a per-chunk usage grid
- the remaining unknown is mostly the exact meaning of the selector vectors for each shader variant, not the tile-loading model itself
- engine-side initializer probes in IDA only register shader resource names and dictionary keys; they do not encode the selector vector values themselves
- so the exact selector semantics come from the compiled shader math plus the runtime constant values, not from the engine-side string registration path