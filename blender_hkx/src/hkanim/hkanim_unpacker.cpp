#include "hkanim_unpacker.h"

#include <fstream>
#include <sstream>

#include <windows.h>

namespace
{
	const char kRelicChunkySignature[16] = {
		'R', 'e', 'l', 'i', 'c', ' ', 'C', 'h',
		'u', 'n', 'k', 'y', '\r', '\n', 0x1A, 0x00
	};

	struct ChunkHeader
	{
		char kind[4];
		char type[4];
		unsigned int version;
		unsigned int size;
		unsigned int nameSize;
		unsigned int unk1;
		unsigned int unk2;
		std::string name;
		std::streamoff dataOffset;
		std::streamoff endOffset;
	};

	std::string joinPath(const std::string& left, const std::string& right)
	{
		if (left.empty())
		{
			return right;
		}

		const char last = left[left.size() - 1];
		if (last == '\\' || last == '/')
		{
			return left + right;
		}
		return left + "\\" + right;
	}

	std::string removeExtension(const std::string& name)
	{
		size_t dot = name.find_last_of('.');
		if (dot == std::string::npos)
		{
			return name;
		}
		return name.substr(0, dot);
	}

	std::string getBaseName(const std::string& path)
	{
		if (path.empty())
		{
			return std::string();
		}

		size_t slash = path.find_last_of("\\/");
		std::string name = (slash == std::string::npos) ? path : path.substr(slash + 1);
		while (!name.empty() && (name[name.size() - 1] == '\\' || name[name.size() - 1] == '/'))
		{
			name.erase(name.size() - 1);
		}
		if (name.empty() && slash != std::string::npos)
		{
			return getBaseName(path.substr(0, slash));
		}
		return name;
	}

	bool hasHkxExtension(const std::string& path)
	{
		const std::string base = getBaseName(path);
		if (base.size() < 4)
		{
			return false;
		}
		const size_t dot = base.find_last_of('.');
		if (dot == std::string::npos)
		{
			return false;
		}
		std::string ext = base.substr(dot);
		for (size_t i = 0; i < ext.size(); ++i)
		{
			char& ch = ext[i];
			if (ch >= 'A' && ch <= 'Z')
			{
				ch = static_cast<char>(ch - 'A' + 'a');
			}
		}
		return ext == ".hkx";
	}

	bool readUint32(std::ifstream& input, unsigned int& value)
	{
		input.read(reinterpret_cast<char*>(&value), sizeof(value));
		return !!input;
	}

	bool readExact(std::ifstream& input, char* buffer, std::streamsize size)
	{
		if (size <= 0)
		{
			return true;
		}
		input.read(buffer, size);
		return !!input;
	}

	bool readChunkHeader(std::ifstream& input, ChunkHeader& outHeader, std::string& errorMessage)
	{
		if (!readExact(input, outHeader.kind, 4) ||
			!readExact(input, outHeader.type, 4) ||
			!readUint32(input, outHeader.version) ||
			!readUint32(input, outHeader.size) ||
			!readUint32(input, outHeader.nameSize) ||
			!readUint32(input, outHeader.unk1) ||
			!readUint32(input, outHeader.unk2))
		{
			errorMessage = "Failed to read chunk header";
			return false;
		}

		outHeader.name.clear();
		if (outHeader.nameSize > 0)
		{
			std::vector<char> nameBytes(outHeader.nameSize);
			if (!readExact(input, &nameBytes[0], static_cast<std::streamsize>(nameBytes.size())))
			{
				errorMessage = "Failed to read chunk name";
				return false;
			}

			if (!nameBytes.empty() && nameBytes[nameBytes.size() - 1] == '\0')
			{
				nameBytes.resize(nameBytes.size() - 1);
			}
			outHeader.name.assign(nameBytes.begin(), nameBytes.end());
		}

		outHeader.dataOffset = input.tellg();
		outHeader.endOffset = outHeader.dataOffset + static_cast<std::streamoff>(outHeader.size);
		return true;
	}

