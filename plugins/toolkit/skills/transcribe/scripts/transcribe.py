#!/usr/bin/env python3
"""本機語音轉逐字稿：Mac（Apple Silicon）用 mlx-whisper，其他平台用 faster-whisper，輸出經 OpenCC s2twp 轉台灣繁體。

用法：
  transcribe.py transcribe <audio> --out <md> [--model large-v3-turbo] [--prompt-file <txt>] [--language zh] [--force]
  transcribe.py doctor
"""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
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


def check_env(record: bool = False) -> List[Tuple[str, bool, str]]:
    backend = pick_backend(platform.system(), platform.machine())
    checks = []
    if record and backend != "mlx":
        # faster-whisper 轉錄不需要 ffmpeg，但錄音需要
        hint = "brew install ffmpeg" if platform.system() == "Darwin" else "winget install ffmpeg"
        checks.append(("ffmpeg（錄音用）", shutil.which("ffmpeg") is not None, hint))
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


def cmd_doctor(record: bool = False) -> int:
    ok = True
    for name, ready, hint in check_env(record):
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


# ---- 錄音（麥克風） ----


def parse_devices(system: str, ffmpeg_stderr: str) -> List[str]:
    """從 ffmpeg -list_devices 的輸出取出音訊輸入裝置名稱。"""
    import re

    if system == "Darwin":
        text = ffmpeg_stderr.split("AVFoundation audio devices:", 1)[-1] if "AVFoundation audio devices:" in ffmpeg_stderr else ""
        return re.findall(r"\] \[\d+\] (.+)$", text, flags=re.M)
    return re.findall(r'"([^"]+)" \(audio\)', ffmpeg_stderr)


def _mic_input(system: str, device: Optional[str]) -> List[str]:
    # 輸入佇列加大：實測 Mac 不加時每 30 秒掉約 3.5 秒音訊
    if system == "Darwin":
        # 不用編號 0：實機上第 0 個常是 Teams 之類的虛擬裝置
        return ["-thread_queue_size", "4096", "-f", "avfoundation", "-i", f":{device or 'default'}"]
    if not device:
        raise ValueError("Windows 需指定 --device（用 `record devices` 查名稱）")
    return ["-thread_queue_size", "4096", "-f", "dshow", "-i", f"audio={device}"]


def _segment_output(out_dir: Path, segment_sec: int) -> List[str]:
    return [
        "-ar", "16000", "-ac", "1",
        # 內層 muxer 每個封包就寫盤：實測不加時硬殺會丟最後約 8 秒（256 KiB 緩衝）
        "-f", "segment", "-segment_format_options", "flush_packets=1",
        "-segment_time", str(segment_sec), "-reset_timestamps", "1",
        str(out_dir / "seg-%03d.wav"),
    ]


def build_record_cmd(system: str, device: Optional[str], out_dir: Path, segment_sec: int) -> List[str]:
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", *_mic_input(system, device),
        # async 重取樣：補齊擷取端的時間誤差
        "-af", "aresample=async=1000", *_segment_output(out_dir, segment_sec),
    ]


def build_pipe_record_cmd(system: str, source: str, mic_device: Optional[str], out_dir: Path, segment_sec: int, rate: int) -> List[str]:
    """系統聲音由 worker 以 float32 單聲道 PCM 寫進 stdin；both 時再混入麥克風。"""
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "f32le", "-ar", str(rate), "-ac", "1", "-i", "pipe:0"]
    if source == "both":
        cmd += [*_mic_input(system, mic_device), "-filter_complex",
                "[1:a]aresample=async=1000[m];[0:a][m]amix=inputs=2:duration=first:normalize=0"]
    else:
        cmd += ["-af", "aresample=async=1000"]
    return cmd + _segment_output(out_dir, segment_sec)


def concat_list(segments: List[Path]) -> str:
    """ffmpeg concat demuxer 清單：用絕對路徑（相對路徑會以清單檔目錄為基準），單引號跳脫成 '\\''；
    每段加 ignore_length——被硬殺的最後一段 wav 檔頭長度沒收尾，不加會被截短。"""
    return "".join(
        "file '" + str(Path(seg).resolve()).replace("'", "'\\''") + "'\noption ignore_length 1\n" for seg in segments
    )


