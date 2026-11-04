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
    cmd = a.build_claude_cmd(MODE, "ABC-123 做到哪了", "[00:01:00] 我們在談排程")
    assert cmd[:2] == ["claude", "-p"]
    prompt = cmd[2]
    assert "你是會議顧問小小。" in prompt and "ABC-123 做到哪了" in prompt and "我們在談排程" in prompt
    assert "2～3 句" in prompt
    assert cmd[cmd.index("--model") + 1] == "sonnet"
    assert cmd[cmd.index("--allowedTools") + 1] == "Read,Grep,WebSearch"
    # 沒給 MCP 設定＝完全不載入 MCP（不吃使用者或專案設定的 server）
    assert "--mcp-config" not in cmd and "--strict-mcp-config" in cmd


def test_build_cmd_locks_down_tools_and_settings():
    """專案設定可能預先允許 Edit、Bash(git *)、開票工具：會中只能有場合檔列的工具。"""
    cmd = a.build_claude_cmd({**MODE, "allowed_tools": ["Read", "Bash(python3 /x/q.py --slug a:*)", "mcp__s__read"]}, "q", "")
    assert cmd[cmd.index("--tools") + 1] == "Read,Bash"
    assert cmd[cmd.index("--setting-sources") + 1] == "user"
    assert cmd[cmd.index("--permission-mode") + 1] == "dontAsk"


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


# ---- 主迴圈 ----

import wave  # noqa: E402


def write_seg(d, i, pcm):
    (d / f"seg-{i:03d}.wav").write_bytes(wav_header() + pcm)


@pytest.fixture
def loop(tmp_path, monkeypatch):
    """假環境：錄音已寫完（不在錄）、runner 依呼叫順序回文字、ask／speak 記錄呼叫。"""
    env = {"dir": tmp_path / "會議", "texts": [], "durations": [], "asked": [], "spoken": [], "now": 1000.0,
           "answer": ("這是小小的回答。", True), "speak_span": None}
    env["dir"].mkdir()
    monkeypatch.setattr(a.tr, "_capture_active", lambda d: False)
    monkeypatch.setattr(a.time, "sleep", lambda s: None)

    def runner(audio, model, prompt, language):
        with wave.open(audio) as w:
            env["durations"].append(w.getnframes() / w.getframerate())
        text = env["texts"].pop(0) if env["texts"] else "（雜音）"
        return [(0.0, text)]

    def ask_fn(mode, question, context, on_slow=lambda: None, **kw):
        env["asked"].append((question, context))
        return env["answer"]

    def speak_fn(text, device):
        env["spoken"].append(text)
        return env["speak_span"] or (env["now"], env["now"] + 3)

    env["run"] = lambda from_start=True: a.run_loop(env["dir"], MODE, runner, ask_fn=ask_fn, speak_fn=speak_fn,
                                                   clock=lambda: env["now"], device="BlackHole 2ch", from_start=from_start)
    env["md"] = lambda: (env["dir"] / "advisor.md").read_text(encoding="utf-8")
    env["state"] = lambda: json.loads((env["dir"] / "advisor.json").read_text(encoding="utf-8"))
    return env


def utts(*secs):
    pcm = b""
    for s in secs:
        pcm += tone(s) + silence(1.0)
    return pcm


def test_wake_triggers_answer_and_writes_advisor_md(loop):
    write_seg(loop["dir"], 0, utts(1.0, 1.0))
    loop["texts"] = ["我們在談換模時間", "嘿，小小，你覺得呢？"]
    assert loop["run"]() == 0
    assert loop["asked"][0][0] == "你覺得呢"
    assert "我們在談換模時間" in loop["asked"][0][1]
    assert loop["spoken"] == ["這是小小的回答。"]
    md = loop["md"]()
    assert "- 問：你覺得呢" in md and "- 小小：這是小小的回答。" in md
    assert loop["state"]()["answered"] == 1


