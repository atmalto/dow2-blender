#include "hkx_451_writer.h"

#include <Common/Base/hkBase.h>
#include <Common/Base/Reflection/hkClass.h>
#include <Common/Base/Reflection/hkInternalClassMember.h>
#include <Common/Base/Reflection/Registry/hkVtableClassRegistry.h>
#include <Common/Base/Object/hkReferencedObject.h>
#include <Common/Base/System/Io/OStream/hkOStream.h>
#include <Common/Serialize/Packfile/Binary/hkBinaryPackfileWriter.h>
#include <Common/Serialize/Packfile/hkPackfileWriter.h>
#include <Common/Serialize/Util/hkRootLevelContainer.h>
#include <Common/Serialize/Util/hkStructureLayout.h>

#include <Animation/Animation/hkaAnimationContainer.h>
#include <Animation/Animation/Rig/hkaSkeleton.h>
#include <Animation/Animation/Rig/hkaBone.h>
#include <Animation/Animation/Animation/hkaAnimationBinding.h>
#include <Animation/Animation/Animation/hkaAnnotationTrack.h>
#include <Animation/Animation/Animation/DeltaCompressed/hkaDeltaCompressedSkeletalAnimation.h>

#include <stdio.h>

namespace
{
	static const char* const kTargetVersion = "Havok-4.5.1-r1";

	struct Legacy451Annotation
	{
		hkReal m_time;
		char* m_text;
	};

	struct Legacy451AnnotationTrack
	{
		char* m_name;
		Legacy451Annotation* m_annotations;
		hkInt32 m_numAnnotations;
	};

	struct Legacy451Bone
	{
		char* m_name;
		hkBool m_lockTranslation;
	};

	struct Legacy451Skeleton
	{
		const char* m_name;
		hkInt16* m_parentIndices;
		hkInt32 m_numParentIndices;
		Legacy451Bone** m_bones;
		hkInt32 m_numBones;
		hkQsTransform* m_referencePose;
		int m_numReferencePose;
	};

	struct Legacy451SkeletalAnimation : public hkReferencedObject
	{
		hkInt32 m_type;
		hkReal m_duration;
		int m_numberOfTracks;
		const void* m_extractedMotion;
		Legacy451AnnotationTrack** m_annotationTracks;
		hkInt32 m_numAnnotationTracks;

		Legacy451SkeletalAnimation()
			: m_type(0),
			  m_duration(0.0f),
			  m_numberOfTracks(0),
			  m_extractedMotion(HK_NULL),
			  m_annotationTracks(HK_NULL),
			  m_numAnnotationTracks(0)
		{
		}
	};

	struct Legacy451DeltaCompressedSkeletalAnimation : public Legacy451SkeletalAnimation
	{
		struct QuantizationFormat
		{
			hkUint8 m_maxBitWidth;
			hkUint8 m_preserved;
			hkUint32 m_numD;
			hkUint32 m_offsetIdx;
			hkUint32 m_scaleIdx;
			hkUint32 m_bitWidthIdx;
		};

		int m_numberOfPoses;
		int m_blockSize;
		QuantizationFormat m_qFormat;
		hkUint32 m_quantizedDataIdx;
		hkUint32 m_quantizedDataSize;
		hkUint32 m_staticMaskIdx;
		hkUint32 m_staticMaskSize;
		hkUint32 m_staticDOFsIdx;
		hkUint32 m_staticDOFsSize;
		hkUint32 m_totalBlockSize;
		hkUint32 m_lastBlockSize;
		hkUint8* m_dataBuffer;
		int m_numDataBuffer;

		Legacy451DeltaCompressedSkeletalAnimation()
			: m_numberOfPoses(0),
			  m_blockSize(0),
			  m_quantizedDataIdx(0),
			  m_quantizedDataSize(0),
			  m_staticMaskIdx(0),
			  m_staticMaskSize(0),
			  m_staticDOFsIdx(0),
			  m_staticDOFsSize(0),
			  m_totalBlockSize(0),
			  m_lastBlockSize(0),
			  m_dataBuffer(HK_NULL),
			  m_numDataBuffer(0)
		{
		}
	};

