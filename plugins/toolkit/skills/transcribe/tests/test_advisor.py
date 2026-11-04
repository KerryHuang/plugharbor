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
