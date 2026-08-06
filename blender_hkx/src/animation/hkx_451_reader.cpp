#include "hkx_451_reader.h"

#include <stdio.h>

#include <Common/Base/hkBase.h>
#include <Common/Base/Math/QsTransform/hkQsTransform.h>
#include <Common/Serialize/Util/hkLoader.h>
#include <Common/Serialize/Util/hkRootLevelContainer.h>

#include <Animation/Animation/hkaAnimationContainer.h>
#include <Animation/Animation/Animation/hkaAnimationBinding.h>
#include <Animation/Animation/Animation/hkaSkeletalAnimation.h>
#include <Animation/Animation/Rig/hkaSkeleton.h>

namespace
{
	void *findObjectByTypeName(const hkRootLevelContainer *rootContainer, const char *typeName)
	{
		if (rootContainer == HK_NULL || typeName == HK_NULL)
		{
			return HK_NULL;
		}

		void *object = rootContainer->findObjectByType(typeName);
		if (object != HK_NULL)
		{
			return object;
		}

		for (int index = 0; index < rootContainer->m_numNamedVariants; ++index)
		{
			const hkRootLevelContainer::NamedVariant &variant = rootContainer->m_namedVariants[index];
			const char *variantTypeName = variant.getTypeName();
			if (variantTypeName != HK_NULL && strcmp(variantTypeName, typeName) == 0)
			{
				return variant.getObject();
			}
		}

		return HK_NULL;
	}

	void copyQsTransform(const hkQsTransform &source, RawTransform &destination)
	{
		const hkVector4 &translation = source.getTranslation();
		destination.pos[0] = translation(0);
		destination.pos[1] = translation(1);
		destination.pos[2] = translation(2);

		const hkQuaternion &rotation = source.getRotation();
		const hkVector4 &imag = rotation.getImag();
		destination.rot[0] = imag(0);
		destination.rot[1] = imag(1);
		destination.rot[2] = imag(2);
		destination.rot[3] = rotation.getReal();

		const hkVector4 &scale = source.getScale();
		destination.scale[0] = scale(0);
		destination.scale[1] = scale(1);
		destination.scale[2] = scale(2);
	}

	const hkaAnimationContainer *findAnimationContainer(const hkRootLevelContainer *rootContainer)
	{
		return reinterpret_cast<const hkaAnimationContainer *>(findObjectByTypeName(rootContainer, "hkaAnimationContainer"));
	}

	const hkaSkeleton *findSkeleton(const hkRootLevelContainer *rootContainer, const hkaAnimationContainer *animationContainer)
	{
		// First try to get the skeleton from the animation container, as it is more likely to be the correct one for the animtion and binding
		// If that fails, look for any skeleton in the root container.
		if (animationContainer != HK_NULL && animationContainer->m_numSkeletons > 0 && animationContainer->m_skeletons != HK_NULL)
		{
			return animationContainer->m_skeletons[0];
		}
		return reinterpret_cast<const hkaSkeleton *>(findObjectByTypeName(rootContainer, "hkaSkeleton"));
	}

	const hkaAnimationBinding *findBinding(const hkRootLevelContainer *rootContainer, const hkaAnimationContainer *animationContainer)
	{
		// Fisrt try to get the binding from the animation container as its more likely to be the correct one for the animation and skeleton
		if (animationContainer != HK_NULL && animationContainer->m_numBindings > 0 && animationContainer->m_bindings != HK_NULL)
		{
			return animationContainer->m_bindings[0];
		}
		return reinterpret_cast<const hkaAnimationBinding *>(findObjectByTypeName(rootContainer, "hkaAnimationBinding"));
	}

	const hkaSkeletalAnimation *findAnimation(const hkRootLevelContainer *rootContainer, const hkaAnimationContainer *animationContainer, const hkaAnimationBinding *binding)
	{
		// first try to get the animation from the binding, as its more likely to be the correct one for the skeleton and track mapping
		if (binding != HK_NULL && binding->m_animation != HK_NULL)
		{
			return binding->m_animation;
		}
		if (animationContainer != HK_NULL && animationContainer->m_numAnimations > 0 && animationContainer->m_animations != HK_NULL)
		{
			return animationContainer->m_animations[0];
		}
		// if that fails, look for any skeletal animation in the root container. 
		// There are multiple types of skeletal animations, so check them in order of most likely to be used for export to least likely
		static const char *const animationTypeNames[] =
			{
				"hkaSplineCompressedAnimation",
				"hkaInterleavedSkeletalAnimation",
				"hkaDeltaCompressedSkeletalAnimation",
				"hkaWaveletCompressedAnimation",
			};
		for (int index = 0; index < static_cast<int>(sizeof(animationTypeNames) / sizeof(animationTypeNames[0])); ++index)
		{
			const hkaSkeletalAnimation *animation = reinterpret_cast<const hkaSkeletalAnimation *>(findObjectByTypeName(rootContainer, animationTypeNames[index]));
			if (animation != HK_NULL)
			{
				return animation;
			}
		}

		return HK_NULL;
	}

