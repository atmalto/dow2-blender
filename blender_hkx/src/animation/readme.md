# anim_blender2khx_451r

Converts JSON animation data from Blender to Havok HKX format using Havok SDK 5.5.0, and can also read Havok animation HKX files back into the same JSON schema for the Blender importer. Write mode builds the animation graph in memory and writes the final output as a Havok 4.5.1 packfile for Dawn of War 2.

## Source Layout

- `animation/main.cpp`: CLI entry point
- `animation/json_animation_input.*`: JSON parsing and raw animation input structs
- `animation/json_animation_output.*`: JSON writer for HKX read mode
- `animation/havok_runtime.*`: Havok SDK setup and teardown
- `animation/animation_scene_builder.*`: 5.5 skeleton/animation graph construction and compression
- `animation/hkx_451_reader.*`: HKX loader and animation sampling for import
- `animation/hkx_451_writer.*`: 4.5.1 mirror graph serialization

The older root-level animation source files are still present as reference during the refactor, but the build now targets the modular files above.

## What The Tool Does

- Parses JSON input containing skeleton hierarchy, reference pose, and animation frames
- Creates Havok skeleton and animation objects using SDK 5.5.0
- Applies delta compression with configurable quantization (8/16-bit) and tolerance settings
- Converts the in-memory 5.5 animation graph into a Havok 4.5.1-compatible packfile for DoW2
- Loads animation HKX files through Havok, samples transform tracks, and writes importer JSON output

## Requirements

- **Havok SDK 5.5.0**: Full SDK installation with headers and libraries
- **Visual Studio 2008**: For compilation (SDK libs are VS2005 but compatible)


## Building

1. Unpack Havok SDK 5.5.0 to a directory (e.g., `C:\Havok\SDK_5_5_0`, I recommend placing it in the root directory of the addon to continue with the following steps wihtout modification)
2. Set `HAVOK_SDK_ROOT` if your SDK is not located at `..\working\havok_sdk_5_5_x`
3. Run `build_anim_451r.bat` or `build_anim_451r.sh`
4. Output: `anim_blender2khx_451r.exe` in the same directory

## Usage

```
anim_blender2khx_451r.exe input.json output.hkx [quantization_bits] [tolerance]
anim_blender2khx_451r.exe write input.json output.hkx [quantization_bits] [tolerance]
anim_blender2khx_451r.exe read input.hkx output.json
```

- `quantization_bits`: 8 or 16 (default: 16 for best quality)
- `tolerance`: 0.0 to 1.0 (default: 0.0 for lossless)

Example: `anim_blender2khx_451r.exe animation.json output.hkx 16 0.0005`
Example: `anim_blender2khx_451r.exe read walk.hkx walk.json`

## Notes

- Output is Havok 4.5.1 hkx format written from a 5.5 in-memory animation graph
- Read mode emits the same JSON schema used by write mode so the Blender importer and exporter stay aligned
- Tolerance > 0 enables delta compression for smaller files but may introduce artifacts (and drift)
- 16-bit quantization + low tolerance recommended (or less) for quality
- The factor that leads to the largest file size reduction is the tolerance setting, the higher the tolerance, the greater the drift, but the smaller the file size; quantization isnt very consequential.
- This tool isn't meant to be used alone, but as part of a toolchain for the 
DoW2 Blender add-on that post-processes the animation to convert json to hkx. To use this tool without the plugin, follow the json format in the appendix. Alternatively, refer to the add-on source code for how to generate the json from Blender.



## Appendix

### JSON Format

```json
{
  "skeleton_name": "DoW2_Armature",
  "duration": 1.333,
  "bones": ["Bip01", "Bip01 Pelvis", ...],
  "parent_indices": [-1, 0, 1, ...],
  "reference_pose": [
    {"pos": [x, y, z], "rot": [x, y, z, w], "scale": [x, y, z]},
    ...
  ],
  "num_frames": 41,
  "transforms": [
    [  // frame 0
      {"pos": [x, y, z], "rot": [x, y, z, w], "scale": [x, y, z]},  // bone 0
      {"pos": [x, y, z], "rot": [x, y, z, w], "scale": [x, y, z]},  // bone 1
      ...
    ],
    ...  // more frames
  ]
}
```

#### Field Explanations

#### `skeleton_name`
A string identifier for the skeleton. Used internally by Havok.

#### `bones`
An ordered array of bone names. The index of each bone in this array is used throughout the file to reference that bone.

