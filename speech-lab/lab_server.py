"""
MTHANDIZI Phase 0 — Speech Lab web server.

Open http://localhost:8077 in a browser, hold the button, speak Chichewa, and see
what the model heard plus how it resolves against the closed sets. Also lets you
type Chichewa and hear the TTS.

This is the tool you and your native-speaker reviewer will actually sit in front of.
It is NOT the production speech service — that is Phase 2 — but the endpoints are
deliberately the same shape so Phase 2 is a hardening job, not a rewrite.

    GET  /            - the lab page
    GET  /health      - liveness + which models are loaded
    POST /asr         - multipart audio -> transcript + closed-set resolutions
    POST /tts         - {"text": "...", "key": "..."} -> wav
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

from lab.asr import AsrEngine, load_audio, trim_silence
from lab.config import settings
from lab.matching import DISTRICTS, MONTHS, SERVICE_INTENTS, YES_NO, resolve

app = FastAPI(title="MTHANDIZI Speech Lab", version="0.1.0")

_asr: AsrEngine | None = None
_tts = None

SLOT_SETS = {
    "intent": SERVICE_INTENTS,
    "district": DISTRICTS,
    "month": MONTHS,
    "yesno": YES_NO,
}


def get_asr() -> AsrEngine:
    global _asr
    if _asr is None:
        _asr = AsrEngine()
        _asr.load()
    return _asr


def get_tts():
    global _tts
    if _tts is None:
        from lab.tts import TtsEngine

        _tts = TtsEngine()
    return _tts


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    page = Path(__file__).parent / "static" / "index.html"
    return page.read_text(encoding="utf-8")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "asr_checkpoint": settings.asr_checkpoint,
        "asr_loaded": _asr is not None,
        "tts_checkpoint": settings.tts_checkpoint,
        "prompts_dir": str(settings.prompts_dir),
        "recorded_prompts": len(list(settings.prompts_dir.glob("*.wav"))),
    }


@app.post("/asr")
async def asr(audio: UploadFile = File(...), slot: str = Form("intent")) -> JSONResponse:
    raw = await audio.read()
    if not raw:
        raise HTTPException(400, "Empty audio upload")

    suffix = Path(audio.filename or "clip.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw)
        tmp_path = Path(tmp.name)

    try:
        samples, duration = load_audio(tmp_path)
        samples = trim_silence(samples)
        duration = len(samples) / 16_000
        result = get_asr().transcribe_array(samples, duration)
    except Exception as exc:  # noqa: BLE001 - surface the real error to the lab UI
        raise HTTPException(500, f"Transcription failed: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    resolutions = {}
    for name, candidates in SLOT_SETS.items():
        m = resolve(result.text, candidates)
        resolutions[name] = {
            "outcome": m.outcome.value,
            "key": m.key,
            "score": m.score,
            "runner_up": m.runner_up,
            "runner_up_score": m.runner_up_score,
        }

    return JSONResponse({
        "text": result.text,
        "seconds": result.seconds,
        "audio_seconds": result.audio_seconds,
        "realtime_factor": round(result.realtime_factor, 3),
        "checkpoint": result.checkpoint,
        "focus": slot,
        "resolutions": resolutions,
    })


class TtsRequest(BaseModel):
    text: str
    key: str | None = None


@app.post("/tts")
def tts(request: TtsRequest) -> FileResponse:
    if not request.text.strip():
        raise HTTPException(400, "text is required")
    try:
        speech = get_tts().speak(request.text, request.key)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Synthesis failed: {exc}") from exc
    return FileResponse(speech.wav_path, media_type="audio/wav",
                        headers={"X-Tts-Source": speech.source,
                                 "X-Tts-Seconds": str(speech.seconds)})


if __name__ == "__main__":
    import uvicorn

    print(f"\nMTHANDIZI Speech Lab -> http://localhost:{settings.port}")
    print(f"ASR checkpoint: {settings.asr_checkpoint}")
    print("First transcription loads the model and will be slow. Later ones are fast.\n")
    uvicorn.run(app, host=settings.host, port=settings.port)
