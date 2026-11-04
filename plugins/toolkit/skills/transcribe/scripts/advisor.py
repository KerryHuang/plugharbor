#!/usr/bin/env python3
"""會議 AI 顧問「小小」：錄音中有人說「嘿，小小，……」時，用語音在會議裡回答。

追讀 transcribe.py 錄音正在寫入的 seg-NNN.wav（ffmpeg 以 flush_packets=1 逐封包寫盤），
能量式 VAD 切句 → Whisper → 比對喚醒詞 → `claude -p` → `say` 送進虛擬麥克風（預設 BlackHole 2ch）。
只支援 macOS。
"""
import argparse
import array
import json
import math
import os
import platform
import re
import shutil
import struct
import tempfile
import subprocess
import sys
import time
import wave
from collections import deque
from pathlib import Path
from typing import Callable, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import transcribe as tr  # noqa: E402

RATE = 16000  # 錄音分段固定 16 kHz、單聲道、16-bit


# ---- 追讀錄音中的分段檔 ----


def wav_data_offset(header: bytes) -> Optional[int]:
    """回傳 data chunk 內容起點；header 還不完整回 None。"""
    if len(header) < 12 or header[:4] != b"RIFF" or header[8:12] != b"WAVE":
        return None
    pos = 12
    while pos + 8 <= len(header):
        cid, size = header[pos:pos + 4], struct.unpack("<I", header[pos + 4:pos + 8])[0]
        if cid == b"data":
            return pos + 8
        pos += 8 + size + (size & 1)
    return None


class SegmentTail:
    """依序讀 seg-NNN.wav 新增的 PCM；目前檔後面出現下一段時，讀完目前檔剩餘資料再切過去。"""

    def __init__(self, out_dir: Path):
        self.out_dir = Path(out_dir)
        self.index = 0
        self.pos: Optional[int] = None

    def _path(self, i: int) -> Path:
        return self.out_dir / f"seg-{i:03d}.wav"

    def _read_current(self) -> Optional[bytes]:
        path = self._path(self.index)
        if not path.exists():
            return None
        with path.open("rb") as f:
            if self.pos is None:
                off = wav_data_offset(f.read(4096))
                if off is None:
                    return b""
                self.pos = off
            f.seek(self.pos)
            data = f.read()
        data = data[: len(data) - (len(data) & 1)]
        self.pos += len(data)
        return data

    def seek_end(self) -> None:
        """跳到目前最新分段的檔尾：只讀之後新錄進來的聲音。"""
        nums = sorted(int(p.stem[4:]) for p in self.out_dir.glob("seg-*.wav") if p.stem[4:].isdigit())
        if not nums:
            return
        self.index = nums[-1]
        path = self._path(self.index)
        with path.open("rb") as f:
            off = wav_data_offset(f.read(4096))
        if off is None:
            self.pos = None
            return
        size = path.stat().st_size - off
        self.pos = off + size - (size & 1)

    def read_new(self) -> bytes:
        out = bytearray()
        while True:
            data = self._read_current()
            if data is None:
                break
            out += data
            if not self._path(self.index + 1).exists():
                break
            out += self._read_current() or b""  # 下一段已出現：目前檔不會再長，收尾後換段
            self.index += 1
            self.pos = None
        return bytes(out)


# ---- 能量式 VAD ----


