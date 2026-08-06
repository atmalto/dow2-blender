// Mod Studio bridge-only helpers.
// These keep the Blender-facing file-path exports intact while giving Mod Studio
// an in-memory animation read path for the live bridge.

#include "mod_studio_animation_bridge.h"

#include <stdio.h>

namespace
{
	void appendIndent(std::string& output, int indentLevel)
	{
		for (int index = 0; index < indentLevel; ++index)
		{
			output += "  ";
		}
	}

	void appendEscapedString(std::string& output, const char* text)
	{
		output += '"';
		const unsigned char* cursor = reinterpret_cast<const unsigned char*>(text != 0 ? text : "");
		while (*cursor != '\0')
		{
			const unsigned char ch = *cursor++;
			switch (ch)
			{
			case '\\':
				output += "\\\\";
				break;
			case '"':
				output += "\\\"";
				break;
			case '\b':
				output += "\\b";
				break;
			case '\f':
				output += "\\f";
				break;
			case '\n':
				output += "\\n";
				break;
			case '\r':
				output += "\\r";
				break;
			case '\t':
				output += "\\t";
				break;
			default:
				if (ch < 0x20)
				{
					char buffer[7];
					const int written = _snprintf(buffer, sizeof(buffer), "\\u%04x", static_cast<unsigned int>(ch));
					if (written > 0)
					{
						output.append(buffer, static_cast<size_t>(written));
					}
				}
				else
				{
					output += static_cast<char>(ch);
				}
				break;
			}
		}
		output += '"';
	}

	void appendFloat(std::string& output, float value)
	{
		char buffer[32];
		const int written = _snprintf(buffer, sizeof(buffer), "%.9g", static_cast<double>(value));
		if (written > 0)
		{
			output.append(buffer, static_cast<size_t>(written));
		}
	}

	void appendInt(std::string& output, int value)
	{
		char buffer[32];
		const int written = _snprintf(buffer, sizeof(buffer), "%d", value);
		if (written > 0)
		{
			output.append(buffer, static_cast<size_t>(written));
		}
	}

	void appendFloatArray(std::string& output, const float* values, int count)
	{
		output += '[';
		for (int index = 0; index < count; ++index)
		{
			if (index > 0)
			{
				output += ", ";
			}
			appendFloat(output, values[index]);
		}
		output += ']';
	}

	void appendTransform(std::string& output, const RawTransform& transform, int indentLevel)
	{
		appendIndent(output, indentLevel);
		output += "{\n";
		appendIndent(output, indentLevel + 1);
		output += "\"pos\": ";
		appendFloatArray(output, transform.pos, 3);
		output += ",\n";
		appendIndent(output, indentLevel + 1);
		output += "\"rot\": ";
		appendFloatArray(output, transform.rot, 4);
		output += ",\n";
		appendIndent(output, indentLevel + 1);
		output += "\"scale\": ";
		appendFloatArray(output, transform.scale, 3);
		output += '\n';
		appendIndent(output, indentLevel);
		output += '}';
	}

	void appendStringArray(std::string& output, const std::vector<std::string>& values, int indentLevel)
	{
		output += "[\n";
		for (size_t index = 0; index < values.size(); ++index)
		{
			appendIndent(output, indentLevel + 1);
			appendEscapedString(output, values[index].c_str());
			if (index + 1 < values.size())
			{
				output += ',';
			}
			output += '\n';
		}
		appendIndent(output, indentLevel);
		output += ']';
	}

	void appendIntArray(std::string& output, const std::vector<int>& values, int indentLevel)
	{
		output += "[\n";
		for (size_t index = 0; index < values.size(); ++index)
		{
			appendIndent(output, indentLevel + 1);
			appendInt(output, values[index]);
			if (index + 1 < values.size())
			{
				output += ',';
			}
			output += '\n';
		}
		appendIndent(output, indentLevel);
		output += ']';
	}

	void appendReferencePose(std::string& output, const std::vector<RawTransform>& values, int indentLevel)
	{
		output += "[\n";
		for (size_t index = 0; index < values.size(); ++index)
		{
			appendTransform(output, values[index], indentLevel + 1);
			if (index + 1 < values.size())
			{
				output += ',';
			}
			output += '\n';
		}
		appendIndent(output, indentLevel);
		output += ']';
	}

	void appendFrameTransforms(std::string& output, const ParsedAnimationData& data, int indentLevel)
	{
		const int numTracks = static_cast<int>(data.trackBoneIndices.size());
		output += "[\n";
		for (int frameIndex = 0; frameIndex < data.numFrames; ++frameIndex)
		{
			appendIndent(output, indentLevel + 1);
			output += "[\n";
			for (int trackIndex = 0; trackIndex < numTracks; ++trackIndex)
			{
				const RawTransform& transform = data.transforms[frameIndex * numTracks + trackIndex];
				appendTransform(output, transform, indentLevel + 2);
				if (trackIndex + 1 < numTracks)
				{
					output += ',';
				}
				output += '\n';
			}
			appendIndent(output, indentLevel + 1);
			output += ']';
			if (frameIndex + 1 < data.numFrames)
			{
				output += ',';
			}
			output += '\n';
		}
		appendIndent(output, indentLevel);
		output += ']';
	}
}

bool writeAnimationJsonForModStudio(const ParsedAnimationData& data, std::string& output)
{
	output.clear();
	output.reserve(4096 + (data.transforms.size() * 96));
	output += "{\n";
	appendIndent(output, 1);
	output += "\"skeleton_name\": ";
	appendEscapedString(output, data.skeletonName.c_str());
	output += ",\n";
	appendIndent(output, 1);
	output += "\"duration\": ";
	appendFloat(output, data.duration);
	output += ",\n";
	appendIndent(output, 1);
	output += "\"bones\": ";
	appendStringArray(output, data.boneNames, 1);
	output += ",\n";
	appendIndent(output, 1);
	output += "\"parent_indices\": ";
	appendIntArray(output, data.parentIndices, 1);
	output += ",\n";
	appendIndent(output, 1);
	output += "\"reference_pose\": ";
	appendReferencePose(output, data.referencePose, 1);
	output += ",\n";
	appendIndent(output, 1);
	output += "\"track_bone_indices\": ";
	appendIntArray(output, data.trackBoneIndices, 1);
	output += ",\n";
	appendIndent(output, 1);
	output += "\"num_frames\": ";
	appendInt(output, data.numFrames);
	output += ",\n";
	appendIndent(output, 1);
	output += "\"transforms\": ";
	appendFrameTransforms(output, data, 1);
	output += "\n}\n";
	return true;
}