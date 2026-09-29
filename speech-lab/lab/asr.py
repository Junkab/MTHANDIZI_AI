"""
MTHANDIZI — ASR engine.

Wraps the CLEAR Global Chichewa checkpoint verified in Section 0 of the build prompt.

    CLEAR-Global/w2v-bert-2.0-chichewa_34_307h

VERIFICATION STATUS
-------------------
This model has been confirmed working on the operator's Windows machine, CPU only:
a real 4.03s Chichewa recording transcribed word-for-word correctly. The code below
was NOT executed in the authoring environment (Hugging Face is unreachable there),
so treat first-run behaviour on your machine as the real test. See BUILD_LOG.md.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from .config import settings

# Checkpoints to compare in Phase 0. Smaller = faster but less accurate.
CHECKPOINTS = {
    "307h": "CLEAR-Global/w2v-bert-2.0-chichewa_34_307h",   # verified working
    "136h": "CLEAR-Global/w2v-bert-2.0-chichewa_34_136h",
    "102h": "CLEAR-Global/w2v-bert-2.0-chichewa_34_102h",
    "68h":  "CLEAR-Global/w2v-bert-2.0-chichewa_34_68h",
    "34h":  "CLEAR-Global/w2v-bert-2.0-chichewa_34_34h",
}

TARGET_SAMPLE_RATE = 16_000   # the rate the model was trained on — do not change


@dataclass
class Transcription:
    text: str
    seconds: float
    audio_seconds: float
    checkpoint: str
    raw: dict = field(default_factory=dict)

    @property
    def realtime_factor(self) -> float:
        """<1.0 means faster than real time. Above ~2.0 the kiosk will feel broken."""
        return self.seconds / self.audio_seconds if self.audio_seconds else 0.0


class AsrEngine:
    """Lazily-loaded ASR. Construction is cheap; the model loads on first use."""

    def __init__(self, checkpoint: str | None = None) -> None:
        self.checkpoint = checkpoint or settings.asr_checkpoint
        self._pipe = None
        self._load_seconds: float | None = None

    def load(self) -> None:
        if self._pipe is not None:
            return
        started = time.perf_counter()
        # Imported here so that `import lab.asr` stays cheap and testable.
        from transformers import pipeline

        self._pipe = pipeline(
            "automatic-speech-recognition",
            model=self.checkpoint,
            device=-1,  # CPU. Set to 0 if a CUDA GPU is available.
        )
        self._load_seconds = time.perf_counter() - started

    @property
    def load_seconds(self) -> float | None:
        return self._load_seconds

    def transcribe_file(self, path: str | Path) -> Transcription:
        audio, duration = load_audio(path)
        return self.transcribe_array(audio, duration)

    def transcribe_array(self, audio, audio_seconds: float) -> Transcription:
        self.load()
        started = time.perf_counter()
        result = self._pipe(audio)
        elapsed = time.perf_counter() - started
        return Transcription(
            text=(result.get("text") or "").strip(),
            seconds=round(elapsed, 3),
            audio_seconds=round(audio_seconds, 3),
            checkpoint=self.checkpoint,
            raw=result,
        )


def load_audio(path: str | Path):
    """
    Load any audio file as 16kHz mono float32, which is what the model expects.

    Resamples if needed. A mismatched sample rate is the most common cause of
    garbage transcriptions, so this is centralised and never bypassed.
    """
    import librosa

    audio, sample_rate = librosa.load(str(path), sr=TARGET_SAMPLE_RATE, mono=True)
    return audio, len(audio) / float(sample_rate)


def trim_silence(audio, top_db: int = 30):
    """
    Trim leading/trailing silence. Shorter audio = faster inference and fewer
    hallucinated words at the edges. Returns the original if trimming fails.
    """
    try:
        import librosa

        trimmed, _ = librosa.effects.trim(audio, top_db=top_db)
        return trimmed if len(trimmed) > 0 else audio
    except Exception:
        return audio