class Vad:
    """以 frame 能量判斷有沒有人說話；靜音超過 end_silence_ms 算一句結束。
    短於 min_ms 的聲音（咳嗽、敲桌）丟掉，長於 max_ms 強制切段。"""

    def __init__(self, rate: int = RATE, frame_ms: int = 30, threshold_db: float = -45.0,
                 end_silence_ms: int = 700, min_ms: int = 400, max_ms: int = 15000, preroll_ms: int = 300):
        self.frame_bytes = rate * frame_ms // 1000 * 2
        self.frame_ms = frame_ms
        self.threshold_db = threshold_db
        self.end_silence_ms = end_silence_ms
        self.min_ms = min_ms
        self.max_ms = max_ms
        self.pending = b""
        self.preroll: deque = deque(maxlen=max(preroll_ms // frame_ms, 1))
        self.utt: Optional[bytearray] = None
        self.voiced_ms = 0
        self.silent_ms = 0

    def _db(self, frame: bytes) -> float:
        samples = array.array("h", frame)
        if not samples:
            return -120.0
        rms = math.sqrt(sum(s * s for s in samples) / len(samples))
        return 20 * math.log10(rms / 32768) if rms > 0 else -120.0

    def _finish(self, out: List[bytes]) -> None:
        if self.utt is not None and self.voiced_ms >= self.min_ms:
            out.append(bytes(self.utt))
        self.utt = None
        self.voiced_ms = self.silent_ms = 0

    def feed(self, pcm: bytes) -> List[bytes]:
        out: List[bytes] = []
        buf = self.pending + pcm
        n = len(buf) - len(buf) % self.frame_bytes
        self.pending = buf[n:]
        for i in range(0, n, self.frame_bytes):
            frame = buf[i:i + self.frame_bytes]
            voiced = self._db(frame) > self.threshold_db
            if self.utt is None:
                if voiced:
                    self.utt = bytearray(b"".join(self.preroll))
                    self.preroll.clear()
                    self.utt += frame
                    self.voiced_ms = self.frame_ms
                else:
                    self.preroll.append(frame)
                continue
            self.utt += frame
            if voiced:
                self.voiced_ms += self.frame_ms
                self.silent_ms = 0
            else:
                self.silent_ms += self.frame_ms
            if self.silent_ms >= self.end_silence_ms or len(self.utt) // 2 * 1000 // RATE >= self.max_ms:
                self._finish(out)
        return out


# ---- 喚醒比對 ----

# 「嘿」接在前一句後面時常被轉成「黑」；單獨的「小小」是口語（小小的問題），不算叫它
_WAKE = re.compile(r"(?:嘿|黑|hey)[\s，,、。.!！?？]*小小", re.IGNORECASE)
_EDGE = " \t\r\n，,、。.!！?？：:；;…"


def match_wake(text: str) -> Optional[str]:
    """命中「嘿，小小」回傳之後的問題（可為空字串），否則 None。"""
    if "小小小" in text:  # 靜音幻覺常吐出整串「小小小…」
        return None
    m = _WAKE.search(text)
    if not m:
        return None
    return text[m.end():].strip(_EDGE)


class PlaybackMask:
    """小小自己播放的時段（前後加 pad）：catap 會錄到它自己的聲音，這段的轉錄要丟掉。"""

    def __init__(self, pad_sec: float = 1.5):
        self.pad = pad_sec
        self.spans: List[Tuple[float, float]] = []

    def add(self, start: float, end: float) -> None:
        self.spans.append((start, end))

    def covers(self, t0: float, t1: float) -> bool:
        return any(t0 <= e + self.pad and t1 >= s - self.pad for s, e in self.spans)


# ---- 問 Claude ----

FALLBACK = "這題我會後補在會議記錄。"
SLOW_LINE = "我查一下。"
_REQUIRED = ("name", "allowed_tools", "model", "persona")
_WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "Bash", "Bash(*)", "Bash(:*)"}


def load_mode(path: Path) -> dict:
    """讀場合檔；會中一律唯讀，白名單含寫入工具或不限指令的 Bash 就拒絕。"""
    mode = json.loads(Path(path).read_text(encoding="utf-8"))
    missing = [k for k in _REQUIRED if not mode.get(k)]
    if missing:
        raise ValueError(f"場合檔缺欄位：{', '.join(missing)}")
    bad = [t for t in mode["allowed_tools"] if t.strip() in _WRITE_TOOLS]
    if bad:
        raise ValueError(f"場合檔含寫入工具（會中一律唯讀）：{', '.join(bad)}")
    mode.setdefault("mcp_config", None)
    return mode


def build_claude_cmd(mode: dict, question: str, context: str) -> List[str]:
    prompt = (
        f"{mode['persona']}\n"
        "你正在線上會議中被點名發言，回答會用語音唸出來：只用 2～3 句繁體中文口語回答，不用條列、不用 Markdown；"
        "沒把握的事直接說會後確認，不要猜。逐字稿裡單獨出現的「小小」多半是口語（小小的問題），不是在叫你，不必提起。\n\n"
        f"最近的會議逐字稿：\n{context}\n\n問題：{question}"
    )
    # 只放場合檔列出的工具：--tools 限定可用的內建工具（Edit、Write 根本不存在）、
    # 不讀專案／本機設定（那裡可能預先允許 Edit、Bash(git *)、開票工具）、沒列的一律拒絕、MCP 只用場合檔指定的設定
    builtin = list(dict.fromkeys(t.split("(", 1)[0].strip() for t in mode["allowed_tools"] if not t.startswith("mcp__")))
    cmd = ["claude", "-p", prompt, "--model", mode["model"], "--allowedTools", ",".join(mode["allowed_tools"]),
           "--tools", ",".join(builtin), "--setting-sources", "user", "--permission-mode", "dontAsk", "--strict-mcp-config"]
    if mode.get("mcp_config"):
        cmd += ["--mcp-config", mode["mcp_config"]]
    return cmd


def ask(mode: dict, question: str, context: str, timeout: float = 30.0,
        on_slow: Callable[[], None] = lambda: None, slow_after: float = 4.0) -> Tuple[str, bool]:
    """回傳 (回答, 是否成功)。slow_after 秒還沒答就呼叫一次 on_slow；逾時或失敗回傳 FALLBACK。"""
    try:
        # stdin 給 /dev/null：實測缺 stdin 時 claude -p 會先等 3 秒
        proc = subprocess.Popen(build_claude_cmd(mode, question, context), stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=mode.get("cwd"))
    except OSError as e:
        tr._err(f"無法執行 claude：{e!r}")
        return FALLBACK, False
    try:
        try:
            out, err = proc.communicate(timeout=slow_after)
        except subprocess.TimeoutExpired:
            on_slow()
            out, err = proc.communicate(timeout=max(timeout - slow_after, 0.1))
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        tr._err(f"claude 超過 {timeout:.0f} 秒沒有回答")
        return FALLBACK, False
    if proc.returncode != 0 or not out.strip():
        tr._err(f"claude 回答失敗（exit {proc.returncode}）：{(err or '').strip()[-300:]}")
        return FALLBACK, False
    return out.strip(), True


# ---- 說話 ----

VOICE = "Meijia"
DEFAULT_DEVICE = "BlackHole 2ch"


def speak(text: str, device: str) -> Tuple[float, float]:
    """用 macOS `say` 唸到指定輸出裝置（虛擬麥克風），回傳播放起訖時間（epoch 秒）。"""
    start = time.time()
    r = subprocess.run(["say", "-v", VOICE, "-a", device, text], capture_output=True, text=True)
    if r.returncode != 0:
        tr._err(f"say 失敗（exit {r.returncode}）：{r.stderr.strip()[-300:]}")
    return start, time.time()


# ---- 主迴圈 ----

STATE = "advisor.json"
LOG_MD = "advisor.md"
UTT_WAV = "advisor-utt.wav"
WAKE_FOLLOWUP_SEC = 8.0  # 只說「嘿，小小」後，這麼久內的下一句才算問題
FEED_CHUNK = RATE // 10 * 2  # VAD 每次餵 0.1 秒：句子的時間推估精度


def _hms(t: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(t))


def _append_md(out_dir: Path, t: float, lines: List[str]) -> None:
    with (out_dir / LOG_MD).open("a", encoding="utf-8") as f:
        f.write(f"### {_hms(t)}\n" + "".join(line + "\n" for line in lines) + "\n")


def _write_utt(path: Path, pcm: bytes) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm)


