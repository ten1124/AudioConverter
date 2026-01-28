Any To Audio

FFmpeg を使って音声ファイルを WAV または主要コーデックへ変換するツールです。
バッチ/シェルの簡易変換と、GUI アプリ (Python/Tkinter) を含みます。

Requirements
- FFmpeg が PATH に入っていること
- Python 3 (GUI アプリの実行とビルド用)

Scripts
Windows (bat)
- scripts/any_to_audio.bat input_file [format]
  Example:
  - scripts/any_to_audio.bat input.mp3 wav

macOS/Linux (sh)
- scripts/any_to_audio.sh input_file [format]

format: wav | mp3 | m4a | aac | flac | opus | ogg


GUI App
- python3 app.py
- ドラッグ&ドロップを使うには `tkinterdnd2` が必要です
  - 例: pip install tkinterdnd2

Output Modes (GUI)
- 入力元と同じフォルダ
- 入力元にサブディレクトリ作成
- 指定フォルダ

Build
Windows exe
- build/build_win.bat

macOS app
- build/build_mac.sh

Output
- Windows: dist/AnyToAudio.exe
- macOS: dist/AnyToAudio.app

Notes
- WAV は pcm_s16le で出力します。
- MP3/AAC/Opus/Ogg はビットレート指定に対応 (GUI で設定可能)。


エンコード設定
- 表示設定で各項目の表示/非表示を切り替え可能
- 非表示の項目は自動的に「ソース一致」で処理されます
