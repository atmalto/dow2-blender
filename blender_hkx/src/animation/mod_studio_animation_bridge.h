#ifndef DOW2_ANIMATION_MOD_STUDIO_ANIMATION_BRIDGE_H
#define DOW2_ANIMATION_MOD_STUDIO_ANIMATION_BRIDGE_H

#include <string>

#include "json_animation_input.h"

bool writeAnimationJsonForModStudio(const ParsedAnimationData& data, std::string& output);

#endif