def run_loop(out_dir: Path, mode: dict, runner, ask_fn=ask, speak_fn=speak, clock: Callable[[], float] = time.time,
             device: str = DEFAULT_DEVICE, prompt: Optional[str] = None, context_min: float = 5.0,
             model: str = "large-v3-turbo", language: str = "zh", poll_sec: float = 0.5, from_start: bool = False) -> int:
    """追讀錄音、被叫到就回答；錄音停止且分段讀完後結束。"""
    out_dir = Path(out_dir)
    conv = tr._converter()
    st = {"pid": os.getpid(), "mode": mode["name"], "started_at": clock(), "answered": 0, "pending": 0, "finished": False}
    tr._write_json(out_dir / STATE, st)
    tail, vad, mask = SegmentTail(out_dir), Vad(), PlaybackMask()
    if not from_start:
        tail.seek_end()  # 開錄後才開小小：之前錄到的「嘿，小小」不補答
    recent: deque = deque()  # (時間, 句子)：給 claude 的最近 N 分鐘逐字稿
    busy_until = 0.0  # 上一題回答播完的時間；之前的喚醒算「思考中」
    waiting_question = False  # 只說了「嘿，小小」：下一句就是問題
    wake_at = 0.0

    def say_line(text: str) -> None:
        s, e = speak_fn(text, device)
        mask.add(s, e)

    def answer(question: str, t: float) -> float:
        cutoff = clock() - context_min * 60
        while recent and recent[0][0] < cutoff:
            recent.popleft()
        context = "\n".join(f"[{_hms(ts)}] {line}" for ts, line in recent)
        text, ok = ask_fn(mode, question, context, on_slow=lambda: say_line(SLOW_LINE))
        s, e = speak_fn(text, device)
        mask.add(s, e)
        tr._err(f"[{_hms(t)}] 句尾後 {s - t:.1f} 秒開口：{question}")
        st["answered" if ok else "pending"] += 1
        tr._write_json(out_dir / STATE, st)
        _append_md(out_dir, t, [f"- 問：{question}", f"- 小小：{text}"] + ([] if ok else ["<!-- advisor pending -->"]))
        return e

    def handle(utt: bytes, t0: float, t1: float) -> None:
        nonlocal busy_until, waiting_question, wake_at
        if mask.covers(t0, t1):
            return  # 小小自己的聲音：不轉錄、不比對
        wav = out_dir / UTT_WAV
        _write_utt(wav, utt)
        try:
            text = "".join(seg_text for _, seg_text in runner(str(wav), model, prompt, language))
        except Exception as e:  # 單句失敗不拖垮整場
            tr._err(f"轉錄失敗：{e!r}")
            return
        finally:
            wav.unlink(missing_ok=True)
        text = tr._zh_tw(conv, text).strip()
        if not text:
            return
        question = match_wake(text)
        if waiting_question and t0 - wake_at > WAKE_FOLLOWUP_SEC:
            waiting_question = False  # 叫了沒下文：之後的話不當問題
        if question is not None and t0 < busy_until:
            _append_md(out_dir, t1, [f"- （思考中，略過：{text}）"])
            return
        if waiting_question and question is None:
            waiting_question = False
            busy_until = answer(text.strip(_EDGE), t1)
            return
        if question is None:
            recent.append((t1, text))
            return
        if not question:
            waiting_question, wake_at = True, t1
            return
        waiting_question = False
        busy_until = answer(question, t1)

    while True:
        active = tr._capture_active(out_dir)  # 先看狀態再讀：判定停止時，最後的資料一定已讀進來
        pcm = tail.read_new()
        if pcm:
            now = clock()
            for i in range(0, len(pcm), FEED_CHUNK):
                end = min(i + FEED_CHUNK, len(pcm))
                for utt in vad.feed(pcm[i:end]):
                    # 以讀到這批資料的時間回推：這批結尾約等於「現在」
                    t1 = now - (len(pcm) - end) / 2 / RATE
                    handle(utt, t1 - len(utt) / 2 / RATE, t1)
            continue
        if not active:
            st["finished"] = True
            tr._write_json(out_dir / STATE, st)
            return 0
        time.sleep(poll_sec)


