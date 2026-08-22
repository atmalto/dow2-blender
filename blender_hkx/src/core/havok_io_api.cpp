#include "havok_io_api.h"

#include <stdio.h>
#include <string.h>

#include <string>

#include <Common/Base/hkBase.h>
#include <Animation/Animation/Animation/DeltaCompressed/hkaDeltaCompressedSkeletalAnimation.h>

#include "havok_runtime.h"
#include "animation_scene_builder.h"
#include "hkx_451_reader.h"
#include "hkx_451_writer.h"
#include "json_animation_input.h"
#include "json_animation_output.h"
#include "mod_studio_animation_bridge.h"
#include "hkx_451r_reader.h"
#include "hkx_55_writer.h"
#include "json_physics_input.h"
#include "json_physics_output.h"
#include "physics_scene_builder.h"
#include "json_ragdoll_input.h"
#include "json_ragdoll_output.h"
#include "..\ragdoll\hkx_451r_reader.h"
#include "..\ragdoll\hkx_451_writer.h"
#include "ragdoll_scene_builder.h"
#include "hkanim_packer.h"
#include "hkanim_unpacker.h"

namespace
{
	void setMessage(char* buffer, int bufferSize, const std::string& message)
	{
		if (!buffer || bufferSize <= 0)
		{
			return;
		}

		const int maxCopy = bufferSize - 1;
		const int messageLength = static_cast<int>(message.size());
		const int copyLength = messageLength < maxCopy ? messageLength : maxCopy;
		if (copyLength > 0)
		{
			memcpy(buffer, message.c_str(), static_cast<size_t>(copyLength));
		}
		buffer[copyLength] = '\0';
	}

	int fail(const std::string& message, char* buffer, int bufferSize)
	{
		setMessage(buffer, bufferSize, message);
		return HAVOK_IO_STATUS_ERROR;
	}

	int notImplemented(const std::string& message, char* buffer, int bufferSize)
	{
		setMessage(buffer, bufferSize, message);
		return HAVOK_IO_STATUS_NOT_IMPLEMENTED;
	}

	bool validatePaths(const char* inputPath, const char* outputPath)
	{
		return inputPath != 0 && inputPath[0] != '\0' && outputPath != 0 && outputPath[0] != '\0';
	}

	int initializeRuntime(HavokRuntime& runtime, char* buffer, int bufferSize)
	{
		if (!runtime.initialize())
		{
			return fail("Failed to initialize Havok runtime", buffer, bufferSize);
		}
		return HAVOK_IO_STATUS_OK;
	}

	int normalizeQuantizationBits(int quantizationBits)
	{
		if (quantizationBits < 1)
		{
			return 1;
		}
		if (quantizationBits > 16)
		{
			return 16;
		}
		return quantizationBits;
	}

	int normalizeBlockSize(int blockSize)
	{
		if (blockSize <= 0)
		{
			return 0;
		}
		return blockSize;
	}

	float clampTolerance(float tolerance)
	{
		if (tolerance < 0.0f)
		{
			return 0.0f;
		}
		if (tolerance > 1.0f)
		{
			return 1.0f;
		}
		return tolerance;
	}

	int normalizeSamplesPerFrame(int samplesPerFrame)
	{
		if (samplesPerFrame < 1)
		{
			return 1;
		}
		return samplesPerFrame;
	}
}

extern "C" HAVOK_IO_API int havok_io_get_version(char* buffer, int bufferSize)
{
	setMessage(buffer, bufferSize, "havok_io/1.0");
	return HAVOK_IO_STATUS_OK;
}

