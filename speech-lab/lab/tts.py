"""
MTHANDIZI — TTS engine.

TWO BACKENDS, ONE INTERFACE
---------------------------
1. RecordedTts  - plays a WAV recorded by a native Chichewa speaker.
                  Perfect pronunciation, zero latency, zero model risk.
                  THIS IS THE DEFAULT FOR THE DEMO.
2. SynthTts     - facebook/mms-tts-nya (VITS). Needed for dynamic text
                  (names, numbers read back) that cannot be pre-recorded.

The kiosk uses RecordedTts wherever a prompt is fixed, and SynthTts only for the
genuinely dynamic fragments. That is not a compromise — it is how professional
IVR systems have always worked, and it is the reason the voice will sound natural.

LICENCE WARNING
---------------
facebook/mms-tts-* checkpoints are CC-BY-NC-4.0 (NON-COMMERCIAL). Fine for a
competition prototype and research demo. A commercial deployment needs either a
different model or a licence conversation. This must appear in LICENCES.md.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path

from .config import settings

MMS_CHECKPOINT = "facebook/mms-tts-nya"   # 'nya' = Nyanja/Chichewa, ISO 639-3


@dataclass
class Speech:
    wav_path: Path
    seconds: float
    source: str          # "recorded" or "synth"
    text: str


class TtsBackend:
    def speak(self, text: str, key: str | None = None) -> Speech:
        raise NotImplementedError


class RecordedTts(TtsBackend):
    """Serves human-recorded prompts keyed by language-pack ID."""

    def __init__(self, prompts_dir: Path | None = None) -> None:
        self.prompts_dir = Path(prompts_dir or settings.prompts_dir)

    def has(self, key: str) -> bool:
        return bool(key) and (self.prompts_dir / f"{key}.wav").exists()

    def speak(self, text: str, key: str | None = None) -> Speech:
        if not key or not self.has(key):
            raise FileNotFoundError(
                f"No recorded prompt for key {key!r} in {self.prompts_dir}"
            )
        path = self.prompts_dir / f"{key}.wav"
        return Speech(path, 0.0, "recorded", text)


class SynthTts(TtsBackend):
    """facebook/mms-tts-nya via transformers VitsModel. Lazily loaded."""

    def __init__(self, checkpoint: str = MMS_CHECKPOINT,
                 out_dir: Path | None = None) -> None:
        self.checkpoint = checkpoint
        self.out_dir = Path(out_dir or settings.tts_out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self._model = None
        self._tokenizer = None

    def load(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import AutoTokenizer, VitsModel

        self._tokenizer = AutoTokenizer.from_pretrained(self.checkpoint)
        self._model = VitsModel.from_pretrained(self.checkpoint)
        self._model.eval()
        # VITS has a stochastic duration predictor, so output varies run to run.
        # Fix the seed for reproducible demo audio.
        torch.manual_seed(settings.tts_seed)

    def speak(self, text: str, key: str | None = None) -> Speech:
        cache_id = hashlib.sha256(f"{key or ''}\0{text}".encode("utf-8")).hexdigest()
        path = self.out_dir / f"synth_{cache_id}.wav"
        if path.is_file():
            return Speech(path, 0.0, "synth-cache", text)

        import soundfile as sf
        import torch

        self.load()
        started = time.perf_counter()
        inputs = self._tokenizer(text, return_tensors="pt")
        with torch.no_grad():
            waveform = self._model(**inputs).waveform
        elapsed = time.perf_counter() - started

        sf.write(path, waveform.squeeze().cpu().numpy(),
                 self._model.config.sampling_rate)
        return Speech(path, round(elapsed, 3), "synth", text)


class TtsEngine(TtsBackend):
    """
    Recorded first, synthesised as fallback. This is what the kiosk talks to,
    and the reason swapping strategies later costs nothing.
    """

    def __init__(self, recorded: RecordedTts | None = None,
                 synth: SynthTts | None = None) -> None:
        self.recorded = recorded or RecordedTts()
        self.synth = synth or SynthTts()

    def speak(self, text: str, key: str | None = None) -> Speech:
        if key and self.recorded.has(key):
            return self.recorded.speak(text, key)
        return self.synth.speak(text, key)
