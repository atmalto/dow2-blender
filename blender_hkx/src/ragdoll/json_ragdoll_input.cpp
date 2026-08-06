#include "json_ragdoll_input.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <fstream>
#include <sstream>

using namespace ragdoll_io;

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
		char* end = 0;
		p = skipWS(p);
		out = static_cast<float>(strtod(p, &end));
		return end;
	}

	const char* parseInt(const char* p, int& out)
	{
		char* end = 0;
		p = skipWS(p);
		out = static_cast<int>(strtol(p, &end, 10));
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
				if (*p == 'n')
				{
					out += '\n';
				}
				else if (*p == 't')
				{
					out += '\t';
				}
				else
				{
					out += *p;
				}
				++p;
			}
			else
			{
				out += *p++;
			}
		}

		if (*p == '"')
		{
			++p;
		}
		return p;
	}

	const char* findKey(const char* p, const char* key)
	{
		const std::string keyString = std::string("\"") + key + "\"";
		const char* found = strstr(p, keyString.c_str());
		if (!found)
		{
			return 0;
		}

		found += keyString.length();
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

	const char* findClosingBracket(const char* p, char open, char close)
	{
		int depth = 1;
		++p;
		while (*p && depth > 0)
		{
			if (*p == open)
			{
				++depth;
			}
			else if (*p == close)
			{
				--depth;
			}
			else if (*p == '"')
			{
				++p;
				while (*p && *p != '"')
				{
					if (*p == '\\' && *(p + 1))
					{
						++p;
					}
					++p;
				}
			}

			if (depth > 0)
			{
				++p;
			}
		}
		return p;
	}

	const char* parseTransformRaw(const char* p, RawTransform& transform)
	{
		p = skipWS(p);
		if (*p != '{')
		{
			return p;
		}

		const char* objectEnd = findClosingBracket(p, '{', '}');
		transform.pos[0] = transform.pos[1] = transform.pos[2] = 0.0f;
		transform.rot[0] = transform.rot[1] = transform.rot[2] = 0.0f;
		transform.rot[3] = 1.0f;
		transform.scale[0] = transform.scale[1] = transform.scale[2] = 1.0f;

		const char* value = findKey(p, "pos");
		if (value && value < objectEnd)
		{
			parseFloatArray(value, transform.pos, 3);
		}

		value = findKey(p, "rot");
		if (value && value < objectEnd)
		{
			parseFloatArray(value, transform.rot, 4);
		}

		value = findKey(p, "scale");
		if (value && value < objectEnd)
		{
			parseFloatArray(value, transform.scale, 3);
		}

		return objectEnd + 1;
	}

	bool parseSkeleton(const char* json, const char* keyName, RawSkeleton& skeleton)
	{
		const char* object = findKey(json, keyName);
		if (!object || *object != '{')
		{
			fprintf(stderr, "Error: cannot find '%s' object\n", keyName);
			return false;
		}

		const char* objectEnd = findClosingBracket(object, '{', '}');
		const char* value = findKey(object, "name");
		if (value && value < objectEnd)
		{
			parseString(value, skeleton.name);
		}

		value = findKey(object, "bones");
		if (value && *value == '[' && value < objectEnd)
		{
			++value;
			while (*value && *value != ']')
			{
				value = skipWS(value);
				if (*value == '"')
				{
					std::string boneName;
					value = parseString(value, boneName);
					skeleton.bones.push_back(boneName);
				}
				value = skipWS(value);
				if (*value == ',')
				{
					++value;
				}
			}
		}

		const int numBones = static_cast<int>(skeleton.bones.size());
		value = findKey(object, "parent_indices");
		if (value && *value == '[' && value < objectEnd)
		{
			++value;
			for (int index = 0; index < numBones && *value && *value != ']'; ++index)
			{
				int parentIndex = -1;
				value = parseInt(value, parentIndex);
				skeleton.parentIndices.push_back(parentIndex);
				value = skipWS(value);
				if (*value == ',')
				{
					++value;
				}
			}
		}

		while (static_cast<int>(skeleton.parentIndices.size()) < numBones)
		{
			skeleton.parentIndices.push_back(-1);
		}

		value = findKey(object, "reference_pose");
		if (value && *value == '[' && value < objectEnd)
		{
			++value;
			for (int index = 0; index < numBones && *value && *value != ']'; )
			{
				value = skipWS(value);
				if (*value == '{')
				{
					RawTransform transform;
					value = parseTransformRaw(value, transform);
					skeleton.referencePose.push_back(transform);
					++index;
				}
				else if (*value == ',')
				{
					++value;
				}
				else
				{
					++value;
				}
			}
		}

		while (static_cast<int>(skeleton.referencePose.size()) < numBones)
		{
			RawTransform transform;
			transform.pos[0] = transform.pos[1] = transform.pos[2] = 0.0f;
			transform.rot[0] = transform.rot[1] = transform.rot[2] = 0.0f;
			transform.rot[3] = 1.0f;
			transform.scale[0] = transform.scale[1] = transform.scale[2] = 1.0f;
			skeleton.referencePose.push_back(transform);
		}

		printf("  %s: %d bones\n", keyName, numBones);
		return true;
	}

	bool parseRigidBodies(const char* json, std::vector<RawRigidBody>& bodies)
	{
		const char* value = findKey(json, "rigid_bodies");
		if (!value || *value != '[')
		{
			fprintf(stderr, "Error: cannot find 'rigid_bodies' array\n");
			return false;
		}

		const char* arrayEnd = findClosingBracket(value, '[', ']');
		++value;
		while (value < arrayEnd)
		{
			value = skipWS(value);
			if (*value == '{')
			{
				const char* objectEnd = findClosingBracket(value, '{', '}');
				RawRigidBody body;
				body.boneIndex = 0;
				body.shapeType = "capsule";
				body.radius = 0.1f;
				body.vertexA[0] = body.vertexA[1] = body.vertexA[2] = 0.0f;
				body.vertexB[0] = 0.1f;
				body.vertexB[1] = body.vertexB[2] = 0.0f;
				body.halfExtents[0] = body.halfExtents[1] = body.halfExtents[2] = 0.1f;
				body.mass = 50.0f;
				body.friction = 1.0f;
				body.restitution = 0.0f;
				body.motionType = "MOTION_BOX_INERTIA";
				body.position[0] = body.position[1] = body.position[2] = body.position[3] = 0.0f;
				body.rotation[0] = body.rotation[1] = body.rotation[2] = 0.0f;
				body.rotation[3] = 1.0f;
				body.linearDamping = 1.0f;
				body.angularDamping = 3.0f;
				body.collisionFilterInfo = 65984;
				body.qualityType = 4;

				const char* field = findKey(value, "name");
				if (field && field < objectEnd) parseString(field, body.name);
				field = findKey(value, "bone_index");
				if (field && field < objectEnd) parseInt(field, body.boneIndex);
				field = findKey(value, "shape_type");
				if (field && field < objectEnd) parseString(field, body.shapeType);
				field = findKey(value, "radius");
				if (field && field < objectEnd) parseNumber(field, body.radius);
				field = findKey(value, "vertex_a");
				if (field && field < objectEnd) parseFloatArray(field, body.vertexA, 3);
				field = findKey(value, "vertex_b");
				if (field && field < objectEnd) parseFloatArray(field, body.vertexB, 3);
				field = findKey(value, "half_extents");
				if (field && field < objectEnd) parseFloatArray(field, body.halfExtents, 3);
				field = findKey(value, "mass");
				if (field && field < objectEnd) parseNumber(field, body.mass);
				field = findKey(value, "friction");
				if (field && field < objectEnd) parseNumber(field, body.friction);
				field = findKey(value, "restitution");
				if (field && field < objectEnd) parseNumber(field, body.restitution);
				field = findKey(value, "motion_type");
				if (field && field < objectEnd) parseString(field, body.motionType);
				field = findKey(value, "position");
				if (field && field < objectEnd) parseFloatArray(field, body.position, 4);
				field = findKey(value, "rotation");
				if (field && field < objectEnd) parseFloatArray(field, body.rotation, 4);
				field = findKey(value, "linear_damping");
				if (field && field < objectEnd) parseNumber(field, body.linearDamping);
				field = findKey(value, "angular_damping");
				if (field && field < objectEnd) parseNumber(field, body.angularDamping);
				field = findKey(value, "collision_filter_info");
				if (field && field < objectEnd) parseInt(field, body.collisionFilterInfo);
				field = findKey(value, "quality_type");
				if (field && field < objectEnd) parseInt(field, body.qualityType);

				bodies.push_back(body);
				value = objectEnd + 1;
			}
			else if (*value == ',')
			{
				++value;
			}
			else
			{
				++value;
			}
		}

		printf("  rigid_bodies: %d bodies\n", static_cast<int>(bodies.size()));
		return true;
	}

	bool parseConstraints(const char* json, std::vector<RawConstraint>& constraints)
	{
		const char* value = findKey(json, "constraints");
		if (!value || *value != '[')
		{
			fprintf(stderr, "Error: cannot find 'constraints' array\n");
			return false;
		}

		const char* arrayEnd = findClosingBracket(value, '[', ']');
		++value;
		while (value < arrayEnd)
		{
			value = skipWS(value);
			if (*value == '{')
			{
				const char* objectEnd = findClosingBracket(value, '{', '}');
				RawConstraint constraint;
				constraint.constraintType = "ragdoll";
				constraint.bodyAIndex = 0;
				constraint.bodyBIndex = 1;
				constraint.pivotA[0] = constraint.pivotA[1] = constraint.pivotA[2] = 0.0f;
				constraint.pivotB[0] = constraint.pivotB[1] = constraint.pivotB[2] = 0.0f;
				constraint.twistAxisA[0] = 1.0f;
				constraint.twistAxisA[1] = constraint.twistAxisA[2] = 0.0f;
				constraint.twistAxisB[0] = 1.0f;
				constraint.twistAxisB[1] = constraint.twistAxisB[2] = 0.0f;
				constraint.planeAxisA[0] = 0.0f;
				constraint.planeAxisA[1] = 1.0f;
				constraint.planeAxisA[2] = 0.0f;
				constraint.planeAxisB[0] = 0.0f;
				constraint.planeAxisB[1] = 1.0f;
				constraint.planeAxisB[2] = 0.0f;
				constraint.twistMin = -0.5f;
				constraint.twistMax = 0.5f;
				constraint.coneAngle = 0.785f;
				constraint.planeMin = -0.5f;
				constraint.planeMax = 0.5f;
				constraint.hingeMin = -3.14159265f;
				constraint.hingeMax = 3.14159265f;
				constraint.frictionTorque = 0.0f;

				const char* field = findKey(value, "name");
				if (field && field < objectEnd) parseString(field, constraint.name);
				field = findKey(value, "constraint_type");
				if (field && field < objectEnd) parseString(field, constraint.constraintType);
				field = findKey(value, "body_a_index");
				if (field && field < objectEnd) parseInt(field, constraint.bodyAIndex);
				field = findKey(value, "body_b_index");
				if (field && field < objectEnd) parseInt(field, constraint.bodyBIndex);
				field = findKey(value, "pivot_a");
				if (field && field < objectEnd) parseFloatArray(field, constraint.pivotA, 3);
				field = findKey(value, "pivot_b");
				if (field && field < objectEnd) parseFloatArray(field, constraint.pivotB, 3);
				field = findKey(value, "twist_axis_a");
				if (field && field < objectEnd) parseFloatArray(field, constraint.twistAxisA, 3);
				field = findKey(value, "twist_axis_b");
				if (field && field < objectEnd) parseFloatArray(field, constraint.twistAxisB, 3);
				field = findKey(value, "plane_axis_a");
				if (field && field < objectEnd) parseFloatArray(field, constraint.planeAxisA, 3);
				field = findKey(value, "plane_axis_b");
				if (field && field < objectEnd) parseFloatArray(field, constraint.planeAxisB, 3);
				field = findKey(value, "twist_min");
				if (field && field < objectEnd) parseNumber(field, constraint.twistMin);
				field = findKey(value, "twist_max");
				if (field && field < objectEnd) parseNumber(field, constraint.twistMax);
				field = findKey(value, "cone_angle");
				if (field && field < objectEnd) parseNumber(field, constraint.coneAngle);
				field = findKey(value, "plane_min");
				if (field && field < objectEnd) parseNumber(field, constraint.planeMin);
				field = findKey(value, "plane_max");
				if (field && field < objectEnd) parseNumber(field, constraint.planeMax);
				field = findKey(value, "hinge_min");
				if (field && field < objectEnd) parseNumber(field, constraint.hingeMin);
				field = findKey(value, "hinge_max");
				if (field && field < objectEnd) parseNumber(field, constraint.hingeMax);
				field = findKey(value, "friction_torque");
				if (field && field < objectEnd) parseNumber(field, constraint.frictionTorque);

				constraints.push_back(constraint);
				value = objectEnd + 1;
			}
			else if (*value == ',')
			{
				++value;
			}
			else
			{
				++value;
			}
		}

		printf("  constraints: %d constraints\n", static_cast<int>(constraints.size()));
		return true;
	}

	bool parseBoneMappings(const char* json, std::vector<RawBoneMapping>& mappings)
	{
		const char* value = findKey(json, "bone_mappings");
		if (!value || *value != '[')
		{
			fprintf(stderr, "Warning: cannot find 'bone_mappings', continuing without explicit mappings\n");
			return true;
		}

		const char* arrayEnd = findClosingBracket(value, '[', ']');
		++value;
		while (value < arrayEnd)
		{
			value = skipWS(value);
			if (*value == '{')
			{
				const char* objectEnd = findClosingBracket(value, '{', '}');
				RawBoneMapping mapping;
				mapping.ragdollBone = 0;
				mapping.animBone = 0;
				mapping.transform.pos[0] = mapping.transform.pos[1] = mapping.transform.pos[2] = 0.0f;
				mapping.transform.rot[0] = mapping.transform.rot[1] = mapping.transform.rot[2] = 0.0f;
				mapping.transform.rot[3] = 1.0f;
				mapping.transform.scale[0] = mapping.transform.scale[1] = mapping.transform.scale[2] = 1.0f;

				const char* field = findKey(value, "ragdoll_bone");
				if (field && field < objectEnd) parseInt(field, mapping.ragdollBone);
				field = findKey(value, "anim_bone");
				if (field && field < objectEnd) parseInt(field, mapping.animBone);
				field = findKey(value, "transform");
				if (field && field < objectEnd && *field == '{') parseTransformRaw(field, mapping.transform);

				mappings.push_back(mapping);
				value = objectEnd + 1;
			}
			else if (*value == ',')
			{
				++value;
			}
			else
			{
				++value;
			}
		}

		printf("  bone_mappings: %d mappings\n", static_cast<int>(mappings.size()));
		return true;
	}
}

namespace ragdoll_io
{
	bool parseJSON(const char* filename, RawRagdollData& data)
{
	printf("Reading JSON file: %s\n", filename);
	std::ifstream file(filename);
	if (!file.is_open())
	{
		fprintf(stderr, "Error: cannot open %s\n", filename);
		return false;
	}

	std::stringstream buffer;
	buffer << file.rdbuf();
	const std::string content = buffer.str();
	const char* json = content.c_str();
	printf("  Read %d bytes\n", static_cast<int>(content.length()));

	return parseSkeleton(json, "animation_skeleton", data.animSkeleton)
		&& parseSkeleton(json, "ragdoll_skeleton", data.ragdollSkeleton)
		&& parseRigidBodies(json, data.rigidBodies)
		&& parseConstraints(json, data.constraints)
		&& parseBoneMappings(json, data.boneMappings);
}
	}