extern "C" HAVOK_IO_API int havok_io_animation_write(
	const char* inputJsonPath,
	const char* outputHkxPath,
	int quantizationBits,
	float tolerance,
	int useBlockCompression,
	int blockSize,
	int useThreeComponentQuaternions,
	char* messageBuffer,
	int messageBufferSize)
{
	if (!validatePaths(inputJsonPath, outputHkxPath))
	{
		return fail("Animation write requires input JSON and output HKX paths", messageBuffer, messageBufferSize);
	}

	HavokRuntime runtime;
	int status = initializeRuntime(runtime, messageBuffer, messageBufferSize);
	if (status != HAVOK_IO_STATUS_OK)
	{
		return status;
	}

	ParsedAnimationData parsedData;
	if (!parseAnimationJson(inputJsonPath, parsedData))
	{
		return fail("Failed to parse animation JSON", messageBuffer, messageBufferSize);
	}

	AnimationBuildOptions options;
	options.quantizationBits = normalizeQuantizationBits(quantizationBits);
	options.tolerance = clampTolerance(tolerance);
	options.useBlockCompression = useBlockCompression != 0;
	options.blockSize = normalizeBlockSize(blockSize);
	options.useThreeComponentQuaternions = useThreeComponentQuaternions != 0;

	BuiltAnimationGraph graph;
	if (!buildAnimationGraph(parsedData, options, graph))
	{
		return fail("Failed to build animation graph", messageBuffer, messageBufferSize);
	}

	if (!writeAnimationGraphAs451(
			graph.rootContainer,
			graph.compressedAnimation,
			&hkaDeltaCompressedSkeletalAnimationClass,
			outputHkxPath))
	{
		return fail("Failed to write animation HKX", messageBuffer, messageBufferSize);
	}

	setMessage(messageBuffer, messageBufferSize, "Animation HKX written successfully");
	return HAVOK_IO_STATUS_OK;
}

extern "C" HAVOK_IO_API int havok_io_animation_read(
	const char* inputHkxPath,
	const char* outputJsonPath,
	char* messageBuffer,
	int messageBufferSize)
{
	if (!validatePaths(inputHkxPath, outputJsonPath))
	{
		return fail("Animation read requires input HKX and output JSON paths", messageBuffer, messageBufferSize);
	}

	HavokRuntime runtime;
	int status = initializeRuntime(runtime, messageBuffer, messageBufferSize);
	if (status != HAVOK_IO_STATUS_OK)
	{
		return status;
	}

	ParsedAnimationData parsedData;
	if (!readAnimationGraph(inputHkxPath, parsedData))
	{
		return fail("Failed to read animation HKX", messageBuffer, messageBufferSize);
	}

	if (!writeAnimationJson(outputJsonPath, parsedData))
	{
		return fail("Failed to write animation JSON", messageBuffer, messageBufferSize);
	}

	setMessage(messageBuffer, messageBufferSize, "Animation JSON written successfully");
	return HAVOK_IO_STATUS_OK;
}

extern "C" HAVOK_IO_API int havok_io_animation_sample(
	const char* inputHkxPath,
	const char* outputJsonPath,
	int startFrame,
	int endFrame,
	int samplesPerFrame,
	char* messageBuffer,
	int messageBufferSize)
{
	if (!validatePaths(inputHkxPath, outputJsonPath))
	{
		return fail("Animation sample requires input HKX and output JSON paths", messageBuffer, messageBufferSize);
	}

	HavokRuntime runtime;
	int status = initializeRuntime(runtime, messageBuffer, messageBufferSize);
	if (status != HAVOK_IO_STATUS_OK)
	{
		return status;
	}

	ParsedAnimationData parsedData;
	if (!sampleAnimationGraph(inputHkxPath, startFrame, endFrame, normalizeSamplesPerFrame(samplesPerFrame), parsedData))
	{
		return fail("Failed to sample animation HKX", messageBuffer, messageBufferSize);
	}

	if (!writeAnimationJson(outputJsonPath, parsedData))
	{
		return fail("Failed to write sampled animation JSON", messageBuffer, messageBufferSize);
	}

	setMessage(messageBuffer, messageBufferSize, "Sampled animation JSON written successfully");
	return HAVOK_IO_STATUS_OK;
}

