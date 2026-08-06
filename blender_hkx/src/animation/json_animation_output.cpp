#include "json_animation_output.h"

#include <stdio.h>

namespace
{
	bool writeEscapedString(FILE* file, const char* text)
	{
		if (fputc('"', file) == EOF)
		{
			return false;
		}

		const unsigned char* cursor = reinterpret_cast<const unsigned char*>(text != 0 ? text : "");
		while (*cursor != '\0')
		{
			const unsigned char ch = *cursor++;
			switch (ch)
			{
			case '\\':
				if (fputs("\\\\", file) == EOF)
				{
					return false;
				}
				break;
			case '"':
				if (fputs("\\\"", file) == EOF)
				{
					return false;
				}
				break;
			case '\b':
				if (fputs("\\b", file) == EOF)
				{
					return false;
				}
				break;
			case '\f':
				if (fputs("\\f", file) == EOF)
				{
					return false;
				}
				break;
			case '\n':
				if (fputs("\\n", file) == EOF)
				{
					return false;
				}
				break;
			case '\r':
				if (fputs("\\r", file) == EOF)
				{
					return false;
				}
				break;
			case '\t':
				if (fputs("\\t", file) == EOF)
				{
					return false;
				}
				break;
			default:
				if (ch < 0x20)
				{
					if (fprintf(file, "\\u%04x", static_cast<unsigned int>(ch)) < 0)
					{
						return false;
					}
				}
				else if (fputc(ch, file) == EOF)
				{
					return false;
				}
				break;
			}
		}

		return fputc('"', file) != EOF;
	}

	bool writeFloat(FILE* file, float value)
	{
		return fprintf(file, "%.9g", static_cast<double>(value)) >= 0;
	}

	bool writeInt(FILE* file, int value)
	{
		return fprintf(file, "%d", value) >= 0;
	}

	bool writeIndent(FILE* file, int indentLevel)
	{
		for (int index = 0; index < indentLevel; ++index)
		{
			if (fputs("  ", file) == EOF)
			{
				return false;
			}
		}
		return true;
	}

	bool writeFloatArray(FILE* file, const float* values, int count)
	{
		if (fputc('[', file) == EOF)
		{
			return false;
		}

		for (int index = 0; index < count; ++index)
		{
			if (index > 0 && fputs(", ", file) == EOF)
			{
				return false;
			}
			if (!writeFloat(file, values[index]))
			{
				return false;
			}
		}

		return fputc(']', file) != EOF;
	}

	bool writeTransform(FILE* file, const RawTransform& transform, int indentLevel)
	{
		if (!writeIndent(file, indentLevel) || fputs("{\n", file) == EOF)
		{
			return false;
		}

		if (!writeIndent(file, indentLevel + 1) || fputs("\"pos\": ", file) == EOF || !writeFloatArray(file, transform.pos, 3) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"rot\": ", file) == EOF || !writeFloatArray(file, transform.rot, 4) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"scale\": ", file) == EOF || !writeFloatArray(file, transform.scale, 3) || fputc('\n', file) == EOF)
		{
			return false;
		}

		return writeIndent(file, indentLevel) && fputc('}', file) != EOF;
	}

	bool writeStringArray(FILE* file, const std::vector<std::string>& values, int indentLevel)
	{
		if (fputs("[\n", file) == EOF)
		{
			return false;
		}

		for (size_t index = 0; index < values.size(); ++index)
		{
			if (!writeIndent(file, indentLevel + 1) || !writeEscapedString(file, values[index].c_str()))
			{
				return false;
			}
			if (index + 1 < values.size() && fputc(',', file) == EOF)
			{
				return false;
			}
			if (fputc('\n', file) == EOF)
			{
				return false;
			}
		}

		if (!writeIndent(file, indentLevel))
		{
			return false;
		}
		return fputc(']', file) != EOF;
	}

			bool writeFloatVector(FILE* file, const std::vector<float>& values, int indentLevel)
			{
				if (fputs("[\n", file) == EOF)
				{
					return false;
				}

				for (size_t index = 0; index < values.size(); ++index)
				{
					if (!writeIndent(file, indentLevel + 1) || !writeFloat(file, values[index]))
					{
						return false;
					}
					if (index + 1 < values.size() && fputc(',', file) == EOF)
					{
						return false;
					}
					if (fputc('\n', file) == EOF)
					{
						return false;
					}
				}

				if (!writeIndent(file, indentLevel))
				{
					return false;
				}
				return fputc(']', file) != EOF;
			}

	bool writeIntArray(FILE* file, const std::vector<int>& values, int indentLevel)
	{
		if (fputs("[\n", file) == EOF)
		{
			return false;
		}

		for (size_t index = 0; index < values.size(); ++index)
		{
			if (!writeIndent(file, indentLevel + 1) || !writeInt(file, values[index]))
			{
				return false;
			}
			if (index + 1 < values.size() && fputc(',', file) == EOF)
			{
				return false;
			}
			if (fputc('\n', file) == EOF)
			{
				return false;
			}
		}

		if (!writeIndent(file, indentLevel))
		{
			return false;
		}
		return fputc(']', file) != EOF;
	}

	bool writeReferencePose(FILE* file, const std::vector<RawTransform>& values, int indentLevel)
	{
		if (fputs("[\n", file) == EOF)
		{
			return false;
		}

		for (size_t index = 0; index < values.size(); ++index)
		{
			if (!writeTransform(file, values[index], indentLevel + 1))
			{
				return false;
			}
			if (index + 1 < values.size() && fputc(',', file) == EOF)
			{
				return false;
			}
			if (fputc('\n', file) == EOF)
			{
				return false;
			}
		}

		if (!writeIndent(file, indentLevel))
		{
			return false;
		}
		return fputc(']', file) != EOF;
	}

	bool writeFrameTransforms(FILE* file, const ParsedAnimationData& data, int indentLevel)
	{
		const int numTracks = static_cast<int>(data.trackBoneIndices.size());
		if (fputs("[\n", file) == EOF)
		{
			return false;
		}

		for (int frameIndex = 0; frameIndex < data.numFrames; ++frameIndex)
		{
			if (!writeIndent(file, indentLevel + 1) || fputs("[\n", file) == EOF)
			{
				return false;
			}

			for (int trackIndex = 0; trackIndex < numTracks; ++trackIndex)
			{
				const RawTransform& transform = data.transforms[frameIndex * numTracks + trackIndex];
				if (!writeTransform(file, transform, indentLevel + 2))
				{
					return false;
				}
				if (trackIndex + 1 < numTracks && fputc(',', file) == EOF)
				{
					return false;
				}
				if (fputc('\n', file) == EOF)
				{
					return false;
				}
			}

			if (!writeIndent(file, indentLevel + 1) || fputc(']', file) == EOF)
			{
				return false;
			}
			if (frameIndex + 1 < data.numFrames && fputc(',', file) == EOF)
			{
				return false;
			}
			if (fputc('\n', file) == EOF)
			{
				return false;
			}
		}

		if (!writeIndent(file, indentLevel))
		{
			return false;
		}
		return fputc(']', file) != EOF;
	}
}

