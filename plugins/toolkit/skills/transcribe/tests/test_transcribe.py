import builtins
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


def test_doctor_reports_missing(monkeypatch, capsys):
    monkeypatch.setattr(t.shutil, "which", lambda name: None)
    rc = t.main(["doctor"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "ffmpeg" in out
    assert "install ffmpeg" in out


def test_missing_ffmpeg_message(audio, tmp_path, monkeypatch, capsys):
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