#### `parent_indices`
An array of integers, one per bone. Each value is the index of that bone's parent in the `bones` array, or `-1` if the bone has no parent (i.e., it's a root bone).

Example: If `bones = ["Root", "Spine", "Head"]` and `parent_indices = [-1, 0, 1]`, then:
- "Root" has no parent (-1)
- "Spine"'s parent is "Root" (index 0)
- "Head"'s parent is "Spine" (index 1)

#### `reference_pose`
An array of transforms, one per bone, defining the skeleton's bind/rest pose. Each transform contains:
- `pos`: Position [x, y, z] relative to the parent bone (local space)
- `rot`: Rotation as quaternion [x, y, z, w] relative to parent
- `scale`: Scale [x, y, z] relative to parent

These transforms are in **local space** (relative to parent). For root bones, they're relative to world origin.

#### `duration`
The total length of the animation in seconds. Calculated as `(num_frames - 1) / fps`.

For example, a 41-frame animation at 30 FPS:
- Frame 0 is at t=0.0
- Frame 40 is at t=40/30 = 1.333 seconds
- Duration = 1.333 seconds

#### `num_frames`
Total number of keyframes in the animation.

#### `transforms`
A 2D array of transforms: `transforms[frame_index][bone_index]`.

Each transform contains:
- `pos`: Local position relative to parent bone
- `rot`: Local rotation as quaternion [x, y, z, w] relative to parent
- `scale`: Local scale relative to parent

**Important**: All transforms are in **local space** (relative to parent bone), not world space. The Havok animation system expects local transforms, which it then chains together using the parent hierarchy to compute final world positions.

#### Coordinate System

The JSON uses **DirectX/Havok coordinate system**:
- X = right
- Y = up  
- Z = forward

