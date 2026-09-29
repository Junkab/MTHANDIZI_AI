"""
Tests for the FastAPI endpoints in app/main.py.

The ASR and TTS engines are monkeypatched to canned responses - Hugging Face is
unreachable from this environment (see BUILD_LOG.md), so these tests prove the
service's OWN logic (routing, validation, response shape, matcher integration)
is correct, independent of whether the real model happens to be reachable.
Running the service against the real model is the operator's job on their own
machine, same pattern as every other phase.
"""

import io
import os
import wave

os.environ.setdefault("MTHANDIZI_EAGER_LOAD", "false")  # never try to load a real model here

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import engines
from app.main import app

client = TestClient(app)


def make_wav_bytes(seconds: float = 1.0, amplitude: float = 0.4, sample_rate: int = 16_000) -> bytes:
    t = np.linspace(0, seconds, int(seconds * sample_rate), endpoint=False)
    samples = (amplitude * np.sin(2 * np.pi * 220 * t) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(samples.tobytes())
    return buf.getvalue()


class FakeTranscription:
    def __init__(self, text, seconds=0.5, audio_seconds=1.0, checkpoint="fake-checkpoint"):
        self.text = text
        self.seconds = seconds
        self.audio_seconds = audio_seconds
        self.checkpoint = checkpoint
        self.realtime_factor = seconds / audio_seconds if audio_seconds else 0.0


class FakeAsrEngine:
    def __init__(self, canned_text="ndikufuna kulembetsa mwana wanga"):
        self.canned_text = canned_text

    def transcribe_array(self, audio, audio_seconds):
        return FakeTranscription(self.canned_text, audio_seconds=audio_seconds)


class FakeSpeech:
    def __init__(self, path):
        self.wav_path = path
        self.seconds = 0.1
        self.source = "fake"


class FakeTtsEngine:
    def __init__(self, wav_path):
        self.wav_path = wav_path

    def speak(self, text, key=None):
        return FakeSpeech(self.wav_path)


@pytest.fixture(autouse=True)
def reset_engines():
    """Every test starts with a clean engine cache so mocks don't leak between tests."""
    engines._asr = None
    engines._tts = None
    engines._asr_load_seconds = None
    yield
    engines._asr = None
    engines._tts = None
    engines._asr_load_seconds = None


# --- /health & /models, no model needed at all ------------------------------------

def test_health_reports_not_loaded_before_any_request():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["asr_loaded"] is False
    assert body["eager_load"] is False  # set via env var above
    assert body["tts_prompts_ready"] is False


def test_models_lists_checkpoints_without_loading_anything():
    r = client.get("/models")
    assert r.status_code == 200
    body = r.json()
    assert body["active"] == "CLEAR-Global/w2v-bert-2.0-chichewa_34_307h"
    assert "307h" in body["available"]
    assert engines.asr_is_loaded() is False  # listing must not trigger a load


# --- /asr --------------------------------------------------------------------------

def test_asr_rejects_empty_upload():
    r = client.post("/asr", files={"audio": ("clip.wav", b"", "audio/wav")})
    assert r.status_code == 400


def test_asr_rejects_unknown_slot(monkeypatch):
    monkeypatch.setattr(engines, "get_asr", lambda: FakeAsrEngine())
    wav = make_wav_bytes()
    r = client.post("/asr?slot=not_a_real_slot", files={"audio": ("clip.wav", wav, "audio/wav")})
    assert r.status_code == 400


def test_asr_transcribes_without_a_slot(monkeypatch):
    monkeypatch.setattr(engines, "get_asr", lambda: FakeAsrEngine("ndikudwala"))
    wav = make_wav_bytes()
    r = client.post("/asr", files={"audio": ("clip.wav", wav, "audio/wav")})
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "ndikudwala"
    assert body["resolution"] is None
    assert body["likely_silent"] is False
    assert body["timing_ms"]["model_ms"] >= 0
    assert body["timing_ms"]["total_ms"] >= body["timing_ms"]["model_ms"]


def test_asr_resolves_against_a_slot(monkeypatch):
    """End-to-end through the real resolve() matcher - this is the part that
    actually matters, proven on real benchmark data in Phase 0."""
    monkeypatch.setattr(engines, "get_asr", lambda: FakeAsrEngine("ndikudwala"))
    wav = make_wav_bytes()
    r = client.post("/asr?slot=intent", files={"audio": ("clip.wav", wav, "audio/wav")})
    assert r.status_code == 200
    body = r.json()
    assert body["resolution"]["outcome"] == "ACCEPT"
    assert body["resolution"]["key"] == "HOSPITAL_QUEUE"


def test_asr_intent_returns_all_six_way_classifier_confidence(monkeypatch):
    monkeypatch.setattr(engines, "get_asr", lambda: FakeAsrEngine("ndikufuna chikalata cha malo"))
    wav = make_wav_bytes()
    response = client.post("/asr?slot=intent", files={"audio": ("clip.wav", wav, "audio/wav")})
    assert response.status_code == 200
    resolution = response.json()["resolution"]
    assert resolution["key"] == "LAND_REGISTRATION"
    assert resolution["outcome"] == "ACCEPT"
    assert resolution["confidence"] == "high"
    assert resolution["score"] == 1.0


def test_asr_detects_silence_before_calling_the_model(monkeypatch):
    """A silent clip must never reach the (expensive) ASR model at all."""
    calls = []
    monkeypatch.setattr(
        engines, "get_asr",
        lambda: (_ for _ in ()).throw(AssertionError("ASR should not be called for silence")),
    )
    silent_wav = make_wav_bytes(amplitude=0.0)
    r = client.post("/asr", files={"audio": ("clip.wav", silent_wav, "audio/wav")})
    assert r.status_code == 200
    assert r.json()["likely_silent"] is True


def test_asr_uses_the_real_sindikufuna_case_from_the_benchmark(monkeypatch):
    """
    Direct regression for the real bug found in Phase 0's benchmark run: a
    perfect 'sindikufuna' transcription (the pack's real NO phrase) must
    resolve to NO through this same endpoint, not misfire into HELP.
    """
    monkeypatch.setattr(engines, "get_asr", lambda: FakeAsrEngine("sindikufuna"))
    wav = make_wav_bytes()
    r = client.post("/asr?slot=yesno", files={"audio": ("clip.wav", wav, "audio/wav")})
    assert r.json()["resolution"]["key"] == "NO"


# --- /tts --------------------------------------------------------------------------

def test_tts_rejects_empty_text():
    r = client.post("/tts", json={"text": "  "})
    assert r.status_code == 400


def test_tts_returns_audio(monkeypatch, tmp_path):
    fake_wav = tmp_path / "out.wav"
    fake_wav.write_bytes(make_wav_bytes())
    monkeypatch.setattr(engines, "get_tts", lambda: FakeTtsEngine(fake_wav))
    r = client.post("/tts", json={"text": "Moni"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert r.headers["x-tts-source"] == "fake"