	struct Legacy451AnimationBinding
	{
		Legacy451DeltaCompressedSkeletalAnimation* m_animation;
		hkInt16* m_animationTrackToBoneIndices;
		hkInt32 m_numAnimationTrackToBoneIndices;
		hkInt8 m_blendHint;

		Legacy451AnimationBinding()
			: m_animation(HK_NULL),
			  m_animationTrackToBoneIndices(HK_NULL),
			  m_numAnimationTrackToBoneIndices(0),
			  m_blendHint(0)
		{
		}
	};

	struct Legacy451AnimationContainer
	{
		Legacy451Skeleton** m_skeletons;
		hkInt32 m_numSkeletons;
		Legacy451DeltaCompressedSkeletalAnimation** m_animations;
		hkInt32 m_numAnimations;
		Legacy451AnimationBinding** m_bindings;
		hkInt32 m_numBindings;
		void** m_attachments;
		hkInt32 m_numAttachments;
		void** m_skins;
		hkInt32 m_numSkins;

		Legacy451AnimationContainer()
			: m_skeletons(HK_NULL),
			  m_numSkeletons(0),
			  m_animations(HK_NULL),
			  m_numAnimations(0),
			  m_bindings(HK_NULL),
			  m_numBindings(0),
			  m_attachments(HK_NULL),
			  m_numAttachments(0),
			  m_skins(HK_NULL),
			  m_numSkins(0)
		{
		}
	};

	extern hkClass g_legacy451AnnotationClass;
	extern hkClass g_legacy451AnnotationTrackClass;
	extern hkClass g_legacy451BoneClass;
	extern hkClass g_legacy451SkeletonClass;
	extern hkClass g_legacy451AnimatedReferenceFrameClass;
	extern hkClass g_legacy451BoneAttachmentClass;
	extern hkClass g_legacy451MeshBindingClass;
	extern hkClass g_legacy451SkeletalAnimationClass;
	extern hkClass g_legacy451DeltaQuantizationFormatClass;
	extern hkClass g_legacy451DeltaCompressedSkeletalAnimationClass;
	extern hkClass g_legacy451AnimationBindingClass;
	extern hkClass g_legacy451AnimationContainerClass;

