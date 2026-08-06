#ifndef DOW2_ANIMATION_JSON_ANIMATION_INPUT_H
#define DOW2_ANIMATION_JSON_ANIMATION_INPUT_H

#include <string>
#include <vector>

struct RawTransform
{
	float pos[3];
	float rot[4];
	float scale[3];
};

struct ParsedAnimationData
{
	std::string skeletonName;
	float duration;
	std::vector<std::string> boneNames;
	std::vector<int> parentIndices;
	std::vector<RawTransform> referencePose;
	std::vector<int> trackBoneIndices;
	std::vector<float> sampleTimes;
	std::vector<float> sampleFramePositions;
	int numFrames;
	std::vector<RawTransform> transforms;

	ParsedAnimationData()
		: duration(0.0f),
		  numFrames(0)
	{
	}
};

bool parseAnimationJson(const char* filename, ParsedAnimationData& outData);

#endif