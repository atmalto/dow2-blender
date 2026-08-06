#ifndef DOW2_HAVOK_IO_RUNTIME_H
#define DOW2_HAVOK_IO_RUNTIME_H

class HavokRuntime
{
public:
	HavokRuntime();
	~HavokRuntime();

	bool initialize();

private:
	HavokRuntime(const HavokRuntime&);
	HavokRuntime& operator=(const HavokRuntime&);

	class hkPoolMemory* m_memoryManager;
	class hkThreadMemory* m_threadMemory;
	char* m_stackBuffer;
	bool m_initialized;
};

#endif