# ---- 啟動／狀態／停止 ----


def _read_advisor(out_dir: Path) -> Optional[dict]:
    f = out_dir / STATE
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def _running(st: Optional[dict]) -> bool:
    return bool(st) and not st.get("finished") and tr._alive(st.get("pid", 0), "python")


def advisor_start(out_dir: Path, mode_file: str, device: str, context_min: float, prompt_file: Optional[str],
                  model: str, language: str) -> int:
    rec = tr._read_state(out_dir)
    if not rec or not tr._capture_active(out_dir):
        tr._err(f"這個目錄不在錄音中：先用 `record start --source both --out \"{out_dir}\"` 開錄")
        return 2
    if rec.get("source", "mic") == "mic":
        tr._err("錄音來源只有麥克風，小小聽不到對方：請用 `--source both` 重新開錄")
        return 2
    try:
        load_mode(Path(mode_file))
    except (OSError, ValueError) as e:
        tr._err(f"場合檔不能用：{e}")
        return 2
    if prompt_file and "小小" in Path(prompt_file).read_text(encoding="utf-8"):
        tr._err("術語提示含「小小」：Whisper 會因此吐出整串「小小小」，請從術語檔拿掉")
        return 2
    st = _read_advisor(out_dir)
    if _running(st):
        tr._err(f"這個目錄的小小已在執行（PID {st['pid']}）")
        return 2
    cmd = [sys.executable, str(Path(__file__).resolve()), "_run", "--out", str(out_dir), "--mode-file",
           str(Path(mode_file).resolve()), "--device", device, "--context-min", str(context_min),
           "--model", model, "--language", language]
    if prompt_file:
        cmd += ["--prompt-file", str(Path(prompt_file).resolve())]
    log = out_dir / "advisor.log"
    pid = tr._spawn(cmd, log)
    for _ in range(10):  # 5 秒內確認起來（寫出自己的 advisor.json）
        st = _read_advisor(out_dir)
        if st and st.get("pid") == pid:
            break
        if tr._child_exited(pid) or not tr._alive(pid, "python"):
            tail = log.read_text(encoding="utf-8", errors="replace")[-800:] if log.exists() else ""
            tr._err("小小沒有啟動成功\n" + tail)
            return 3
        time.sleep(0.5)
    print(f"小小已上線（PID {pid}）：說「嘿，小小，……」叫它；發言記在 {out_dir / LOG_MD}")
    return 0


