import array
import math
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import advisor as a  # noqa: E402

RATE = 16000


def tone(seconds, amp=8000, freq=440):
    n = int(RATE * seconds)
    return array.array("h", (int(amp * math.sin(2 * math.pi * freq * i / RATE)) for i in range(n))).tobytes()


def silence(seconds):
    return b"\0\0" * int(RATE * seconds)


def wav_header(extra_list_chunk=False):
    fmt = b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, RATE, RATE * 2, 2, 16)
    lst = b"LIST" + struct.pack("<I", 26) + b"INFOISFT" + struct.pack("<I", 14) + b"Lavf61.7.100\0\0" if extra_list_chunk else b""
    return b"RIFF" + struct.pack("<I", 0) + b"WAVE" + fmt + lst + b"data" + struct.pack("<I", 0)


# ---- wav_data_offset ----


def test_wav_data_offset_finds_data_chunk():
    h = wav_header()
    assert a.wav_data_offset(h) == len(h)
    h2 = wav_header(extra_list_chunk=True)
    assert a.wav_data_offset(h2) == len(h2)


def test_wav_data_offset_incomplete_header():
    assert a.wav_data_offset(wav_header()[:20]) is None


# ---- SegmentTail ----


def test_tail_reads_appended_bytes(tmp_path):
    seg = tmp_path / "seg-000.wav"
    seg.write_bytes(wav_header(True) + b"\x01\x00" * 10)
    tail = a.SegmentTail(tmp_path)
    assert tail.read_new() == b"\x01\x00" * 10
    assert tail.read_new() == b""
    with seg.open("ab") as f:
        f.write(b"\x02\x00" * 5 + b"\x03")  # 奇數位元組：半個 sample 先不讀
    assert tail.read_new() == b"\x02\x00" * 5
    with seg.open("ab") as f:
        f.write(b"\x00")
    assert tail.read_new() == b"\x03\x00"


def test_tail_switches_to_next_segment(tmp_path):
    (tmp_path / "seg-000.wav").write_bytes(wav_header() + b"\x01\x00" * 4)
    tail = a.SegmentTail(tmp_path)
    assert tail.read_new() == b"\x01\x00" * 4
    with (tmp_path / "seg-000.wav").open("ab") as f:
        f.write(b"\x02\x00" * 2)  # 換段前目前檔又寫了一點
    (tmp_path / "seg-001.wav").write_bytes(wav_header(True) + b"\x03\x00" * 3)
    assert tail.read_new() == b"\x02\x00" * 2 + b"\x03\x00" * 3


def test_tail_waits_for_first_segment(tmp_path):
    tail = a.SegmentTail(tmp_path)
    assert tail.read_new() == b""
    (tmp_path / "seg-000.wav").write_bytes(wav_header() + b"\x05\x00")
    assert tail.read_new() == b"\x05\x00"


# ---- Vad ----


def feed_all(vad, pcm, chunk=3200):
    out = []
    for i in range(0, len(pcm), chunk):
        out += vad.feed(pcm[i:i + chunk])
    return out


def test_vad_splits_on_silence():
    vad = a.Vad()
    utts = feed_all(vad, tone(0.5) + silence(1.0) + tone(0.5) + silence(1.0))
    assert len(utts) == 2
    for u in utts:
        assert 0.4 <= len(u) / 2 / RATE <= 1.6


def test_silence_yields_no_utterance():
    vad = a.Vad()
    assert feed_all(vad, silence(10)) == []


def test_vad_ignores_short_click():
    vad = a.Vad()
    assert feed_all(vad, tone(0.1) + silence(1.0)) == []


def test_vad_caps_long_utterance():
    vad = a.Vad()
    utts = feed_all(vad, tone(20) + silence(1.0))
    assert utts and len(utts[0]) / 2 / RATE <= 15.0
    assert sum(len(u) for u in utts) / 2 / RATE >= 19.0


# ---- 喚醒比對 ----


def test_wake_variants():
    assert a.match_wake("嘿，小小，你覺得呢？") == "你覺得呢"
    assert a.match_wake("黑小小 MP3368 做到哪了") == "MP3368 做到哪了"
    assert a.match_wake("Hey 小小 幫我查") == "幫我查"
    assert a.match_wake("hey,小小,幫我查") == "幫我查"


def test_wake_without_question_returns_empty():
    assert a.match_wake("嘿，小小。") == ""


def test_plain_xiaoxiao_not_wake():
    assert a.match_wake("這只是一個小小的問題") is None
    assert a.match_wake("這邊小小改一下") is None


def test_wake_mid_sentence():
    assert a.match_wake("好，那先這樣。嘿，小小，幫我查一下") == "幫我查一下"


def test_repeated_xiaoxiao_rejected():
    assert a.match_wake("小小小小小小小小") is None
    assert a.match_wake("嘿小小小小小小小小") is None


# ---- 播放遮蔽 ----


def test_mask_covers_tail_after_playback():
    m = a.PlaybackMask()
    m.add(100, 108)
    assert m.covers(109, 109.4) is True
    assert m.covers(110, 111) is False
    assert m.covers(98.0, 98.4) is False
    assert m.covers(98.6, 99) is True