def test_no_wake_no_answer(loop):
    write_seg(loop["dir"], 0, utts(1.0))
    loop["texts"] = ["這只是一個小小的問題"]
    assert loop["run"]() == 0
    assert loop["asked"] == [] and loop["spoken"] == []


def test_masked_sentence_not_in_context(loop):
    write_seg(loop["dir"], 0, utts(1.0, 1.0, 1.0))
    loop["texts"] = ["嘿，小小，第一題", "這句是小小自己的聲音", "嘿，小小，第二題"]
    # 第一次回答的播放時段蓋住第二句（所有句子的推估時間都落在 now 之前約 6 秒內）
    spans = [(990.0, 997.6), (2000.0, 2001.0)]
    loop["speak_span"] = None

    def speak_fn_spans(text, device):
        loop["spoken"].append(text)
        return spans.pop(0)

    r = a.run_loop(loop["dir"], MODE, lambda *x: [(0.0, loop["texts"].pop(0))],
                   ask_fn=lambda m, q, c, on_slow=None, **k: loop["asked"].append((q, c)) or ("答", True),
                   speak_fn=speak_fn_spans, clock=lambda: loop["now"], device="X", from_start=True)
    assert r == 0
    assert [q for q, _ in loop["asked"]] == ["第一題"]  # 第三句也落在遮蔽／思考區間內
    assert all("小小自己的聲音" not in c for _, c in loop["asked"])


def test_busy_wake_is_ignored_and_logged(loop):
    write_seg(loop["dir"], 0, utts(1.0, 1.0))
    loop["texts"] = ["嘿，小小，第一題", "嘿，小小，第二題"]
    loop["speak_span"] = (2000.0, 2001.0)  # 播放在很久之後：第二句落在「思考中」
    assert loop["run"]() == 0
    assert [q for q, _ in loop["asked"]] == ["第一題"]
    assert "思考中，略過：嘿，小小，第二題" in loop["md"]()


def test_empty_question_merges_next_sentence(loop):
    write_seg(loop["dir"], 0, utts(1.0, 1.0))
    loop["texts"] = ["嘿，小小。", "ABC-123 做到哪了"]
    assert loop["run"]() == 0
    assert loop["asked"][0][0] == "ABC-123 做到哪了"


def test_fallback_marks_pending(loop):
    write_seg(loop["dir"], 0, utts(1.0))
    loop["texts"] = ["嘿，小小，查一下"]
    loop["answer"] = (a.FALLBACK, False)
    assert loop["run"]() == 0
    assert "<!-- advisor pending -->" in loop["md"]()
    st = loop["state"]()
    assert st["pending"] == 1 and st["answered"] == 0 and st["finished"] is True


def test_utterance_spans_segment_rollover(loop):
    pcm = utts(1.2)
    cut = 19200  # 0.6 秒處：切在那句話的聲音中間
    write_seg(loop["dir"], 0, pcm[:cut])
    write_seg(loop["dir"], 1, pcm[cut:])
    loop["texts"] = ["一句話"]
    assert loop["run"]() == 0
    assert len(loop["durations"]) == 1 and loop["durations"][0] >= 1.1


def test_loop_exits_after_recording_stopped(loop, monkeypatch):
    write_seg(loop["dir"], 0, utts(1.0))
    calls = {"n": 0}

    def active(d):
        calls["n"] += 1
        return calls["n"] < 3

    monkeypatch.setattr(a.tr, "_capture_active", active)
    loop["texts"] = ["普通的一句話"]
    assert loop["run"]() == 0
    assert calls["n"] >= 3 and loop["state"]()["finished"] is True


# ---- 生命週期 ----


