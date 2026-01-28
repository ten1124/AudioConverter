#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out_dir="$root_dir/LICENSES"

mkdir -p "$out_dir"

curl -L -o "$out_dir/Python-PSF-License.html" "https://docs.python.org/3.12/license.html"
curl -L -o "$out_dir/PyInstaller-COPYING.txt" "https://raw.githubusercontent.com/pyinstaller/pyinstaller/develop/COPYING.txt"
curl -L -o "$out_dir/GPL-2.0.txt" "https://www.gnu.org/licenses/gpl-2.0.txt"
curl -L -o "$out_dir/Apache-2.0.txt" "https://www.apache.org/licenses/LICENSE-2.0.txt"
curl -L -o "$out_dir/tkinterdnd2-LICENSE.txt" "https://raw.githubusercontent.com/pmgagne/tkinterdnd2/master/LICENSE"
curl -L -o "$out_dir/LGPL-2.1.txt" "https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt"

echo "Saved license texts to $out_dir"
