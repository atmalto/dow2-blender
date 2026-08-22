#ifndef DOW2_RAGDOLL_JSON_OUTPUT_H
#define DOW2_RAGDOLL_JSON_OUTPUT_H

#include "json_ragdoll_input.h"

bool writeRagdollJson(
	const char* filename,
	const ragdoll_io::RawRagdollData& data);

#endif