	static hkInternalClassMember g_legacy451AnnotationMembers[] =
	{
		{ "time", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451Annotation, m_time), HK_NULL },
		{ "text", HK_NULL, HK_NULL, hkClassMember::TYPE_CSTRING, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451Annotation, m_text), HK_NULL },
	};

	hkClass g_legacy451AnnotationClass(
		"hkAnnotationTrackAnnotation",
		HK_NULL,
		sizeof(Legacy451Annotation),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy451AnnotationMembers),
		HK_COUNT_OF(g_legacy451AnnotationMembers),
		HK_NULL,
		HK_NULL,
		0);

	static hkInternalClassMember g_legacy451AnnotationTrackMembers[] =
	{
		{ "name", HK_NULL, HK_NULL, hkClassMember::TYPE_CSTRING, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451AnnotationTrack, m_name), HK_NULL },
		{ "annotations", &g_legacy451AnnotationClass, HK_NULL, hkClassMember::TYPE_SIMPLEARRAY, hkClassMember::TYPE_STRUCT, 0, 0, HK_OFFSET_OF(Legacy451AnnotationTrack, m_annotations), HK_NULL },
	};

	hkClass g_legacy451AnnotationTrackClass(
		"hkAnnotationTrack",
		HK_NULL,
		sizeof(Legacy451AnnotationTrack),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy451AnnotationTrackMembers),
		HK_COUNT_OF(g_legacy451AnnotationTrackMembers),
		HK_NULL,
		HK_NULL,
		0);

	static hkInternalClassMember g_legacy451BoneMembers[] =
	{
		{ "name", HK_NULL, HK_NULL, hkClassMember::TYPE_CSTRING, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451Bone, m_name), HK_NULL },
		{ "lockTranslation", HK_NULL, HK_NULL, hkClassMember::TYPE_BOOL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451Bone, m_lockTranslation), HK_NULL },
	};

	hkClass g_legacy451BoneClass(
		"hkBone",
		HK_NULL,
		sizeof(Legacy451Bone),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy451BoneMembers),
		HK_COUNT_OF(g_legacy451BoneMembers),
		HK_NULL,
		HK_NULL,
		0);

	static hkInternalClassMember g_legacy451SkeletonMembers[] =
	{
		{ "name", HK_NULL, HK_NULL, hkClassMember::TYPE_CSTRING, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451Skeleton, m_name), HK_NULL },
		{ "parentIndices", HK_NULL, HK_NULL, hkClassMember::TYPE_SIMPLEARRAY, hkClassMember::TYPE_INT16, 0, 0, HK_OFFSET_OF(Legacy451Skeleton, m_parentIndices), HK_NULL },
		{ "bones", &g_legacy451BoneClass, HK_NULL, hkClassMember::TYPE_SIMPLEARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy451Skeleton, m_bones), HK_NULL },
		{ "referencePose", HK_NULL, HK_NULL, hkClassMember::TYPE_SIMPLEARRAY, hkClassMember::TYPE_QSTRANSFORM, 0, 0, HK_OFFSET_OF(Legacy451Skeleton, m_referencePose), HK_NULL },
	};

	hkClass g_legacy451SkeletonClass(
		"hkSkeleton",
		HK_NULL,
		sizeof(Legacy451Skeleton),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy451SkeletonMembers),
		HK_COUNT_OF(g_legacy451SkeletonMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy451AnimatedReferenceFrameClass(
		"hkAnimatedReferenceFrame",
		&hkReferencedObjectClass,
		sizeof(hkReferencedObject),
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy451BoneAttachmentClass(
		"hkBoneAttachment",
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy451MeshBindingClass(
		"hkMeshBinding",
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		HK_NULL,
		0);

	static hkInternalClassMember g_legacy451SkeletalAnimationMembers[] =
	{
		{ "type", HK_NULL, HK_NULL, hkClassMember::TYPE_INT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451SkeletalAnimation, m_type), HK_NULL },
		{ "duration", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451SkeletalAnimation, m_duration), HK_NULL },
		{ "numberOfTracks", HK_NULL, HK_NULL, hkClassMember::TYPE_INT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451SkeletalAnimation, m_numberOfTracks), HK_NULL },
		{ "extractedMotion", &g_legacy451AnimatedReferenceFrameClass, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_STRUCT, 0, 0, HK_OFFSET_OF(Legacy451SkeletalAnimation, m_extractedMotion), HK_NULL },
		{ "annotationTracks", &g_legacy451AnnotationTrackClass, HK_NULL, hkClassMember::TYPE_SIMPLEARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy451SkeletalAnimation, m_annotationTracks), HK_NULL },
	};

	hkClass g_legacy451SkeletalAnimationClass(
		"hkSkeletalAnimation",
		&hkReferencedObjectClass,
		sizeof(Legacy451SkeletalAnimation),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy451SkeletalAnimationMembers),
		HK_COUNT_OF(g_legacy451SkeletalAnimationMembers),
		HK_NULL,
		HK_NULL,
		0);

	static hkInternalClassMember g_legacy451DeltaQuantizationFormatMembers[] =
	{
		{ "maxBitWidth", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451DeltaCompressedSkeletalAnimation::QuantizationFormat, m_maxBitWidth), HK_NULL },
		{ "preserved", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451DeltaCompressedSkeletalAnimation::QuantizationFormat, m_preserved), HK_NULL },
		{ "numD", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451DeltaCompressedSkeletalAnimation::QuantizationFormat, m_numD), HK_NULL },
		{ "offsetIdx", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451DeltaCompressedSkeletalAnimation::QuantizationFormat, m_offsetIdx), HK_NULL },
		{ "scaleIdx", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451DeltaCompressedSkeletalAnimation::QuantizationFormat, m_scaleIdx), HK_NULL },
		{ "bitWidthIdx", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451DeltaCompressedSkeletalAnimation::QuantizationFormat, m_bitWidthIdx), HK_NULL },
	};

	hkClass g_legacy451DeltaQuantizationFormatClass(
		"hkDeltaCompressedSkeletalAnimationQuantizationFormat",
		HK_NULL,
		sizeof(Legacy451DeltaCompressedSkeletalAnimation::QuantizationFormat),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy451DeltaQuantizationFormatMembers),
		HK_COUNT_OF(g_legacy451DeltaQuantizationFormatMembers),
		HK_NULL,
		HK_NULL,
		0);

	static hkInternalClassMember g_legacy451DeltaCompressedMembers[] =
	{
		{ "numberOfPoses", HK_NULL, HK_NULL, hkClassMember::TYPE_INT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451DeltaCompressedSkeletalAnimation, m_numberOfPoses), HK_NULL },
		{ "blockSize", HK_NULL, HK_NULL, hkClassMember::TYPE_INT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451DeltaCompressedSkeletalAnimation, m_blockSize), HK_NULL },
		{ "qFormat", &g_legacy451DeltaQuantizationFormatClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451DeltaCompressedSkeletalAnimation, m_qFormat), HK_NULL },
		{ "quantizedDataIdx", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451DeltaCompressedSkeletalAnimation, m_quantizedDataIdx), HK_NULL },
		{ "quantizedDataSize", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451DeltaCompressedSkeletalAnimation, m_quantizedDataSize), HK_NULL },
		{ "staticMaskIdx", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451DeltaCompressedSkeletalAnimation, m_staticMaskIdx), HK_NULL },
		{ "staticMaskSize", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451DeltaCompressedSkeletalAnimation, m_staticMaskSize), HK_NULL },
		{ "staticDOFsIdx", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451DeltaCompressedSkeletalAnimation, m_staticDOFsIdx), HK_NULL },
		{ "staticDOFsSize", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451DeltaCompressedSkeletalAnimation, m_staticDOFsSize), HK_NULL },
		{ "totalBlockSize", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451DeltaCompressedSkeletalAnimation, m_totalBlockSize), HK_NULL },
		{ "lastBlockSize", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451DeltaCompressedSkeletalAnimation, m_lastBlockSize), HK_NULL },
		{ "dataBuffer", HK_NULL, HK_NULL, hkClassMember::TYPE_SIMPLEARRAY, hkClassMember::TYPE_UINT8, 0, 0, HK_OFFSET_OF(Legacy451DeltaCompressedSkeletalAnimation, m_dataBuffer), HK_NULL },
	};

	hkClass g_legacy451DeltaCompressedSkeletalAnimationClass(
		"hkDeltaCompressedSkeletalAnimation",
		&g_legacy451SkeletalAnimationClass,
		sizeof(Legacy451DeltaCompressedSkeletalAnimation),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy451DeltaCompressedMembers),
		HK_COUNT_OF(g_legacy451DeltaCompressedMembers),
		HK_NULL,
		HK_NULL,
		0);

	static hkInternalClassMember g_legacy451AnimationBindingMembers[] =
	{
		{ "animation", &g_legacy451DeltaCompressedSkeletalAnimationClass, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_STRUCT, 0, 0, HK_OFFSET_OF(Legacy451AnimationBinding, m_animation), HK_NULL },
		{ "animationTrackToBoneIndices", HK_NULL, HK_NULL, hkClassMember::TYPE_SIMPLEARRAY, hkClassMember::TYPE_INT16, 0, 0, HK_OFFSET_OF(Legacy451AnimationBinding, m_animationTrackToBoneIndices), HK_NULL },
		{ "blendHint", HK_NULL, HK_NULL, hkClassMember::TYPE_INT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451AnimationBinding, m_blendHint), HK_NULL },
	};

	hkClass g_legacy451AnimationBindingClass(
		"hkAnimationBinding",
		HK_NULL,
		sizeof(Legacy451AnimationBinding),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy451AnimationBindingMembers),
		HK_COUNT_OF(g_legacy451AnimationBindingMembers),
		HK_NULL,
		HK_NULL,
		0);

	static hkInternalClassMember g_legacy451AnimationContainerMembers[] =
	{
		{ "skeletons", &g_legacy451SkeletonClass, HK_NULL, hkClassMember::TYPE_SIMPLEARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy451AnimationContainer, m_skeletons), HK_NULL },
		{ "animations", &g_legacy451DeltaCompressedSkeletalAnimationClass, HK_NULL, hkClassMember::TYPE_SIMPLEARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy451AnimationContainer, m_animations), HK_NULL },
		{ "bindings", &g_legacy451AnimationBindingClass, HK_NULL, hkClassMember::TYPE_SIMPLEARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy451AnimationContainer, m_bindings), HK_NULL },
		{ "attachments", &g_legacy451BoneAttachmentClass, HK_NULL, hkClassMember::TYPE_SIMPLEARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy451AnimationContainer, m_attachments), HK_NULL },
		{ "skins", &g_legacy451MeshBindingClass, HK_NULL, hkClassMember::TYPE_SIMPLEARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy451AnimationContainer, m_skins), HK_NULL },
	};

	hkClass g_legacy451AnimationContainerClass(
		"hkAnimationContainer",
		HK_NULL,
		sizeof(Legacy451AnimationContainer),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy451AnimationContainerMembers),
		HK_COUNT_OF(g_legacy451AnimationContainerMembers),
		HK_NULL,
		HK_NULL,
		0);

	class ExactLegacyClassListener : public hkPackfileWriter::AddObjectListener
	{
	public:
		ExactLegacyClassListener(const void* exactObject, const hkClass* exactClass)
			: m_exactObject(exactObject),
			  m_exactClass(exactClass)
		{
		}

		virtual void addObjectCallback(ObjectPointer& objP, ClassPointer& klassP)
		{
			if (objP == m_exactObject && m_exactClass != HK_NULL)
			{
				klassP = m_exactClass;
			}
		}

	private:
		const void* m_exactObject;
		const hkClass* m_exactClass;
	};

	bool buildLegacyGraph(
		hkRootLevelContainer* legacyRoot,
		Legacy451AnimationContainer& legacyContainer,
		Legacy451Skeleton& legacySkeleton,
		Legacy451AnimationBinding& legacyBinding,
		Legacy451DeltaCompressedSkeletalAnimation& legacyAnimation,
		const hkRootLevelContainer* currentRoot,
		const hkaDeltaCompressedSkeletalAnimation* currentAnimation)
	{
		if (currentRoot == HK_NULL || currentRoot->m_numNamedVariants <= 0 || currentAnimation == HK_NULL)
		{
			fprintf(stderr, "Error: invalid animation graph passed to legacy builder\n");
			return false;
		}

		const hkaAnimationContainer* currentContainer = reinterpret_cast<const hkaAnimationContainer*>(currentRoot->m_namedVariants[0].getObject());
		if (currentContainer == HK_NULL || currentContainer->m_numSkeletons <= 0 || currentContainer->m_numBindings <= 0)
		{
			fprintf(stderr, "Error: current animation container is incomplete\n");
			return false;
		}

		const hkaSkeleton* currentSkeleton = currentContainer->m_skeletons[0];
		const hkaAnimationBinding* currentBinding = currentContainer->m_bindings[0];
		if (currentSkeleton == HK_NULL || currentBinding == HK_NULL)
		{
			fprintf(stderr, "Error: current skeleton or binding is null\n");
			return false;
		}

		legacySkeleton.m_name = currentSkeleton->m_name;
		legacySkeleton.m_parentIndices = currentSkeleton->m_parentIndices;
		legacySkeleton.m_numParentIndices = currentSkeleton->m_numParentIndices;
		legacySkeleton.m_numBones = currentSkeleton->m_numBones;
		legacySkeleton.m_referencePose = currentSkeleton->m_referencePose;
		legacySkeleton.m_numReferencePose = currentSkeleton->m_numReferencePose;
		legacySkeleton.m_bones = new Legacy451Bone*[legacySkeleton.m_numBones];
		for (int i = 0; i < legacySkeleton.m_numBones; ++i)
		{
			Legacy451Bone* legacyBone = new Legacy451Bone();
			legacyBone->m_name = currentSkeleton->m_bones[i]->m_name;
			legacyBone->m_lockTranslation = currentSkeleton->m_bones[i]->m_lockTranslation;
			legacySkeleton.m_bones[i] = legacyBone;
		}

		legacyAnimation.m_type = 2;
		legacyAnimation.m_duration = currentAnimation->m_duration;
		legacyAnimation.m_numberOfTracks = currentAnimation->m_numberOfTransformTracks;
		legacyAnimation.m_extractedMotion = HK_NULL;
		legacyAnimation.m_numAnnotationTracks = currentAnimation->m_numAnnotationTracks;
		legacyAnimation.m_annotationTracks = new Legacy451AnnotationTrack*[legacyAnimation.m_numAnnotationTracks];
		for (int i = 0; i < legacyAnimation.m_numAnnotationTracks; ++i)
		{
			Legacy451AnnotationTrack* legacyTrack = new Legacy451AnnotationTrack();
			legacyTrack->m_name = currentAnimation->m_annotationTracks[i]->m_name;
			legacyTrack->m_annotations = HK_NULL;
			legacyTrack->m_numAnnotations = 0;
			legacyAnimation.m_annotationTracks[i] = legacyTrack;
		}

		legacyAnimation.m_numberOfPoses = currentAnimation->m_numberOfPoses;
		legacyAnimation.m_blockSize = currentAnimation->m_blockSize;
		legacyAnimation.m_qFormat.m_maxBitWidth = currentAnimation->m_qFormat.m_maxBitWidth;
		legacyAnimation.m_qFormat.m_preserved = currentAnimation->m_qFormat.m_preserved;
		legacyAnimation.m_qFormat.m_numD = currentAnimation->m_qFormat.m_numD;
		legacyAnimation.m_qFormat.m_offsetIdx = currentAnimation->m_qFormat.m_offsetIdx;
		legacyAnimation.m_qFormat.m_scaleIdx = currentAnimation->m_qFormat.m_scaleIdx;
		legacyAnimation.m_qFormat.m_bitWidthIdx = currentAnimation->m_qFormat.m_bitWidthIdx;
		legacyAnimation.m_quantizedDataIdx = currentAnimation->m_quantizedDataIdx;
		legacyAnimation.m_quantizedDataSize = currentAnimation->m_quantizedDataSize;
		legacyAnimation.m_staticMaskIdx = currentAnimation->m_staticMaskIdx;
		legacyAnimation.m_staticMaskSize = currentAnimation->m_staticMaskSize;
		legacyAnimation.m_staticDOFsIdx = currentAnimation->m_staticDOFsIdx;
		legacyAnimation.m_staticDOFsSize = currentAnimation->m_staticDOFsSize;
		legacyAnimation.m_totalBlockSize = currentAnimation->m_totalBlockSize;
		legacyAnimation.m_lastBlockSize = currentAnimation->m_lastBlockSize;
		legacyAnimation.m_dataBuffer = currentAnimation->m_dataBuffer;
		legacyAnimation.m_numDataBuffer = currentAnimation->m_numDataBuffer;

		legacyBinding.m_animation = &legacyAnimation;
		legacyBinding.m_animationTrackToBoneIndices = currentBinding->m_transformTrackToBoneIndices;
		legacyBinding.m_numAnimationTrackToBoneIndices = currentBinding->m_numTransformTrackToBoneIndices;
		legacyBinding.m_blendHint = currentBinding->m_blendHint;

		legacyContainer.m_skeletons = new Legacy451Skeleton*[1];
		legacyContainer.m_skeletons[0] = &legacySkeleton;
		legacyContainer.m_numSkeletons = 1;

		legacyContainer.m_animations = new Legacy451DeltaCompressedSkeletalAnimation*[1];
		legacyContainer.m_animations[0] = &legacyAnimation;
		legacyContainer.m_numAnimations = 1;

		legacyContainer.m_bindings = new Legacy451AnimationBinding*[1];
		legacyContainer.m_bindings[0] = &legacyBinding;
		legacyContainer.m_numBindings = 1;
		legacyContainer.m_attachments = HK_NULL;
		legacyContainer.m_numAttachments = 0;
		legacyContainer.m_skins = HK_NULL;
		legacyContainer.m_numSkins = 0;

		legacyRoot->m_namedVariants = hkAllocate<hkRootLevelContainer::NamedVariant>(1, HK_MEMORY_CLASS_SERIALIZE);
		legacyRoot->m_numNamedVariants = 1;
		legacyRoot->m_namedVariants[0].set("Animation Container", &legacyContainer, &g_legacy451AnimationContainerClass);
		return true;
	}
}

