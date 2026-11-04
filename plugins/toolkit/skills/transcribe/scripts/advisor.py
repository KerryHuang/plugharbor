#!/usr/bin/env python3
"""會議 AI 顧問「小小」：錄音中有人說「嘿，小小，……」時，用語音在會議裡回答。

追讀 transcribe.py 錄音正在寫入的 seg-NNN.wav（ffmpeg 以 flush_packets=1 逐封包寫盤），
能量式 VAD 切句 → Whisper → 比對喚醒詞 → `claude -p` → `say` 送進虛擬麥克風（預設 BlackHole 2ch）。
只支援 macOS。
"""
import array
import json
import math
import re
import struct
import subprocess
import sys
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
        "沒把握的事直接說會後確認，不要猜。\n\n"
        f"最近的會議逐字稿：\n{context}\n\n問題：{question}"
    )
    cmd = ["claude", "-p", prompt, "--model", mode["model"], "--allowedTools", ",".join(mode["allowed_tools"])]
    if mode.get("mcp_config"):
        cmd += ["--mcp-config", mode["mcp_config"], "--strict-mcp-config"]
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