	bool ensureDirectoryExists(const std::string& directory, std::string& errorMessage)
	{
		if (directory.empty())
		{
			return true;
		}

		DWORD attributes = GetFileAttributesA(directory.c_str());
		if (attributes != INVALID_FILE_ATTRIBUTES)
		{
			if ((attributes & FILE_ATTRIBUTE_DIRECTORY) != 0)
			{
				return true;
			}
			errorMessage = std::string("Path exists but is not a directory: ") + directory;
			return false;
		}

		size_t slash = directory.find_last_of("\\/");
		if (slash != std::string::npos)
		{
			const std::string parent = directory.substr(0, slash);
			if (!parent.empty() && !ensureDirectoryExists(parent, errorMessage))
			{
				return false;
			}
		}

		if (CreateDirectoryA(directory.c_str(), NULL) != 0 || GetLastError() == ERROR_ALREADY_EXISTS)
		{
			return true;
		}

		errorMessage = std::string("Failed to create directory: ") + directory;
		return false;
	}

	bool ensureParentDirectory(const std::string& filePath, std::string& errorMessage)
	{
		size_t slash = filePath.find_last_of("\\/");
		if (slash == std::string::npos)
		{
			return true;
		}
		return ensureDirectoryExists(filePath.substr(0, slash), errorMessage);
	}

	bool writeFileBytes(const std::string& path, const std::vector<char>& bytes, std::string& errorMessage)
	{
		if (!ensureParentDirectory(path, errorMessage))
		{
			return false;
		}

		std::ofstream output(path.c_str(), std::ios::binary);
		if (!output)
		{
			errorMessage = std::string("Failed to create HKX file: ") + path;
			return false;
		}

		if (!bytes.empty())
		{
			output.write(&bytes[0], static_cast<std::streamsize>(bytes.size()));
		}

		if (!output.good())
		{
			errorMessage = std::string("Failed to write HKX file: ") + path;
			return false;
		}

		return true;
	}

	std::string normalizeEntryPath(const HkAnimSet& set, const HkAnimEntry& entry)
	{
		std::string relativePath = entry.relativeName;
		if (relativePath.empty())
		{
			relativePath = set.name.empty() ? std::string("animation") : set.name;
		}

		if (!set.name.empty())
		{
			const std::string prefix = set.name + "\\";
			const std::string altPrefix = set.name + "/";
			if (relativePath.compare(0, prefix.size(), prefix) != 0 &&
				relativePath.compare(0, altPrefix.size(), altPrefix) != 0 &&
				relativePath != set.name)
			{
				relativePath = joinPath(set.name, relativePath);
			}
		}

		for (size_t i = 0; i < relativePath.size(); ++i)
		{
			if (relativePath[i] == '/')
			{
				relativePath[i] = '\\';
			}
		}

		if (!hasHkxExtension(relativePath))
		{
			relativePath += ".hkx";
		}

		return relativePath;
	}

	bool readSetPayload(std::ifstream& input, const ChunkHeader& setHeader, HkAnimSet& outSet, std::string& errorMessage)
	{
		unsigned int entryCount = 0;
		if (!readUint32(input, entryCount))
		{
			errorMessage = std::string("Failed to read entry count for set: ") + outSet.name;
			return false;
		}

		outSet.entries.clear();
		outSet.entries.resize(entryCount);
		for (unsigned int index = 0; index < entryCount; ++index)
		{
			unsigned int nameSize = 0;
			if (!readUint32(input, nameSize))
			{
				errorMessage = std::string("Failed to read animation name length for set: ") + outSet.name;
				return false;
			}

			if (nameSize > 0)
			{
				std::vector<char> nameBytes(nameSize);
				if (!readExact(input, &nameBytes[0], static_cast<std::streamsize>(nameBytes.size())))
				{
					errorMessage = std::string("Failed to read animation name for set: ") + outSet.name;
					return false;
				}
				outSet.entries[index].relativeName.assign(nameBytes.begin(), nameBytes.end());
			}
		}

		for (unsigned int index = 0; index < entryCount; ++index)
		{
			unsigned int blobSize = 0;
			if (!readUint32(input, blobSize))
			{
				errorMessage = std::string("Failed to read animation blob size for set: ") + outSet.name;
				return false;
			}

			HkAnimEntry& entry = outSet.entries[index];
			entry.empty = (blobSize == 0);
			entry.bytes.clear();
			if (blobSize > 0)
			{
				entry.bytes.resize(blobSize);
				if (!readExact(input, &entry.bytes[0], static_cast<std::streamsize>(entry.bytes.size())))
				{
					errorMessage = std::string("Failed to read animation blob for set: ") + outSet.name;
					return false;
				}
			}
		}

		const std::streamoff currentOffset = static_cast<std::streamoff>(input.tellg());
		if (currentOffset != setHeader.endOffset)
		{
			input.seekg(setHeader.endOffset);
		}

		return true;
	}
}

