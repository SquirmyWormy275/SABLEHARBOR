"""Bounded local ASR/TTS subprocess adapters; no browser microphone permission.

The HTTP layer independently authenticates and authorizes each audio operation.
No transcript is a command until a learner reviews and submits it explicitly.
"""

from __future__ import annotations

import io
import json
import subprocess
import tempfile
import wave
from pathlib import Path

from .inference import _private_json
from .store import DomainError

ASR_WORKER = """import json,sys
from faster_whisper import WhisperModel
model=WhisperModel(sys.argv[1],device="cpu",compute_type="int8",cpu_threads=4,local_files_only=True)
segments,info=model.transcribe(sys.argv[2],language="en",beam_size=3,vad_filter=True)
rows=[{"start":s.start,"end":s.end,"text":s.text.strip()} for s in segments]
result={"text":" ".join(s["text"] for s in rows),"segments":rows,
        "language":info.language,"duration":info.duration}
print(json.dumps(result))
"""
TTS_WORKER = """import io,sys,wave
from piper import PiperVoice
voice=PiperVoice.load(sys.argv[1])
buf=io.BytesIO()
with wave.open(buf,"wb") as out:
    voice.synthesize_wav(sys.stdin.buffer.read(12000).decode("utf-8"),out)
sys.stdout.buffer.write(buf.getvalue())
"""
FORMATS = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/webm": "matroska",
    "audio/ogg": "ogg",
    "audio/mp4": "mov",
    "audio/mpeg": "mp3",
}


class LocalVoice:
    def __init__(self, config_path: str | Path):
        config = _private_json(Path(config_path))
        self.python = Path(config["python"]).absolute()
        self.asr_model = Path(config["asr_model"]).resolve()
        self.tts_model = Path(config["tts_model"]).resolve()
        self.ffmpeg = Path(config["ffmpeg"]).resolve()
        self.temporary = Path(config["temporary"]).resolve()
        if (
            not self.python.is_file()
            or not self.asr_model.is_dir()
            or not self.tts_model.is_file()
            or not self.ffmpeg.is_file()
        ):
            raise DomainError(
                "Local voice runtime is incomplete", code="VOICE_UNAVAILABLE", status=503
            )
        self.temporary.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.temporary.chmod(0o700)
        self.environment = {
            "PATH": "/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "TMPDIR": str(self.temporary),
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
        }

    def _run(self, argv: list[str], data: bytes | None = None, limit: int = 8_000_000) -> bytes:
        try:
            result = subprocess.run(
                argv,
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=120,
                check=True,
                env=self.environment,
            )
        except (OSError, subprocess.SubprocessError):
            raise DomainError(
                "Local speech processing failed", code="VOICE_UNAVAILABLE", status=503
            ) from None
        if len(result.stdout) > limit:
            raise DomainError("Speech output exceeded limit")
        return result.stdout

    def transcribe(self, audio_bytes: bytes, mime: str) -> dict:
        if not isinstance(audio_bytes, bytes) or not 1 <= len(audio_bytes) <= 12_000_000:
            raise DomainError("Audio must contain 1–12000000 bytes")
        format_name = FORMATS.get(mime.split(";", 1)[0].strip().lower())
        if not format_name:
            raise DomainError("Unsupported audio format")
        # No external URLs, manifests, filesystem references or network protocols.
        wav = self._run(
            [
                str(self.ffmpeg),
                "-v",
                "error",
                "-nostdin",
                "-protocol_whitelist",
                "pipe",
                "-f",
                format_name,
                "-i",
                "pipe:0",
                "-t",
                "121",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-f",
                "wav",
                "-fs",
                "4000000",
                "pipe:1",
            ],
            audio_bytes,
            4_000_000,
        )
        # Streaming WAV headers can contain unknown frame length; count PCM bytes.
        try:
            with wave.open(io.BytesIO(wav)) as source:
                frames = source.readframes(16000 * 121)
                duration = len(frames) / source.getframerate() / source.getsampwidth()
            if not 0 < duration <= 120:
                raise ValueError
        except (ValueError, wave.Error, EOFError):
            raise DomainError("Audio must decode to at most 120 seconds") from None
        with tempfile.TemporaryDirectory(prefix="speech-", dir=self.temporary) as directory:
            path = Path(directory) / "input.wav"
            path.write_bytes(wav)
            path.chmod(0o600)
            output = self._run(
                [str(self.python), "-I", "-c", ASR_WORKER, str(self.asr_model), str(path)],
                limit=100000,
            )
        try:
            result = json.loads(output)
            if not isinstance(result.get("text"), str) or len(result["text"]) > 20000:
                raise ValueError
        except (ValueError, TypeError):
            raise DomainError("Speech runtime returned invalid transcription") from None
        return {
            **result,
            "model": "faster-whisper-base.en",
            "local": True,
            "requires_confirmation": True,
            "automatic_submission": False,
        }

    def synthesize(self, text: str) -> dict:
        if not isinstance(text, str) or not text.strip() or len(text) > 1500:
            raise DomainError("Speech synthesis requires 1–1500 text characters")
        output = self._run(
            [str(self.python), "-I", "-c", TTS_WORKER, str(self.tts_model)], text.encode()
        )
        try:
            with wave.open(io.BytesIO(output)) as source:
                duration = source.getnframes() / source.getframerate()
            if duration > 120:
                raise ValueError
        except (ValueError, wave.Error, EOFError):
            raise DomainError("Speech runtime returned invalid audio") from None
        return {
            "bytes": output,
            "mime": "audio/wav",
            "duration": duration,
            "local": True,
            "model": "piper-en_US-ljspeech-medium",
            "synthetic_voice": True,
        }
