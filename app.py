import os
import queue
import shutil
import subprocess
import threading
import tkinter as tk
import sys
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    DND_AVAILABLE = True
    DND_ERROR = ""
    BASE_TK = TkinterDnD.Tk
except Exception as exc:
    DND_AVAILABLE = False
    DND_ERROR = f"{type(exc).__name__}: {exc}"
    BASE_TK = tk.Tk

FORMATS = {
    "wav": {
        "label": "WAV (pcm_s16le)",
        "codec": "pcm_s16le",
        "ext": "wav",
        "bitrate": False,
    },
    "mp3": {
        "label": "MP3 (libmp3lame)",
        "codec": "libmp3lame",
        "ext": "mp3",
        "bitrate": True,
        "bitrate_default": "192k",
    },
    "m4a": {
        "label": "M4A (AAC)",
        "codec": "aac",
        "ext": "m4a",
        "bitrate": True,
        "bitrate_default": "192k",
    },
    "aac": {
        "label": "AAC (raw)",
        "codec": "aac",
        "ext": "aac",
        "bitrate": True,
        "bitrate_default": "192k",
    },
    "flac": {
        "label": "FLAC",
        "codec": "flac",
        "ext": "flac",
        "bitrate": False,
    },
    "opus": {
        "label": "Opus (libopus)",
        "codec": "libopus",
        "ext": "opus",
        "bitrate": True,
        "bitrate_default": "128k",
    },
    "ogg": {
        "label": "Ogg Vorbis (libvorbis)",
        "codec": "libvorbis",
        "ext": "ogg",
        "bitrate": True,
        "bitrate_default": "160k",
    },
}

SOURCE_VALUE = "ソース一致"


def which_ffmpeg():
    exe = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    return shutil.which(exe)


def which_ffprobe():
    exe = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    return shutil.which(exe)


def safe_stem(path):
    base = os.path.basename(path)
    if "." in base:
        return ".".join(base.split(".")[:-1])
    return base


def parse_float(value):
    try:
        return float(value)
    except Exception:
        return None


def ensure_dir(path):
    if path and not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