bool writeAnimationJson(const char* filename, const ParsedAnimationData& data)
{
	if (filename == 0)
	{
		fprintf(stderr, "Error: invalid output JSON path\n");
		return false;
	}

	FILE* file = 0;
#if defined(_MSC_VER)
	if (fopen_s(&file, filename, "wb") != 0)
	{
		file = 0;
	}
#else
	file = fopen(filename, "wb");
#endif
	if (file == 0)
	{
		fprintf(stderr, "Error: cannot open output JSON file %s\n", filename);
		return false;
	}

	const bool ok =
		fputs("{\n", file) != EOF &&
		writeIndent(file, 1) && fputs("\"skeleton_name\": ", file) != EOF && writeEscapedString(file, data.skeletonName.c_str()) && fputs(",\n", file) != EOF &&
		writeIndent(file, 1) && fputs("\"duration\": ", file) != EOF && writeFloat(file, data.duration) && fputs(",\n", file) != EOF &&
		(data.sampleTimes.empty() || (writeIndent(file, 1) && fputs("\"sample_times\": ", file) != EOF && writeFloatVector(file, data.sampleTimes, 1) && fputs(",\n", file) != EOF)) &&
		(data.sampleFramePositions.empty() || (writeIndent(file, 1) && fputs("\"sample_frame_positions\": ", file) != EOF && writeFloatVector(file, data.sampleFramePositions, 1) && fputs(",\n", file) != EOF)) &&
		writeIndent(file, 1) && fputs("\"bones\": ", file) != EOF && writeStringArray(file, data.boneNames, 1) && fputs(",\n", file) != EOF &&
		writeIndent(file, 1) && fputs("\"parent_indices\": ", file) != EOF && writeIntArray(file, data.parentIndices, 1) && fputs(",\n", file) != EOF &&
		writeIndent(file, 1) && fputs("\"reference_pose\": ", file) != EOF && writeReferencePose(file, data.referencePose, 1) && fputs(",\n", file) != EOF &&
		writeIndent(file, 1) && fputs("\"track_bone_indices\": ", file) != EOF && writeIntArray(file, data.trackBoneIndices, 1) && fputs(",\n", file) != EOF &&
		writeIndent(file, 1) && fputs("\"num_frames\": ", file) != EOF && writeInt(file, data.numFrames) && fputs(",\n", file) != EOF &&
		writeIndent(file, 1) && fputs("\"transforms\": ", file) != EOF && writeFrameTransforms(file, data, 1) && fputc('\n', file) != EOF &&
		fputs("}\n", file) != EOF;

	if (fclose(file) != 0 || !ok)
	{
		fprintf(stderr, "Error: failed to write output JSON file %s\n", filename);
		return false;
	}

	return true;
}