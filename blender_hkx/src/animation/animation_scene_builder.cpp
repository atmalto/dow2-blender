#include "animation_scene_builder.h"

#include <stdio.h>
#include <string.h>

#include <Common/Base/hkBase.h>
#include <Common/Serialize/Util/hkRootLevelContainer.h>

#include <Animation/Animation/hkaAnimationContainer.h>
#include <Animation/Animation/Rig/hkaSkeleton.h>
#include <Animation/Animation/Rig/hkaBone.h>
#include <Animation/Animation/Animation/hkaSkeletalAnimation.h>
#include <Animation/Animation/Animation/Interleaved/hkaInterleavedSkeletalAnimation.h>
#include <Animation/Animation/Animation/DeltaCompressed/hkaDeltaCompressedSkeletalAnimation.h>
#include <Animation/Animation/Animation/hkaAnimationBinding.h>
#include <Animation/Animation/Animation/hkaAnnotationTrack.h>

namespace
{
	char* duplicateString(const char* text)
	{
		const size_t length = strlen(text);
		char* copy = new char[length + 1];
		strcpy_s(copy, length + 1, text);
		return copy;
	}

	void copyRawTransform(const RawTransform& raw, hkQsTransform& outTransform)
	{
		outTransform.setTranslation(hkVector4(raw.pos[0], raw.pos[1], raw.pos[2]));
		outTransform.setRotation(hkQuaternion(raw.rot[0], raw.rot[1], raw.rot[2], raw.rot[3]));
		outTransform.setScale(hkVector4(raw.scale[0], raw.scale[1], raw.scale[2]));
	}
}

BuiltAnimationGraph::BuiltAnimationGraph()
	: skeleton(0),
	  interleavedAnimation(0),
	  compressedAnimation(0),
	  binding(0),
	  container(0),
	  rootContainer(0)
{
}

BuiltAnimationGraph::~BuiltAnimationGraph()
{
	for (size_t i = 0; i < ownedStrings.size(); ++i)
	{
		delete[] ownedStrings[i];
	}
	ownedStrings.clear();
}

