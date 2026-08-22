#ifndef DOW2_RAGDOLL_HKX_451R_READER_H
#define DOW2_RAGDOLL_HKX_451R_READER_H

#include "json_ragdoll_input.h"

bool readRagdollPackfile(
	const char* inputFile,
	ragdoll_io::RawRagdollData& dataOut);

#endif