def advisor_status(out_dir: Path) -> int:
    st = _read_advisor(out_dir)
    if not st:
        print("小小：沒有啟動")
        return 0
    state = "執行中" if _running(st) else ("已結束" if st.get("finished") else "已中止（原因看 advisor.log）")
    print(f"小小：{state}，已回答 {st.get('answered', 0)} 題、待補 {st.get('pending', 0)} 題")
    return 0


def advisor_stop(out_dir: Path) -> int:
    st = _read_advisor(out_dir)
    if not _running(st):
        print("小小沒有在執行")
        return 0
    tr._kill(st["pid"], platform.system(), "python")
    st["finished"] = True
    tr._write_json(out_dir / STATE, st)
    print(f"小小已下線（已回答 {st.get('answered', 0)} 題、待補 {st.get('pending', 0)} 題）")
    return 0


# ---- 開會前自我檢查 ----

MEETING_MIC = "小小麥克風"
LOOPBACK_DB = -30.0
AGGREGATE_STEPS = (
    "建立聚合裝置：開「音訊MIDI設定」（應用程式 → 工具程式）→ 左下「＋」→「建立聚合裝置」→ 改名「{name}」→ "
    "先勾實體麥克風、再勾 BlackHole 2ch → 「時脈來源」選實體麥克風；會議軟體的麥克風改選「{name}」，喇叭維持原本的輸出"
)


def _has_voice(voice: str) -> bool:
    r = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, errors="replace")
    return any(line.split()[:1] == [voice] for line in r.stdout.splitlines())


def _list_input_devices() -> List[str]:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-list_devices", "true", "-f", "avfoundation", "-i", ""],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return tr.parse_devices("Darwin", r.stderr)


def _probe_volume(device: str, seconds: float, say_text: Optional[str] = None) -> Optional[float]:
    """從輸入裝置錄 seconds 秒回傳 max_volume（dB）；有 say_text 時同時把它唸到同名輸出裝置（迴路測試）。"""
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "probe.wav"
        proc = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "avfoundation",
                                 "-i", f":{device}", "-t", str(seconds), str(wav)],
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if say_text:
            time.sleep(0.8)  # 等 ffmpeg 開好裝置
            subprocess.run(["say", "-v", VOICE, "-a", device, say_text], capture_output=True)
        try:
            proc.wait(timeout=seconds + 10)
        except subprocess.TimeoutExpired:
            proc.kill()
            return None
        return tr._max_volume(wav) if wav.exists() else None