bool buildAnimationGraph(
	const ParsedAnimationData& input,
	const AnimationBuildOptions& options,
	BuiltAnimationGraph& output)
{
	const int numBones = (int)input.boneNames.size();
	const int numTracks = (int)input.trackBoneIndices.size();
	if (numBones <= 0 || input.numFrames <= 0)
	{
		fprintf(stderr, "Error: animation input is incomplete\n");
		return false;
	}

	printf("Creating skeleton with %d bones...\n", numBones);

	output.skeleton = new hkaSkeleton();
	char* skeletonNameCopy = duplicateString(input.skeletonName.c_str());
	output.ownedStrings.push_back(skeletonNameCopy);
	output.skeleton->m_name = skeletonNameCopy;

	output.skeleton->m_parentIndices = hkAllocate<hkInt16>(numBones, HK_MEMORY_CLASS_ANIMATION);
	output.skeleton->m_numParentIndices = numBones;
	for (int i = 0; i < numBones; ++i)
	{
		output.skeleton->m_parentIndices[i] = (hkInt16)input.parentIndices[i];
	}

	output.skeleton->m_bones = hkAllocate<hkaBone*>(numBones, HK_MEMORY_CLASS_ANIMATION);
	output.skeleton->m_numBones = numBones;
	for (int i = 0; i < numBones; ++i)
	{
		output.skeleton->m_bones[i] = new hkaBone();
		char* boneNameCopy = duplicateString(input.boneNames[i].c_str());
		output.ownedStrings.push_back(boneNameCopy);
		output.skeleton->m_bones[i]->m_name = boneNameCopy;
		output.skeleton->m_bones[i]->m_lockTranslation = false;
	}

	output.skeleton->m_referencePose = hkAllocate<hkQsTransform>(numBones, HK_MEMORY_CLASS_ANIMATION);
	output.skeleton->m_numReferencePose = numBones;
	for (int i = 0; i < numBones; ++i)
	{
		copyRawTransform(input.referencePose[i], output.skeleton->m_referencePose[i]);
	}

	output.skeleton->m_floatSlots = HK_NULL;
	output.skeleton->m_numFloatSlots = 0;

	printf("Creating interleaved animation with %d frames and %d tracks...\n", input.numFrames, numTracks);

	output.interleavedAnimation = new hkaInterleavedSkeletalAnimation();
	output.interleavedAnimation->m_duration = input.duration;
	output.interleavedAnimation->m_numberOfTransformTracks = numTracks;
	output.interleavedAnimation->m_numberOfFloatTracks = 0;

	const int totalTransforms = input.numFrames * numTracks;
	output.interleavedAnimation->m_transforms = hkAllocate<hkQsTransform>(totalTransforms, HK_MEMORY_CLASS_ANIMATION);
	output.interleavedAnimation->m_numTransforms = totalTransforms;

	printf("  Sample transforms (frame 0, first 4 bones):\n");
	for (int track = 0; track < numTracks && track < 4; ++track)
	{
		const int boneIndex = input.trackBoneIndices[track];
		printf(
			"    Track %d -> Bone %d (%s): rot=[%.4f, %.4f, %.4f, %.4f]\n",
			track,
			boneIndex,
			input.boneNames[boneIndex].c_str(),
			input.transforms[track].rot[0],
			input.transforms[track].rot[1],
			input.transforms[track].rot[2],
			input.transforms[track].rot[3]);
	}

	for (int i = 0; i < totalTransforms; ++i)
	{
		copyRawTransform(input.transforms[i], output.interleavedAnimation->m_transforms[i]);
	}

	output.interleavedAnimation->m_floats = HK_NULL;
	output.interleavedAnimation->m_numFloats = 0;

	output.interleavedAnimation->m_annotationTracks = numTracks > 0 ? hkAllocate<hkaAnnotationTrack*>(numTracks, HK_MEMORY_CLASS_ANIMATION) : HK_NULL;
	output.interleavedAnimation->m_numAnnotationTracks = numTracks;
	for (int i = 0; i < numTracks; ++i)
	{
		output.interleavedAnimation->m_annotationTracks[i] = new hkaAnnotationTrack();
		const int boneIndex = input.trackBoneIndices[i];
		output.interleavedAnimation->m_annotationTracks[i]->m_name = output.skeleton->m_bones[boneIndex]->m_name;
		output.interleavedAnimation->m_annotationTracks[i]->m_annotations = HK_NULL;
		output.interleavedAnimation->m_annotationTracks[i]->m_numAnnotations = 0;
	}

	printf(
		"Compressing animation (delta compression, %d-bit, tolerance %.4f, block compression %s, block size %d, 3-component quats %s)...\n",
		options.quantizationBits,
		options.tolerance,
		options.useBlockCompression ? "on" : "off",
		options.useBlockCompression ? options.blockSize : input.numFrames,
		options.useThreeComponentQuaternions ? "on" : "off");

	hkaDeltaCompressedSkeletalAnimation::CompressionParams dparams;
	dparams.m_quantizationBits = options.quantizationBits;
	if (options.useBlockCompression && options.blockSize > 0)
	{
		dparams.m_blockSize = options.blockSize < input.numFrames ? options.blockSize : input.numFrames;
	}
	else
	{
		dparams.m_blockSize = input.numFrames;
	}
	dparams.m_absolutePositionTolerance = 0.0f;
	dparams.m_relativePositionTolerance = options.tolerance;
	dparams.m_rotationTolerance = options.tolerance;
	dparams.m_scaleTolerance = options.tolerance;
	dparams.m_absoluteFloatTolerance = options.tolerance;

	output.compressedAnimation = new hkaDeltaCompressedSkeletalAnimation(
		*output.interleavedAnimation,
		dparams,
		options.useThreeComponentQuaternions);

	printf("Creating animation binding...\n");

	output.binding = new hkaAnimationBinding();
	output.binding->m_animation = output.compressedAnimation;
	output.binding->m_transformTrackToBoneIndices = numTracks > 0 ? hkAllocate<hkInt16>(numTracks, HK_MEMORY_CLASS_ANIMATION) : HK_NULL;
	output.binding->m_numTransformTrackToBoneIndices = numTracks;
	for (int i = 0; i < numTracks; ++i)
	{
		output.binding->m_transformTrackToBoneIndices[i] = (hkInt16)input.trackBoneIndices[i];
	}
	output.binding->m_floatTrackToFloatSlotIndices = HK_NULL;
	output.binding->m_numFloatTrackToFloatSlotIndices = 0;
	output.binding->m_blendHint = hkaAnimationBinding::NORMAL;

	printf("Creating animation container...\n");

	output.container = new hkaAnimationContainer();
	output.container->m_skeletons = hkAllocate<hkaSkeleton*>(1, HK_MEMORY_CLASS_ANIMATION);
	output.container->m_numSkeletons = 1;
	output.container->m_skeletons[0] = output.skeleton;

	output.container->m_animations = hkAllocate<hkaSkeletalAnimation*>(1, HK_MEMORY_CLASS_ANIMATION);
	output.container->m_numAnimations = 1;
	output.container->m_animations[0] = output.compressedAnimation;

	output.container->m_bindings = hkAllocate<hkaAnimationBinding*>(1, HK_MEMORY_CLASS_ANIMATION);
	output.container->m_numBindings = 1;
	output.container->m_bindings[0] = output.binding;

	output.container->m_attachments = HK_NULL;
	output.container->m_numAttachments = 0;
	output.container->m_skins = HK_NULL;
	output.container->m_numSkins = 0;

	printf("Creating root container...\n");

	output.rootContainer = new hkRootLevelContainer();
	output.rootContainer->m_namedVariants = hkAllocate<hkRootLevelContainer::NamedVariant>(1, HK_MEMORY_CLASS_SERIALIZE);
	output.rootContainer->m_numNamedVariants = 1;
	output.rootContainer->m_namedVariants[0].set("Animation Container", output.container, &hkaAnimationContainerClass);

	return true;
}