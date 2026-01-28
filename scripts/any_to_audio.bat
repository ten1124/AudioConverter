@echo off
setlocal enabledelayedexpansion

if "%~1"=="" (
  echo Usage: any_to_audio.bat input_file [format]
  echo   format: wav ^| mp3 ^| m4a ^| aac ^| flac ^| opus ^| ogg
  echo Example: any_to_audio.bat input.mp3 wav
  exit /b 1
)

set "INPUT=%~1"
set "FORMAT=%~2"
if "%FORMAT%"=="" set "FORMAT=wav"

set "CODEC="
set "EXT="

if /i "%FORMAT%"=="wav"  (set "CODEC=pcm_s16le" & set "EXT=wav")
if /i "%FORMAT%"=="mp3"  (set "CODEC=libmp3lame" & set "EXT=mp3")
if /i "%FORMAT%"=="m4a"  (set "CODEC=aac"        & set "EXT=m4a")
if /i "%FORMAT%"=="aac"  (set "CODEC=aac"        & set "EXT=aac")
if /i "%FORMAT%"=="flac" (set "CODEC=flac"       & set "EXT=flac")
if /i "%FORMAT%"=="opus" (set "CODEC=libopus"    & set "EXT=opus")
if /i "%FORMAT%"=="ogg"  (set "CODEC=libvorbis"  & set "EXT=ogg")

if "%CODEC%"=="" (
  echo Unknown format: %FORMAT%
  exit /b 1
)

set "OUT=%~dpn1.%EXT%"

echo Converting: "%INPUT%" -> "%OUT%" (%FORMAT%)
ffmpeg -y -i "%INPUT%" -c:a %CODEC% "%OUT%"

if errorlevel 1 (
  echo Conversion failed.
  exit /b 1
)

echo Done.
endlocal
