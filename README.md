<!-- dummy --># AudioConverter

[![Release](https://img.shields.io/github/v/release/ten1124/AudioConverter)](https://github.com/ten1124/AudioConverter/releases)[![Build](https://github.com/ten1124/AudioConverter/actions/workflows/build.yml/badge.svg)](https://github.com/ten1124/AudioConverter/actions/workflows/build.yml)![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)

FFmpeg を使って音声ファイルを WAV や主要コーデックへ変換するツールです。  
バッチ/シェルの簡易変換と、GUI アプリ (Python/Tkinter) を含みます。

## Features
- WAV / MP3 / M4A / AAC / FLAC / Opus / Ogg に変換
- Windows / macOS / Linux で利用可能
- GUI でビットレート指定や出力先の指定が可能
- ドラッグ&ドロップで変換できる

## For Users
### Install
- GitHub Releases から OS に合ったビルド済みファイルをダウンロードしてください
- Releases: [![Release](https://img.shields.io/github/v/release/ten1124/AudioConverter)](https://github.com/ten1124/AudioConverter/releases)

### Requirements
- FFmpeg（初回起動時に自動チェックされ、未インストールの場合は OS 別のインストールページが開きます）
  - 手動でインストールする場合は `https://ffmpeg.org/download.html` を参照してくださいS

### CLI (Windows / macOS / Linux)

### Windows (bat)
```bat
scripts/audio_converter.bat input_file [format]
```
Example:
```bat
scripts/audio_converter.bat input.mp3 wav
```

### macOS / Linux (sh)
```sh
scripts/audio_converter.sh input_file [format]
```

format: `wav` | `mp3` | `m4a` | `aac` | `flac` | `opus` | `ogg`

### GUI App
アプリを起動してファイルをドラッグ&ドロップできます。

### Output Modes (GUI)
- 入力元と同じフォルダ
- 入力元にサブディレクトリ作成
- 指定フォルダ

### Notes
- WAV は `pcm_s16le` で出力します
- MP3/AAC/Opus/Ogg はビットレート指定に対応（GUI で設定可能）
- 動作確認していますが、個人制作のため不具合があるかもしれません。重要な用途では結果を確認して使ってください。

### エンコード設定
- 表示設定で各項目の表示/非表示を切り替え可能
- 非表示の項目は自動的に「ソース一致」で処理されます

## For Developers
### Requirements
- Python 3（GUI アプリの実行とビルド用）
- FFmpeg が PATH に入っていること

### Run (GUI)
```sh
python3 app.py
```
ドラッグ&ドロップを使うには `tkinterdnd2` が必要です。
```sh
pip install tkinterdnd2
```

### Build
#### Windows (.exe)
```bat
build\\build_win.bat
```

#### macOS (.app)
```sh
build/build_mac.sh
```

#### Output
- Windows: `dist/AudioConverter.exe`
- macOS: `dist/AudioConverter.app`
