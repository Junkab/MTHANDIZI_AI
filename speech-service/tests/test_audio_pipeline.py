"""
Tests for app/audio_pipeline.py. Pure numpy - no model, no network, runs
anywhere. The ASR-dependent parts of preprocess() (trim_silence, which lives in
speech-lab/lab/asr.py) are exercised indirectly through the app.audio_pipeline
imports, which is fine - trim_silence itself needs no model either.
"""

import numpy as np
import pytest

from app.audio_pipeline import MIN_PEAK_TO_BOOST, TARGET_PEAK, apply_agc, preprocess


def sine(seconds: float, amplitude: float, sample_rate: int = 16_000) -> np.ndarray:
    t = np.linspace(0, seconds, int(seconds * sample_rate), endpoint=False)
    return (amplitude * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


# --- AGC -------------------------------------------------------------------------

def test_agc_boosts_quiet_signal_to_target_peak():
    quiet = sine(1.0, amplitude=0.1)
    boosted = apply_agc(quiet)
    assert np.abs(boosted).max() == pytest.approx(TARGET_PEAK, abs=0.01)


def test_agc_does_not_clip_beyond_full_scale():
    loud = sine(1.0, amplitude=0.99)
    boosted = apply_agc(loud)
    assert np.abs(boosted).max() <= 1.0


def test_agc_leaves_near_silence_alone():
    """Boosting noise floor into a fake 'loud' signal would be worse than doing
    nothing - the downstream silence check needs the real peak to work."""
    near_silent = sine(1.0, amplitude=0.001)
    result = apply_agc(near_silent)
    assert np.abs(result).max() < MIN_PEAK_TO_BOOST


def test_agc_handles_empty_array():
    result = apply_agc(np.array([], dtype=np.float32))
    assert len(result) == 0


def test_agc_reduces_an_already_loud_signal_toward_target():
    already_loud = sine(1.0, amplitude=1.0)
    result = apply_agc(already_loud)
    assert np.abs(result).max() == pytest.approx(TARGET_PEAK, abs=0.01)


# --- preprocess() end to end (still no model) -------------------------------------

def test_preprocess_reports_silence_correctly():
    silent = np.zeros(16_000, dtype=np.float32)
    _, report = preprocess(silent, sample_rate=16_000)
    assert report["likely_silent"] is True
    assert report["agc_applied"] is False


def test_preprocess_reports_normal_speech_correctly():
    speech_like = sine(2.0, amplitude=0.3)
    _, report = preprocess(speech_like, sample_rate=16_000)
    assert report["likely_silent"] is False
    assert report["agc_applied"] is True
    assert report["peak_after_agc"] == pytest.approx(TARGET_PEAK, abs=0.01)


def test_preprocess_trims_leading_and_trailing_silence():
    silence = np.zeros(8_000, dtype=np.float32)
    speech = sine(1.0, amplitude=0.5)
    padded = np.concatenate([silence, speech, silence])
    processed, report = preprocess(padded, sample_rate=16_000)
    assert report["trimmed_seconds"] < report["original_seconds"]
    assert report["silence_trimmed_seconds"] > 0