extern "C" HAVOK_IO_API int havok_io_animation_read_mod_studio(
	const char* inputHkxPath,
	char* outputJsonBuffer,
	int outputJsonBufferSize,
	int* outputJsonLength,
	char* messageBuffer,
	int messageBufferSize)
{
	if (inputHkxPath == 0 || inputHkxPath[0] == '\0')
	{
		return fail("Mod Studio animation read requires an input HKX path", messageBuffer, messageBufferSize);
	}
	if (outputJsonLength == 0)
	{
		return fail("Mod Studio animation read requires an output length pointer", messageBuffer, messageBufferSize);
	}

	HavokRuntime runtime;
	int status = initializeRuntime(runtime, messageBuffer, messageBufferSize);
	if (status != HAVOK_IO_STATUS_OK)
	{
		return status;
	}

	ParsedAnimationData parsedData;
	if (!readAnimationGraph(inputHkxPath, parsedData))
	{
		return fail("Failed to read animation HKX", messageBuffer, messageBufferSize);
	}

	std::string outputJson;
	if (!writeAnimationJsonForModStudio(parsedData, outputJson))
	{
		return fail("Failed to serialize Mod Studio animation JSON", messageBuffer, messageBufferSize);
	}

	*outputJsonLength = static_cast<int>(outputJson.size());
	if (outputJsonBuffer == 0 || outputJsonBufferSize <= 0)
	{
		setMessage(messageBuffer, messageBufferSize, "Mod Studio animation JSON size reported successfully");
		return HAVOK_IO_STATUS_OK;
	}

	if (outputJsonBufferSize <= static_cast<int>(outputJson.size()))
	{
		return fail("Mod Studio animation output buffer is too small", messageBuffer, messageBufferSize);
	}

	memcpy(outputJsonBuffer, outputJson.data(), outputJson.size());
	outputJsonBuffer[outputJson.size()] = '\0';
	setMessage(messageBuffer, messageBufferSize, "Mod Studio animation JSON written successfully");
	return HAVOK_IO_STATUS_OK;
}

extern "C" HAVOK_IO_API int havok_io_physics_write(
	const char* inputJsonPath,
	const char* outputHkxPath,
	char* messageBuffer,
	int messageBufferSize)
{
	if (!validatePaths(inputJsonPath, outputHkxPath))
	{
		return fail("Physics write requires input JSON and output HKX paths", messageBuffer, messageBufferSize);
	}

	HavokRuntime runtime;
	int status = initializeRuntime(runtime, messageBuffer, messageBufferSize);
	if (status != HAVOK_IO_STATUS_OK)
	{
		return status;
	}

	std::vector<RawPhysicsSystem> rawSystems;
	if (!parsePhysicsJson(inputJsonPath, rawSystems))
	{
		return fail("Failed to parse physics JSON", messageBuffer, messageBufferSize);
	}

	PhysicsBuildResult result;
	if (!buildPhysicsScene(rawSystems, result))
	{
		return fail("Failed to build physics scene", messageBuffer, messageBufferSize);
	}

	if (!writePhysicsPackfile(result.rootContainer, outputHkxPath))
	{
		return fail("Failed to write physics HKX", messageBuffer, messageBufferSize);
	}

	setMessage(messageBuffer, messageBufferSize, "Physics HKX written successfully");
	return HAVOK_IO_STATUS_OK;
}

extern "C" HAVOK_IO_API int havok_io_physics_read(
	const char* inputHkxPath,
	const char* outputJsonPath,
	char* messageBuffer,
	int messageBufferSize)
{
	if (!validatePaths(inputHkxPath, outputJsonPath))
	{
		return fail("Physics read requires input HKX and output JSON paths", messageBuffer, messageBufferSize);
	}

	HavokRuntime runtime;
	int status = initializeRuntime(runtime, messageBuffer, messageBufferSize);
	if (status != HAVOK_IO_STATUS_OK)
	{
		return status;
	}

	std::vector<RawPhysicsSystem> rawSystems;
	if (!readPhysicsPackfile(inputHkxPath, rawSystems))
	{
		return fail("Failed to read physics HKX", messageBuffer, messageBufferSize);
	}

	if (!writePhysicsJson(outputJsonPath, rawSystems, "hkx"))
	{
		return fail("Failed to write physics JSON", messageBuffer, messageBufferSize);
	}

	setMessage(messageBuffer, messageBufferSize, "Physics JSON written successfully");
	return HAVOK_IO_STATUS_OK;
}

