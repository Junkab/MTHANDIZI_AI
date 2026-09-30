"""
MTHANDIZI Speech Service — engine lifecycle.

One AsrEngine, one TtsEngine, loaded once and reused across every request. The
Phase 0 lab server loaded the ASR model lazily (on first request) - fine for
exploratory use, wrong for a kiosk, where the first real citizen should never
be the one who eats a 2-minute model-load delay. This service loads eagerly at
startup by default (see config.settings.eager_load_asr).
"""

from __future__ import annotations

import time
from threading import Lock

from .config import settings

_asr = None
_tts = None
_asr_load_seconds: float | None = None
_tts_prompts_warmed = False
_asr_lock = Lock()

KIOSK_PROMPTS = (
    "Ndine Mthandizi. Ndingakuthandizeni bwanji lero?",
    "Mukufuna kulembetsa mwana wanu wobadwa kumene, ndi choncho?",
    "Dzina la mwana ndi ndani?",
    "Mwana anabadwa liti? Nenani tsiku, mwezi ndi chaka.",
    "Mwana anabadwira kuti?",
    "Dzina la amayi a mwana ndi ndani?",
    "Dzina la abambo a mwana ndi ndani? Mungasiye.",
    "Muli mmudzi wanji?",
    "Muli mboma lanji?",
)


def get_asr():
    global _asr, _asr_load_seconds
    if _asr is None:
        from lab.asr import AsrEngine

        started = time.perf_counter()
        _asr = AsrEngine(settings.asr_checkpoint)
        _asr.load()
        _asr_load_seconds = round(time.perf_counter() - started, 2)
    return _asr


def transcribe_array(samples, audio_seconds):
    with _asr_lock:
        return get_asr().transcribe_array(samples, audio_seconds)


def get_tts():
    global _tts
    if _tts is None:
        from lab.tts import TtsEngine

        _tts = TtsEngine()
    return _tts


def asr_is_loaded() -> bool:
    return _asr is not None


def asr_load_seconds() -> float | None:
    return _asr_load_seconds


def warm_up() -> None:
    """Called at startup when eager loading is enabled."""
    get_asr()


def warm_up_tts_prompts() -> None:
    """Cache fixed birth-registration prompts before the kiosk serves users."""
    global _tts_prompts_warmed
    tts = get_tts()
    for index, text in enumerate(KIOSK_PROMPTS, start=1):
        speech = tts.speak(text)
        print(f"[startup] TTS prompt {index}/{len(KIOSK_PROMPTS)} ready ({speech.source}).")
    _tts_prompts_warmed = True


def tts_prompts_warmed() -> bool:
    return _tts_prompts_warmed
