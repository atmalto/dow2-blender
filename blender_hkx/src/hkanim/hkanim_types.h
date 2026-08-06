#ifndef DOW2_HKANIM_TYPES_H
#define DOW2_HKANIM_TYPES_H

#include <string>
#include <vector>

struct HkAnimEntry
{
	std::string relativeName;
	std::string sourcePath;
	std::vector<char> bytes;
	bool empty;

	HkAnimEntry()
		: empty(false)
	{
	}
};

struct HkAnimSet
{
	std::string name;
	std::vector<HkAnimEntry> entries;
};

struct HkAnimPackOptions
{
	bool includeRagdollPlaceholder;
	std::string singleSetName;

	HkAnimPackOptions()
		: includeRagdollPlaceholder(true)
	{
	}
};

#endif