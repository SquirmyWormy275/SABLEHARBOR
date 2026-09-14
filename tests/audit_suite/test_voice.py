import json

import pytest

from enterprise.audit_suite.store import DomainError
from enterprise.audit_suite.voice import LocalVoice


def voice(tmp_path):
    for name in ["python", "tts", "ffmpeg"]:
        (tmp_path / name).touch()
    (tmp_path / "asr").mkdir()
    p = tmp_path / "voice.json"
    p.write_text(
        json.dumps(
            {
                "python": str(tmp_path / "python"),
                "tts_model": str(tmp_path / "tts"),
                "asr_model": str(tmp_path / "asr"),
                "ffmpeg": str(tmp_path / "ffmpeg"),
                "temporary": str(tmp_path / "tmp"),
            }
        )
    )
    p.chmod(0o600)
    return LocalVoice(p)


def test_audio_bounds_and_formats_before_execution(tmp_path):
    adapter = voice(tmp_path)
    for audio, mime in [(b"", "audio/wav"), (b"a", "text/html"), (b"a" * 12000001, "audio/wav")]:
        with pytest.raises(DomainError):
            adapter.transcribe(audio, mime)
    for text in ["", "a" * 1501, None]:
        with pytest.raises(DomainError):
            adapter.synthesize(text)


def test_runtime_failure_does_not_echo_audio_or_text(tmp_path):
    adapter = voice(tmp_path)
    with pytest.raises(DomainError, match="Local speech processing failed") as error:
        adapter.synthesize("private source text")
    assert "private source text" not in str(error.value)
