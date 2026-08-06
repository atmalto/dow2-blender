#ifndef DOW2_ANIMATION_HKX_451_WRITER_H
#define DOW2_ANIMATION_HKX_451_WRITER_H

class hkRootLevelContainer;
class hkClass;

bool writeAnimationGraphAs451(
	hkRootLevelContainer* rootContainer,
	const void* exactAnimationObject,
	const hkClass* exactAnimationClass,
	const char* outputFile);

#endif