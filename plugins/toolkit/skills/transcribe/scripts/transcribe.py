#!/usr/bin/env python3
"""本機語音轉逐字稿：Mac（Apple Silicon）用 mlx-whisper，其他平台用 faster-whisper，輸出經 OpenCC s2twp 轉台灣繁體。

用法：
  transcribe.py transcribe <audio> --out <md> [--model large-v3-turbo] [--prompt-file <txt>] [--language zh] [--force]
  transcribe.py doctor
"""
from __future__ import annotations

import argparse
import platform
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Tuple

Segment = Tuple[float, str]
BackendRunner = Callable[[str, str, Optional[str], str], List[Segment]]

DEFAULT_MODEL = "large-v3-turbo"


def format_ts(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def render_markdown(segments: List[Segment], meta: dict) -> str:
    lines = [
        "# 逐字稿",
        "",
        f"- 音檔：{meta['audio']}",
        f"- 模型：{meta['model']}",
        f"- 轉錄時間：{meta['transcribed_at']}",
        "",
    ]
    lines += [f"[{format_ts(start)}] {text.strip()}" for start, text in segments]
    return "\n".join(lines) + "\n"


def pick_backend(system: str, machine: str) -> str:
    return "mlx" if system == "Darwin" and machine == "arm64" else "faster-whisper"


def _converter():
    import opencc

    return opencc.OpenCC("s2twp")


def _zh_tw(conv, text: str) -> str:
    # OpenCC 把「台」一律轉成「臺」，台灣日常與商務寫法以「台」為主（台灣、平台、機台）
    return conv.convert(text).replace("臺", "台")


def to_zh_tw(text: str) -> str:
    return _zh_tw(_converter(), text)


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


MLX_MODELS = {"large-v3-turbo": "mlx-community/whisper-large-v3-turbo"}
# Whisper prompt 上限約 223 tokens，超過時保留尾端、截掉開頭；中文約一字一 token，留點餘裕
PROMPT_CHAR_LIMIT = 200


def parse_silences(ffmpeg_stderr: str, duration: float) -> List[Tuple[float, float]]:
    """解析 ffmpeg silencedetect 輸出；結尾沒有 silence_end 的區段延伸到 duration。"""
    import re

    out: List[Tuple[float, float]] = []
    start = None
    for m in re.finditer(r"silence_(start|end): ([0-9.]+)", ffmpeg_stderr):
        if m.group(1) == "start":
            start = float(m.group(2))
        elif start is not None:
            out.append((start, float(m.group(2))))
            start = None
    if start is not None:
        out.append((start, duration))
    return out


def detect_silences(audio: str) -> List[Tuple[float, float]]:
    """用 ffmpeg 找出接近無聲的區段；ffmpeg 失敗時回空清單（等同不過濾）。"""
    import subprocess

    try:
        r = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", "-i", audio, "-af", "silencedetect=noise=-45dB:d=1", "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        )
    except OSError:
        return []
    import re

    m = re.search(r"Duration: (\d+):(\d+):([0-9.]+)", r.stderr)
    duration = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else float("inf")
    return parse_silences(r.stderr, duration)


def drop_silent(raw: List[dict], silences: List[Tuple[float, float]]) -> List[dict]:
    """丟掉八成以上落在無聲區段的段落——Whisper 在無聲處會幻覺出「訂閱、字幕由…提供」之類文字。"""
    kept = []
    for seg in raw:
        start, end = float(seg["start"]), float(seg.get("end", seg["start"]))
        length = max(end - start, 1e-6)
        covered = sum(max(0.0, min(end, b) - max(start, a)) for a, b in silences)
        if covered / length < 0.8:
            kept.append(seg)
    return kept


def run_mlx(audio: str, model: str, prompt: Optional[str], language: str) -> List[Segment]:
    import mlx_whisper

    result = mlx_whisper.transcribe(
        audio,
        path_or_hf_repo=MLX_MODELS.get(model, model),
        initial_prompt=prompt,
        language=language,
        word_timestamps=True,
        hallucination_silence_threshold=2.0,
        verbose=None,
    )
    raw = drop_silent(result.get("segments", []), detect_silences(audio))
    return [(float(s["start"]), s["text"]) for s in raw]


def _has_cuda() -> bool:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def run_faster_whisper(audio: str, model: str, prompt: Optional[str], language: str) -> List[Segment]:
    from faster_whisper import WhisperModel

    compute_type = "float16" if _has_cuda() else "int8"
    wm = WhisperModel(model, device="auto", compute_type=compute_type)
    segments, info = wm.transcribe(audio, language=language, initial_prompt=prompt, vad_filter=True)
    out: List[Segment] = []
    tty = sys.stderr.isatty()  # 背景執行時不印逐段進度，免得 stderr 變成一條數十 KB 的長行
    for s in segments:
        out.append((float(s.start), s.text))
        if tty:
            print(f"\r進度 {format_ts(s.end)} / {format_ts(info.duration)}", end="", file=sys.stderr, flush=True)
    if tty:
        print(file=sys.stderr)
    return out