If your source data uses a different coordinate system (e.g., Blender's Z-up), you must convert before writing the JSON.

---

### How The Refactored Animation Tool Works

This section explains the internal design and flow of the converter for developers who want to understand or modify it.

#### Overview

The tool converts JSON animation data into Havok's proprietary HKX binary format using the Havok SDK 5.5.0. The process involves:

1. Parsing JSON into a `ParsedAnimationData` container before Havok initialization
2. Initializing the Havok SDK memory system
3. Building a Havok 5.5 animation graph in memory
4. Compressing the animation using delta compression
5. Translating the runtime graph into explicit Havok 4.5.1 mirror structs
6. Serializing the mirrored graph as a 4.5.1 binary packfile

#### Program Flow

```
main()
  │
  ├─> Parse CLI arguments (input, output, quantization_bits, tolerance)
  │
  ├─> parseAnimationJson()
  │     ├─> Parse skeleton_name, duration, num_frames
  │     ├─> Parse bones[] array
  │     ├─> Parse parent_indices[] array  
  │     ├─> Parse reference_pose[] transforms
  │     └─> Parse transforms[][] (frames × bones)
  │
  ├─> HavokRuntime::initialize()
  │     ├─> Create hkPoolMemory and hkThreadMemory
  │     ├─> Call hkBaseSystem::init()
  │     └─> Allocate 1MB stack buffer for Havok operations
  │
  ├─> buildAnimationGraph()
  │     ├─> Build hkaSkeleton from names, parents, and reference pose
  │     ├─> Build hkaInterleavedSkeletalAnimation from frame transforms
  │     ├─> Create per-bone hkaAnnotationTrack entries
  │     ├─> Compress to hkaDeltaCompressedSkeletalAnimation
  │     ├─> Build hkaAnimationBinding with 1:1 track-to-bone mapping
  │     ├─> Build hkaAnimationContainer
  │     └─> Build hkRootLevelContainer with an "Animation Container" named variant
  │
  ├─> writeAnimationGraphAs451()
  │     ├─> Copy the runtime graph into explicit 4.5.1 mirror structs
  │     ├─> Register the legacy delta animation vtable/class mapping
  │     ├─> Call hkBinaryPackfileWriter::setContentsWithRegistry()
  │     ├─> Set Win32 32-bit layout for DoW2 compatibility
  │     ├─> Set contents version to Havok-4.5.1-r1
  │     └─> Write the final binary HKX to output file
  │
  └─> Cleanup and exit
```

#### Key Havok Classes

**Class : Purpose**
 `hkaSkeleton` : Defines bone hierarchy with names, parent indices, and reference pose 
 `hkaBone` : Individual bone with name and lock flags 
 `hkaInterleavedSkeletalAnimation` : Uncompressed animation with all transforms stored sequentially 
 `hkaDeltaCompressedSkeletalAnimation` : Compressed animation using delta encoding and quantization 
 `hkaAnimationBinding` : Maps animation tracks to skeleton bones 
 `hkaAnimationContainer` : Top-level container holding skeleton, animations, and bindings 
 `hkRootLevelContainer` : Root serialization container with named variants 
 `hkQsTransform` : Quaternion-Scale transform (pos, rot, scale) 
 `Legacy451DeltaCompressedSkeletalAnimation` : Local mirror of the 4.5.1 compressed animation layout used for final serialization 
 `hkVtableClassRegistry` : Ensures the legacy polymorphic animation object is emitted with the correct 4.5.1 class metadata 

#### Memory Model (SDK 5.5)

The JSON parser runs before Havok starts and stores data in normal C++ containers. Once Havok is initialized, the runtime graph is allocated with Havok's manual memory management model:

```cpp
// Initialize memory system (in later SDKs, this only requires hkMemoryInitUtil)
hkPoolMemory* memoryManager = new hkPoolMemory();
hkThreadMemory* threadMemory = new hkThreadMemory(memoryManager, 16);
hkBaseSystem::init(memoryManager, threadMemory, errorReport);

// Allocate stack for Havok operations (required)
char* stackBuffer = hkAllocate<char>(stackSize, HK_MEMORY_CLASS_BASE);
hkThreadMemory::getInstance().setStackArea(stackBuffer, stackSize);
```

Arrays are allocated with `hkAllocate<T>()` and sizes stored separately:
```cpp
skeleton->m_bones = hkAllocate<hkaBone*>(numBones, HK_MEMORY_CLASS_ANIMATION);
skeleton->m_numBones = numBones;
```

#### Delta Compression

The `hkaDeltaCompressedSkeletalAnimation` class compresses animation data by

1. Quantization: Reduces floating-point precision to 8 or 16 bits
2. Delta encoding: Stores differences between frames instead of absolute values
3. Tolerance-based culling: Removes keyframes within tolerance threshold

```cpp
hkaDeltaCompressedSkeletalAnimation::CompressionParams dparams;
dparams.m_quantizationBits = 16;           // 8 or 16 bits per component
dparams.m_blockSize = 65535;               // Compression block size
dparams.m_absolutePositionTolerance = 0.0; // Absolute position tolerance
dparams.m_relativePositionTolerance = 0.0; // Position tolerance
dparams.m_rotationTolerance = 0.0;         // Rotation tolerance
dparams.m_scaleTolerance = 0.0;            // Scale tolerance
dparams.m_absoluteFloatTolerance = 0.0;    // Float-track tolerance
```
You can extend the tool with custom args for each of these parameters if you have a pos/rot/scale sensitive sytem.

#### Serialization

The final HKX is not written directly from the 5.5 runtime graph. The writer first builds a mirror graph matching the 4.5.1 class layout, then serializes that mirror graph with an explicit registry/listener pair:

```cpp
ExactLegacyClassListener listener(&legacyAnimation, &g_legacy451DeltaCompressedSkeletalAnimationClass);
hkVtableClassRegistry registry;
registry.registerVtable(
  *reinterpret_cast<const void* const*>(&legacyAnimation),
  &g_legacy451DeltaCompressedSkeletalAnimationClass);

hkBinaryPackfileWriter writer;
writer.setContentsWithRegistry(&legacyRoot, hkRootLevelContainerClass, &registry, &listener);

hkPackfileWriter::Options options;
options.m_layout = hkStructureLayout::MsvcWin32LayoutRules;  // this is the 32-bit layout
options.m_writeMetaInfo = true;  // Include type metadata
options.m_contentsVersion = "Havok-4.5.1-r1";

writer.save(stream.getStreamWriter(), options);
```


#### A further note on build requirements

Linking is done against: `hkBase.lib`, `hkSerialize.lib`, `hkaAnimation.lib`, `hkaInternal.lib`, `hkCompat.lib`

Key compilation units register Havok's type system and compatibility layer:
```cpp
#include <Common/Base/keycode.cxx>  // License key
#define HK_CLASSES_FILE <Common/Serialize/Classlist/hkAnimationClasses.h>
#include <Common/Serialize/Util/hkBuiltinTypeRegistry.cxx>  // Type registry

#define HK_COMPAT_FILE <Common/Compat/hkCompatVersions.h>
#include <Common/Compat/hkCompat_All.cxx>  // Compatibility conversions and version tables
```