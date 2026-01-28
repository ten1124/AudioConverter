#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: audio_converter.sh input_file [format]"
  echo "  format: wav | mp3 | m4a | aac | flac | opus | ogg"
  echo "Example: audio_converter.sh input.mp3 wav"
  exit 1
fi

input="$1"
format="${2:-wav}"

codec=""
ext=""

case "${format,,}" in
  wav)  codec="pcm_s16le"; ext="wav";;
  mp3)  codec="libmp3lame"; ext="mp3";;
  m4a)  codec="aac"; ext="m4a";;
  aac)  codec="aac"; ext="aac";;
  flac) codec="flac"; ext="flac";;
  opus) codec="libopus"; ext="opus";;
  ogg)  codec="libvorbis"; ext="ogg";;
  *)
    echo "Unknown format: ${format}"
    exit 1
    ;;
 esac

out="${input%.*}.${ext}"

echo "Converting: ${input} -> ${out} (${format})"
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg が見つかりません。PATH に追加して再度お試しください。"
  exit 1
fi
ffmpeg -y -i "${input}" -c:a "${codec}" "${out}"

echo "Done."
