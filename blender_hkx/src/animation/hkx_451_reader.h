#ifndef DOW2_ANIMATION_HKX_451_READER_H
#define DOW2_ANIMATION_HKX_451_READER_H

#include "json_animation_input.h"

bool readAnimationGraph(const char* inputFile, ParsedAnimationData& outData);
bool sampleAnimationGraph(const char* inputFile, int startFrame, int endFrame, int samplesPerFrame, ParsedAnimationData& outData);

#endif