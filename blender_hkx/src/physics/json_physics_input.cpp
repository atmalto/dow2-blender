#include "json_physics_input.h"

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
		float temp = 0.0f;
		const char* end = parseNumber(p, temp);
		out = (int)temp;
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

	const char* parseBool(const char* p, bool& out)
	{
		p = skipWS(p);
		if (strncmp(p, "true", 4) == 0)
		{
			out = true;
			return p + 4;
		}
		if (strncmp(p, "false", 5) == 0)
		{
			out = false;
			return p + 5;
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

	const char* findMatchingBrace(const char* p, char open, char close)
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
			++p;
		}
		return p;
	}

	const char* parseVertices(const char* p, std::vector<RawVertex>& vertices)
	{
		p = skipWS(p);
		if (*p != '[')
		{
			return p;
		}

		++p;
		while (*p && *p != ']')
		{
			p = skipWS(p);
			if (*p == '[')
			{
				++p;
				RawVertex vertex;
				p = parseNumber(p, vertex.x);
				p = skipWS(p);
				if (*p == ',')
				{
					++p;
				}
				p = parseNumber(p, vertex.y);
				p = skipWS(p);
				if (*p == ',')
				{
					++p;
				}
				p = parseNumber(p, vertex.z);
				p = skipWS(p);
				if (*p == ']')
				{
					++p;
				}
				vertices.push_back(vertex);
			}
			p = skipWS(p);
			if (*p == ',')
			{
				++p;
			}
		}

		if (*p == ']')
		{
			++p;
		}
		return p;
	}

	const char* parseRigidBody(const char* p, RawRigidBody& body)
	{
		p = skipWS(p);
		if (*p != '{')
		{
			return p;
		}

		const char* objEnd = findMatchingBrace(p, '{', '}');

		const char* namePtr = findKey(p, "name");
		if (namePtr && namePtr < objEnd)
		{
			parseString(namePtr, body.name);
		}

		const char* vertsPtr = findKey(p, "vertices");
		if (vertsPtr && vertsPtr < objEnd)
		{
			parseVertices(vertsPtr, body.vertices);
		}

		const char* posPtr = findKey(p, "position");
		if (posPtr && posPtr < objEnd)
		{
			parseFloatArray(posPtr, body.position, 3);
		}

		const char* rotPtr = findKey(p, "rotation");
		if (rotPtr && rotPtr < objEnd)
		{
			parseFloatArray(rotPtr, body.rotation, 4);
		}

		const char* fricPtr = findKey(p, "friction");
		if (fricPtr && fricPtr < objEnd)
		{
			parseNumber(fricPtr, body.friction);
		}

		const char* restPtr = findKey(p, "restitution");
		if (restPtr && restPtr < objEnd)
		{
			parseNumber(restPtr, body.restitution);
		}

		const char* motionPtr = findKey(p, "motion_type");
		if (motionPtr && motionPtr < objEnd)
		{
			parseString(motionPtr, body.motionType);
		}

		const char* qualityPtr = findKey(p, "quality_type");
		if (qualityPtr && qualityPtr < objEnd)
		{
			parseInt(qualityPtr, body.qualityType);
		}

		const char* penetrationPtr = findKey(p, "allowed_penetration_depth");
		if (penetrationPtr && penetrationPtr < objEnd)
		{
			parseNumber(penetrationPtr, body.allowedPenetrationDepth);
		}

		const char* callbackPtr = findKey(p, "process_contact_callback_delay");
		if (callbackPtr && callbackPtr < objEnd)
		{
			parseInt(callbackPtr, body.processContactCallbackDelay);
		}

		const char* deactivationClassPtr = findKey(p, "deactivation_class");
		if (deactivationClassPtr && deactivationClassPtr < objEnd)
		{
			parseInt(deactivationClassPtr, body.deactivationClass);
		}

		const char* deactivationCounterPtr = findKey(p, "deactivation_integrate_counter");
		if (deactivationCounterPtr && deactivationCounterPtr < objEnd)
		{
			parseInt(deactivationCounterPtr, body.deactivationIntegrateCounter);
		}

		const char* linearDampingPtr = findKey(p, "linear_damping");
		if (linearDampingPtr && linearDampingPtr < objEnd)
		{
			parseNumber(linearDampingPtr, body.linearDamping);
		}

		const char* angularDampingPtr = findKey(p, "angular_damping");
		if (angularDampingPtr && angularDampingPtr < objEnd)
		{
			parseNumber(angularDampingPtr, body.angularDamping);
		}

		const char* maxLinearVelocityPtr = findKey(p, "max_linear_velocity");
		if (maxLinearVelocityPtr && maxLinearVelocityPtr < objEnd)
		{
			parseNumber(maxLinearVelocityPtr, body.maxLinearVelocity);
		}

		const char* maxAngularVelocityPtr = findKey(p, "max_angular_velocity");
		if (maxAngularVelocityPtr && maxAngularVelocityPtr < objEnd)
		{
			parseNumber(maxAngularVelocityPtr, body.maxAngularVelocity);
		}

		const char* collisionFilterPtr = findKey(p, "collision_filter_info");
		if (collisionFilterPtr && collisionFilterPtr < objEnd)
		{
			int temp = 0;
			parseInt(collisionFilterPtr, temp);
			body.collisionFilterInfo = (unsigned int)temp;
		}

		const char* eventFilterPtr = findKey(p, "event_filter");
		if (eventFilterPtr && eventFilterPtr < objEnd)
		{
			parseInt(eventFilterPtr, body.eventFilter);
		}

		const char* userFilterPtr = findKey(p, "user_filter");
		if (userFilterPtr && userFilterPtr < objEnd)
		{
			parseInt(userFilterPtr, body.userFilter);
		}

		const char* massPtr = findKey(p, "mass");
		if (massPtr && massPtr < objEnd)
		{
			parseNumber(massPtr, body.mass);
		}

		const char* centerModePtr = findKey(p, "center_of_mass_mode");
		if (centerModePtr && centerModePtr < objEnd)
		{
			parseString(centerModePtr, body.centerOfMassMode);
		}

		const char* centerOverridePtr = findKey(p, "center_of_mass_override");
		if (centerOverridePtr && centerOverridePtr < objEnd)
		{
			parseFloatArray(centerOverridePtr, body.centerOfMassOverride, 3);
		}

		const char* shapeRadiusPtr = findKey(p, "shape_radius");
		if (shapeRadiusPtr && shapeRadiusPtr < objEnd)
		{
			parseNumber(shapeRadiusPtr, body.shapeRadius);
		}

		const char* responsePtr = findKey(p, "response_type");
		if (responsePtr && responsePtr < objEnd)
		{
			parseString(responsePtr, body.responseType);
		}

		const char* deactivatorPtr = findKey(p, "deactivator_present");
		if (deactivatorPtr && deactivatorPtr < objEnd)
		{
			parseBool(deactivatorPtr, body.deactivatorPresent);
		}

		return objEnd;
	}
}

