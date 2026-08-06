#ifndef DOW2_PHYSICS_JSON_OUTPUT_H
#define DOW2_PHYSICS_JSON_OUTPUT_H

#include <vector>

#include "json_physics_input.h"

bool writePhysicsJson(
	const char* filename,
	const std::vector<RawPhysicsSystem>& systems,
	const char* sourceFormat);

#endif