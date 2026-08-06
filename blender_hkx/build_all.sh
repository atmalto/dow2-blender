#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
bash_exe=${COMSPEC:-cmd.exe}

if command -v cygpath >/dev/null 2>&1; then
	build_bat=$(cygpath -w "$script_dir/build_all.bat")
else
	build_bat="$script_dir/build_all.bat"
fi

"$bash_exe" //c "$build_bat"