def _resolve_runner(name: str) -> BackendRunner:
    return run_mlx if name == "mlx" else run_faster_whisper


def _importable(module: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(module) is not None


def _pkg_version(name: str) -> Optional[str]:
    from importlib import metadata

    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _major(version: Optional[str]) -> int:
    try:
        return int((version or "0").split(".")[0])
    except ValueError:
        return 0


def check_env() -> List[Tuple[str, bool, str]]:
    backend = pick_backend(platform.system(), platform.machine())
    checks = []
    if backend == "mlx":
        checks.append(("ffmpeg", shutil.which("ffmpeg") is not None, "brew install ffmpeg"))
        module, pkg = "mlx_whisper", "mlx-whisper"
    else:
        module, pkg = "faster_whisper", "faster-whisper"
    checks.append((pkg, _importable(module), f"pip install {pkg}"))
    if backend == "faster-whisper":
        # faster-whisper 1.2.x 呼叫 av.open(metadata_errors=…)，PyAV 17 起已移除（2026-11 實測 19.0.2 失敗、16.1.0 可用）
        av = _pkg_version("av")
        checks.append((f"PyAV {av or '未安裝'}", av is not None and _major(av) < 17, 'pip install "av<17"'))
    checks.append(("opencc", _importable("opencc"), "pip install opencc-python-reimplemented"))
    return checks


def cmd_doctor() -> int:
    ok = True
    for name, ready, hint in check_env():
        print(f"{'OK ' if ready else 'NG '} {name}" + ("" if ready else f"　→ {hint}"))
        ok = ok and ready
    return 0 if ok else 1


def cmd_transcribe(args, backend_runner: Optional[BackendRunner]) -> int:
    audio = Path(args.audio)
    out = Path(args.out)
    if not audio.is_file():
        _err(f"找不到音檔：{audio}")
        return 2
    backend = pick_backend(platform.system(), platform.machine())
    # faster-whisper 以 PyAV 自帶解碼，只有 mlx-whisper 需要系統的 ffmpeg
    if backend == "mlx" and shutil.which("ffmpeg") is None:
        _err("找不到 ffmpeg，無法解碼音檔；先跑 `transcribe.py doctor` 看安裝指令")
        return 3
    if out.exists() and not args.force:
        _err(f"輸出檔已存在：{out}（要覆寫請加 --force）")
        return 2
    try:
        conv = _converter()
    except ImportError:
        _err("缺少 OpenCC，無法轉繁體：pip install opencc-python-reimplemented（或先跑 doctor）")
        return 3
    prompt = Path(args.prompt_file).read_text(encoding="utf-8").strip() if args.prompt_file else None
    if prompt and len(prompt) > PROMPT_CHAR_LIMIT:
        _err(f"警告：術語提示 {len(prompt)} 字，超過 Whisper 上限（約 {PROMPT_CHAR_LIMIT} 字），開頭會被截掉；最重要的詞請放在檔尾")

    runner = backend_runner or _resolve_runner(backend)
    segments = runner(str(audio), args.model, prompt, args.language)
    segments = [(start, _zh_tw(conv, text)) for start, text in segments if text.strip()]
    if not segments:
        _err("未偵測到語音：音檔可能是靜音或格式無法解析，未產生逐字稿")
        return 4

    meta = {
        "audio": audio.name,
        "model": args.model,
        "transcribed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_markdown(segments, meta), encoding="utf-8")
    print(f"逐字稿已寫入：{out}（{len(segments)} 段）")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="transcribe.py", description="本機語音轉逐字稿")
    sub = p.add_subparsers(dest="cmd", required=True)
    tr = sub.add_parser("transcribe", help="把音檔轉成逐字稿 Markdown")
    tr.add_argument("audio")
    tr.add_argument("--out", required=True)
    tr.add_argument("--model", default=DEFAULT_MODEL)
    tr.add_argument("--prompt-file")
    tr.add_argument("--language", default="zh")
    tr.add_argument("--force", action="store_true")
    sub.add_parser("doctor", help="檢查 ffmpeg／轉錄套件／OpenCC 是否就緒")
    return p


def main(argv: List[str], backend_runner: Optional[BackendRunner] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    if args.cmd == "transcribe":
        return cmd_transcribe(args, backend_runner)
    return cmd_doctor()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