bool writeAnimationGraphAs451(
	hkRootLevelContainer* rootContainer,
	const void* exactAnimationObject,
	const hkClass* exactAnimationClass,
	const char* outputFile)
{
	(void)exactAnimationClass;

	if (rootContainer == HK_NULL || exactAnimationObject == HK_NULL || outputFile == HK_NULL)
	{
		fprintf(stderr, "Error: invalid arguments passed to writeAnimationGraphAs451\n");
		return false;
	}

	hkRootLevelContainer legacyRoot;
	Legacy451AnimationContainer legacyContainer;
	Legacy451Skeleton legacySkeleton;
	Legacy451AnimationBinding legacyBinding;
	Legacy451DeltaCompressedSkeletalAnimation legacyAnimation;

	if (!buildLegacyGraph(
			&legacyRoot,
			legacyContainer,
			legacySkeleton,
			legacyBinding,
			legacyAnimation,
			rootContainer,
			reinterpret_cast<const hkaDeltaCompressedSkeletalAnimation*>(exactAnimationObject)))
	{
		return false;
	}

	ExactLegacyClassListener listener(&legacyAnimation, &g_legacy451DeltaCompressedSkeletalAnimationClass);
	hkVtableClassRegistry registry;
	registry.registerVtable(*reinterpret_cast<const void* const*>(&legacyAnimation), &g_legacy451DeltaCompressedSkeletalAnimationClass);

	hkBinaryPackfileWriter writer;
	writer.setContentsWithRegistry(&legacyRoot, hkRootLevelContainerClass, &registry, &listener);

	hkPackfileWriter::Options options;
	options.m_layout = hkStructureLayout::MsvcWin32LayoutRules;
	options.m_writeMetaInfo = true;
	options.m_contentsVersion = kTargetVersion;

	hkOstream stream(outputFile);
	if (!stream.isOk())
	{
		fprintf(stderr, "Error: cannot open output HKX file %s\n", outputFile);
		return false;
	}

	if (writer.save(stream.getStreamWriter(), options) != HK_SUCCESS)
	{
		fprintf(stderr, "Error: failed to write Havok 4.5.1 packfile\n");
		return false;
	}

	return true;
}