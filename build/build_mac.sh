#!/usr/bin/env bash
set -euo pipefail

# Build macOS .app with PyInstaller
python3 -m pip install --upgrade pip
python3 -m pip install pyinstaller tkinterdnd2

python3 -m PyInstaller --windowed --name AudioConverter app.py

echo "Done. Output: dist/AudioConverter.app"
