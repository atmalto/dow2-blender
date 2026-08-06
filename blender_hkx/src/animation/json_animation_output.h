#ifndef DOW2_ANIMATION_JSON_ANIMATION_OUTPUT_H
#define DOW2_ANIMATION_JSON_ANIMATION_OUTPUT_H

#include "json_animation_input.h"

bool writeAnimationJson(const char* filename, const ParsedAnimationData& data);

#endif