def cmd_doctor(device: str, meeting_mic: str) -> int:
    checks: List[Tuple[str, bool, str]] = [
        (f"say 中文聲音 {VOICE}", _has_voice(VOICE), f"系統設定 → 輔助使用 → 朗讀內容 → 系統聲音 → 管理聲音，下載「{VOICE}」"),
        ("claude CLI", shutil.which("claude") is not None, "安裝 Claude Code，並確認 `claude` 在 PATH"),
        ("ffmpeg", shutil.which("ffmpeg") is not None, "brew install ffmpeg"),
    ]
    devices = _list_input_devices() if checks[2][1] else []
    has_dev = device in devices
    checks.append((f"虛擬麥克風「{device}」", has_dev, "brew install --cask blackhole-2ch，裝完重啟音訊服務（sudo killall coreaudiod）"))
    checks.append((f"聚合裝置「{meeting_mic}」", meeting_mic in devices, AGGREGATE_STEPS.format(name=meeting_mic)))
    if has_dev:
        v = _probe_volume(device, 4, "小小測試")
        checks.append((f"迴路測試：唸到「{device}」錄得到（{v} dB，需 > {LOOPBACK_DB:.0f}）", v is not None and v > LOOPBACK_DB,
                       f"確認 say 能輸出到「{device}」；剛裝 BlackHole 要先重啟音訊服務"))
    v = _probe_volume("default", 2)
    checks.append((f"實體麥克風有聲音（{v} dB，需 > {tr.SILENCE_DB:.0f}）", v is not None and v > tr.SILENCE_DB,
                   "系統設定 → 隱私權與安全性 → 麥克風，允許目前的終端機；並確認系統預設輸入是實體麥克風"))
    checks += tr.check_system_env()
    ok = True
    for name, ready, hint in checks:
        print(f"{'OK ' if ready else 'NG '} {name}" + ("" if ready else f"　→ {hint}"))
        ok = ok and ready
    print(f"！ {tr.SYSTEM_AUDIO_PERMISSION}")
    return 0 if ok else 1


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="advisor.py", description="會議 AI 顧問「小小」")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("start", "_run"):
        sp = sub.add_parser(name)
        sp.add_argument("--out", required=True)
        sp.add_argument("--mode-file", required=True)
        sp.add_argument("--device", default=DEFAULT_DEVICE)
        sp.add_argument("--context-min", type=float, default=5.0)
        sp.add_argument("--prompt-file")
        sp.add_argument("--model", default="large-v3-turbo")
        sp.add_argument("--language", default="zh")
    for name in ("status", "stop"):
        sub.add_parser(name).add_argument("--out", required=True)
    dp = sub.add_parser("doctor")
    dp.add_argument("--device", default=DEFAULT_DEVICE)
    dp.add_argument("--meeting-mic", default=MEETING_MIC)
    args = p.parse_args(argv)
    if platform.system() != "Darwin":
        tr._err("小小目前只支援 macOS")
        return 2
    if args.cmd == "doctor":
        return cmd_doctor(args.device, args.meeting_mic)
    out_dir = Path(args.out)
    if args.cmd == "status":
        return advisor_status(out_dir)
    if args.cmd == "stop":
        return advisor_stop(out_dir)
    if args.cmd == "start":
        return advisor_start(out_dir, args.mode_file, args.device, args.context_min, args.prompt_file, args.model, args.language)
    prompt = Path(args.prompt_file).read_text(encoding="utf-8").strip() if args.prompt_file else None
    runner = tr._resolve_runner(tr.pick_backend(platform.system(), platform.machine()))
    try:
        return run_loop(out_dir, load_mode(Path(args.mode_file)), runner, device=args.device, prompt=prompt,
                        context_min=args.context_min, model=args.model, language=args.language)
    except KeyboardInterrupt:  # `stop` 送 SIGINT：正常下線，不留 traceback
        return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):  # 與 transcribe.py 一致：輸出一律 UTF-8
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    sys.exit(main())
