#include "json_physics_output.h"

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

	bool writeBool(FILE* file, bool value)
	{
		return fputs(value ? "true" : "false", file) != EOF;
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

	bool writeVector(FILE* file, const float* values, int count)
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

	bool writeVertices(FILE* file, const std::vector<RawVertex>& vertices, int indentLevel)
	{
		if (fputs("[\n", file) == EOF)
		{
			return false;
		}

		for (size_t index = 0; index < vertices.size(); ++index)
		{
			const RawVertex& vertex = vertices[index];
			const float values[3] = { vertex.x, vertex.y, vertex.z };
			if (!writeIndent(file, indentLevel + 1))
			{
				return false;
			}
			if (!writeVector(file, values, 3))
			{
				return false;
			}
			if (index + 1 < vertices.size() && fputc(',', file) == EOF)
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

	bool writeRigidBody(FILE* file, const RawRigidBody& body, int indentLevel)
	{
		if (!writeIndent(file, indentLevel) || fputs("{\n", file) == EOF)
		{
			return false;
		}

		if (!writeIndent(file, indentLevel + 1) || fputs("\"name\": ", file) == EOF || !writeEscapedString(file, body.name.c_str()) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"vertices\": ", file) == EOF || !writeVertices(file, body.vertices, indentLevel + 1) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"position\": ", file) == EOF || !writeVector(file, body.position, 3) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"rotation\": ", file) == EOF || !writeVector(file, body.rotation, 4) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"friction\": ", file) == EOF || !writeFloat(file, body.friction) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"restitution\": ", file) == EOF || !writeFloat(file, body.restitution) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"motion_type\": ", file) == EOF || !writeEscapedString(file, body.motionType.c_str()) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"quality_type\": ", file) == EOF || !writeInt(file, body.qualityType) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"allowed_penetration_depth\": ", file) == EOF || !writeFloat(file, body.allowedPenetrationDepth) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"process_contact_callback_delay\": ", file) == EOF || !writeInt(file, body.processContactCallbackDelay) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"deactivation_class\": ", file) == EOF || !writeInt(file, body.deactivationClass) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"deactivation_integrate_counter\": ", file) == EOF || !writeInt(file, body.deactivationIntegrateCounter) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"linear_damping\": ", file) == EOF || !writeFloat(file, body.linearDamping) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"angular_damping\": ", file) == EOF || !writeFloat(file, body.angularDamping) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"max_linear_velocity\": ", file) == EOF || !writeFloat(file, body.maxLinearVelocity) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"max_angular_velocity\": ", file) == EOF || !writeFloat(file, body.maxAngularVelocity) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"collision_filter_info\": ", file) == EOF || !writeInt(file, (int)body.collisionFilterInfo) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"event_filter\": ", file) == EOF || !writeInt(file, body.eventFilter) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"user_filter\": ", file) == EOF || !writeInt(file, body.userFilter) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"mass\": ", file) == EOF || !writeFloat(file, body.mass) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"center_of_mass_mode\": ", file) == EOF || !writeEscapedString(file, body.centerOfMassMode.c_str()) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"center_of_mass_override\": ", file) == EOF || !writeVector(file, body.centerOfMassOverride, 3) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"shape_radius\": ", file) == EOF || !writeFloat(file, body.shapeRadius) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"response_type\": ", file) == EOF || !writeEscapedString(file, body.responseType.c_str()) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"deactivator_present\": ", file) == EOF || !writeBool(file, body.deactivatorPresent) || fputc('\n', file) == EOF)
		{
			return false;
		}

		return writeIndent(file, indentLevel) && fputc('}', file) != EOF;
	}

	bool writePhysicsSystem(FILE* file, const RawPhysicsSystem& system, int indentLevel)
	{
		if (!writeIndent(file, indentLevel) || fputs("{\n", file) == EOF)
		{
			return false;
		}

		if (!writeIndent(file, indentLevel + 1) || fputs("\"name\": ", file) == EOF || !writeEscapedString(file, system.name.c_str()) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"rigid_bodies\": [\n", file) == EOF)
		{
			return false;
		}

		for (size_t index = 0; index < system.rigidBodies.size(); ++index)
		{
			if (!writeRigidBody(file, system.rigidBodies[index], indentLevel + 2))
			{
				return false;
			}
			if (index + 1 < system.rigidBodies.size() && fputc(',', file) == EOF)
			{
				return false;
			}
			if (fputc('\n', file) == EOF)
			{
				return false;
			}
		}

		if (!writeIndent(file, indentLevel + 1) || fputs("]\n", file) == EOF)
		{
			return false;
		}

		return writeIndent(file, indentLevel) && fputc('}', file) != EOF;
	}
}

bool writePhysicsJson(
	const char* filename,
	const std::vector<RawPhysicsSystem>& systems,
	const char* sourceFormat)
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

	const char* format = (sourceFormat != 0 && sourceFormat[0] != '\0') ? sourceFormat : "hkx";
	const bool headerSuccess =
		fputs("{\n", file) != EOF &&
		writeIndent(file, 1) && fputs("\"version\": \"1.0\",\n", file) != EOF &&
		writeIndent(file, 1) && fputs("\"source_format\": ", file) != EOF && writeEscapedString(file, format) && fputs(",\n", file) != EOF &&
		writeIndent(file, 1) && fputs("\"physics_systems\": [\n", file) != EOF;

	if (!headerSuccess)
	{
		fclose(file);
		return false;
	}

	for (size_t index = 0; index < systems.size(); ++index)
	{
		if (!writePhysicsSystem(file, systems[index], 2))
		{
			fclose(file);
			return false;
		}
		if (index + 1 < systems.size() && fputc(',', file) == EOF)
		{
			fclose(file);
			return false;
		}
		if (fputc('\n', file) == EOF)
		{
			fclose(file);
			return false;
		}
	}

	const bool footerSuccess =
		writeIndent(file, 1) && fputs("]\n", file) != EOF &&
		fputs("}\n", file) != EOF;

	if (fclose(file) != 0 || !footerSuccess)
	{
		fprintf(stderr, "Error: failed to write output JSON file %s\n", filename);
		return false;
	}

	return true;
}