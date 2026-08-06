#include "hkanim_packer.h"

#include <algorithm>
#include <fstream>
#include <set>
#include <sstream>

#include <windows.h>

namespace
{
	const char kRelicChunkySignature[16] = {
		'R', 'e', 'l', 'i', 'c', ' ', 'C', 'h',
		'u', 'n', 'k', 'y', '\r', '\n', 0x1A, 0x00
	};

	struct ChunkWriteState
	{
		std::streamoff headerOffset;
		std::streamoff dataOffset;
	};

	std::string toLowerAscii(const std::string& value)
	{
		std::string result = value;
		for (size_t i = 0; i < result.size(); ++i)
		{
			char& ch = result[i];
			if (ch >= 'A' && ch <= 'Z')
			{
				ch = static_cast<char>(ch - 'A' + 'a');
			}
		}
		return result;
	}

	bool compareCaseInsensitive(const std::string& left, const std::string& right)
	{
		return toLowerAscii(left) < toLowerAscii(right);
	}

	bool compareEntriesByName(const HkAnimEntry& left, const HkAnimEntry& right)
	{
		return compareCaseInsensitive(left.relativeName, right.relativeName);
	}

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
			std::string trimmed = path.substr(0, slash);
			return getBaseName(trimmed);
		}
		return name;
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

	bool hasExtensionInsensitive(const std::string& name, const std::string& extension)
	{
		const std::string lowerName = toLowerAscii(name);
		const std::string lowerExtension = toLowerAscii(extension);
		if (lowerName.size() < lowerExtension.size())
		{
			return false;
		}
		return lowerName.compare(lowerName.size() - lowerExtension.size(), lowerExtension.size(), lowerExtension) == 0;
	}

	void listDirectoryEntries(
		const std::string& directory,
		bool wantDirectories,
		const std::string& extension,
		std::vector<std::string>& outEntries,
		std::string& errorMessage)
	{
		outEntries.clear();

		WIN32_FIND_DATAA findData;
		const std::string searchPattern = joinPath(directory, "*");
		HANDLE handle = FindFirstFileA(searchPattern.c_str(), &findData);
		if (handle == INVALID_HANDLE_VALUE)
		{
			DWORD error = GetLastError();
			if (error == ERROR_FILE_NOT_FOUND || error == ERROR_PATH_NOT_FOUND)
			{
				return;
			}

			std::ostringstream stream;
			stream << "Failed to enumerate directory: " << directory;
			errorMessage = stream.str();
			return;
		}

		do
		{
			const char* name = findData.cFileName;
			if (strcmp(name, ".") == 0 || strcmp(name, "..") == 0)
			{
				continue;
			}

			const bool isDirectory = (findData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0;
			if (wantDirectories)
			{
				if (isDirectory)
				{
					outEntries.push_back(name);
				}
			}
			else if (!isDirectory)
			{
				if (extension.empty() || hasExtensionInsensitive(name, extension))
				{
					outEntries.push_back(name);
				}
			}
		} while (FindNextFileA(handle, &findData));

		FindClose(handle);
		std::sort(outEntries.begin(), outEntries.end(), compareCaseInsensitive);
	}

	bool readFileBytes(const std::string& path, std::vector<char>& outBytes, std::string& errorMessage)
	{
		std::ifstream input(path.c_str(), std::ios::binary);
		if (!input)
		{
			errorMessage = std::string("Failed to open HKX file: ") + path;
			return false;
		}

		input.seekg(0, std::ios::end);
		const std::streamoff length = input.tellg();
		input.seekg(0, std::ios::beg);

		if (length < 0)
		{
			errorMessage = std::string("Failed to determine HKX size: ") + path;
			return false;
		}

		outBytes.resize(static_cast<size_t>(length));
		if (!outBytes.empty())
		{
			input.read(&outBytes[0], length);
			if (!input)
			{
				errorMessage = std::string("Failed to read HKX file: ") + path;
				return false;
			}
		}

		return true;
	}

	void writeUint32(std::ofstream& output, unsigned int value)
	{
		output.write(reinterpret_cast<const char*>(&value), sizeof(value));
	}

	ChunkWriteState beginChunk(
		std::ofstream& output,
		const char kind[4],
		const char type[4],
		unsigned int version,
		const std::string& name,
		unsigned int unk1)
	{
		ChunkWriteState state;
		state.headerOffset = output.tellp();

		output.write(kind, 4);
		output.write(type, 4);
		writeUint32(output, version);
		writeUint32(output, 0);
		writeUint32(output, name.empty() ? 0u : static_cast<unsigned int>(name.size() + 1));
		writeUint32(output, unk1);
		writeUint32(output, 0);
		if (!name.empty())
		{
			output.write(name.data(), static_cast<std::streamsize>(name.size()));
			output.put('\0');
		}

		state.dataOffset = output.tellp();
		return state;
	}

	void endChunk(std::ofstream& output, const ChunkWriteState& state)
	{
		const std::streamoff endOffset = output.tellp();
		const unsigned int size = static_cast<unsigned int>(endOffset - state.dataOffset);
		output.seekp(state.headerOffset + 12);
		writeUint32(output, size);
		output.seekp(endOffset);
	}

	bool buildSingleSet(
		const std::string& directory,
		const std::string& setName,
		const HkAnimPackOptions& options,
		HkAnimSet& outSet,
		std::string& errorMessage)
	{
		std::vector<std::string> hkxFiles;
		listDirectoryEntries(directory, false, ".hkx", hkxFiles, errorMessage);
		if (!errorMessage.empty())
		{
			return false;
		}

		if (hkxFiles.empty())
		{
			std::ostringstream stream;
			stream << "No HKX files found in set directory: " << directory;
			errorMessage = stream.str();
			return false;
		}

		outSet.name = setName;
		outSet.entries.clear();

		std::set<std::string> lowerNames;
		for (size_t i = 0; i < hkxFiles.size(); ++i)
		{
			const std::string stem = removeExtension(hkxFiles[i]);
			HkAnimEntry entry;
			entry.relativeName = setName + "\\" + stem;
			entry.sourcePath = joinPath(directory, hkxFiles[i]);
			entry.empty = false;
			outSet.entries.push_back(entry);
			lowerNames.insert(toLowerAscii(entry.relativeName));
		}

		if (options.includeRagdollPlaceholder)
		{
			const std::string ragdollName = setName + "\\ragdoll";
			if (lowerNames.find(toLowerAscii(ragdollName)) == lowerNames.end())
			{
				HkAnimEntry entry;
				entry.relativeName = ragdollName;
				entry.empty = true;
				outSet.entries.push_back(entry);
			}
		}

		std::sort(
			outSet.entries.begin(),
			outSet.entries.end(),
			compareEntriesByName);

		return true;
	}

	bool writeSetPayload(std::ofstream& output, const HkAnimSet& set, std::string& errorMessage)
	{
		writeUint32(output, static_cast<unsigned int>(set.entries.size()));

		for (size_t i = 0; i < set.entries.size(); ++i)
		{
			const HkAnimEntry& entry = set.entries[i];
			writeUint32(output, static_cast<unsigned int>(entry.relativeName.size()));
			if (!entry.relativeName.empty())
			{
				output.write(entry.relativeName.data(), static_cast<std::streamsize>(entry.relativeName.size()));
			}
		}

		std::vector<char> bytes;
		for (size_t i = 0; i < set.entries.size(); ++i)
		{
			const HkAnimEntry& entry = set.entries[i];
			if (entry.empty)
			{
				writeUint32(output, 0);
				continue;
			}

			bytes.clear();
			if (!readFileBytes(entry.sourcePath, bytes, errorMessage))
			{
				return false;
			}

			writeUint32(output, static_cast<unsigned int>(bytes.size()));
			if (!bytes.empty())
			{
				output.write(&bytes[0], static_cast<std::streamsize>(bytes.size()));
			}
		}

		return output.good();
	}
}