extern "C" HAVOK_IO_API int havok_io_ragdoll_write(
	const char* inputJsonPath,
	const char* outputHkxPath,
	char* messageBuffer,
	int messageBufferSize)
{
	if (!validatePaths(inputJsonPath, outputHkxPath))
	{
		return fail("Ragdoll write requires input JSON and output HKX paths", messageBuffer, messageBufferSize);
	}

	HavokRuntime runtime;
	int status = initializeRuntime(runtime, messageBuffer, messageBufferSize);
	if (status != HAVOK_IO_STATUS_OK)
	{
		return status;
	}

	ragdoll_io::RawRagdollData rawData;
	if (!ragdoll_io::parseJSON(inputJsonPath, rawData))
	{
		return fail("Failed to parse ragdoll JSON", messageBuffer, messageBufferSize);
	}

	RagdollBuildResult buildResult;
	if (!buildRagdollScene(rawData, buildResult))
	{
		return fail("Failed to build ragdoll scene", messageBuffer, messageBufferSize);
	}

	if (!writeRagdollGraphAs451(buildResult, outputHkxPath))
	{
		return fail("Failed to write ragdoll HKX", messageBuffer, messageBufferSize);
	}

	setMessage(messageBuffer, messageBufferSize, "Ragdoll HKX written successfully");
	return HAVOK_IO_STATUS_OK;
}

extern "C" HAVOK_IO_API int havok_io_ragdoll_read(
	const char* inputHkxPath,
	const char* outputJsonPath,
	char* messageBuffer,
	int messageBufferSize)
{
	if (!validatePaths(inputHkxPath, outputJsonPath))
	{
		return fail("Ragdoll read requires input HKX and output JSON paths", messageBuffer, messageBufferSize);
	}

	HavokRuntime runtime;
	int status = initializeRuntime(runtime, messageBuffer, messageBufferSize);
	if (status != HAVOK_IO_STATUS_OK)
	{
		return status;
	}

	ragdoll_io::RawRagdollData rawData;
	if (!readRagdollPackfile(inputHkxPath, rawData))
	{
		return fail("Failed to read ragdoll HKX", messageBuffer, messageBufferSize);
	}

	if (!writeRagdollJson(outputJsonPath, rawData))
	{
		return fail("Failed to write ragdoll JSON", messageBuffer, messageBufferSize);
	}

	setMessage(messageBuffer, messageBufferSize, "Ragdoll JSON written successfully");
	return HAVOK_IO_STATUS_OK;
}

extern "C" HAVOK_IO_API int havok_io_hkanim_pack(
	const char* inputDirectory,
	const char* outputPath,
	const char* setName,
	int includeRagdollPlaceholder,
	char* messageBuffer,
	int messageBufferSize)
{
	if (!validatePaths(inputDirectory, outputPath))
	{
		return fail("HKANIM pack requires input directory and output path", messageBuffer, messageBufferSize);
	}

	HkAnimPackOptions options;
	options.includeRagdollPlaceholder = includeRagdollPlaceholder != 0;
	if (setName && setName[0] != '\0')
	{
		options.singleSetName = setName;
	}

	std::string errorMessage;
	if (!packHkAnimFromDirectory(inputDirectory, outputPath, options, errorMessage))
	{
		return fail(errorMessage.empty() ? "Failed to pack HKANIM container" : errorMessage, messageBuffer, messageBufferSize);
	}

	setMessage(messageBuffer, messageBufferSize, "HKANIM container written successfully");
	return HAVOK_IO_STATUS_OK;
}

extern "C" HAVOK_IO_API int havok_io_hkanim_unpack(
	const char* inputPath,
	const char* outputDirectory,
	char* messageBuffer,
	int messageBufferSize)
{
	if (!validatePaths(inputPath, outputDirectory))
	{
		return fail("HKANIM unpack requires input path and output directory", messageBuffer, messageBufferSize);
	}

	std::string errorMessage;
	if (!unpackHkAnimToDirectory(inputPath, outputDirectory, errorMessage))
	{
		return fail(errorMessage.empty() ? "Failed to unpack HKANIM container" : errorMessage, messageBuffer, messageBufferSize);
	}

	setMessage(messageBuffer, messageBufferSize, "HKANIM container unpacked successfully");
	return HAVOK_IO_STATUS_OK;
}