	bool readAnimationGraphInternal(const char *inputFile, int startFrame, int endFrame, int samplesPerFrame, bool useSampleWindow, ParsedAnimationData &outData)
	{
		// The target sample fps for the output animation data; if the source animation has a duration and more than 1 frame, it will be resampled to this fps. If the source animation has 0 duration or only 1 frame, it will not be resampled and the original frame count will be used (which may still be 1 if the source animation has no frames or duration).
		const hkReal kTargetSampleFps = 30.0f;

		outData = ParsedAnimationData();

		hkLoader loader;
		hkRootLevelContainer *rootContainer = loader.load(inputFile);
		if (rootContainer == HK_NULL)
		{
			fprintf(stderr, "Error: failed to load animation HKX %s\n", inputFile);
			return false;
		}

		const hkaAnimationContainer *animationContainer = findAnimationContainer(rootContainer);
		if (animationContainer == HK_NULL)
		{
			fprintf(stderr, "Error: animation container not found in %s\n", inputFile);
			return false;
		}

		const hkaAnimationBinding *binding = findBinding(rootContainer, animationContainer);
		const hkaSkeletalAnimation *animation = findAnimation(rootContainer, animationContainer, binding);
		if (animation == HK_NULL)
		{
			fprintf(stderr, "Error: no animation tracks found in %s\n", inputFile);
			return false;
		}

		const hkaSkeleton *skeleton = findSkeleton(rootContainer, animationContainer);
		const bool hasSkeleton =
			skeleton != HK_NULL &&
			skeleton->m_numBones > 0 &&
			skeleton->m_bones != HK_NULL;

		const int numTracks = animation->m_numberOfTransformTracks;
		if (numTracks <= 0)
		{
			fprintf(stderr, "Error: animation has no transform tracks in %s\n", inputFile);
			return false;
		}

		outData.skeletonName = (hasSkeleton && skeleton->m_name != HK_NULL && skeleton->m_name[0] != '\0') ? skeleton->m_name : "";
		outData.duration = animation->m_duration;
		const int originalFrameCount = animation->getNumOriginalFrames() > 0 ? animation->getNumOriginalFrames() : 1;
		int sampledFrameCount = originalFrameCount;
		if (outData.duration > 0.0f)
		{
			const int durationSampledFrameCount = static_cast<int>((outData.duration * kTargetSampleFps) + 0.5f) + 1;
			if (durationSampledFrameCount > 1)
			{
				sampledFrameCount = durationSampledFrameCount;
			}
		}
		outData.numFrames = sampledFrameCount;

		if (useSampleWindow && outData.duration > 0.0f && sampledFrameCount > 1)
		{
			const int clampedSamplesPerFrame = samplesPerFrame > 0 ? samplesPerFrame : 1;
			const int maxFrameIndex = sampledFrameCount - 1;
			int clampedStartFrame = startFrame < 0 ? 0 : startFrame;
			if (clampedStartFrame > maxFrameIndex)
			{
				clampedStartFrame = maxFrameIndex;
			}
			int clampedEndFrame = endFrame < clampedStartFrame ? clampedStartFrame : endFrame;
			if (clampedEndFrame > maxFrameIndex)
			{
				clampedEndFrame = maxFrameIndex;
			}

			for (int frameIndex = clampedStartFrame; frameIndex < clampedEndFrame; ++frameIndex)
			{
				for (int stepIndex = 0; stepIndex < clampedSamplesPerFrame; ++stepIndex)
				{
					const hkReal sampleFrame = static_cast<hkReal>(frameIndex) + (static_cast<hkReal>(stepIndex) / static_cast<hkReal>(clampedSamplesPerFrame));
					outData.sampleFramePositions.push_back(sampleFrame);
					outData.sampleTimes.push_back(outData.duration * (sampleFrame / static_cast<hkReal>(maxFrameIndex)));
				}
			}
			outData.sampleFramePositions.push_back(static_cast<hkReal>(clampedEndFrame));
			outData.sampleTimes.push_back(outData.duration * (static_cast<hkReal>(clampedEndFrame) / static_cast<hkReal>(maxFrameIndex)));
			outData.numFrames = static_cast<int>(outData.sampleTimes.size());
		}
		else
		{
			if (outData.numFrames <= 0)
			{
				outData.numFrames = 1;
			}
		}

		int fallbackBoneCount = numTracks;
		outData.trackBoneIndices.reserve(numTracks);
		if (binding != HK_NULL &&
			binding->m_transformTrackToBoneIndices != HK_NULL &&
			binding->m_numTransformTrackToBoneIndices == numTracks)
		{
			for (int trackIndex = 0; trackIndex < numTracks; ++trackIndex)
			{
				const int boneIndex = binding->m_transformTrackToBoneIndices[trackIndex];
				if (boneIndex < 0)
				{
					fprintf(stderr, "Error: invalid binding index %d for track %d in %s\n", boneIndex, trackIndex, inputFile);
					return false;
				}
				outData.trackBoneIndices.push_back(boneIndex);
				if (boneIndex + 1 > fallbackBoneCount)
				{
					fallbackBoneCount = boneIndex + 1;
				}
			}
		}
		else
		{
			for (int trackIndex = 0; trackIndex < numTracks; ++trackIndex)
			{
				outData.trackBoneIndices.push_back(trackIndex);
			}
		}

		if (hasSkeleton)
		{
			const int numBones = skeleton->m_numBones;
			outData.boneNames.reserve(numBones);
			outData.parentIndices.reserve(numBones);
			outData.referencePose.reserve(numBones);
			for (int boneIndex = 0; boneIndex < numBones; ++boneIndex)
			{
				const char *boneName = (skeleton->m_bones[boneIndex] != HK_NULL) ? skeleton->m_bones[boneIndex]->m_name : HK_NULL;
				outData.boneNames.push_back((boneName != HK_NULL && boneName[0] != '\0') ? boneName : "Bone");
				outData.parentIndices.push_back(skeleton->m_parentIndices != HK_NULL ? skeleton->m_parentIndices[boneIndex] : -1);

				RawTransform transform;
				if (skeleton->m_referencePose != HK_NULL && boneIndex < skeleton->m_numReferencePose)
				{
					copyQsTransform(skeleton->m_referencePose[boneIndex], transform);
				}
				else
				{
					transform.pos[0] = transform.pos[1] = transform.pos[2] = 0.0f;
					transform.rot[0] = transform.rot[1] = transform.rot[2] = 0.0f;
					transform.rot[3] = 1.0f;
					transform.scale[0] = transform.scale[1] = transform.scale[2] = 1.0f;
				}
				outData.referencePose.push_back(transform);
			}

			for (int trackIndex = 0; trackIndex < numTracks; ++trackIndex)
			{
				const int boneIndex = outData.trackBoneIndices[trackIndex];
				if (boneIndex < 0 || boneIndex >= numBones)
				{
					fprintf(stderr, "Error: invalid binding index %d for track %d in %s\n", boneIndex, trackIndex, inputFile);
					return false;
				}
			}
		}
		else if (fallbackBoneCount <= 0)
		{
			fprintf(stderr, "Error: animation has no usable track mapping in %s\n", inputFile);
			return false;
		}

		outData.transforms.resize(outData.numFrames * numTracks);
		hkQsTransform *sampledTracks = hkAllocate<hkQsTransform>(numTracks, HK_MEMORY_CLASS_ANIMATION);
		for (int frameIndex = 0; frameIndex < outData.numFrames; ++frameIndex)
		{
			hkReal sampleTime = 0.0f;
			if (!outData.sampleTimes.empty())
			{
				sampleTime = outData.sampleTimes[frameIndex];
			}
			else if (outData.numFrames > 1 && outData.duration > 0.0f)
			{
				sampleTime = outData.duration * (static_cast<hkReal>(frameIndex) / static_cast<hkReal>(outData.numFrames - 1));
			}

			animation->sampleTracks(sampleTime, sampledTracks, HK_NULL, HK_NULL);
			for (int trackIndex = 0; trackIndex < numTracks; ++trackIndex)
			{
				copyQsTransform(sampledTracks[trackIndex], outData.transforms[frameIndex * numTracks + trackIndex]);
			}
		}
		hkDeallocate(sampledTracks);

		printf(
			"Read animation HKX: %d bones, %d tracks, %d frames, duration %.3f\n",
			hasSkeleton ? skeleton->m_numBones : 0,
			numTracks,
			outData.numFrames,
			outData.duration);
		return true;
	}
}

bool readAnimationGraph(const char *inputFile, ParsedAnimationData &outData)
{
	return readAnimationGraphInternal(inputFile, 0, 0, 1, false, outData);
}

bool sampleAnimationGraph(const char *inputFile, int startFrame, int endFrame, int samplesPerFrame, ParsedAnimationData &outData)
{
	return readAnimationGraphInternal(inputFile, startFrame, endFrame, samplesPerFrame, true, outData);
}