bool buildHkAnimSetsFromDirectory(
	const std::string& inputDirectory,
	const HkAnimPackOptions& options,
	std::vector<HkAnimSet>& outSets,
	std::string& errorMessage)
{
	outSets.clear();
	errorMessage.clear();

	std::vector<std::string> rootFiles;
	listDirectoryEntries(inputDirectory, false, ".hkx", rootFiles, errorMessage);
	if (!errorMessage.empty())
	{
		return false;
	}

	std::vector<std::string> childDirectories;
	listDirectoryEntries(inputDirectory, true, std::string(), childDirectories, errorMessage);
	if (!errorMessage.empty())
	{
		return false;
	}

	if (!rootFiles.empty())
	{
		const std::string setName = options.singleSetName.empty() ? getBaseName(inputDirectory) : options.singleSetName;
		HkAnimSet set;
		if (!buildSingleSet(inputDirectory, setName, options, set, errorMessage))
		{
			return false;
		}
		outSets.push_back(set);
	}

	for (size_t i = 0; i < childDirectories.size(); ++i)
	{
		const std::string setDirectory = joinPath(inputDirectory, childDirectories[i]);
		std::vector<std::string> hkxFiles;
		listDirectoryEntries(setDirectory, false, ".hkx", hkxFiles, errorMessage);
		if (!errorMessage.empty())
		{
			return false;
		}
		if (hkxFiles.empty())
		{
			continue;
		}

		HkAnimSet set;
		if (!buildSingleSet(setDirectory, childDirectories[i], options, set, errorMessage))
		{
			return false;
		}
		outSets.push_back(set);
	}

	if (outSets.empty())
	{
		errorMessage = std::string("No HKX animation sets found under: ") + inputDirectory;
		return false;
	}

	return true;
}

