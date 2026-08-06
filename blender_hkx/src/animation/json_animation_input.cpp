#include "json_animation_input.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <fstream>
#include <sstream>

namespace
{
	const char* skipWS(const char* p)
	{
		while (*p && (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r'))
		{
			++p;
		}
		return p;
	}

	const char* parseNumber(const char* p, float& out)
	{
		p = skipWS(p);
		char* end = 0;
		out = (float)strtod(p, &end);
		return end;
	}

	const char* parseInt(const char* p, int& out)
	{
		p = skipWS(p);
		char* end = 0;
		out = (int)strtol(p, &end, 10);
		return end;
	}

	const char* parseString(const char* p, std::string& out)
	{
		p = skipWS(p);
		if (*p != '"')
		{
			return p;
		}

		++p;
		out.clear();
		while (*p && *p != '"')
		{
			if (*p == '\\' && *(p + 1))
			{
				++p;
			}
			out += *p++;
		}

		if (*p == '"')
		{
			++p;
		}
		return p;
	}

	const char* findKey(const char* p, const char* key)
	{
		std::string keyStr = std::string("\"") + key + "\"";
		const char* found = strstr(p, keyStr.c_str());
		if (!found)
		{
			return 0;
		}

		found += keyStr.length();
		found = skipWS(found);
		if (*found == ':')
		{
			++found;
		}
		return skipWS(found);
	}

	const char* parseFloatArray(const char* p, float* arr, int count)
	{
		p = skipWS(p);
		if (*p != '[')
		{
			return p;
		}

		++p;
		for (int i = 0; i < count; ++i)
		{
			p = parseNumber(p, arr[i]);
			p = skipWS(p);
			if (*p == ',')
			{
				++p;
			}
		}

		p = skipWS(p);
		if (*p == ']')
		{
			++p;
		}
		return p;
	}

	const char* parseTransformRaw(const char* p, RawTransform& t)
	{
		p = skipWS(p);
		if (*p != '{')
		{
			return p;
		}

		const char* objEnd = strchr(p, '}');
		if (!objEnd)
		{
			return p;
		}

		t.pos[0] = t.pos[1] = t.pos[2] = 0.0f;
		t.rot[0] = t.rot[1] = t.rot[2] = 0.0f;
		t.rot[3] = 1.0f;
		t.scale[0] = t.scale[1] = t.scale[2] = 1.0f;

		const char* posPtr = findKey(p, "pos");
		if (posPtr && posPtr < objEnd)
		{
			parseFloatArray(posPtr, t.pos, 3);
		}

		const char* rotPtr = findKey(p, "rot");
		if (rotPtr && rotPtr < objEnd)
		{
			parseFloatArray(rotPtr, t.rot, 4);
		}

		const char* scalePtr = findKey(p, "scale");
		if (scalePtr && scalePtr < objEnd)
		{
			parseFloatArray(scalePtr, t.scale, 3);
		}

		return objEnd + 1;
	}
}

bool parseAnimationJson(const char* filename, ParsedAnimationData& outData)
{
	printf("  Opening file...\n");

	std::ifstream file(filename);
	if (!file.is_open())
	{
		fprintf(stderr, "Error: Cannot open file %s\n", filename);
		return false;
	}

	printf("  Reading content...\n");

	std::stringstream buffer;
	buffer << file.rdbuf();
	std::string content = buffer.str();
	const char* json = content.c_str();

	printf("  Read %d bytes\n", (int)content.length());

	const char* p = findKey(json, "skeleton_name");
	if (p)
	{
		parseString(p, outData.skeletonName);
	}
	else
	{
		outData.skeletonName = "skeleton";
	}
	printf("  skeleton_name = %s\n", outData.skeletonName.c_str());

	p = findKey(json, "duration");
	if (p)
	{
		parseNumber(p, outData.duration);
	}
	else
	{
		outData.duration = 1.0f;
	}
	printf("  duration = %.3f\n", outData.duration);

	p = findKey(json, "num_frames");
	if (p)
	{
		parseInt(p, outData.numFrames);
	}
	else
	{
		outData.numFrames = 1;
	}
	printf("  num_frames = %d\n", outData.numFrames);

	p = findKey(json, "bones");
	if (p && *p == '[')
	{
		++p;
		while (*p && *p != ']')
		{
			p = skipWS(p);
			if (*p == '"')
			{
				std::string boneName;
				p = parseString(p, boneName);
				outData.boneNames.push_back(boneName);
			}
			p = skipWS(p);
			if (*p == ',')
			{
				++p;
			}
		}
	}
	printf("  Found %d bones\n", (int)outData.boneNames.size());

	const int numBones = (int)outData.boneNames.size();
	if (numBones == 0)
	{
		fprintf(stderr, "Error: No bones found in JSON\n");
		return false;
	}

	p = findKey(json, "parent_indices");
	if (p && *p == '[')
	{
		++p;
		for (int i = 0; i < numBones && *p && *p != ']'; ++i)
		{
			int idx = -1;
			p = parseInt(p, idx);
			outData.parentIndices.push_back(idx);
			p = skipWS(p);
			if (*p == ',')
			{
				++p;
			}
		}
	}
	printf("  Found %d parent indices\n", (int)outData.parentIndices.size());

	while ((int)outData.parentIndices.size() < numBones)
	{
		outData.parentIndices.push_back(-1);
	}

	p = findKey(json, "reference_pose");
	if (p && *p == '[')
	{
		++p;
		for (int i = 0; i < numBones && *p && *p != ']'; )
		{
			p = skipWS(p);
			if (*p == '{')
			{
				RawTransform t;
				p = parseTransformRaw(p, t);
				outData.referencePose.push_back(t);
				++i;
			}
			else if (*p == ',')
			{
				++p;
			}
			else
			{
				++p;
			}
		}
	}
	printf("  Found %d reference poses\n", (int)outData.referencePose.size());

	while ((int)outData.referencePose.size() < numBones)
	{
		RawTransform t;
		t.pos[0] = t.pos[1] = t.pos[2] = 0.0f;
		t.rot[0] = t.rot[1] = t.rot[2] = 0.0f;
		t.rot[3] = 1.0f;
		t.scale[0] = t.scale[1] = t.scale[2] = 1.0f;
		outData.referencePose.push_back(t);
	}

	p = findKey(json, "track_bone_indices");
	if (p && *p == '[')
	{
		++p;
		while (*p && *p != ']')
		{
			int idx = -1;
			p = parseInt(p, idx);
			outData.trackBoneIndices.push_back(idx);
			p = skipWS(p);
			if (*p == ',')
			{
				++p;
			}
		}
	}

	if (outData.trackBoneIndices.empty())
	{
		for (int i = 0; i < numBones; ++i)
		{
			outData.trackBoneIndices.push_back(i);
		}
	}

	const int numTracks = (int)outData.trackBoneIndices.size();
	for (int i = 0; i < numTracks; ++i)
	{
		if (outData.trackBoneIndices[i] < 0 || outData.trackBoneIndices[i] >= numBones)
		{
			fprintf(stderr, "Error: Invalid track_bone_indices[%d] = %d\n", i, outData.trackBoneIndices[i]);
			return false;
		}
	}
	printf("  Found %d track mappings\n", numTracks);

	printf("  Parsing transforms (%d frames x %d tracks)...\n", outData.numFrames, numTracks);
	outData.transforms.resize(outData.numFrames * numTracks);
	for (int i = 0; i < outData.numFrames * numTracks; ++i)
	{
		outData.transforms[i].pos[0] = outData.transforms[i].pos[1] = outData.transforms[i].pos[2] = 0.0f;
		outData.transforms[i].rot[0] = outData.transforms[i].rot[1] = outData.transforms[i].rot[2] = 0.0f;
		outData.transforms[i].rot[3] = 1.0f;
		outData.transforms[i].scale[0] = outData.transforms[i].scale[1] = outData.transforms[i].scale[2] = 1.0f;
	}

	p = findKey(json, "transforms");
	if (p && *p == '[')
	{
		++p;
		for (int frame = 0; frame < outData.numFrames && *p && *p != ']'; )
		{
			p = skipWS(p);
			if (*p == '[')
			{
				++p;
				for (int track = 0; track < numTracks && *p && *p != ']'; )
				{
					p = skipWS(p);
					if (*p == '{')
					{
						p = parseTransformRaw(p, outData.transforms[frame * numTracks + track]);
						++track;
					}
					else if (*p == ',')
					{
						++p;
					}
					else
					{
						++p;
					}
				}
				if (*p == ']')
				{
					++p;
				}
				++frame;
			}
			else if (*p == ',')
			{
				++p;
			}
			else
			{
				++p;
			}
		}
	}

	printf(
		"Parsed: %d bones, %d tracks, %d frames, duration %.3f\n",
		numBones,
		numTracks,
		outData.numFrames,
		outData.duration);
	return true;
}