#!/usr/bin/env bash
set -euo pipefail

# Build macOS .app with PyInstaller
python3 -m pip install --upgrade pip
python3 -m pip install pyinstaller

python3 -m PyInstaller --windowed --name AnyToAudio app.py

echo "Done. Output: dist/AnyToAudio.app"
