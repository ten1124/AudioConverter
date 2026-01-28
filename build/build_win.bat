@echo off
setlocal
cd /d "%~dp0.."


rem Build Windows .exe with PyInstaller
py -m pip install --upgrade pip
py -m pip install pyinstaller tkinterdnd2

py -m PyInstaller --noconsole --onefile --name AudioConverter app.py

if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)

echo Done. Output: dist\AudioConverter.exe
pause
endlocal