bool writeHkAnimContainer(
	const std::vector<HkAnimSet>& sets,
	const std::string& outputPath,
	std::string& errorMessage)
{
	errorMessage.clear();

	if (sets.empty())
	{
		errorMessage = "No animation sets were provided for packing";
		return false;
	}

	std::ofstream output(outputPath.c_str(), std::ios::binary);
	if (!output)
	{
		errorMessage = std::string("Failed to create output file: ") + outputPath;
		return false;
	}

	output.write(kRelicChunkySignature, sizeof(kRelicChunkySignature));
	writeUint32(output, 3);
	writeUint32(output, 1);
	writeUint32(output, 36);
	writeUint32(output, 28);
	writeUint32(output, 1);

	const char foldKind[4] = {'F', 'O', 'L', 'D'};
	const char dataKind[4] = {'D', 'A', 'T', 'A'};
	const char haasType[4] = {'H', 'A', 'A', 'S'};
	const char hawsType[4] = {'H', 'A', 'W', 'S'};

	ChunkWriteState rootChunk = beginChunk(output, foldKind, haasType, 1, std::string(), 0);
	for (size_t i = 0; i < sets.size(); ++i)
	{
		const HkAnimSet& set = sets[i];
		ChunkWriteState setChunk = beginChunk(output, dataKind, hawsType, 1, set.name, 0xFFFFFFFFu);
		if (!writeSetPayload(output, set, errorMessage))
		{
			return false;
		}
		endChunk(output, setChunk);
	}
	endChunk(output, rootChunk);

	if (!output.good())
	{
		errorMessage = std::string("Failed while writing output file: ") + outputPath;
		return false;
	}

	return true;
}

bool packHkAnimFromDirectory(
	const std::string& inputDirectory,
	const std::string& outputPath,
	const HkAnimPackOptions& options,
	std::string& errorMessage)
{
	std::vector<HkAnimSet> sets;
	if (!buildHkAnimSetsFromDirectory(inputDirectory, options, sets, errorMessage))
	{
		return false;
	}

	return writeHkAnimContainer(sets, outputPath, errorMessage);
}