class App(BASE_TK):
    def __init__(self):
        super().__init__()
        self.title("音声変換")
        self.geometry("900x700")
        self.minsize(720, 560)

        self.log_queue = queue.Queue()
        self.worker = None
        self.files = []
        self.option_rows = {}
        self.option_visible = {}
        self.option_reset = {}

        self._build_ui()
        self._poll_log()

    def _build_ui(self):
        main = ttk.Frame(self, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        file_frame = ttk.LabelFrame(main, text="入力ファイル", padding=10)
        file_frame.pack(fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(file_frame, height=8)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        if DND_AVAILABLE:
            self.listbox.drop_target_register(DND_FILES)
            self.listbox.dnd_bind("<<Drop>>", self.on_drop)
        else:
            ttk.Label(
                file_frame,
                text=f"ドラッグ&ドロップ不可 ({DND_ERROR})",
                foreground="#666666",
            ).pack(anchor="w", pady=(6, 0))

        btns = ttk.Frame(file_frame)
        btns.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

        ttk.Button(btns, text="追加", command=self.add_files).pack(fill=tk.X)
        ttk.Button(btns, text="削除", command=self.remove_selected).pack(
            fill=tk.X, pady=6
        )
        ttk.Button(btns, text="クリア", command=self.clear_files).pack(fill=tk.X)

        out_frame = ttk.LabelFrame(main, text="出力", padding=10)
        out_frame.pack(fill=tk.X, pady=(10, 0))

        self.output_mode = tk.StringVar(value="sync")
        mode_frame = ttk.Frame(out_frame)
        mode_frame.pack(fill=tk.X)
        ttk.Radiobutton(
            mode_frame,
            text="入力元と同じフォルダ",
            value="sync",
            variable=self.output_mode,
            command=self.on_output_mode_change,
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            mode_frame,
            text="入力元にサブフォルダ作成",
            value="subdir",
            variable=self.output_mode,
            command=self.on_output_mode_change,
        ).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Radiobutton(
            mode_frame,
            text="指定フォルダ",
            value="custom",
            variable=self.output_mode,
            command=self.on_output_mode_change,
        ).pack(side=tk.LEFT, padx=(12, 0))

        sub_frame = ttk.Frame(out_frame)
        sub_frame.pack(fill=tk.X, pady=(8, 0))
        self.subdir_name = tk.StringVar(value="converted")
        self.subdir_entry = ttk.Entry(sub_frame, textvariable=self.subdir_name, width=18)
        self.subdir_entry.pack(side=tk.LEFT)
        ttk.Label(sub_frame, text="サブフォルダ名").pack(side=tk.LEFT, padx=(6, 0))

        custom_frame = ttk.Frame(out_frame)
        custom_frame.pack(fill=tk.X, pady=(8, 0))
        self.out_dir = tk.StringVar(value=os.getcwd())
        self.out_entry = ttk.Entry(custom_frame, textvariable=self.out_dir)
        self.out_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.out_browse = ttk.Button(custom_frame, text="参照", command=self.pick_out_dir)
        self.out_browse.pack(side=tk.LEFT, padx=(8, 0))

        fmt_frame = ttk.LabelFrame(main, text="形式", padding=10)
        fmt_frame.pack(fill=tk.X, pady=(10, 0))

        self.format_var = tk.StringVar(value="wav")
        fmt_values = [f"{k} - {v['label']}" for k, v in FORMATS.items()]
        self.format_combo = ttk.Combobox(
            fmt_frame, values=fmt_values, state="readonly"
        )
        self.format_combo.current(0)
        self.format_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.format_combo.bind("<<ComboboxSelected>>", self.on_format_change)

        self.bitrate_var = tk.StringVar(value="")
        self.bitrate_entry = ttk.Entry(fmt_frame, textvariable=self.bitrate_var, width=10)
        self.bitrate_entry.pack(side=tk.LEFT, padx=(10, 0))
        self.bitrate_label = ttk.Label(fmt_frame, text="ビットレート (例: 192k)")
        self.bitrate_label.pack(side=tk.LEFT, padx=(6, 0))

        action_frame = ttk.Frame(main)
        action_frame.pack(fill=tk.X, pady=(10, 0))

        self.convert_btn = ttk.Button(action_frame, text="変換", command=self.start_convert)
        self.convert_btn.pack(side=tk.LEFT)

        self.open_out_btn = ttk.Button(
            action_frame, text="出力フォルダを開く", command=self.open_out_dir
        )
        self.open_out_btn.pack(side=tk.LEFT, padx=(8, 0))

        ttk.Button(action_frame, text="表示設定", command=self.open_visibility_settings).pack(
            side=tk.RIGHT
        )

        notebook = ttk.Notebook(main)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        adv_tab = ttk.Frame(notebook, padding=6)
        log_tab = ttk.Frame(notebook, padding=6)
        notebook.add(adv_tab, text="エンコード設定")
        notebook.add(log_tab, text="ログ")

        adv_frame = ttk.Frame(adv_tab)
        adv_frame.pack(fill=tk.BOTH, expand=True)
        self._build_options(adv_frame)

        log_frame = ttk.Frame(log_tab)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(log_frame, height=10, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.on_format_change()
        self.on_output_mode_change()

    def _build_options(self, parent):
        canvas = tk.Canvas(parent, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        self.options_frame = ttk.Frame(canvas)

        self.options_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.create_window((0, 0), window=self.options_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def add_row(key, label_text):
            row = ttk.Frame(self.options_frame)
            ttk.Label(row, text=label_text, width=26, anchor="w").pack(side=tk.LEFT)
            self.option_rows[key] = row
            self.option_visible[key] = tk.BooleanVar(value=True)
            return row

        def register_reset(key, func):
            self.option_reset[key] = func

        # 1 サンプルレート
        row = add_row("sample_rate", "サンプルレート")
        self.sample_rate_var = tk.StringVar(value=SOURCE_VALUE)
        sample_rates = [SOURCE_VALUE, "44100", "48000", "96000", "カスタム"]
        self.sample_rate_combo = ttk.Combobox(row, values=sample_rates, state="readonly", width=12)
        self.sample_rate_combo.pack(side=tk.LEFT)
        self.sample_rate_combo.set(SOURCE_VALUE)
        self.sample_rate_custom = tk.StringVar(value="")
        self.sample_rate_entry = ttk.Entry(row, textvariable=self.sample_rate_custom, width=10)
        self.sample_rate_entry.pack(side=tk.LEFT, padx=(8, 0))
        self.sample_rate_combo.bind("<<ComboboxSelected>>", lambda *_: self._sync_sample_rate())
        register_reset("sample_rate", lambda: self._reset_sample_rate())

        # 2 ビットレート
        row = add_row("bitrate", "ビットレート")
        self.bitrate_mode_var = tk.StringVar(value=SOURCE_VALUE)
        bitrate_modes = [SOURCE_VALUE, "CBR", "VBR", "カスタム"]
        self.bitrate_mode_combo = ttk.Combobox(row, values=bitrate_modes, state="readonly", width=10)
        self.bitrate_mode_combo.pack(side=tk.LEFT)
        self.bitrate_mode_combo.set(SOURCE_VALUE)
        self.bitrate_mode_combo.bind("<<ComboboxSelected>>", lambda *_: self._sync_bitrate_mode())
        self.bitrate_value_var = tk.StringVar(value="")
        self.bitrate_value_entry = ttk.Entry(row, textvariable=self.bitrate_value_var, width=10)
        self.bitrate_value_entry.pack(side=tk.LEFT, padx=(8, 0))
        register_reset("bitrate", lambda: self._reset_bitrate())

        # 3 品質 (q)
        row = add_row("quality", "品質 (q)")
        self.quality_var = tk.StringVar(value=SOURCE_VALUE)
        self.quality_combo = ttk.Combobox(
            row,
            values=[SOURCE_VALUE] + [str(i) for i in range(0, 11)],
            state="readonly",
            width=10,
        )
        self.quality_combo.pack(side=tk.LEFT)
        self.quality_combo.set(SOURCE_VALUE)
        register_reset("quality", lambda: self.quality_combo.set(SOURCE_VALUE))

        # 4 チャンネル数
        row = add_row("channels", "チャンネル数")
        self.channels_var = tk.StringVar(value=SOURCE_VALUE)
        self.channels_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE, "1", "2"], state="readonly", width=10
        )
        self.channels_combo.pack(side=tk.LEFT)
        self.channels_combo.set(SOURCE_VALUE)
        register_reset("channels", lambda: self.channels_combo.set(SOURCE_VALUE))

        # 5 音量調整
        row = add_row("volume", "音量調整 (dB)")
        self.volume_var = tk.StringVar(value=SOURCE_VALUE)
        self.volume_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE, "有効"], state="readonly", width=10
        )
        self.volume_combo.pack(side=tk.LEFT)
        self.volume_combo.set(SOURCE_VALUE)
        self.volume_db = tk.StringVar(value="0")
        self.volume_entry = ttk.Entry(row, textvariable=self.volume_db, width=8)
        self.volume_entry.pack(side=tk.LEFT, padx=(8, 0))
        register_reset("volume", lambda: self._reset_volume())

        # 6 ビット深度 (WAV)
        row = add_row("bit_depth", "ビット深度 (WAV)")
        self.bit_depth_var = tk.StringVar(value=SOURCE_VALUE)
        self.bit_depth_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE, "16", "24", "32"], state="readonly", width=10
        )
        self.bit_depth_combo.pack(side=tk.LEFT)
        self.bit_depth_combo.set(SOURCE_VALUE)
        register_reset("bit_depth", lambda: self.bit_depth_combo.set(SOURCE_VALUE))

        # 7 FLAC 圧縮レベル
        row = add_row("flac_level", "FLAC 圧縮レベル")
        self.flac_level_var = tk.StringVar(value=SOURCE_VALUE)
        self.flac_level_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE] + [str(i) for i in range(0, 13)], state="readonly", width=10
        )
        self.flac_level_combo.pack(side=tk.LEFT)
        self.flac_level_combo.set(SOURCE_VALUE)
        register_reset("flac_level", lambda: self.flac_level_combo.set(SOURCE_VALUE))

        # 8 ステレオモード (MP3)
        row = add_row("stereo_mode", "ステレオモード (MP3)")
        self.stereo_mode_var = tk.StringVar(value=SOURCE_VALUE)
        self.stereo_mode_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE, "joint", "stereo"], state="readonly", width=10
        )
        self.stereo_mode_combo.pack(side=tk.LEFT)
        self.stereo_mode_combo.set(SOURCE_VALUE)
        register_reset("stereo_mode", lambda: self.stereo_mode_combo.set(SOURCE_VALUE))

        # 9 Opus 帯域幅
        row = add_row("opus_bandwidth", "Opus 帯域幅")
        self.opus_bandwidth_var = tk.StringVar(value=SOURCE_VALUE)
        self.opus_bandwidth_combo = ttk.Combobox(
            row,
            values=[SOURCE_VALUE, "narrow", "medium", "wide", "superwide", "full"],
            state="readonly",
            width=12,
        )
        self.opus_bandwidth_combo.pack(side=tk.LEFT)
        self.opus_bandwidth_combo.set(SOURCE_VALUE)
        register_reset("opus_bandwidth", lambda: self.opus_bandwidth_combo.set(SOURCE_VALUE))

        # 10 Ogg/Opus/Vorbis 品質
        row = add_row("codec_quality", "Ogg/Opus/Vorbis 品質")
        self.codec_quality_var = tk.StringVar(value=SOURCE_VALUE)
        self.codec_quality_combo = ttk.Combobox(
            row,
            values=[SOURCE_VALUE] + [str(i) for i in range(-1, 11)],
            state="readonly",
            width=10,
        )
        self.codec_quality_combo.pack(side=tk.LEFT)
        self.codec_quality_combo.set(SOURCE_VALUE)
        register_reset("codec_quality", lambda: self.codec_quality_combo.set(SOURCE_VALUE))

        # 11 トリム
        row = add_row("trim", "トリム (秒)")
        self.trim_start = tk.StringVar(value="")
        self.trim_end = tk.StringVar(value="")
        ttk.Label(row, text="開始").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.trim_start, width=8).pack(side=tk.LEFT, padx=(4, 8))
        ttk.Label(row, text="終了").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.trim_end, width=8).pack(side=tk.LEFT, padx=(4, 0))
        register_reset("trim", lambda: self._reset_trim())

        # 12 メタデータ
        row = add_row("metadata", "メタデータ")
        self.metadata_var = tk.StringVar(value=SOURCE_VALUE)
        self.metadata_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE, "保持", "削除"], state="readonly", width=10
        )
        self.metadata_combo.pack(side=tk.LEFT)
        self.metadata_combo.set(SOURCE_VALUE)
        register_reset("metadata", lambda: self.metadata_combo.set(SOURCE_VALUE))

        # 13 ファイル名サフィックス
        row = add_row("suffix", "ファイル名サフィックス")
        self.suffix_var = tk.StringVar(value="")
        ttk.Entry(row, textvariable=self.suffix_var, width=16).pack(side=tk.LEFT)
        register_reset("suffix", lambda: self.suffix_var.set(""))

        # 14 リサンプル方式
        row = add_row("resample", "リサンプル方式")
        self.resample_var = tk.StringVar(value=SOURCE_VALUE)
        self.resample_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE, "soxr", "swr"], state="readonly", width=10
        )
        self.resample_combo.pack(side=tk.LEFT)
        self.resample_combo.set(SOURCE_VALUE)
        register_reset("resample", lambda: self.resample_combo.set(SOURCE_VALUE))

        # 15 ディザー
        row = add_row("dither", "ディザー")
        self.dither_var = tk.StringVar(value=SOURCE_VALUE)
        self.dither_combo = ttk.Combobox(
            row,
            values=[SOURCE_VALUE, "none", "triangular", "shibata"],
            state="readonly",
            width=12,
        )
        self.dither_combo.pack(side=tk.LEFT)
        self.dither_combo.set(SOURCE_VALUE)
        register_reset("dither", lambda: self.dither_combo.set(SOURCE_VALUE))

        # 16 ReplayGain
        row = add_row("replaygain", "ReplayGain")
        self.replaygain_var = tk.StringVar(value=SOURCE_VALUE)
        self.replaygain_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE, "track", "album"], state="readonly", width=10
        )
        self.replaygain_combo.pack(side=tk.LEFT)
        self.replaygain_combo.set(SOURCE_VALUE)
        register_reset("replaygain", lambda: self.replaygain_combo.set(SOURCE_VALUE))

        # 17 無音トリム
        row = add_row("silence_trim", "無音トリム")
        self.silence_trim_var = tk.StringVar(value=SOURCE_VALUE)
        self.silence_trim_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE, "有効"], state="readonly", width=10
        )
        self.silence_trim_combo.pack(side=tk.LEFT)
        self.silence_trim_combo.set(SOURCE_VALUE)
        register_reset("silence_trim", lambda: self.silence_trim_combo.set(SOURCE_VALUE))

        # 18 フェードイン/アウト
        row = add_row("fade", "フェード (秒)")
        self.fade_in = tk.StringVar(value="")
        self.fade_out_start = tk.StringVar(value="")
        self.fade_out = tk.StringVar(value="")
        ttk.Label(row, text="イン").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.fade_in, width=6).pack(side=tk.LEFT, padx=(4, 8))
        ttk.Label(row, text="アウト開始").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.fade_out_start, width=6).pack(side=tk.LEFT, padx=(4, 8))
        ttk.Label(row, text="アウト長").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.fade_out, width=6).pack(side=tk.LEFT, padx=(4, 0))
        register_reset("fade", lambda: self._reset_fade())

        # 19 ラウドネス正規化
        row = add_row("loudnorm", "ラウドネス正規化")
        self.loudnorm_var = tk.StringVar(value=SOURCE_VALUE)
        self.loudnorm_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE, "有効"], state="readonly", width=10
        )
        self.loudnorm_combo.pack(side=tk.LEFT)
        self.loudnorm_combo.set(SOURCE_VALUE)
        self.loudnorm_target = tk.StringVar(value="-16")
        ttk.Label(row, text="LUFS").pack(side=tk.LEFT, padx=(6, 0))
        ttk.Entry(row, textvariable=self.loudnorm_target, width=6).pack(side=tk.LEFT)
        register_reset("loudnorm", lambda: self._reset_loudnorm())

        # 20 AAC プロファイル
        row = add_row("aac_profile", "AAC プロファイル")
        self.aac_profile_var = tk.StringVar(value=SOURCE_VALUE)
        self.aac_profile_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE, "LC", "HE", "HEv2"], state="readonly", width=10
        )
        self.aac_profile_combo.pack(side=tk.LEFT)
        self.aac_profile_combo.set(SOURCE_VALUE)
        register_reset("aac_profile", lambda: self.aac_profile_combo.set(SOURCE_VALUE))

        # 21 MP3 VBR モード
        row = add_row("mp3_vbr", "MP3 VBR モード")
        self.mp3_vbr_var = tk.StringVar(value=SOURCE_VALUE)
        self.mp3_vbr_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE] + [str(i) for i in range(0, 10)], state="readonly", width=10
        )
        self.mp3_vbr_combo.pack(side=tk.LEFT)
        self.mp3_vbr_combo.set(SOURCE_VALUE)
        register_reset("mp3_vbr", lambda: self.mp3_vbr_combo.set(SOURCE_VALUE))

        # 22 Opus フレーム長
        row = add_row("opus_frame", "Opus フレーム長")
        self.opus_frame_var = tk.StringVar(value=SOURCE_VALUE)
        self.opus_frame_combo = ttk.Combobox(
            row,
            values=[SOURCE_VALUE, "2.5", "5", "10", "20", "40", "60"],
            state="readonly",
            width=10,
        )
        self.opus_frame_combo.pack(side=tk.LEFT)
        self.opus_frame_combo.set(SOURCE_VALUE)
        register_reset("opus_frame", lambda: self.opus_frame_combo.set(SOURCE_VALUE))

        # 23 Opus アプリケーション
        row = add_row("opus_app", "Opus アプリケーション")
        self.opus_app_var = tk.StringVar(value=SOURCE_VALUE)
        self.opus_app_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE, "audio", "voip", "lowdelay"], state="readonly", width=10
        )
        self.opus_app_combo.pack(side=tk.LEFT)
        self.opus_app_combo.set(SOURCE_VALUE)
        register_reset("opus_app", lambda: self.opus_app_combo.set(SOURCE_VALUE))

        # 24 Vorbis 品質
        row = add_row("vorbis_quality", "Vorbis 品質")
        self.vorbis_quality_var = tk.StringVar(value=SOURCE_VALUE)
        self.vorbis_quality_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE] + [str(i) for i in range(-1, 11)], state="readonly", width=10
        )
        self.vorbis_quality_combo.pack(side=tk.LEFT)
        self.vorbis_quality_combo.set(SOURCE_VALUE)
        register_reset("vorbis_quality", lambda: self.vorbis_quality_combo.set(SOURCE_VALUE))

        # 25 ファイル名テンプレート
        row = add_row("name_template", "ファイル名テンプレート")
        self.name_template_var = tk.StringVar(value="")
        ttk.Entry(row, textvariable=self.name_template_var, width=28).pack(side=tk.LEFT)
        ttk.Label(row, text="{name} {ext} {date} {n}").pack(side=tk.LEFT, padx=(8, 0))
        register_reset("name_template", lambda: self.name_template_var.set(""))

        # 26 既存ファイルの扱い
        row = add_row("overwrite", "既存ファイルの扱い")
        self.overwrite_var = tk.StringVar(value=SOURCE_VALUE)
        self.overwrite_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE, "上書き", "スキップ", "連番"], state="readonly", width=10
        )
        self.overwrite_combo.pack(side=tk.LEFT)
        self.overwrite_combo.set(SOURCE_VALUE)
        register_reset("overwrite", lambda: self.overwrite_combo.set(SOURCE_VALUE))

        # 27 変換後の元ファイル
        row = add_row("post_action", "変換後の元ファイル")
        self.post_action_var = tk.StringVar(value=SOURCE_VALUE)
        self.post_action_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE, "なし", "コピー", "移動"], state="readonly", width=10
        )
        self.post_action_combo.pack(side=tk.LEFT)
        self.post_action_combo.set(SOURCE_VALUE)
        register_reset("post_action", lambda: self.post_action_combo.set(SOURCE_VALUE))

        # 28 並列数
        row = add_row("parallel", "並列数")
        self.parallel_var = tk.StringVar(value=SOURCE_VALUE)
        self.parallel_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE, "1", "2", "4", "8"], state="readonly", width=10
        )
        self.parallel_combo.pack(side=tk.LEFT)
        self.parallel_combo.set(SOURCE_VALUE)
        register_reset("parallel", lambda: self.parallel_combo.set(SOURCE_VALUE))

        # 29 音声のみ抽出
        row = add_row("audio_only", "音声のみ抽出")
        self.audio_only_var = tk.StringVar(value=SOURCE_VALUE)
        self.audio_only_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE, "有効"], state="readonly", width=10
        )
        self.audio_only_combo.pack(side=tk.LEFT)
        self.audio_only_combo.set(SOURCE_VALUE)
        register_reset("audio_only", lambda: self.audio_only_combo.set(SOURCE_VALUE))

        # 30 アルバムアート
        row = add_row("album_art", "アルバムアート")
        self.album_art_var = tk.StringVar(value=SOURCE_VALUE)
        self.album_art_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE, "保持", "削除"], state="readonly", width=10
        )
        self.album_art_combo.pack(side=tk.LEFT)
        self.album_art_combo.set(SOURCE_VALUE)
        register_reset("album_art", lambda: self.album_art_combo.set(SOURCE_VALUE))

        # 31 情報表示
        row = add_row("info", "情報表示")
        self.info_var = tk.StringVar(value=SOURCE_VALUE)
        self.info_combo = ttk.Combobox(
            row, values=[SOURCE_VALUE, "有効"], state="readonly", width=10
        )
        self.info_combo.pack(side=tk.LEFT)
        self.info_combo.set(SOURCE_VALUE)
        register_reset("info", lambda: self.info_combo.set(SOURCE_VALUE))

        for key, row in self.option_rows.items():
            row.pack(fill=tk.X, pady=2)

    def open_visibility_settings(self):
        win = tk.Toplevel(self)
        win.title("表示設定")
        win.geometry("420x600")
        win.transient(self)

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        for key, row in self.option_rows.items():
            var = self.option_visible[key]
            text = row.winfo_children()[0].cget("text")
            cb = ttk.Checkbutton(
                frame,
                text=text,
                variable=var,
                command=lambda k=key: self.set_option_visibility(k, self.option_visible[k].get()),
            )
            cb.pack(anchor="w", pady=2)

        ttk.Button(frame, text="閉じる", command=win.destroy).pack(anchor="e", pady=8)

    def set_option_visibility(self, key, visible):
        row = self.option_rows.get(key)
        if not row:
            return
        if visible:
            row.pack(fill=tk.X, pady=2)
        else:
            row.pack_forget()
            reset = self.option_reset.get(key)
            if reset:
                reset()

    def _reset_sample_rate(self):
        self.sample_rate_combo.set(SOURCE_VALUE)
        self.sample_rate_custom.set("")

    def _sync_sample_rate(self):
        if self.sample_rate_combo.get() != "カスタム":
            self.sample_rate_custom.set("")

    def _reset_bitrate(self):
        self.bitrate_mode_combo.set(SOURCE_VALUE)
        self.bitrate_value_var.set("")

    def _sync_bitrate_mode(self):
        if self.bitrate_mode_combo.get() == SOURCE_VALUE:
            self.bitrate_value_var.set("")

    def _reset_volume(self):
        self.volume_combo.set(SOURCE_VALUE)
        self.volume_db.set("0")

    def _reset_trim(self):
        self.trim_start.set("")
        self.trim_end.set("")

    def _reset_fade(self):
        self.fade_in.set("")
        self.fade_out_start.set("")
        self.fade_out.set("")

    def _reset_loudnorm(self):
        self.loudnorm_combo.set(SOURCE_VALUE)
        self.loudnorm_target.set("-16")

    def add_files(self):
        paths = filedialog.askopenfilenames(title="音声ファイルを選択")
        if not paths:
            return
        for path in paths:
            self._add_file(path)

    def on_drop(self, event):
        paths = self.tk.splitlist(event.data)
        for path in paths:
            if os.path.isfile(path):
                self._add_file(path)
        return "break"

    def _add_file(self, path):
        if path not in self.files:
            self.files.append(path)
            self.listbox.insert(tk.END, path)

    def remove_selected(self):
        selected = list(self.listbox.curselection())
        if not selected:
            return
        for idx in reversed(selected):
            self.listbox.delete(idx)
            del self.files[idx]

    def clear_files(self):
        self.listbox.delete(0, tk.END)
        self.files = []

    def pick_out_dir(self):
        path = filedialog.askdirectory(title="出力フォルダを選択")
        if path:
            self.out_dir.set(path)

    def open_out_dir(self):
        path = self.get_preview_output_dir()
        if not path:
            return
        if os.name == "nt":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)

    def on_output_mode_change(self):
        mode = self.output_mode.get()
        if mode == "subdir":
            self.subdir_entry.configure(state="normal")
        else:
            self.subdir_entry.configure(state="disabled")

        if mode == "custom":
            self.out_entry.configure(state="normal")
            self.out_browse.configure(state="normal")
        else:
            self.out_entry.configure(state="disabled")
            self.out_browse.configure(state="disabled")

    def get_preview_output_dir(self):
        mode = self.output_mode.get()
        if mode == "custom":
            return self.out_dir.get().strip()
        if not self.files:
            return ""
        base_dir = os.path.dirname(self.files[0])
        if mode == "sync":
            return base_dir
        subdir = self.subdir_name.get().strip()
        if not subdir:
            return ""
        return os.path.join(base_dir, subdir)

    def on_format_change(self, *_):
        selection = self.format_combo.get().split(" - ")[0]
        fmt = FORMATS.get(selection, FORMATS["wav"])
        if fmt.get("bitrate"):
            default = fmt.get("bitrate_default", "192k")
            if not self.bitrate_var.get():
                self.bitrate_var.set(default)
            self.bitrate_entry.configure(state="normal")
            self.bitrate_label.configure(state="normal")
        else:
            self.bitrate_var.set("")
            self.bitrate_entry.configure(state="disabled")
            self.bitrate_label.configure(state="disabled")

    def log(self, message):
        self.log_queue.put(message)

    def _poll_log(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.configure(state=tk.NORMAL)
                self.log_text.insert(tk.END, msg + "\n")
                self.log_text.see(tk.END)
                self.log_text.configure(state=tk.DISABLED)
        except queue.Empty:
            pass
        self.after(100, self._poll_log)

    def start_convert(self):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("処理中", "変換が進行中です。")
            return
        if not self.files:
            messagebox.showwarning("入力なし", "入力ファイルを追加してください。")
            return
        mode = self.output_mode.get()
        if mode == "custom":
            out_dir = self.out_dir.get().strip()
            if not out_dir:
                messagebox.showwarning("出力先", "出力フォルダを選択してください。")
                return
            if not os.path.isdir(out_dir):
                messagebox.showwarning("出力先", "出力フォルダが存在しません。")
                return
        elif mode == "subdir":
            subdir = self.subdir_name.get().strip()
            if not subdir:
                messagebox.showwarning("出力先", "サブフォルダ名を入力してください。")
                return
        if not which_ffmpeg():
            messagebox.showerror(
                "ffmpeg が見つかりません",
                "PATH に ffmpeg が見つかりません。インストールして再度お試しください。",
            )
            return

        self.convert_btn.configure(state="disabled")
        self.worker = threading.Thread(target=self._convert_worker, daemon=True)
        self.worker.start()

    def _convert_worker(self):
        selection = self.format_combo.get().split(" - ")[0]
        fmt = FORMATS.get(selection, FORMATS["wav"])
        codec = fmt["codec"]
        ext = fmt["ext"]

        bitrate = self.bitrate_var.get().strip()
        use_bitrate = fmt.get("bitrate") and bitrate

        self.log("変換を開始します...")
        failures = 0
        counter = 1

        parallel = self.parallel_combo.get() if hasattr(self, "parallel_combo") else SOURCE_VALUE
        parallel_count = 1
        if parallel != SOURCE_VALUE:
            try:
                parallel_count = int(parallel)
            except Exception:
                parallel_count = 1

        tasks = []
        for path in self.files:
            tasks.append((path, counter))
            counter += 1

        if parallel_count <= 1:
            for path, index in tasks:
                ok = self._convert_one(path, index, codec, ext, use_bitrate)
                if not ok:
                    failures += 1
        else:
            from concurrent.futures import ThreadPoolExecutor

            with ThreadPoolExecutor(max_workers=parallel_count) as exe:
                results = exe.map(
                    lambda item: self._convert_one(item[0], item[1], codec, ext, use_bitrate),
                    tasks,
                )
                for ok in results:
                    if not ok:
                        failures += 1

        if failures:
            self.log(f"完了 (エラーあり)。失敗: {failures}")
        else:
            self.log("完了。")

        self.after(0, lambda: self.convert_btn.configure(state="normal"))

    def _convert_one(self, path, index, codec, ext, use_bitrate):
        out_dir = self._resolve_output_dir(path)
        if not out_dir:
            return False
        ensure_dir(out_dir)

        name = safe_stem(path)
        suffix = self.suffix_var.get().strip()
        if suffix:
            name = f"{name}{suffix}"

        template = self.name_template_var.get().strip()
        if template:
            now = datetime.now().strftime("%Y%m%d")
            name = template.replace("{name}", safe_stem(path))
            name = name.replace("{ext}", ext)
            name = name.replace("{date}", now)
            name = name.replace("{n}", str(index))

        out_path = os.path.join(out_dir, f"{name}.{ext}")
        out_path = self._resolve_overwrite(out_path)
        if not out_path:
            self.log(f"スキップ: {path}")
            return True

        cmd, filters = self._build_command(path, out_path, codec, ext, use_bitrate)
        if filters:
            cmd += ["-af", ",".join(filters)]
        cmd.append(out_path)

        self.log(f"{path} -> {out_path}")

        if self.info_combo.get() == "有効" and which_ffprobe():
            self._log_media_info(path)

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            tail = result.stderr.strip().splitlines()[-6:]
            for line in tail:
                self.log(line)
            return False

        post = self.post_action_combo.get()
        if post == "コピー":
            try:
                shutil.copy2(path, out_dir)
            except Exception as exc:
                self.log(f"コピー失敗: {exc}")
        elif post == "移動":
            try:
                shutil.move(path, out_dir)
            except Exception as exc:
                self.log(f"移動失敗: {exc}")

        if self.info_combo.get() == "有効" and which_ffprobe():
            self._log_media_info(out_path)

        return True

    def _resolve_output_dir(self, path):
        if self.output_mode.get() == "custom":
            return self.out_dir.get().strip()
        base_dir = os.path.dirname(path)
        if self.output_mode.get() == "sync":
            return base_dir
        subdir = self.subdir_name.get().strip()
        if not subdir:
            return base_dir
        return os.path.join(base_dir, subdir)

    def _resolve_overwrite(self, out_path):
        policy = self.overwrite_combo.get()
        if policy == SOURCE_VALUE or policy == "上書き":
            return out_path
        if not os.path.exists(out_path):
            return out_path
        if policy == "スキップ":
            return ""
        if policy == "連番":
            base, ext = os.path.splitext(out_path)
            idx = 1
            while True:
                candidate = f"{base}_{idx}{ext}"
                if not os.path.exists(candidate):
                    return candidate
                idx += 1
        return out_path

    def _build_command(self, path, out_path, codec, ext, use_bitrate):
        cmd = ["ffmpeg"]
        overwrite_policy = self.overwrite_combo.get()
        if overwrite_policy == "スキップ":
            cmd.append("-n")
        else:
            cmd.append("-y")

        cmd += ["-i", path]

        if self.audio_only_combo.get() == "有効":
            cmd.append("-vn")

        if self.album_art_combo.get() == "削除":
            cmd += ["-map", "0:a"]

        if self.metadata_combo.get() == "削除":
            cmd += ["-map_metadata", "-1"]

        trim_start = parse_float(self.trim_start.get())
        trim_end = parse_float(self.trim_end.get())
        if trim_start is not None:
            cmd += ["-ss", str(trim_start)]
        if trim_end is not None:
            cmd += ["-to", str(trim_end)]

        # codec
        if ext == "wav":
            bit_depth = self.bit_depth_combo.get()
            if bit_depth == "24":
                codec = "pcm_s24le"
            elif bit_depth == "32":
                codec = "pcm_s32le"

        cmd += ["-c:a", codec]

        if ext == "flac" and self.flac_level_combo.get() != SOURCE_VALUE:
            cmd += ["-compression_level", self.flac_level_combo.get()]

        if ext in ("m4a", "aac") and self.aac_profile_combo.get() != SOURCE_VALUE:
            profile_map = {"LC": "aac_low", "HE": "aac_he", "HEv2": "aac_he_v2"}
            cmd += ["-profile:a", profile_map[self.aac_profile_combo.get()]]

        if ext == "mp3" and self.stereo_mode_combo.get() != SOURCE_VALUE:
            joint = "1" if self.stereo_mode_combo.get() == "joint" else "0"
            cmd += ["-joint_stereo", joint]

        q_value = None
        bitrate_mode = self.bitrate_mode_combo.get()
        bitrate_value = self.bitrate_value_var.get().strip()

        if ext == "mp3" and self.mp3_vbr_combo.get() != SOURCE_VALUE:
            q_value = self.mp3_vbr_combo.get()
        elif ext == "ogg" and self.vorbis_quality_combo.get() != SOURCE_VALUE:
            q_value = self.vorbis_quality_combo.get()
        elif ext in ("ogg", "opus") and self.codec_quality_combo.get() != SOURCE_VALUE:
            q_value = self.codec_quality_combo.get()
        elif bitrate_mode == "VBR" and bitrate_value:
            q_value = bitrate_value
        elif self.quality_combo.get() != SOURCE_VALUE:
            q_value = self.quality_combo.get()

        if q_value:
            cmd += ["-q:a", q_value]
        else:
            if bitrate_mode in ("CBR", "カスタム") and bitrate_value:
                cmd += ["-b:a", bitrate_value]
            elif use_bitrate and bitrate_mode == SOURCE_VALUE:
                cmd += ["-b:a", bitrate]

        if ext == "opus":
            if self.opus_bandwidth_combo.get() != SOURCE_VALUE:
                cmd += ["-bandwidth", self.opus_bandwidth_combo.get()]
            if self.opus_frame_combo.get() != SOURCE_VALUE:
                cmd += ["-frame_duration", self.opus_frame_combo.get()]
            if self.opus_app_combo.get() != SOURCE_VALUE:
                cmd += ["-application", self.opus_app_combo.get()]

        if self.sample_rate_combo.get() != SOURCE_VALUE:
            if self.sample_rate_combo.get() == "カスタム":
                custom = self.sample_rate_custom.get().strip()
                if custom:
                    cmd += ["-ar", custom]
            else:
                cmd += ["-ar", self.sample_rate_combo.get()]

        if self.channels_combo.get() != SOURCE_VALUE:
            cmd += ["-ac", self.channels_combo.get()]

        filters = []

        if self.resample_combo.get() != SOURCE_VALUE or self.dither_combo.get() != SOURCE_VALUE:
            params = []
            if self.resample_combo.get() != SOURCE_VALUE:
                params.append(f"resampler={self.resample_combo.get()}")
            if self.sample_rate_combo.get() not in (SOURCE_VALUE, "カスタム"):
                params.append(f"sample_rate={self.sample_rate_combo.get()}")
            if self.sample_rate_combo.get() == "カスタム" and self.sample_rate_custom.get().strip():
                params.append(f"sample_rate={self.sample_rate_custom.get().strip()}")
            if self.dither_combo.get() != SOURCE_VALUE:
                params.append(f"dither_method={self.dither_combo.get()}")
            filters.append("aresample=" + ":".join(params))

        if self.volume_combo.get() == "有効":
            vol = self.volume_db.get().strip()
            if vol:
                filters.append(f"volume={vol}dB")

        if self.loudnorm_combo.get() == "有効":
            lufs = self.loudnorm_target.get().strip() or "-16"
            filters.append(f"loudnorm=I={lufs}:TP=-1.5:LRA=11")

        if self.replaygain_combo.get() != SOURCE_VALUE:
            filters.append(f"replaygain={self.replaygain_combo.get()}")

        if self.silence_trim_combo.get() == "有効":
            filters.append("silenceremove=start_periods=1:start_threshold=-50dB:stop_periods=1:stop_threshold=-50dB")

        fade_in = parse_float(self.fade_in.get())
        fade_out_start = parse_float(self.fade_out_start.get())
        fade_out = parse_float(self.fade_out.get())
        if fade_in is not None and fade_in > 0:
            filters.append(f"afade=t=in:st=0:d={fade_in}")
        if fade_out is not None and fade_out_start is not None:
            filters.append(f"afade=t=out:st={fade_out_start}:d={fade_out}")

        return cmd, filters

    def _log_media_info(self, path):
        cmd = [
            which_ffprobe(),
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,codec_type,channels,sample_rate,bit_rate",
            "-show_entries",
            "format=duration,bit_rate",
            "-of",
            "default=nw=1",
            path,
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                self.log(f"info: {line}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
