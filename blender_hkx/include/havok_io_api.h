#ifndef DOW2_HAVOK_IO_API_H
#define DOW2_HAVOK_IO_API_H

#if defined(_WIN32)
#	if defined(HAVOK_IO_EXPORTS)
#		define HAVOK_IO_API __declspec(dllexport)
#	else
#		define HAVOK_IO_API __declspec(dllimport)
#	endif
#else
#	define HAVOK_IO_API
#endif

enum HavokIoStatus
{
	HAVOK_IO_STATUS_OK = 0,
	HAVOK_IO_STATUS_ERROR = 1,
	HAVOK_IO_STATUS_NOT_IMPLEMENTED = 2
};

#ifdef __cplusplus
extern "C"
{
#endif

HAVOK_IO_API int havok_io_get_version(char* buffer, int bufferSize);

HAVOK_IO_API int havok_io_animation_write(
	const char* inputJsonPath,
	const char* outputHkxPath,
	int quantizationBits,
	float tolerance,
	int useBlockCompression,
	int blockSize,
	int useThreeComponentQuaternions,
	char* messageBuffer,
	int messageBufferSize);

HAVOK_IO_API int havok_io_animation_read(
	const char* inputHkxPath,
	const char* outputJsonPath,
	char* messageBuffer,
	int messageBufferSize);

HAVOK_IO_API int havok_io_animation_sample(
	const char* inputHkxPath,
	const char* outputJsonPath,
	int startFrame,
	int endFrame,
	int samplesPerFrame,
	char* messageBuffer,
	int messageBufferSize);

HAVOK_IO_API int havok_io_animation_read_mod_studio(
	const char* inputHkxPath,
	char* outputJsonBuffer,
	int outputJsonBufferSize,
	int* outputJsonLength,
	char* messageBuffer,
	int messageBufferSize);

HAVOK_IO_API int havok_io_physics_write(
	const char* inputJsonPath,
	const char* outputHkxPath,
	char* messageBuffer,
	int messageBufferSize);

HAVOK_IO_API int havok_io_physics_read(
	const char* inputHkxPath,
	const char* outputJsonPath,
	char* messageBuffer,
	int messageBufferSize);

HAVOK_IO_API int havok_io_ragdoll_write(
	const char* inputJsonPath,
	const char* outputHkxPath,
	char* messageBuffer,
	int messageBufferSize);

HAVOK_IO_API int havok_io_ragdoll_read(
	const char* inputHkxPath,
	const char* outputJsonPath,
	char* messageBuffer,
	int messageBufferSize);

HAVOK_IO_API int havok_io_hkanim_pack(
	const char* inputDirectory,
	const char* outputPath,
	const char* setName,
	int includeRagdollPlaceholder,
	char* messageBuffer,
	int messageBufferSize);

HAVOK_IO_API int havok_io_hkanim_unpack(
	const char* inputPath,
	const char* outputDirectory,
	char* messageBuffer,
	int messageBufferSize);

#ifdef __cplusplus
}
#endif

#endif