bool readHkAnimContainer(
	const std::string& inputPath,
	std::vector<HkAnimSet>& outSets,
	std::string& errorMessage)
{
	outSets.clear();
	errorMessage.clear();

	std::ifstream input(inputPath.c_str(), std::ios::binary);
	if (!input)
	{
		errorMessage = std::string("Failed to open HKANIM file: ") + inputPath;
		return false;
	}

	char signature[sizeof(kRelicChunkySignature)];
	if (!readExact(input, signature, sizeof(signature)))
	{
		errorMessage = std::string("Failed to read HKANIM signature: ") + inputPath;
		return false;
	}
	for (size_t i = 0; i < sizeof(signature); ++i)
	{
		if (signature[i] != kRelicChunkySignature[i])
		{
			errorMessage = std::string("File is not a supported Relic Chunky HKANIM container: ") + inputPath;
			return false;
		}
	}

	unsigned int headerValues[5];
	for (size_t i = 0; i < 5; ++i)
	{
		if (!readUint32(input, headerValues[i]))
		{
			errorMessage = std::string("Failed to read HKANIM header: ") + inputPath;
			return false;
		}
	}

	ChunkHeader rootHeader;
	if (!readChunkHeader(input, rootHeader, errorMessage))
	{
		return false;
	}

	if (memcmp(rootHeader.kind, "FOLD", 4) != 0 || memcmp(rootHeader.type, "HAAS", 4) != 0)
	{
		errorMessage = std::string("Unsupported HKANIM root chunk in: ") + inputPath;
		return false;
	}

	while (input && input.tellg() < rootHeader.endOffset)
	{
		ChunkHeader setHeader;
		if (!readChunkHeader(input, setHeader, errorMessage))
		{
			return false;
		}

		if (memcmp(setHeader.kind, "DATA", 4) != 0 || memcmp(setHeader.type, "HAWS", 4) != 0)
		{
			std::ostringstream stream;
			stream << "Unsupported HKANIM child chunk '" << std::string(setHeader.type, 4) << "' in: " << inputPath;
			errorMessage = stream.str();
			return false;
		}

		HkAnimSet set;
		set.name = setHeader.name.empty() ? removeExtension(getBaseName(inputPath)) : setHeader.name;
		if (!readSetPayload(input, setHeader, set, errorMessage))
		{
			return false;
		}
		outSets.push_back(set);
	}

	if (outSets.empty())
	{
		errorMessage = std::string("No animation sets were found in HKANIM file: ") + inputPath;
		return false;
	}

	return true;
}

bool unpackHkAnimToDirectory(
	const std::string& inputPath,
	const std::string& outputDirectory,
	std::string& errorMessage)
{
	std::vector<HkAnimSet> sets;
	if (!readHkAnimContainer(inputPath, sets, errorMessage))
	{
		return false;
	}

	if (!ensureDirectoryExists(outputDirectory, errorMessage))
	{
		return false;
	}

	for (size_t setIndex = 0; setIndex < sets.size(); ++setIndex)
	{
		const HkAnimSet& set = sets[setIndex];
		for (size_t entryIndex = 0; entryIndex < set.entries.size(); ++entryIndex)
		{
			const HkAnimEntry& entry = set.entries[entryIndex];
			if (entry.empty)
			{
				continue;
			}

			const std::string outputPath = joinPath(outputDirectory, normalizeEntryPath(set, entry));
			if (!writeFileBytes(outputPath, entry.bytes, errorMessage))
			{
				return false;
			}
		}
	}

	return true;
}