bool parsePhysicsJson(const char* filename, std::vector<RawPhysicsSystem>& systems)
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

	const char* p = findKey(json, "physics_systems");
	if (!p)
	{
		fprintf(stderr, "Error: No 'physics_systems' array found in JSON\n");
		return false;
	}

	p = skipWS(p);
	if (*p != '[')
	{
		fprintf(stderr, "Error: 'physics_systems' should be an array\n");
		return false;
	}
	++p;

	while (*p && *p != ']')
	{
		p = skipWS(p);
		if (*p == '{')
		{
			RawPhysicsSystem system;
			const char* sysEnd = findMatchingBrace(p, '{', '}');

			const char* namePtr = findKey(p, "name");
			if (namePtr && namePtr < sysEnd)
			{
				parseString(namePtr, system.name);
			}
			else
			{
				system.name = "Default Physics System";
			}

			printf("  Parsing physics system: %s\n", system.name.c_str());

			const char* bodiesPtr = findKey(p, "rigid_bodies");
			if (bodiesPtr && bodiesPtr < sysEnd)
			{
				bodiesPtr = skipWS(bodiesPtr);
				if (*bodiesPtr == '[')
				{
					++bodiesPtr;
					while (*bodiesPtr && *bodiesPtr != ']')
					{
						bodiesPtr = skipWS(bodiesPtr);
						if (*bodiesPtr == '{')
						{
							RawRigidBody body;
							bodiesPtr = parseRigidBody(bodiesPtr, body);
							if (!body.vertices.empty())
							{
								system.rigidBodies.push_back(body);
								printf(
									"    Parsed rigid body: %s (%d vertices)\n",
									body.name.c_str(),
									(int)body.vertices.size());
							}
						}
						bodiesPtr = skipWS(bodiesPtr);
						if (*bodiesPtr == ',')
						{
							++bodiesPtr;
						}
					}
				}
			}

			if (!system.rigidBodies.empty())
			{
				systems.push_back(system);
				printf("  Physics system has %d rigid bodies\n", (int)system.rigidBodies.size());
			}

			p = sysEnd;
		}

		p = skipWS(p);
		if (*p == ',')
		{
			++p;
		}
	}

	int totalBodies = 0;
	for (size_t i = 0; i < systems.size(); ++i)
	{
		totalBodies += (int)systems[i].rigidBodies.size();
	}

	printf(
		"Parsed %d physics systems with %d total rigid bodies from JSON\n",
		(int)systems.size(),
		totalBodies);

	return !systems.empty();
}