# ---- 問 Claude ----

import json  # noqa: E402
import subprocess  # noqa: E402

MODE = {"name": "內部", "allowed_tools": ["Read", "Grep", "WebSearch"], "mcp_config": None,
        "model": "sonnet", "persona": "你是會議顧問小小。"}


def write_mode(tmp_path, **over):
    p = tmp_path / "mode.json"
    p.write_text(json.dumps({**MODE, **over}, ensure_ascii=False), encoding="utf-8")
    return p


def test_load_mode_ok(tmp_path):
    m = a.load_mode(write_mode(tmp_path))
    assert m["allowed_tools"] == ["Read", "Grep", "WebSearch"]


@pytest.mark.parametrize("tools", [["Read", "Write"], ["Edit"], ["NotebookEdit"], ["Bash"], ["Bash(*)"]])
def test_load_mode_rejects_write_tools(tmp_path, tools):
    with pytest.raises(ValueError):
        a.load_mode(write_mode(tmp_path, allowed_tools=tools))


def test_load_mode_allows_scoped_bash(tmp_path):
    a.load_mode(write_mode(tmp_path, allowed_tools=["Bash(python3 /x/customer_sql.py --slug abc:*)"]))


def test_load_mode_requires_fields(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"name": "x"}), encoding="utf-8")
    with pytest.raises(ValueError):
        a.load_mode(p)


def test_build_cmd_without_mcp():
    cmd = a.build_claude_cmd(MODE, "MP-3368 做到哪了", "[00:01:00] 我們在談排程")
    assert cmd[:2] == ["claude", "-p"]
    prompt = cmd[2]
    assert "你是會議顧問小小。" in prompt and "MP-3368 做到哪了" in prompt and "我們在談排程" in prompt
    assert "2～3 句" in prompt
    assert cmd[cmd.index("--model") + 1] == "sonnet"
    assert cmd[cmd.index("--allowedTools") + 1] == "Read,Grep,WebSearch"
    assert "--mcp-config" not in cmd and "--strict-mcp-config" not in cmd


def test_build_cmd_with_mcp_config():
    cmd = a.build_claude_cmd({**MODE, "mcp_config": "/x/mcp.json"}, "q", "")
    assert cmd[cmd.index("--mcp-config") + 1] == "/x/mcp.json"
    assert "--strict-mcp-config" in cmd


class FakeProc:
    """communicate 依假時鐘決定逾時：delay 秒後才有輸出。"""

    def __init__(self, delay=1.0, out="好的，這是回答。", code=0):
        self.delay, self.out, self.code = delay, out, code
        self.killed = False
        self.returncode = None
        self.kw = None

    def __call__(self, cmd, **kw):
        self.kw = kw
        return self

    def communicate(self, timeout=None):
        if self.killed:
            return "", ""
        if timeout is not None and self.delay > timeout:
            self.delay -= timeout
            raise subprocess.TimeoutExpired("claude", timeout)
        self.returncode = self.code
        return self.out, "boom" if self.code else ""

    def kill(self):
        self.killed = True


def test_fast_answer(monkeypatch):
    fp = FakeProc(delay=1.0)
    monkeypatch.setattr(a.subprocess, "Popen", fp)
    slow = []
    assert a.ask(MODE, "q", "", on_slow=lambda: slow.append(1)) == ("好的，這是回答。", True)
    assert slow == []
    assert fp.kw["stdin"] == subprocess.DEVNULL


def test_slow_answer_calls_on_slow_once(monkeypatch):
    monkeypatch.setattr(a.subprocess, "Popen", FakeProc(delay=10.0))
    slow = []
    text, ok = a.ask(MODE, "q", "", on_slow=lambda: slow.append(1))
    assert ok and slow == [1]


def test_timeout_returns_fallback(monkeypatch):
    fp = FakeProc(delay=99.0)
    monkeypatch.setattr(a.subprocess, "Popen", fp)
    assert a.ask(MODE, "q", "", timeout=30.0, on_slow=lambda: None) == (a.FALLBACK, False)
    assert fp.killed


def test_cli_error_returns_fallback(monkeypatch):
    monkeypatch.setattr(a.subprocess, "Popen", FakeProc(code=1))
    assert a.ask(MODE, "q", "", on_slow=lambda: None) == (a.FALLBACK, False)


def test_missing_cli_returns_fallback(monkeypatch):
    def boom(*a_, **k):
        raise FileNotFoundError("claude")

    monkeypatch.setattr(a.subprocess, "Popen", boom)
    assert a.ask(MODE, "q", "", on_slow=lambda: None) == (a.FALLBACK, False)


def test_ask_uses_mode_cwd(monkeypatch):
    fp = FakeProc()
    monkeypatch.setattr(a.subprocess, "Popen", fp)
    a.ask({**MODE, "cwd": "/work"}, "q", "", on_slow=lambda: None)
    assert fp.kw["cwd"] == "/work"