@pytest.fixture
def life(tmp_path, monkeypatch):
    env = {"dir": tmp_path / "會議", "spawned": [], "alive": True}
    env["dir"].mkdir()
    monkeypatch.setattr(a.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(a.tr, "_capture_active", lambda d: True)
    monkeypatch.setattr(a.tr, "_alive", lambda pid, name="ffmpeg": env["alive"])
    monkeypatch.setattr(a.tr, "_child_exited", lambda pid: False)
    monkeypatch.setattr(a.time, "sleep", lambda s: None)

    def spawn(cmd, log):
        env["spawned"].append(cmd)
        (env["dir"] / "advisor.json").write_text(json.dumps({"pid": 555, "finished": False}), encoding="utf-8")
        return 555

    monkeypatch.setattr(a.tr, "_spawn", spawn)
    env["mode"] = write_mode(tmp_path)
    return env


def rec_state(d, source):
    a.tr._write_state(d, {"pid": 1, "source": source, "stopped_at": None})


def test_start_spawns_runner(life):
    rec_state(life["dir"], "both")
    assert a.main(["start", "--out", str(life["dir"]), "--mode-file", str(life["mode"])]) == 0
    cmd = life["spawned"][0]
    assert "_run" in cmd and cmd[cmd.index("--device") + 1] == "BlackHole 2ch"


def test_start_refuses_mic_only_source(life, capsys):
    rec_state(life["dir"], "mic")
    assert a.main(["start", "--out", str(life["dir"]), "--mode-file", str(life["mode"])]) == 2
    assert life["spawned"] == []


def test_start_refuses_without_recording(life, monkeypatch):
    monkeypatch.setattr(a.tr, "_capture_active", lambda d: False)
    rec_state(life["dir"], "both")
    assert a.main(["start", "--out", str(life["dir"]), "--mode-file", str(life["mode"])]) == 2


def test_start_refuses_duplicate(life):
    rec_state(life["dir"], "both")
    (life["dir"] / "advisor.json").write_text(json.dumps({"pid": 9, "finished": False}), encoding="utf-8")
    assert a.main(["start", "--out", str(life["dir"]), "--mode-file", str(life["mode"])]) == 2
    assert life["spawned"] == []


def test_start_refuses_bad_mode(life, tmp_path):
    rec_state(life["dir"], "both")
    bad = write_mode(tmp_path, allowed_tools=["Write"])
    assert a.main(["start", "--out", str(life["dir"]), "--mode-file", str(bad)]) == 2


def test_start_refuses_prompt_with_wake_word(life, tmp_path):
    rec_state(life["dir"], "both")
    g = tmp_path / "g.txt"
    g.write_text("嘿，小小，你好。", encoding="utf-8")
    assert a.main(["start", "--out", str(life["dir"]), "--mode-file", str(life["mode"]), "--prompt-file", str(g)]) == 2


def test_start_reports_dead_child(life, monkeypatch, capsys):
    rec_state(life["dir"], "both")
    monkeypatch.setattr(a.tr, "_spawn", lambda cmd, log: (log.write_text("Traceback: boom", encoding="utf-8"), 777)[1])
    monkeypatch.setattr(a.tr, "_child_exited", lambda pid: True)
    assert a.main(["start", "--out", str(life["dir"]), "--mode-file", str(life["mode"])]) == 3
    assert "boom" in capsys.readouterr().err


def test_windows_not_supported(life, monkeypatch):
    monkeypatch.setattr(a.platform, "system", lambda: "Windows")
    assert a.main(["status", "--out", str(life["dir"])]) == 2


# ---- doctor ----


@pytest.fixture
def doc(monkeypatch):
    env = {"devices": ["MacBook Air的麥克風", "BlackHole 2ch", "小小麥克風"], "vol": {"BlackHole 2ch": -12.0, "default": -40.0}}
    monkeypatch.setattr(a.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(a, "_has_voice", lambda v: True)
    monkeypatch.setattr(a.shutil, "which", lambda n: f"/usr/bin/{n}")
    monkeypatch.setattr(a, "_list_input_devices", lambda: env["devices"])
    monkeypatch.setattr(a, "_probe_volume", lambda device, seconds, say_text=None: env["vol"].get(device))
    monkeypatch.setattr(a.tr, "check_system_env", lambda: [("catap", True, "")])
    return env


def test_doctor_all_ok(doc, capsys):
    assert a.main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "NG" not in out and "OK" in out


def test_doctor_missing_aggregate_prints_steps(doc, capsys):
    doc["devices"] = ["MacBook Air的麥克風", "BlackHole 2ch"]
    assert a.main(["doctor"]) == 1
    out = capsys.readouterr().out
    assert "NG" in out and "小小麥克風" in out and "音訊MIDI設定" in out


def test_doctor_loopback_silent_fails(doc, capsys):
    doc["vol"]["BlackHole 2ch"] = -91.0
    assert a.main(["doctor"]) == 1
    assert "BlackHole 2ch" in capsys.readouterr().out


def test_doctor_silent_mic_fails(doc, capsys):
    doc["vol"]["default"] = float("-inf")
    assert a.main(["doctor"]) == 1
    assert "麥克風" in capsys.readouterr().out


def test_doctor_missing_claude_fails(doc, monkeypatch, capsys):
    monkeypatch.setattr(a.shutil, "which", lambda n: None if n == "claude" else f"/usr/bin/{n}")
    assert a.main(["doctor"]) == 1


def test_answer_logs_latency(loop, capsys):
    write_seg(loop["dir"], 0, utts(1.0))
    loop["texts"] = ["嘿，小小，現在幾點"]
    loop["speak_span"] = (1004.0, 1006.0)  # 句尾在 999.7（聲音 1 秒＋靜音 0.7 秒後切句，之後還有 0.3 秒）
    assert loop["run"]() == 0
    import re
    m = re.search(r"句尾後 ([\d.]+) 秒開口：現在幾點", capsys.readouterr().err)
    assert m and abs(float(m.group(1)) - 4.3) <= 0.2  # 30 ms frame、0.1 秒餵入的量化誤差


def test_prompt_says_casual_mentions_are_not_calls():
    prompt = a.build_claude_cmd(MODE, "Q", "ctx")[2]
    assert "不是在叫你" in prompt


def test_run_exits_cleanly_on_stop_signal(tmp_path, monkeypatch):
    monkeypatch.setattr(a.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(a.tr, "_resolve_runner", lambda name: None)

    def interrupted(*args, **kw):
        raise KeyboardInterrupt

    monkeypatch.setattr(a, "run_loop", interrupted)
    assert a.main(["_run", "--out", str(tmp_path), "--mode-file", str(write_mode(tmp_path))]) == 0


def test_start_skips_audio_recorded_before_advisor(loop):
    """開錄後才開小小：之前錄到的「嘿，小小」不能補答。"""
    write_seg(loop["dir"], 0, utts(1.0))
    write_seg(loop["dir"], 1, utts(1.0))
    loop["texts"] = ["嘿，小小，舊的問題", "嘿，小小，舊的問題二"]
    assert loop["run"](from_start=False) == 0
    assert loop["asked"] == [] and loop["durations"] == []


def test_seek_end_reads_only_new_audio(tmp_path):
    write_seg(tmp_path, 0, utts(1.0))
    write_seg(tmp_path, 1, tone(0.5))
    t = a.SegmentTail(tmp_path)
    t.seek_end()
    assert t.read_new() == b""
    with (tmp_path / "seg-001.wav").open("ab") as f:
        f.write(silence(0.25))
    assert t.read_new() == silence(0.25)


def test_bare_wake_expires_when_no_question_follows(loop):
    write_seg(loop["dir"], 0, utts(1.0) + silence(10.0) + utts(1.0))
    loop["texts"] = ["嘿，小小。", "好，那下週再看"]
    assert loop["run"]() == 0
    assert loop["asked"] == []


# ---- 本機同步播放：耳機兩邊播、喇叭只走喇叭（不讓麥克風再收一次） ----


def _profile(*items):
    return {"SPAudioDataType": [{"_items": list(items)}]}


def _default_out(**kw):
    return {"_name": "X", "coreaudio_default_audio_output_device": "spaudio_yes", **kw}


def test_route_builtin_speakers_is_speakers():
    p = _profile(_default_out(coreaudio_device_transport="coreaudio_device_type_builtin",
                              coreaudio_output_source="MacBook Air的揚聲器"))
    assert a.output_route(p) == "speakers"


def test_route_english_internal_speakers_is_speakers():
    p = _profile(_default_out(coreaudio_device_transport="coreaudio_device_type_builtin",
                              coreaudio_output_source="spaudio_internal_speakers"))
    assert a.output_route(p) == "speakers"


def test_route_bluetooth_is_headphones():
    p = _profile(_default_out(_name="AirPods", coreaudio_device_transport="coreaudio_device_type_bluetooth"))
    assert a.output_route(p) == "headphones"


def test_route_builtin_headphone_jack_is_headphones():
    p = _profile(_default_out(coreaudio_device_transport="coreaudio_device_type_builtin",
                              coreaudio_output_source="外接耳機"))
    assert a.output_route(p) == "headphones"


def test_route_unknown_falls_back_to_headphones():
    """認不出就兩邊都播：寧可對方聽到回音，也不能讓對方完全聽不到。"""
    assert a.output_route(_profile(_default_out(coreaudio_device_transport="coreaudio_device_type_usb"))) == "headphones"
    assert a.output_route({}) == "headphones"


def test_say_targets_headphones_plays_virtual_mic_and_local():
    assert a.say_targets("headphones", "BlackHole 2ch") == ["BlackHole 2ch", None]


def test_say_targets_speakers_plays_local_only():
    """喇叭播出會被麥克風收進會議：虛擬麥克風再送一份就重複，所以只走喇叭。"""
    assert a.say_targets("speakers", "BlackHole 2ch") == [None]


# ---- 叫小小散會：不送 claude，提醒要在 Claude 輸入 ----


@pytest.mark.parametrize("q", ["散會", "三會哈哈哈哈", "散會。", "會議結束"])
def test_end_meeting_phrase_gets_fixed_reply(loop, q):
    write_seg(loop["dir"], 0, utts(1.0))
    loop["texts"] = [f"嘿，小小，{q}"]
    assert loop["run"]() == 0
    assert loop["asked"] == []
    assert loop["spoken"] == [a.END_LINE]
    assert "輸入" in a.END_LINE and f"- 小小：{a.END_LINE}" in loop["md"]()


def test_question_mentioning_meeting_end_still_asks(loop):
    write_seg(loop["dir"], 0, utts(1.0))
    loop["texts"] = ["嘿，小小，散會後要做什麼？"]
    assert loop["run"]() == 0
    assert loop["asked"][0][0] == "散會後要做什麼"


# ---- 完整逐字稿：最近 N 分鐘之外的上下文要能查 ----


def test_prompt_points_to_full_transcript():
    prompt = a.build_claude_cmd(MODE, "Q", "ctx", transcript_path="/x/會議/transcript.md")[2]
    assert "/x/會議/transcript.md" in prompt and "發音相近" in prompt


def test_prompt_without_transcript_has_no_path():
    assert "transcript.md" not in a.build_claude_cmd(MODE, "Q", "ctx")[2]


def test_loop_passes_transcript_path_when_present(loop, monkeypatch):
    (loop["dir"] / "transcript.md").write_text("[00:00:01] 前情", encoding="utf-8")
    seen = []

    def ask_fn(mode, question, context, on_slow=lambda: None, **kw):
        seen.append(kw.get("transcript_path"))
        return ("好。", True)

    write_seg(loop["dir"], 0, utts(1.0))
    loop["texts"] = ["嘿，小小，前面談了什麼？"]
    assert a.run_loop(loop["dir"], MODE, lambda *x: [(0.0, loop["texts"].pop(0))], ask_fn=ask_fn,
                      speak_fn=lambda t, d: (1000.0, 1001.0), clock=lambda: 1000.0, from_start=True) == 0
    assert seen == [str(loop["dir"] / "transcript.md")]
