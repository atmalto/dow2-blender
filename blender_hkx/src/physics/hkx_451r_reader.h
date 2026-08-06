#ifndef DOW2_PHYSICS_HKX_451R_READER_H
#define DOW2_PHYSICS_HKX_451R_READER_H

#include <vector>

#include "json_physics_input.h"

bool readPhysicsPackfile(
	const char* inputFile,
	std::vector<RawPhysicsSystem>& systemsOut);

#endif