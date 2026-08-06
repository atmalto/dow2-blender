#ifndef DOW2_PHYSICS_HKX_55_WRITER_H
#define DOW2_PHYSICS_HKX_55_WRITER_H

class hkRootLevelContainer;

bool writePhysicsPackfile(
	hkRootLevelContainer* rootContainer,
	const char* outputFile);

#endif