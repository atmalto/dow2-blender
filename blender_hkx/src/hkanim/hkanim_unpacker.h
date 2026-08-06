#ifndef DOW2_HKANIM_UNPACKER_H
#define DOW2_HKANIM_UNPACKER_H

#include <string>
#include <vector>

#include "hkanim_types.h"

bool readHkAnimContainer(
	const std::string& inputPath,
	std::vector<HkAnimSet>& outSets,
	std::string& errorMessage);

bool unpackHkAnimToDirectory(
	const std::string& inputPath,
	const std::string& outputDirectory,
	std::string& errorMessage);

#endif