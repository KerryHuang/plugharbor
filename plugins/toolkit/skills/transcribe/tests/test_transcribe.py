import builtins
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import transcribe as t  # noqa: E402


def fake_backend(segments):
    calls = []

    def run(audio, model, prompt, language):
        calls.append({"audio": audio, "model": model, "prompt": prompt, "language": language})
        return list(segments)

    run.calls = calls
    return run


@pytest.fixture
def audio(tmp_path):
    p = tmp_path / "meeting.wav"
    p.write_bytes(b"RIFF")
    return p


@pytest.fixture(autouse=True)
def has_ffmpeg(monkeypatch):
    monkeypatch.setattr(t.shutil, "which", lambda name: "/usr/bin/" + name)


def test_format_ts():
    assert t.format_ts(3725.4) == "01:02:05"


def test_render_markdown():
    md = t.render_markdown(
        [(0.0, "大家好"), (65.0, "開始")],
        {"model": "large-v3-turbo", "audio": "m.wav", "transcribed_at": "2026-11-03 10:00"},
    )
    assert "[00:00:00] 大家好" in md
    assert "[00:01:05] 開始" in md
    assert "large-v3-turbo" in md
    assert "m.wav" in md


def test_pick_backend():
    assert t.pick_backend("Darwin", "arm64") == "mlx"
    assert t.pick_backend("Windows", "AMD64") == "faster-whisper"
    assert t.pick_backend("Darwin", "x86_64") == "faster-whisper"


def test_converts_to_traditional(audio, tmp_path):
    out = tmp_path / "out.md"
    rc = t.main(["transcribe", str(audio), "--out", str(out)], backend_runner=fake_backend([(0.0, "软件开发")]))
    assert rc == 0
    assert "軟體開發" in out.read_text(encoding="utf-8")


def test_cli_handles_cjk_path(tmp_path):
    a = tmp_path / "客戶 會議.wav"
    a.write_bytes(b"RIFF")
    out = tmp_path / "逐字稿 一.md"
    rc = t.main(["transcribe", str(a), "--out", str(out)], backend_runner=fake_backend([(0.0, "好")]))
    assert rc == 0
    assert out.exists()


def test_no_segments_fails(audio, tmp_path, capsys):
    out = tmp_path / "out.md"
    rc = t.main(["transcribe", str(audio), "--out", str(out)], backend_runner=fake_backend([]))
    assert rc != 0
    assert "未偵測到語音" in capsys.readouterr().err
    assert not out.exists()


def test_missing_opencc_fails_before_transcribe(audio, tmp_path, monkeypatch):
    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "opencc":
            raise ImportError("no opencc")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    run = fake_backend([(0.0, "x")])
    rc = t.main(["transcribe", str(audio), "--out", str(tmp_path / "o.md")], backend_runner=run)
    assert rc != 0
    assert run.calls == []


def test_refuses_overwrite(audio, tmp_path):
    out = tmp_path / "out.md"
    out.write_text("舊的", encoding="utf-8")
    run = fake_backend([(0.0, "新的")])
    assert t.main(["transcribe", str(audio), "--out", str(out)], backend_runner=run) != 0
    assert out.read_text(encoding="utf-8") == "舊的"
    assert t.main(["transcribe", str(audio), "--out", str(out), "--force"], backend_runner=run) == 0
    assert "新的" in out.read_text(encoding="utf-8")


def test_prompt_file_passed(audio, tmp_path):
    pf = tmp_path / "glossary.txt"
    pf.write_text("模具 射出 排程", encoding="utf-8")
    run = fake_backend([(0.0, "x")])
    t.main(["transcribe", str(audio), "--out", str(tmp_path / "o.md"), "--prompt-file", str(pf)], backend_runner=run)
    assert run.calls[0]["prompt"] == "模具 射出 排程"


