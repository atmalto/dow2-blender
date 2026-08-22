#include "json_ragdoll_output.h"

#include <stdio.h>

using namespace ragdoll_io;

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

	bool writeTransform(FILE* file, const RawTransform& transform, int indentLevel)
	{
		if (!writeIndent(file, indentLevel) || fputs("{\n", file) == EOF)
		{
			return false;
		}

		if (!writeIndent(file, indentLevel + 1) || fputs("\"pos\": ", file) == EOF || !writeVector(file, transform.pos, 3) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"rot\": ", file) == EOF || !writeVector(file, transform.rot, 4) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"scale\": ", file) == EOF || !writeVector(file, transform.scale, 3) || fputc('\n', file) == EOF)
		{
			return false;
		}

		return writeIndent(file, indentLevel) && fputc('}', file) != EOF;
	}

	bool writeTransformArray(FILE* file, const std::vector<RawTransform>& transforms, int indentLevel)
	{
		if (fputs("[\n", file) == EOF)
		{
			return false;
		}

		for (size_t index = 0; index < transforms.size(); ++index)
		{
			if (!writeTransform(file, transforms[index], indentLevel + 1))
			{
				return false;
			}
			if (index + 1 < transforms.size() && fputc(',', file) == EOF)
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

	bool writeIntArray(FILE* file, const std::vector<int>& values)
	{
		if (fputc('[', file) == EOF)
		{
			return false;
		}

		for (size_t index = 0; index < values.size(); ++index)
		{
			if (index > 0 && fputs(", ", file) == EOF)
			{
				return false;
			}
			if (!writeInt(file, values[index]))
			{
				return false;
			}
		}

		return fputc(']', file) != EOF;
	}

	bool writeSkeleton(FILE* file, const char* label, const RawSkeleton& skeleton, int indentLevel)
	{
		if (!writeIndent(file, indentLevel) || fputc('"', file) == EOF || fputs(label, file) == EOF || fputs("\": {\n", file) == EOF)
		{
			return false;
		}

		if (!writeIndent(file, indentLevel + 1) || fputs("\"name\": ", file) == EOF || !writeEscapedString(file, skeleton.name.c_str()) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"bones\": ", file) == EOF || !writeStringArray(file, skeleton.bones, indentLevel + 1) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"parent_indices\": ", file) == EOF || !writeIntArray(file, skeleton.parentIndices) || fputs(",\n", file) == EOF)
		{
			return false;
		}
		if (!writeIndent(file, indentLevel + 1) || fputs("\"reference_pose\": ", file) == EOF || !writeTransformArray(file, skeleton.referencePose, indentLevel + 1) || fputc('\n', file) == EOF)
		{
			return false;
		}

		return writeIndent(file, indentLevel) && fputc('}', file) != EOF;
	}

	bool writeBoneMappings(FILE* file, const std::vector<RawBoneMapping>& mappings, int indentLevel)
	{
		if (!writeIndent(file, indentLevel) || fputs("\"bone_mappings\": [\n", file) == EOF)
		{
			return false;
		}

		for (size_t index = 0; index < mappings.size(); ++index)
		{
			const RawBoneMapping& mapping = mappings[index];
			if (!writeIndent(file, indentLevel + 1) || fputs("{\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"ragdoll_bone\": ", file) == EOF || !writeInt(file, mapping.ragdollBone) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"anim_bone\": ", file) == EOF || !writeInt(file, mapping.animBone) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"transform\": ", file) == EOF || !writeTransform(file, mapping.transform, indentLevel + 2) || fputc('\n', file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 1) || fputc('}', file) == EOF)
			{
				return false;
			}
			if (index + 1 < mappings.size() && fputc(',', file) == EOF)
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

	bool writeRigidBodies(FILE* file, const std::vector<RawRigidBody>& bodies, int indentLevel)
	{
		if (!writeIndent(file, indentLevel) || fputs("\"rigid_bodies\": [\n", file) == EOF)
		{
			return false;
		}

		for (size_t index = 0; index < bodies.size(); ++index)
		{
			const RawRigidBody& body = bodies[index];
			if (!writeIndent(file, indentLevel + 1) || fputs("{\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"name\": ", file) == EOF || !writeEscapedString(file, body.name.c_str()) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"bone_index\": ", file) == EOF || !writeInt(file, body.boneIndex) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"shape_type\": ", file) == EOF || !writeEscapedString(file, body.shapeType.c_str()) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"radius\": ", file) == EOF || !writeFloat(file, body.radius) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"vertex_a\": ", file) == EOF || !writeVector(file, body.vertexA, 3) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"vertex_b\": ", file) == EOF || !writeVector(file, body.vertexB, 3) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"half_extents\": ", file) == EOF || !writeVector(file, body.halfExtents, 3) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"mass\": ", file) == EOF || !writeFloat(file, body.mass) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"friction\": ", file) == EOF || !writeFloat(file, body.friction) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"restitution\": ", file) == EOF || !writeFloat(file, body.restitution) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"motion_type\": ", file) == EOF || !writeEscapedString(file, body.motionType.c_str()) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"position\": ", file) == EOF || !writeVector(file, body.position, 3) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"rotation\": ", file) == EOF || !writeVector(file, body.rotation, 4) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"linear_damping\": ", file) == EOF || !writeFloat(file, body.linearDamping) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"angular_damping\": ", file) == EOF || !writeFloat(file, body.angularDamping) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"collision_filter_info\": ", file) == EOF || !writeInt(file, body.collisionFilterInfo) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"quality_type\": ", file) == EOF || !writeInt(file, body.qualityType) || fputc('\n', file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 1) || fputc('}', file) == EOF)
			{
				return false;
			}
			if (index + 1 < bodies.size() && fputc(',', file) == EOF)
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

	bool writeConstraints(FILE* file, const std::vector<RawConstraint>& constraints, int indentLevel)
	{
		if (!writeIndent(file, indentLevel) || fputs("\"constraints\": [\n", file) == EOF)
		{
			return false;
		}

		for (size_t index = 0; index < constraints.size(); ++index)
		{
			const RawConstraint& constraint = constraints[index];
			if (!writeIndent(file, indentLevel + 1) || fputs("{\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"name\": ", file) == EOF || !writeEscapedString(file, constraint.name.c_str()) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"body_a_index\": ", file) == EOF || !writeInt(file, constraint.bodyAIndex) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"body_b_index\": ", file) == EOF || !writeInt(file, constraint.bodyBIndex) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"constraint_type\": ", file) == EOF || !writeEscapedString(file, constraint.constraintType.c_str()) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"pivot_a\": ", file) == EOF || !writeVector(file, constraint.pivotA, 3) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"pivot_b\": ", file) == EOF || !writeVector(file, constraint.pivotB, 3) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"twist_axis_a\": ", file) == EOF || !writeVector(file, constraint.twistAxisA, 3) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"twist_axis_b\": ", file) == EOF || !writeVector(file, constraint.twistAxisB, 3) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"plane_axis_a\": ", file) == EOF || !writeVector(file, constraint.planeAxisA, 3) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"plane_axis_b\": ", file) == EOF || !writeVector(file, constraint.planeAxisB, 3) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"twist_min\": ", file) == EOF || !writeFloat(file, constraint.twistMin) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"twist_max\": ", file) == EOF || !writeFloat(file, constraint.twistMax) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"cone_angle\": ", file) == EOF || !writeFloat(file, constraint.coneAngle) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"plane_min\": ", file) == EOF || !writeFloat(file, constraint.planeMin) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"plane_max\": ", file) == EOF || !writeFloat(file, constraint.planeMax) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"hinge_min\": ", file) == EOF || !writeFloat(file, constraint.hingeMin) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"hinge_max\": ", file) == EOF || !writeFloat(file, constraint.hingeMax) || fputs(",\n", file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 2) || fputs("\"friction_torque\": ", file) == EOF || !writeFloat(file, constraint.frictionTorque) || fputc('\n', file) == EOF)
			{
				return false;
			}
			if (!writeIndent(file, indentLevel + 1) || fputc('}', file) == EOF)
			{
				return false;
			}
			if (index + 1 < constraints.size() && fputc(',', file) == EOF)
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

bool writeRagdollJson(
	const char* filename,
	const ragdoll_io::RawRagdollData& data)
{
	FILE* file = fopen(filename, "wb");
	if (file == 0)
	{
		fprintf(stderr, "Error: cannot open %s for writing\n", filename);
		return false;
	}

	bool ok =
		fputs("{\n", file) != EOF
		&& writeSkeleton(file, "animation_skeleton", data.animSkeleton, 1)
		&& fputs(",\n", file) != EOF
		&& writeSkeleton(file, "ragdoll_skeleton", data.ragdollSkeleton, 1)
		&& fputs(",\n", file) != EOF
		&& writeBoneMappings(file, data.boneMappings, 1)
		&& fputs(",\n", file) != EOF
		&& writeRigidBodies(file, data.rigidBodies, 1)
		&& fputs(",\n", file) != EOF
		&& writeConstraints(file, data.constraints, 1)
		&& fputs("\n}\n", file) != EOF;

	if (fclose(file) != 0)
	{
		ok = false;
	}

	if (!ok)
	{
		fprintf(stderr, "Error: failed to write ragdoll JSON %s\n", filename);
	}

	return ok;
}