#ifndef DOW2_ANIMATION_SCENE_BUILDER_H
#define DOW2_ANIMATION_SCENE_BUILDER_H

#include <vector>

#include "json_animation_input.h"

class hkRootLevelContainer;
class hkaSkeleton;
class hkaInterleavedSkeletalAnimation;
class hkaDeltaCompressedSkeletalAnimation;
class hkaAnimationBinding;
class hkaAnimationContainer;

struct AnimationBuildOptions
{
	int quantizationBits;
	float tolerance;
	bool useBlockCompression;
	int blockSize;
	bool useThreeComponentQuaternions;

	AnimationBuildOptions()
		: quantizationBits(8),
		  tolerance(0.0f),
		  useBlockCompression(true),
		  blockSize(8),
		  useThreeComponentQuaternions(true)
	{
	}
};

struct BuiltAnimationGraph
{
	hkaSkeleton* skeleton;
	hkaInterleavedSkeletalAnimation* interleavedAnimation;
	hkaDeltaCompressedSkeletalAnimation* compressedAnimation;
	hkaAnimationBinding* binding;
	hkaAnimationContainer* container;
	hkRootLevelContainer* rootContainer;
	std::vector<char*> ownedStrings;

	BuiltAnimationGraph();
	~BuiltAnimationGraph();

private:
	BuiltAnimationGraph(const BuiltAnimationGraph&);
	BuiltAnimationGraph& operator=(const BuiltAnimationGraph&);
};

bool buildAnimationGraph(
	const ParsedAnimationData& input,
	const AnimationBuildOptions& options,
	BuiltAnimationGraph& output);

#endif