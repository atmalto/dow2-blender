#ifndef DOW2_HKANIM_PACKER_H
#define DOW2_HKANIM_PACKER_H

#include <string>
#include <vector>

#include "hkanim_types.h"

bool buildHkAnimSetsFromDirectory(
	const std::string& inputDirectory,
	const HkAnimPackOptions& options,
	std::vector<HkAnimSet>& outSets,
	std::string& errorMessage);

bool writeHkAnimContainer(
	const std::vector<HkAnimSet>& sets,
	const std::string& outputPath,
	std::string& errorMessage);

bool packHkAnimFromDirectory(
	const std::string& inputDirectory,
	const std::string& outputPath,
	const HkAnimPackOptions& options,
	std::string& errorMessage);

#endif