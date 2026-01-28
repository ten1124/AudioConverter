@echo off
setlocal
cd /d "%~dp0.."


rem Build Windows .exe with PyInstaller
py -m pip install --upgrade pip
py -m pip install pyinstaller

py -m PyInstaller --noconsole --onefile --name AnyToAudio app.py

if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)

echo Done. Output: dist\AnyToAudio.exe
pause
endlocal
