#include <stdio.h>
#include <stdlib.h>
#include <string>

#include "havok_io_api.h"

namespace
{
	const int kMessageBufferSize = 4096;

	void printUsage()
	{
		printf("Usage:\n");
		printf("  havok_io_cli.exe animation write <input.json> <output.hkx> [quantization_bits] [tolerance] [use_block_compression] [block_size] [use_three_component_quaternions]\n");
		printf("  havok_io_cli.exe animation read <input.hkx> <output.json>\n");
		printf("  havok_io_cli.exe animation sample <input.hkx> <output.json> <start_frame> <end_frame> [samples_per_frame]\n");
		printf("  havok_io_cli.exe physics write <input.json> <output.hkx>\n");
		printf("  havok_io_cli.exe physics read <input.hkx> <output.json>\n");
		printf("  havok_io_cli.exe ragdoll write <input.json> <output.hkx>\n");
		printf("  havok_io_cli.exe ragdoll read <input.hkx> <output.json>\n");
		printf("  havok_io_cli.exe hkanim pack <input_folder> <output.hkanim> [--set-name <name>] [--no-ragdoll-placeholder]\n");
		printf("  havok_io_cli.exe hkanim unpack <input.hkanim> <output_folder>\n");
	}

	int printStatus(int status, const char* message)
	{
		if (message && message[0] != '\0')
		{
			if (status == HAVOK_IO_STATUS_OK)
			{
				printf("%s\n", message);
			}
			else
			{
				fprintf(stderr, "%s\n", message);
			}
		}
		return status;
	}
}

int main(int argc, char* argv[])
{
	char message[kMessageBufferSize];
	message[0] = '\0';

	if (argc == 2 && std::string(argv[1]) == "--version")
	{
		return printStatus(havok_io_get_version(message, kMessageBufferSize), message);
	}

	if (argc < 4)
	{
		printUsage();
		return 1;
	}

	const std::string domain = argv[1];
	const std::string mode = argv[2];

	if (domain == "animation")
	{
		if (mode == "write")
		{
			const int quantizationBits = argc >= 6 ? atoi(argv[5]) : 8;
			const float tolerance = argc >= 7 ? static_cast<float>(atof(argv[6])) : 0.0f;
			const int useBlockCompression = argc >= 8 ? atoi(argv[7]) : 1;
			const int blockSize = argc >= 9 ? atoi(argv[8]) : 8;
			const int useThreeComponentQuaternions = argc >= 10 ? atoi(argv[9]) : 1;
			if (argc < 5)
			{
				printUsage();
				return 1;
			}
			return printStatus(
				havok_io_animation_write(
					argv[3],
					argv[4],
					quantizationBits,
					tolerance,
					useBlockCompression,
					blockSize,
					useThreeComponentQuaternions,
					message,
					kMessageBufferSize),
				message);
		}

		if (mode == "read" && argc == 5)
		{
			return printStatus(havok_io_animation_read(argv[3], argv[4], message, kMessageBufferSize), message);
		}

		if (mode == "sample" && argc >= 7)
		{
			const int startFrame = atoi(argv[5]);
			const int endFrame = atoi(argv[6]);
			const int samplesPerFrame = argc >= 8 ? atoi(argv[7]) : 4;
			return printStatus(
				havok_io_animation_sample(argv[3], argv[4], startFrame, endFrame, samplesPerFrame, message, kMessageBufferSize),
				message);
		}
	}

	if (domain == "physics")
	{
		if (mode == "write" && argc == 5)
		{
			return printStatus(havok_io_physics_write(argv[3], argv[4], message, kMessageBufferSize), message);
		}

		if (mode == "read" && argc == 5)
		{
			return printStatus(havok_io_physics_read(argv[3], argv[4], message, kMessageBufferSize), message);
		}
	}

	if (domain == "ragdoll")
	{
		if (mode == "write" && argc == 5)
		{
			return printStatus(havok_io_ragdoll_write(argv[3], argv[4], message, kMessageBufferSize), message);
		}

		if (mode == "read" && argc == 5)
		{
			return printStatus(havok_io_ragdoll_read(argv[3], argv[4], message, kMessageBufferSize), message);
		}
	}

	if (domain == "hkanim")
	{
		if (mode == "pack")
		{
			if (argc < 5)
			{
				printUsage();
				return 1;
			}

			const char* setName = 0;
			int includeRagdollPlaceholder = 1;
			for (int index = 5; index < argc; ++index)
			{
				const std::string argument = argv[index];
				if (argument == "--no-ragdoll-placeholder")
				{
					includeRagdollPlaceholder = 0;
				}
				else if (argument == "--set-name")
				{
					if (index + 1 >= argc)
					{
						fprintf(stderr, "Error: --set-name requires a value\n");
						return 1;
					}
					setName = argv[++index];
				}
				else
				{
					fprintf(stderr, "Error: unknown argument: %s\n", argument.c_str());
					return 1;
				}
			}

			return printStatus(
				havok_io_hkanim_pack(argv[3], argv[4], setName, includeRagdollPlaceholder, message, kMessageBufferSize),
				message);
		}

		if (mode == "unpack" && argc == 5)
		{
			return printStatus(havok_io_hkanim_unpack(argv[3], argv[4], message, kMessageBufferSize), message);
		}
	}

	printUsage();
	return 1;
}