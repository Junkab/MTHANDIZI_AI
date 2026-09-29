"""
MTHANDIZI Speech Service — audio preprocessing.

Applied to every clip before it reaches the ASR model. Two stages:

1. Voice activity detection / silence trimming - reuses lab.asr.trim_silence
   (energy-based, via librosa). Cuts dead air at the start/end of a recording,
   which speeds up inference and reduces edge-of-clip hallucination.

2. Automatic gain control - normalises peak amplitude so a citizen speaking
   quietly (common - people often speak softly to a machine in a public hall)
   isn't handed to the model at a whisper-level signal it was never tuned on.

HONEST LIMITATION: this is energy-based VAD (librosa.effects.trim), not a
trained voice-activity model like silero-vad or webrtcvad. The build prompt
(Section 2.3/4.7) names those as the real target. Energy-based trimming is
what's implemented and tested here; swapping in a trained VAD model is a
drop-in replacement for `trim_silence()` - see the TODO below - not a redesign.
"""

from __future__ import annotations

import numpy as np

# Importing .config (even unused directly) ensures ../speech-lab is on sys.path
# before anything here tries `from lab.asr import trim_silence`. Without this,
# whether that import works depends on some OTHER module having been imported
# first - which is exactly the kind of order-dependent bug that only shows up
# in some entry points and not others. See config.py for why the path is set
# up there in the first place.
from . import config as _config  # noqa: F401

# TODO(Phase 2 follow-up): replace with silero-vad or webrtcvad for real speech/
# noise discrimination. Energy-based trimming (current) cannot distinguish a
# quiet voice from loud background noise the way a trained VAD can - it will
# under-trim in a noisy hall and over-trim a soft-spoken citizen. Flagged
# honestly rather than left silently as a known gap; see BUILD_LOG.md.

TARGET_PEAK = 0.7    # normalise to 70% of full scale, leaving headroom
MIN_PEAK_TO_BOOST = 0.01   # don't try to "boost" near-silence into meaningful signal


def apply_agc(audio: np.ndarray) -> np.ndarray:
    """
    Automatic gain control: scale the clip so its peak amplitude hits
    TARGET_PEAK, without amplifying near-silent noise floor recordings into
    something that looks like speech.
    """
    peak = np.abs(audio).max() if len(audio) else 0.0
    if peak < MIN_PEAK_TO_BOOST:
        return audio  # too quiet to safely boost - let ASR/VAD downstream reject it
    gain = TARGET_PEAK / peak
    return np.clip(audio * gain, -1.0, 1.0).astype(audio.dtype, copy=False)


def preprocess(audio: np.ndarray, sample_rate: int) -> tuple[np.ndarray, dict]:
    """
    Full pipeline: trim silence, then apply AGC. Returns the processed audio
    plus a small report of what happened, useful for logging/debugging a
    citizen's failed interaction after the fact.
    """
    from lab.asr import trim_silence  # the proven Phase 0 implementation

    original_len = len(audio)
    trimmed = trim_silence(audio)
    trimmed_len = len(trimmed)

    peak_before = float(np.abs(trimmed).max()) if trimmed_len else 0.0
    processed = apply_agc(trimmed)
    peak_after = float(np.abs(processed).max()) if len(processed) else 0.0

    report = {
        "original_seconds": round(original_len / sample_rate, 3),
        "trimmed_seconds": round(trimmed_len / sample_rate, 3),
        "silence_trimmed_seconds": round((original_len - trimmed_len) / sample_rate, 3),
        "peak_before_agc": round(peak_before, 4),
        "peak_after_agc": round(peak_after, 4),
        "agc_applied": peak_before >= MIN_PEAK_TO_BOOST,
        "likely_silent": peak_before < MIN_PEAK_TO_BOOST,
    }
    return processed, report