def on_mac(monkeypatch):
    monkeypatch.setattr(t.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(t.platform, "machine", lambda: "arm64")


def on_windows(monkeypatch):
    monkeypatch.setattr(t.platform, "system", lambda: "Windows")
    monkeypatch.setattr(t.platform, "machine", lambda: "AMD64")


def test_doctor_reports_missing(monkeypatch, capsys):
    on_mac(monkeypatch)
    monkeypatch.setattr(t.shutil, "which", lambda name: None)
    rc = t.main(["doctor"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "ffmpeg" in out
    assert "install ffmpeg" in out


def test_missing_ffmpeg_message(audio, tmp_path, monkeypatch, capsys):
    on_mac(monkeypatch)
    monkeypatch.setattr(t.shutil, "which", lambda name: None)
    run = fake_backend([(0.0, "x")])
    rc = t.main(["transcribe", str(audio), "--out", str(tmp_path / "o.md")], backend_runner=run)
    assert rc != 0
    assert run.calls == []
    assert "doctor" in capsys.readouterr().err


def test_mlx_model_mapping(monkeypatch):
    import types

    seen = {}

    def fake_transcribe(audio, **kw):
        seen.update(kw)
        return {"segments": [{"start": 1.5, "text": "你好"}]}

    monkeypatch.setitem(sys.modules, "mlx_whisper", types.SimpleNamespace(transcribe=fake_transcribe))
    segs = t.run_mlx("a.wav", "large-v3-turbo", "模具", "zh")
    assert seen["path_or_hf_repo"] == "mlx-community/whisper-large-v3-turbo"
    assert seen["initial_prompt"] == "模具"
    assert segs == [(1.5, "你好")]


def test_keeps_common_tai(audio, tmp_path):
    out = tmp_path / "out.md"
    t.main(["transcribe", str(audio), "--out", str(out)], backend_runner=fake_backend([(0.0, "机台在台湾的平台")]))
    assert "機台在台灣的平台" in out.read_text(encoding="utf-8")


def test_faster_whisper_skips_ffmpeg(audio, tmp_path, monkeypatch, capsys):
    on_windows(monkeypatch)
    monkeypatch.setattr(t.shutil, "which", lambda name: None)
    rc = t.main(["transcribe", str(audio), "--out", str(tmp_path / "o.md")], backend_runner=fake_backend([(0.0, "好")]))
    assert rc == 0
    rc = t.main(["doctor"])
    assert "ffmpeg" not in capsys.readouterr().out.split("逐字稿已寫入")[-1]


def test_doctor_flags_incompatible_pyav(monkeypatch, capsys):
    on_windows(monkeypatch)
    monkeypatch.setattr(t, "_importable", lambda m: True)
    monkeypatch.setattr(t, "_pkg_version", lambda name: "19.0.2" if name == "av" else "1.2.1")
    assert t.main(["doctor"]) == 1
    assert 'av<17' in capsys.readouterr().out


def test_doctor_accepts_pyav_16(monkeypatch):
    on_windows(monkeypatch)
    monkeypatch.setattr(t, "_importable", lambda m: True)
    monkeypatch.setattr(t, "_pkg_version", lambda name: "16.1.0" if name == "av" else "1.2.1")
    assert t.main(["doctor"]) == 0


SILENCEDETECT = """[Parsed_silencedetect_0 @ 0x1] silence_start: 0
[Parsed_silencedetect_0 @ 0x1] silence_end: 90.002 | silence_duration: 90.002
[Parsed_silencedetect_0 @ 0x1] silence_start: 120.5
"""


def test_parse_silences_open_ended():
    assert t.parse_silences(SILENCEDETECT, duration=130.0) == [(0.0, 90.002), (120.5, 130.0)]


def test_drop_silent_removes_hallucination_in_silence():
    raw = [
        {"start": 58.8, "end": 60.0, "text": "优优独播剧场"},
        {"start": 89.8, "end": 95.0, "text": "今天讨论模具排程"},
        {"start": 121.0, "end": 125.0, "text": "请不吝点赞订阅"},
    ]
    kept = t.drop_silent(raw, [(0.0, 90.002), (120.5, 130.0)])
    assert [s["text"] for s in kept] == ["今天讨论模具排程"]


def test_mlx_uses_hallucination_guard_and_silence_filter(monkeypatch):
    import types

    seen = {}

    def fake_transcribe(audio, **kw):
        seen.update(kw)
        return {"segments": [{"start": 58.8, "end": 60.0, "text": "幻覺"}, {"start": 90.0, "end": 92.0, "text": "你好"}]}

    monkeypatch.setitem(sys.modules, "mlx_whisper", types.SimpleNamespace(transcribe=fake_transcribe))
    monkeypatch.setattr(t, "detect_silences", lambda audio: [(0.0, 89.5)])
    assert t.run_mlx("a.wav", "large-v3-turbo", None, "zh") == [(90.0, "你好")]
    assert seen["word_timestamps"] is True
    assert seen["hallucination_silence_threshold"] == 2.0


def test_warns_when_prompt_too_long(audio, tmp_path, capsys):
    pf = tmp_path / "g.txt"
    pf.write_text("模具" * 150, encoding="utf-8")
    t.main(["transcribe", str(audio), "--out", str(tmp_path / "o.md"), "--prompt-file", str(pf)], backend_runner=fake_backend([(0.0, "x")]))
    assert "開頭會被截掉" in capsys.readouterr().err


def test_no_progress_spam_when_not_tty(monkeypatch, capsys):
    import types

    seg = types.SimpleNamespace(start=0.0, end=1.0, text="好")
    info = types.SimpleNamespace(duration=1.0)

    class FakeModel:
        def __init__(self, *a, **kw):
            pass

        def transcribe(self, *a, **kw):
            return iter([seg] * 50), info

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeModel))
    monkeypatch.setattr(t, "_has_cuda", lambda: False)
    t.run_faster_whisper("a.wav", "large-v3-turbo", None, "zh")
    assert capsys.readouterr().err.count("進度") == 0


# ---- 第二階段：麥克風錄音 ----

MAC_DEVICES = """[AVFoundation indev @ 0x1] AVFoundation video devices:
[AVFoundation indev @ 0x1] [0] FaceTime HD Camera
[AVFoundation indev @ 0x1] AVFoundation audio devices:
[AVFoundation indev @ 0x1] [0] Microsoft Teams Audio
[AVFoundation indev @ 0x1] [1] MacBook Air的麥克風
[AVFoundation indev @ 0x1] [2] Kerry的iPhone 14麥克風
[in#0 @ 0x2] Error opening input: Input/output error
"""

WIN_DEVICES = """[dshow @ 000001] "Integrated Webcam" (video)
[dshow @ 000001]   Alternative name "@device_pnp_xxx"
[dshow @ 000001] "麥克風陣列 (Realtek(R) Audio)" (audio)
[dshow @ 000001]   Alternative name "@device_cm_{33D9A762}\\wave_{AAA}"
[dshow @ 000001] "Stereo Mix (Realtek(R) Audio)" (audio)
"""


def test_parse_devices_mac():
    assert t.parse_devices("Darwin", MAC_DEVICES) == ["Microsoft Teams Audio", "MacBook Air的麥克風", "Kerry的iPhone 14麥克風"]


def test_parse_devices_windows():
    assert t.parse_devices("Windows", WIN_DEVICES) == ["麥克風陣列 (Realtek(R) Audio)", "Stereo Mix (Realtek(R) Audio)"]


def test_build_record_cmd_mac_default(tmp_path):
    cmd = t.build_record_cmd("Darwin", None, tmp_path, 300)
    assert cmd[cmd.index("-f") + 1] == "avfoundation"
    assert cmd[cmd.index("-i") + 1] == ":default"
    assert cmd[-1] == str(tmp_path / "seg-%03d.wav")
    assert ["-ar", "16000", "-ac", "1"] == cmd[cmd.index("-ar"):cmd.index("-ar") + 4]
    assert cmd[cmd.index("-segment_time") + 1] == "300"


def test_build_record_cmd_windows(tmp_path):
    cmd = t.build_record_cmd("Windows", "麥克風陣列 (Realtek(R) Audio)", tmp_path, 60)
    assert cmd[cmd.index("-f") + 1] == "dshow"
    assert cmd[cmd.index("-i") + 1] == "audio=麥克風陣列 (Realtek(R) Audio)"


def test_concat_list_escapes_quotes(tmp_path):
    segs = [tmp_path / "客戶 會議" / "seg-000.wav", tmp_path / "it's" / "seg-001.wav"]
    text = t.concat_list(segs)
    lines = text.splitlines()
    assert lines[0] == f"file '{segs[0]}'"
    assert lines[2] == "file '" + str(segs[1]).replace("'", "'\\''") + "'"


def test_concat_list_absolute_and_ignores_stale_header(tmp_path, monkeypatch):
    # 實測：清單路徑以清單檔所在目錄為基準（相對 --out 會變成 dir/dir/seg）；
    # 被硬殺的最後一段檔頭長度沒收尾，不加 ignore_length 會被截短
    monkeypatch.chdir(tmp_path)
    lines = t.concat_list([Path("rec") / "seg-000.wav"]).splitlines()
    assert lines[0] == f"file '{(tmp_path / 'rec' / 'seg-000.wav').resolve()}'"
    assert lines[1] == "option ignore_length 1"


@pytest.fixture
def rec(monkeypatch, tmp_path):
    """假的錄音環境：Popen 會建出 seg-000.wav，程序存活與音量可控。"""
    import json as _json

    on_mac(monkeypatch)
    state = {"alive": True, "ffmpeg_alive": False, "volume": -30.0, "spawned": [], "killed": [], "concat": []}
    monkeypatch.setattr(t, "_importable", lambda m: True)
    monkeypatch.setattr(t.sys, "version_info", (3, 12, 0))

    def fake_spawn(cmd, log_path):
        state["spawned"].append(cmd)
        out_dir = Path(cmd[cmd.index("--out") + 1]) if "--out" in cmd else Path(cmd[-1]).parent
        (out_dir / "seg-000.wav").write_bytes(b"RIFF" + b"\0" * 40 + b"\0" * 32000)
        return 4242

    def fake_concat(list_file, out):
        state["concat"].append(Path(list_file).read_text(encoding="utf-8"))
        Path(out).write_bytes(b"RIFF" + b"\0" * 40 + b"\0" * 64000)
        return True

    monkeypatch.setattr(t, "_spawn", fake_spawn)
    monkeypatch.setattr(t, "_alive", lambda pid, name="ffmpeg": state["alive"] if pid == 4242 else state["ffmpeg_alive"])
    monkeypatch.setattr(t, "_max_volume", lambda path: state["volume"])
    monkeypatch.setattr(t, "_kill", lambda pid, system, name="ffmpeg": state["killed"].append(pid) or state.update(alive=False))
    monkeypatch.setattr(t, "_run_ffmpeg_concat", fake_concat)
    monkeypatch.setattr(t.time, "sleep", lambda s: None)
    monkeypatch.setattr(t.shutil, "which", lambda name: "/usr/bin/" + name)
    state["dir"] = tmp_path / "會議 素材"
    state["read"] = lambda: _json.loads((state["dir"] / "record.json").read_text(encoding="utf-8"))
    return state


def test_start_writes_state_and_detaches(rec, capsys):
    assert t.main(["record", "start", "--out", str(rec["dir"])]) == 0
    st = rec["read"]()
    assert st["pid"] == 4242 and st["stopped_at"] is None and st["segment_sec"] == 300
    assert len(rec["spawned"]) == 1


def test_start_refuses_when_running(rec, capsys):
    t.main(["record", "start", "--out", str(rec["dir"])])
    capsys.readouterr()
    assert t.main(["record", "start", "--out", str(rec["dir"])]) == 2
    assert "4242" in capsys.readouterr().err
    assert len(rec["spawned"]) == 1


def test_start_warns_on_silence(rec, capsys):
    rec["volume"] = -91.0
    assert t.main(["record", "start", "--out", str(rec["dir"])]) == 0
    assert "靜音" in capsys.readouterr().err


def test_start_fails_when_ffmpeg_dies(rec, capsys):
    rec["alive"] = False
    rec["dir"].mkdir(parents=True)
    (rec["dir"] / "ffmpeg.log").write_text("Error opening input: Permission denied", encoding="utf-8")
    assert t.main(["record", "start", "--out", str(rec["dir"])]) == 3
    assert "Permission denied" in capsys.readouterr().err


def test_stop_merges_when_process_gone(rec, capsys):
    t.main(["record", "start", "--out", str(rec["dir"])])
    (rec["dir"] / "seg-001.wav").write_bytes(b"RIFF")
    rec["alive"] = False
    assert t.main(["record", "stop", "--out", str(rec["dir"])]) == 0
    assert rec["killed"] == []
    assert "seg-000.wav" in rec["concat"][0] and "seg-001.wav" in rec["concat"][0]
    assert rec["read"]()["stopped_at"] is not None
    assert "recording.wav" in capsys.readouterr().out


def test_stop_kills_running(rec):
    t.main(["record", "start", "--out", str(rec["dir"])])
    assert t.main(["record", "stop", "--out", str(rec["dir"])]) == 0
    assert rec["killed"] == [4242]


def test_stop_without_segments_fails(rec, capsys):
    t.main(["record", "start", "--out", str(rec["dir"])])
    (rec["dir"] / "seg-000.wav").unlink()
    assert t.main(["record", "stop", "--out", str(rec["dir"])]) == 4
    assert not (rec["dir"] / "recording.wav").exists()


def test_status_not_recording(rec, capsys):
    assert t.main(["record", "status", "--out", str(rec["dir"])]) == 1


def test_build_record_cmd_prevents_sample_drop(tmp_path):
    # 實測：沒有加大輸入佇列與 async 重取樣時，Mac 每 30 秒掉約 3.5 秒音訊
    for system, dev in (("Darwin", None), ("Windows", "Mic")):
        cmd = t.build_record_cmd(system, dev, tmp_path, 300)
        assert cmd.index("-thread_queue_size") < cmd.index("-i")
        assert cmd[cmd.index("-af") + 1] == "aresample=async=1000"


def test_doctor_record_requires_ffmpeg_on_windows(monkeypatch, capsys):
    on_windows(monkeypatch)
    monkeypatch.setattr(t, "_importable", lambda m: True)
    monkeypatch.setattr(t, "_pkg_version", lambda name: "16.1.0")
    monkeypatch.setattr(t.shutil, "which", lambda name: None)
    assert t.main(["doctor"]) == 0
    assert t.main(["doctor", "--record"]) == 1
    assert "winget install ffmpeg" in capsys.readouterr().out


def test_spawn_windows_breaks_away_from_job(monkeypatch, tmp_path):
    # 實測：Windows OpenSSH／終端機會把子程序放進 job，連線結束就一起被砍
    on_windows(monkeypatch)
    calls = []

    class FakePopen:
        def __init__(self, cmd, **kw):
            calls.append(kw.get("creationflags", 0))
            if len(calls) == 1 and kw["creationflags"] & 0x01000000:
                raise PermissionError("job 不允許 breakaway")
            self.pid = 7

    monkeypatch.setattr(t.subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200, raising=False)
    monkeypatch.setattr(t.subprocess, "DETACHED_PROCESS", 0x8, raising=False)
    monkeypatch.setattr(t.subprocess, "Popen", FakePopen)
    assert t._spawn(["ffmpeg"], tmp_path / "ffmpeg.log") == 7
    assert calls[0] & 0x01000000
    assert not calls[1] & 0x01000000


def test_build_record_cmd_flushes_segments(tmp_path):
    # 實測：segment 內層 muxer 每 256 KiB 才寫盤，硬殺（Windows 一律 taskkill /F）會丟最後約 8 秒
    cmd = t.build_record_cmd("Darwin", None, tmp_path, 300)
    assert cmd[cmd.index("-segment_format_options") + 1] == "flush_packets=1"


def test_start_refuses_dir_with_old_segments(rec, capsys):
    # 舊錄音程序已死（重開機）時在同一目錄再 start，segment muxer 會從 seg-000 覆蓋前半場
    rec["dir"].mkdir(parents=True)
    old = rec["dir"] / "seg-000.wav"
    old.write_bytes(b"OLD")
    rec["alive"] = False
    assert t.main(["record", "start", "--out", str(rec["dir"])]) == 2
    assert old.read_bytes() == b"OLD"
    assert rec["spawned"] == []
    assert "換" in capsys.readouterr().err


def test_start_refuses_dir_with_recording(rec):
    rec["dir"].mkdir(parents=True)
    (rec["dir"] / "recording.wav").write_bytes(b"OLD")
    assert t.main(["record", "start", "--out", str(rec["dir"])]) == 2
    assert rec["spawned"] == []


def test_start_without_ffmpeg_fails_cleanly(rec, monkeypatch, capsys):
    monkeypatch.setattr(t.shutil, "which", lambda name: None)
    assert t.main(["record", "start", "--out", str(rec["dir"])]) == 3
    assert "doctor --record" in capsys.readouterr().err
    assert rec["spawned"] == []


def test_alive_rejects_reused_pid_posix(monkeypatch):
    # 當機後 PID 被別的程序拿走：不能把它當成錄音中的 ffmpeg
    on_mac(monkeypatch)
    out = {"stdout": "Safari\n"}

    class R:
        def __init__(self):
            self.stdout = out["stdout"]
            self.returncode = 0 if out["stdout"] else 1

    monkeypatch.setattr(t.subprocess, "run", lambda *a, **k: R())
    assert t._alive(4242) is False
    out["stdout"] = "/opt/homebrew/bin/ffmpeg\n"
    assert t._alive(4242) is True
    out["stdout"] = ""
    assert t._alive(4242) is False


def test_alive_rejects_reused_pid_windows(monkeypatch):
    on_windows(monkeypatch)
    out = {"stdout": '"notepad.exe","4242","Console","1","10,000 K"\n'}

    class R:
        def __init__(self):
            self.stdout = out["stdout"]
            self.returncode = 0

    monkeypatch.setattr(t.subprocess, "run", lambda *a, **k: R())
    assert t._alive(4242) is False
    out["stdout"] = '"ffmpeg.exe","4242","Console","1","30,000 K"\n'
    assert t._alive(4242) is True
    out["stdout"] = "INFO: No tasks are running which match the specified criteria.\n"
    assert t._alive(4242) is False


def test_kill_windows_does_not_kill_tree(monkeypatch):
    calls = []
    monkeypatch.setattr(t.subprocess, "run", lambda cmd, **k: calls.append(cmd))
    t._kill(4242, "Windows")
    assert "/T" not in calls[0]


def test_kill_tolerates_process_exiting_midway(monkeypatch):
    # ffmpeg 在 SIGINT 前或最後一次輪詢後自己結束：stop 不能噴 traceback
    on_mac(monkeypatch)
    monkeypatch.setattr(t, "_alive", lambda pid: True)
    monkeypatch.setattr(t.time, "sleep", lambda s: None)

    def gone(pid, sig):
        raise ProcessLookupError

    monkeypatch.setattr(t.os, "kill", gone)
    t._kill(4242, "Darwin")  # 不丟例外即通過


def test_child_exited_detects_zombie():
    # ffmpeg 一啟動就死時是本程序的 zombie，os.kill(pid, 0) 仍成功；要先 reap 才判得出來
    import subprocess

    p = subprocess.Popen([sys.executable, "-c", "pass"])
    import time as _time

    _time.sleep(1.0)
    assert t._child_exited(p.pid) is True
    assert t._child_exited(os.getpid()) is False


# ---- 第三階段：系統聲音 ----


def test_build_pipe_record_cmd_system(tmp_path):
    cmd = t.build_pipe_record_cmd("Darwin", "system", None, tmp_path, 300, 48000)
    assert cmd[cmd.index("-i") + 1] == "pipe:0"
    assert cmd[cmd.index("-f") + 1] == "f32le" and cmd[cmd.index("-ar") + 1] == "48000"
    assert "avfoundation" not in cmd
    assert cmd[cmd.index("-af") + 1] == "aresample=async=1000"
    assert cmd[cmd.index("-segment_format_options") + 1] == "flush_packets=1"
    assert cmd[-1].endswith("seg-%03d.wav")


def test_build_pipe_record_cmd_both_mixes_mic(tmp_path):
    cmd = t.build_pipe_record_cmd("Darwin", "both", None, tmp_path, 300, 44100)
    inputs = [cmd[i + 1] for i, a in enumerate(cmd) if a == "-i"]
    assert inputs == ["pipe:0", ":default"]
    assert "amix=inputs=2" in cmd[cmd.index("-filter_complex") + 1]
    assert "-af" not in cmd
    assert cmd.index("-thread_queue_size") < cmd.index("avfoundation")


def test_padding_frames():
    assert t.padding_frames(2.0, 48000, 48000) == 48000
    assert t.padding_frames(1.0, 60000, 48000) == 0


def test_is_heard():
    assert t.is_heard(0.5) is True
    assert t.is_heard(1e-5) is False
    assert t.is_heard(0.0) is False


class _FakeStdin:
    def __init__(self):
        self.n = 0
        self.closed = False

    def write(self, b):
        self.n += len(b)

    def flush(self):
        pass

    def close(self):
        self.closed = True


def _worker_env(monkeypatch, tmp_path, chunk_from=1.0, stop_at=3.0):
    import array as _array

    on_mac(monkeypatch)
    env = {"now": 0.0, "stopped": False, "stdin": _FakeStdin(), "cmd": None}

    class FakeProc:
        pid = 777

        def __init__(self, cmd, **kw):
            env["cmd"] = cmd
            self.stdin = env["stdin"]

        def wait(self, timeout=None):
            return 0

    def fake_capture(on_chunk):
        env["on_chunk"] = on_chunk
        return (lambda: env.update(stopped=True)), 48000

    def fake_sleep(s):
        env["now"] += s
        if env["now"] >= chunk_from:
            env["on_chunk"](_array.array("f", [0.5] * int(48000 * s)).tobytes())
        if env["now"] >= stop_at:
            t._STOP.set()

    monkeypatch.setattr(t.subprocess, "Popen", FakeProc)
    monkeypatch.setattr(t, "_open_system_capture", fake_capture)
    monkeypatch.setattr(t, "_now", lambda: env["now"])
    monkeypatch.setattr(t.time, "sleep", fake_sleep)
    monkeypatch.setattr(t, "_install_stop_handlers", lambda: None)
    return env


def test_system_worker_pads_and_writes_heard(monkeypatch, tmp_path):
    import json as _json

    env = _worker_env(monkeypatch, tmp_path)
    assert t._system_worker(tmp_path, "system", None, 300) == 0
    frames = env["stdin"].n / 4
    assert (env["now"] - 0.6) * 48000 <= frames <= (env["now"] + 0.6) * 48000
    st = _json.loads((tmp_path / "system.json").read_text(encoding="utf-8"))
    assert st["heard_at"] is not None and st["ffmpeg_pid"] == 777
    assert env["cmd"][env["cmd"].index("-i") + 1] == "pipe:0"


def test_system_worker_never_heard(monkeypatch, tmp_path):
    import json as _json

    _worker_env(monkeypatch, tmp_path, chunk_from=99.0)
    assert t._system_worker(tmp_path, "system", None, 300) == 0
    assert _json.loads((tmp_path / "system.json").read_text(encoding="utf-8"))["heard_at"] is None


def test_system_worker_stops_cleanly(monkeypatch, tmp_path):
    env = _worker_env(monkeypatch, tmp_path)
    assert t._system_worker(tmp_path, "system", None, 300) == 0
    assert env["stopped"] is True and env["stdin"].closed is True


def test_start_system_spawns_worker(rec):
    assert t.main(["record", "start", "--out", str(rec["dir"]), "--source", "system"]) == 0
    cmd = rec["spawned"][0]
    assert "_worker" in cmd and cmd[cmd.index("--source") + 1] == "system"
    assert rec["read"]()["source"] == "system"


def test_start_system_skips_silence_warning(rec, capsys):
    rec["volume"] = -91.0
    assert t.main(["record", "start", "--out", str(rec["dir"]), "--source", "system"]) == 0
    assert "靜音" not in capsys.readouterr().err


def test_start_both_keeps_silence_warning(rec, capsys):
    rec["volume"] = -91.0
    assert t.main(["record", "start", "--out", str(rec["dir"]), "--source", "both"]) == 0
    assert "靜音" in capsys.readouterr().err


def test_start_system_refused_on_windows(rec, monkeypatch, capsys):
    on_windows(monkeypatch)
    assert t.main(["record", "start", "--out", str(rec["dir"]), "--source", "both", "--device", "Mic"]) == 2
    assert "尚未驗證" in capsys.readouterr().err
    assert rec["spawned"] == []


def test_start_system_requires_py311_and_catap(rec, monkeypatch, capsys):
    monkeypatch.setattr(t, "_importable", lambda m: m != "catap")
    assert t.main(["record", "start", "--out", str(rec["dir"]), "--source", "system"]) == 3
    assert "doctor --record --source system" in capsys.readouterr().err
    monkeypatch.setattr(t, "_importable", lambda m: True)
    monkeypatch.setattr(t.sys, "version_info", (3, 10, 0))
    assert t.main(["record", "start", "--out", str(rec["dir"]), "--source", "system"]) == 3
    assert rec["spawned"] == []


def test_status_reports_system_not_heard(rec, capsys):
    import json as _json

    t.main(["record", "start", "--out", str(rec["dir"]), "--source", "system"])
    (rec["dir"] / "system.json").write_text(_json.dumps({"heard_at": None, "ffmpeg_pid": 99}), encoding="utf-8")
    capsys.readouterr()
    assert t.main(["record", "status", "--out", str(rec["dir"])]) == 0
    assert "尚未收到" in capsys.readouterr().out
    (rec["dir"] / "system.json").write_text(_json.dumps({"heard_at": "2026-11-03T10:00:00", "ffmpeg_pid": 99}), encoding="utf-8")
    t.main(["record", "status", "--out", str(rec["dir"])])
    assert "10:00:00" in capsys.readouterr().out


def test_stop_kills_orphan_ffmpeg(rec, capsys):
    import json as _json

    t.main(["record", "start", "--out", str(rec["dir"]), "--source", "system"])
    (rec["dir"] / "system.json").write_text(_json.dumps({"heard_at": None, "ffmpeg_pid": 99}), encoding="utf-8")
    rec["alive"] = False
    rec["ffmpeg_alive"] = True
    assert t.main(["record", "stop", "--out", str(rec["dir"])]) == 0
    assert rec["killed"] == [99]
    assert rec["concat"]


def test_stop_system_stops_worker(rec):
    t.main(["record", "start", "--out", str(rec["dir"]), "--source", "system"])
    assert t.main(["record", "stop", "--out", str(rec["dir"])]) == 0
    assert rec["killed"] == [4242]


def test_alive_matches_worker_name(monkeypatch):
    on_mac(monkeypatch)

    class R:
        returncode = 0
        stdout = "/opt/homebrew/bin/Python\n"

    monkeypatch.setattr(t.subprocess, "run", lambda *a, **k: R())
    assert t._alive(5, "python") is True
    assert t._alive(5) is False


def test_mic_default_unchanged(rec):
    t.main(["record", "start", "--out", str(rec["dir"])])
    cmd = rec["spawned"][0]
    assert cmd[0] == "ffmpeg" and "_worker" not in cmd
    assert rec["read"]()["source"] == "mic"


def test_both_mix_ends_with_system_pipe(tmp_path):
    # 實測：duration=longest 時關掉 stdin，ffmpeg 仍等麥克風輸入，stop 要等 10 秒逾時硬殺，多錄 10 秒
    cmd = t.build_pipe_record_cmd("Darwin", "both", None, tmp_path, 300, 48000)
    assert "duration=first" in cmd[cmd.index("-filter_complex") + 1]
