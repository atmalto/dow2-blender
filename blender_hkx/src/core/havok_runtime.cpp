#include "havok_runtime.h"

#include <stdio.h>

#include <Common/Base/hkBase.h>
#include <Common/Base/System/hkBaseSystem.h>
#include <Common/Base/Memory/hkThreadMemory.h>
#include <Common/Base/Memory/Memory/Pool/hkPoolMemory.h>

namespace
{
	static void HK_CALL errorReport(const char* msg, void* userContext)
	{
		(void)userContext;
		fprintf(stderr, "Havok Error: %s\n", msg);
	}
}

HavokRuntime::HavokRuntime()
	: m_memoryManager(0),
	  m_threadMemory(0),
	  m_stackBuffer(0),
	  m_initialized(false)
{
}

HavokRuntime::~HavokRuntime()
{
	if (m_initialized)
	{
		hkThreadMemory::getInstance().setStackArea(0, 0);
		if (m_stackBuffer)
		{
			hkDeallocate(m_stackBuffer);
			m_stackBuffer = 0;
		}

		if (m_threadMemory)
		{
			m_threadMemory->removeReference();
			m_threadMemory = 0;
		}

		hkBaseSystem::quit();
		m_initialized = false;
	}
}

bool HavokRuntime::initialize()
{
	if (m_initialized)
	{
		return true;
	}

	m_memoryManager = new hkPoolMemory();
	m_threadMemory = new hkThreadMemory(m_memoryManager, 16);
	hkBaseSystem::init(m_memoryManager, m_threadMemory, errorReport);
	m_memoryManager->removeReference();
	m_memoryManager = 0;

	const int stackSize = 0x100000;
	m_stackBuffer = hkAllocate<char>(stackSize, HK_MEMORY_CLASS_BASE);
	hkThreadMemory::getInstance().setStackArea(m_stackBuffer, stackSize);
	m_initialized = true;
	return true;
}