SILENCE_DB = -70.0
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
STATE_FILE = "record.json"


def _spawn(cmd: List[str], log_path: Path) -> int:
    """以 detach 方式啟動 ffmpeg，Claude session 或發起的 shell 結束後照常錄。"""
    log = open(log_path, "ab")
    kw = {"stdin": subprocess.DEVNULL, "stdout": log, "stderr": log}
    if platform.system() != "Windows":
        kw["start_new_session"] = True
        return subprocess.Popen(cmd, **kw).pid
    base = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    # 實測：Windows 的 SSH 連線（與部分終端機）把子程序放進 job，連線一結束就一起砍；要脫離 job 才活得下來
    try:
        return subprocess.Popen(cmd, creationflags=base | CREATE_BREAKAWAY_FROM_JOB, **kw).pid
    except OSError:
        return subprocess.Popen(cmd, creationflags=base, **kw).pid


def _alive(pid: int, name: str = "ffmpeg") -> bool:
    """PID 還在而且是指定程式（ffmpeg 或 python worker）：當機後 PID 可能被別的程序拿走，不能只看存不存在。"""
    if platform.system() == "Windows":
        r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], capture_output=True, text=True, errors="replace")
        return any(line.lower().startswith(f'"{name}') and f'"{pid}"' in line for line in r.stdout.splitlines())
    r = subprocess.run(["ps", "-p", str(pid), "-o", "comm="], capture_output=True, text=True, errors="replace")
    return r.returncode == 0 and name in r.stdout.lower()


def _child_exited(pid: int) -> bool:
    """本程序剛啟動的 ffmpeg 若已結束會變 zombie，ps／kill 仍查得到；先 reap 才判得出來。"""
    if platform.system() == "Windows":
        return False
    try:
        done, _ = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        return False
    return done == pid


def _kill(pid: int, system: str, name: str = "ffmpeg") -> None:
    if system == "Windows":
        # 不帶 /T：ffmpeg 沒有子程序，帶了只會擴大 PID 被重用時的誤殺範圍
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
        return
    import signal

    try:
        os.kill(pid, signal.SIGINT)  # 讓 ffmpeg 正常收尾、寫好最後一段的檔頭
        for _ in range(20):
            if not _alive(pid, name):
                return
            time.sleep(0.5)
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return  # 送訊號前後自己結束了


def _max_volume(path: Path) -> Optional[float]:
    import re

    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    m = re.search(r"max_volume: (-?[0-9.]+|-inf) dB", r.stderr)
    if not m:
        return None
    return float("-inf") if m.group(1) == "-inf" else float(m.group(1))


def _run_ffmpeg_concat(list_file: Path, out: Path) -> bool:
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        _err(r.stderr.strip())
    return r.returncode == 0 and out.exists()


def _read_state(out_dir: Path) -> Optional[dict]:
    f = out_dir / STATE_FILE
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_state(out_dir: Path, state: dict) -> None:
    _write_json(out_dir / STATE_FILE, state)


def _proc_name(state: dict) -> str:
    return "ffmpeg" if state.get("source", "mic") == "mic" else "python"


def _recording(state: Optional[dict]) -> bool:
    return bool(state) and state.get("stopped_at") is None and _alive(state["pid"], _proc_name(state))


def _system_state(out_dir: Path) -> Optional[dict]:
    f = out_dir / "system.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def _system_ready(system: str) -> Optional[Tuple[int, str]]:
    """system／both 的前置條件；不符回 (exit code, 訊息)。"""
    if system == "Windows":
        return 2, "Windows 的系統聲音擷取尚未驗證，暫不開放；請改用 --source mic"
    if sys.version_info[:2] < (3, 11) or not _importable("catap"):
        return 3, "系統聲音擷取需要 Python 3.11 以上與 catap；先跑 `doctor --record --source system` 看安裝方式"
    return None


