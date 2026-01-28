#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: any_to_audio.sh input_file [format]"
  echo "  format: wav | mp3 | m4a | aac | flac | opus | ogg"
  echo "Example: any_to_audio.sh input.mp3 wav"
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
ffmpeg -y -i "${input}" -c:a "${codec}" "${out}"

echo "Done."