def _segments(out_dir: Path) -> List[Path]:
    return sorted(out_dir.glob("seg-*.wav"))


# ---- 系統聲音（線上會議對方的聲音） ----

SYSTEM_PAD_TOLERANCE = 0.25  # 秒：擷取端正常延遲不算缺口
_STOP = threading.Event()
_now = time.monotonic


def padding_frames(elapsed_sec: float, frames_written: int, rate: int) -> int:
    return max(0, int(elapsed_sec * rate) - frames_written)


def is_heard(peak: float, threshold_db: float = -60.0) -> bool:
    return peak > 0 and 20 * math.log10(peak) > threshold_db


def _install_stop_handlers() -> None:
    import signal

    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), lambda *_: _STOP.set())


def _open_system_capture(on_chunk: Callable[[bytes], None]) -> Tuple[Callable[[], None], int]:
    """開始擷取系統輸出（float32 單聲道），回傳 (stop, 取樣率)。"""
    if platform.system() == "Darwin":
        import catap

        sess = catap.record_system_audio(mono=True, on_buffer=lambda buf: on_chunk(buf.data))
        sess.start()
        fmt = sess.stream_format
        if not (fmt.is_float and fmt.bits_per_sample == 32 and fmt.num_channels == 1):
            sess.stop()
            sess.close()
            raise RuntimeError(f"不支援的擷取格式：{fmt}")

        def stop() -> None:
            sess.stop()
            sess.close()

        return stop, int(fmt.sample_rate)
    # Windows：WASAPI loopback（尚未驗證，D9 由呼叫端擋下）
    import soundcard as sc

    rate = 48000
    loop = sc.get_microphone(id=str(sc.default_speaker().name), include_loopback=True)
    done = threading.Event()

    def run() -> None:
        with loop.recorder(samplerate=rate, channels=1) as rec:
            while not done.is_set():
                on_chunk(rec.record(numframes=rate // 10).astype("float32").tobytes())

    th = threading.Thread(target=run, daemon=True)
    th.start()

    def stop() -> None:
        done.set()
        th.join(timeout=2)

    return stop, rate


def _system_worker(out_dir: Path, source: str, mic_device: Optional[str], segment_sec: int) -> int:
    """擷取系統聲音寫進 ffmpeg；沒聲音時（Windows WASAPI 不送資料）依牆鐘補零，時間軸才不會縮短。"""
    import array

    _STOP.clear()
    _install_stop_handlers()
    lock = threading.Lock()
    st = {"written": 0, "heard_at": None, "proc": None, "early": []}

    def on_chunk(data: bytes) -> None:
        samples = array.array("f")
        samples.frombytes(data[: len(data) - len(data) % 4])
        peak = max(map(abs, samples), default=0.0)
        with lock:
            if is_heard(peak):
                st["heard_at"] = datetime.now().isoformat(timespec="seconds")
            if st["proc"] is None:
                st["early"].append(data)
            else:
                st["proc"].stdin.write(data)
            st["written"] += len(samples)

    def save() -> None:
        _write_json(out_dir / "system.json", {"heard_at": st["heard_at"], "ffmpeg_pid": st["proc"].pid})

    stop_capture, rate = _open_system_capture(on_chunk)
    cmd = build_pipe_record_cmd(platform.system(), source, mic_device, out_dir, segment_sec, rate)
    log = open(out_dir / "ffmpeg.log", "ab")
    t0 = _now()
    with lock:
        st["proc"] = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=log, stderr=log)
        for data in st["early"]:
            st["proc"].stdin.write(data)
        st["early"] = []
    save()
    last_save = _now()
    try:
        while not _STOP.is_set():
            with lock:
                pad = padding_frames(_now() - t0 - SYSTEM_PAD_TOLERANCE, st["written"], rate)
                if pad:
                    st["proc"].stdin.write(b"\0" * (pad * 4))
                    st["written"] += pad
            if _now() - last_save >= 5:
                save()
                last_save = _now()
            time.sleep(0.5)
    except (BrokenPipeError, OSError) as e:  # ffmpeg 先死了
        _err(f"ffmpeg 管線中斷：{e}")
    finally:
        stop_capture()
        with lock:
            try:
                st["proc"].stdin.close()
            except OSError:
                pass
        try:
            st["proc"].wait(timeout=10)
        except subprocess.TimeoutExpired:
            st["proc"].kill()
        save()
    return 0


def record_devices() -> int:
    system = platform.system()
    fmt = ["-f", "avfoundation", "-i", ""] if system == "Darwin" else ["-f", "dshow", "-i", "dummy"]
    r = subprocess.run(["ffmpeg", "-hide_banner", "-list_devices", "true", *fmt], capture_output=True, text=True, encoding="utf-8", errors="replace")
    devices = parse_devices(system, r.stderr)
    if not devices:
        _err("找不到音訊輸入裝置" + ("（Mac 可直接用預設裝置，不帶 --device）" if system == "Darwin" else ""))
        return 1
    for d in devices:
        print(d)
    return 0


def record_start(out_dir: Path, device: Optional[str], segment_sec: int, source: str = "mic") -> int:
    state = _read_state(out_dir)
    if _recording(state):
        _err(f"這個目錄已經在錄音（PID {state['pid']}）；要結束請用 `record stop`")
        return 2
    if _segments(out_dir) or (out_dir / "recording.wav").exists():
        # segment muxer 會從 seg-000 開始覆蓋，前一段錄音救不回來
        _err(f"這個目錄已有之前的錄音分段：{out_dir}\n請換一個新目錄再開錄；要合併舊的請用 `record stop`")
        return 2
    if not shutil.which("ffmpeg"):
        _err("找不到 ffmpeg，請先跑 `doctor --record` 看安裝方式")
        return 3
    system = platform.system()
    if source != "mic":
        blocked = _system_ready(system)
        if blocked:
            _err(blocked[1])
            return blocked[0]
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        cmd = build_record_cmd(system, device, out_dir, segment_sec)
    except ValueError as e:
        if source != "system":
            _err(str(e))
            return 2
    if source != "mic":
        # worker 自己再起 ffmpeg；log 分開，ffmpeg.log 留給 ffmpeg
        cmd = [sys.executable, str(Path(__file__).resolve()), "record", "_worker", "--out", str(out_dir),
               "--source", source, "--segment-sec", str(segment_sec)] + (["--device", device] if device else [])
    log_path = out_dir / ("ffmpeg.log" if source == "mic" else "worker.log")
    pid = _spawn(cmd, log_path)
    # 先寫狀態檔：就算接下來 session 中斷，新 session 也找得到這個 PID 來 stop
    state = {
        "pid": pid, "started_at": datetime.now().isoformat(timespec="seconds"), "system": system,
        "device": device or "default", "segment_sec": segment_sec, "source": source, "stopped_at": None,
    }
    _write_state(out_dir, state)
    time.sleep(3)
    first = out_dir / "seg-000.wav"
    name = _proc_name(state)
    if _child_exited(pid) or not _alive(pid, name) or not first.exists():
        if _alive(pid, name):
            _kill(pid, system, name)
        state["stopped_at"] = datetime.now().isoformat(timespec="seconds")
        _write_state(out_dir, state)
        logs = [f for f in (log_path, out_dir / "ffmpeg.log") if f.exists()]
        tail = "".join(dict.fromkeys(f.read_text(encoding="utf-8", errors="replace")[-800:] for f in logs))
        _err("錄音沒有啟動成功（裝置名稱或麥克風權限有誤？）\n" + tail)
        return 3
    # 系統聲音開錄時沒聲音是正常的（還沒人講話），只對麥克風做靜音檢查
    vol = _max_volume(first) if source != "system" else None
    if vol is not None and vol < SILENCE_DB:
        _err(f"警告：開頭 3 秒幾乎是靜音（max {vol} dB）——裝置可能選錯或沒有麥克風權限，確認後再繼續")
    print(f"錄音中（PID {pid}），分段寫在 {out_dir}；散會後用 `record stop --out \"{out_dir}\"` 結束")
    return 0


def record_status(out_dir: Path) -> int:
    state = _read_state(out_dir)
    segs = _segments(out_dir)
    if not _recording(state):
        print(f"沒有在錄音（分段 {len(segs)} 個）")
        return 1
    started = datetime.fromisoformat(state["started_at"])
    print(f"錄音中（PID {state['pid']}），已錄 {format_ts((datetime.now() - started).total_seconds())}，分段 {len(segs)} 個")
    if state.get("source", "mic") != "mic":
        heard = (_system_state(out_dir) or {}).get("heard_at")
        if heard:
            print(f"對方聲音：最近 {heard.replace('T', ' ')}")
        else:
            print("對方聲音：尚未收到（還沒人講話，或沒有授權系統錄音給啟動 Claude Code 的那個 App）")
    return 0


def record_stop(out_dir: Path) -> int:
    state = _read_state(out_dir)
    if not state:
        _err(f"找不到錄音狀態檔：{out_dir / STATE_FILE}")
        return 2
    system = state.get("system", platform.system())
    if _recording(state):
        _kill(state["pid"], system, _proc_name(state))
    if state.get("source", "mic") != "mic":
        # worker 被硬殺時它的 ffmpeg 會變孤兒，一併停掉
        fpid = (_system_state(out_dir) or {}).get("ffmpeg_pid")
        if fpid and _alive(fpid):
            _kill(fpid, system)
    segs = _segments(out_dir)
    if not segs:
        _err("沒有任何錄音分段，無法合併")
        return 4
    list_file = out_dir / "segments.txt"
    list_file.write_text(concat_list(segs), encoding="utf-8")
    out = out_dir / "recording.wav"
    if not _run_ffmpeg_concat(list_file, out):
        _err("合併分段失敗，原始分段仍保留在目錄內")
        return 3
    state["stopped_at"] = datetime.now().isoformat(timespec="seconds")
    _write_state(out_dir, state)
    seconds = max(out.stat().st_size - 44, 0) / 32000  # 16 kHz、單聲道、16-bit
    print(f"錄音已結束，合併為 {out}（約 {format_ts(seconds)}，{len(segs)} 段）")
    return 0


def cmd_record(args) -> int:
    out_dir = Path(args.out) if getattr(args, "out", None) else None
    if args.action == "devices":
        return record_devices()
    if args.action == "start":
        return record_start(out_dir, args.device, args.segment_sec, args.source)
    if args.action == "_worker":
        return _system_worker(out_dir, args.source, args.device, args.segment_sec)
    if args.action == "status":
        return record_status(out_dir)
    return record_stop(out_dir)


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
    doc = sub.add_parser("doctor", help="檢查 ffmpeg／轉錄套件／OpenCC 是否就緒")
    doc.add_argument("--record", action="store_true", help="一併檢查錄音需要的 ffmpeg")
    rec = sub.add_parser("record", help="背景錄音（麥克風／系統聲音）")
    rsub = rec.add_subparsers(dest="action", required=True)
    rsub.add_parser("devices", help="列出音訊輸入裝置")
    rs = rsub.add_parser("start", help="開始背景錄音")
    rs.add_argument("--out", required=True)
    rs.add_argument("--device")
    rs.add_argument("--segment-sec", type=int, default=300)
    rs.add_argument("--source", choices=["mic", "system", "both"], default="mic",
                    help="mic＝麥克風；system＝系統播放的聲音（線上會議對方）；both＝兩者混成一軌")
    rw = rsub.add_parser("_worker", help=argparse.SUPPRESS)
    rw.add_argument("--out", required=True)
    rw.add_argument("--device")
    rw.add_argument("--segment-sec", type=int, default=300)
    rw.add_argument("--source", choices=["system", "both"], required=True)
    for name in ("status", "stop"):
        rsub.add_parser(name).add_argument("--out", required=True)
    return p


def main(argv: List[str], backend_runner: Optional[BackendRunner] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    if args.cmd == "transcribe":
        return cmd_transcribe(args, backend_runner)
    if args.cmd == "record":
        return cmd_record(args)
    return cmd_doctor(args.record)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
