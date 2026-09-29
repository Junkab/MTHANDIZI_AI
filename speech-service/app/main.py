"""
MTHANDIZI Speech Service (Phase 2)

The FastAPI sidecar that runs on the kiosk's local compute unit (a PC or
mini-PC). Both the Android client and the Windows/PC client talk to this over
a private LAN link - see the "kiosk targets both PC and phone" architecture
note in BUILD_LOG.md. No internet connection is required for any endpoint here.

    GET  /health          - liveness, model status, uptime
    GET  /models           - which ASR checkpoints exist, which is active
    POST /asr               - wav upload -> transcript (+ matcher resolution if
                              a slot is specified)
    POST /tts                - text -> wav audio

ON "N-BEST" (a term used in the original build spec, Section 2.3)
--------------------------------------------------------------------
This service does NOT implement literal ASR n-best (multiple raw decode
hypotheses from beam search). That would need bypassing the transformers
pipeline for raw logits and a CTC beam-search decoder (pyctcdecode + a
language model) - a real engineering project of its own, and one likely to hit
the same "needs a C++/Rust toolchain on Windows" trap this project already
escaped once with `tokenizers` (see BUILD_LOG.md). Rather than fake it, /asr
instead exposes what the project's OWN architecture (Section 4 of the build
prompt) already treats as the real confidence signal for a closed-set slot:
the matcher's top match plus its runner-up and the score gap between them -
proven on real benchmark data (Phase 0, 2026-09-19) to correctly flag
uncertain cases (see the DISAMBIGUATE path). If a real literal n-best decoder
is wanted later, it's a clean drop-in at the AsrEngine layer, not a redesign
here.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from . import engines
from .audio_pipeline import preprocess
from .config import settings

START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.eager_load_asr:
        print(f"[startup] Eagerly loading ASR checkpoint: {settings.asr_checkpoint}")
        print("[startup] This can take a couple of minutes on first run.")
        engines.warm_up()
        print(f"[startup] ASR loaded in {engines.asr_load_seconds()}s.")
        print("[startup] Preparing fixed kiosk speech prompts; first run may take a few minutes.")
        engines.warm_up_tts_prompts()
        print("[startup] Speech prompts ready. Service ready.")
    else:
        print("[startup] Lazy load mode - model loads on first /asr request.")
    yield
    # No shutdown work needed - nothing to flush or close explicitly.


app = FastAPI(title="MTHANDIZI Speech Service", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allow_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- health & introspection -----------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "asr_checkpoint": settings.asr_checkpoint,
        "asr_loaded": engines.asr_is_loaded(),
        "asr_load_seconds": engines.asr_load_seconds(),
        "eager_load": settings.eager_load_asr,
        "tts_prompts_ready": engines.tts_prompts_warmed(),
    }


@app.get("/models")
def models() -> dict:
    from lab.asr import CHECKPOINTS

    return {
        "active": settings.asr_checkpoint,
        "available": CHECKPOINTS,
        "note": (
            "Only the active checkpoint is loaded into memory. Switching requires "
            "a service restart with MTHANDIZI_ASR_CHECKPOINT set - hot-swapping "
            "checkpoints at runtime is not implemented."
        ),
    }


# --- ASR --------------------------------------------------------------------------

SLOT_SETS_NAMES = ("intent", "district", "month", "yesno")


@app.post("/asr")
async def asr(
    audio: UploadFile = File(...),
    slot: str | None = Query(
        default=None,
        description=(
            f"Optional. One of {SLOT_SETS_NAMES} to also resolve the transcript "
            "against a closed answer set (see module docstring on why this "
            "replaces literal n-best). Omit for free-dictation / raw transcript only."
        ),
    ),
) -> dict:
    from lab.asr import load_audio
    from lab.matching import (
        DISTRICTS,
        MONTHS,
        SERVICE_INTENTS,
        YES_NO,
        classify_intent,
        resolve,
    )

    slot_sets = {
        "intent": SERVICE_INTENTS,
        "district": DISTRICTS,
        "month": MONTHS,
        "yesno": YES_NO,
    }

    request_started = time.perf_counter()
    timings = {}
    raw = await audio.read()
    timings["upload_read_ms"] = round((time.perf_counter() - request_started) * 1000, 1)
    if not raw:
        raise HTTPException(400, "Empty audio upload")
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(413, f"Audio exceeds {settings.max_upload_bytes} bytes")

    suffix = Path(audio.filename or "clip.wav").suffix or ".wav"
    write_started = time.perf_counter()
    with tempfile.NamedTemporaryFile(
        suffix=suffix, delete=False, dir=settings.tmp_dir
    ) as tmp:
        tmp.write(raw)
        tmp_path = Path(tmp.name)
    timings["temp_write_ms"] = round((time.perf_counter() - write_started) * 1000, 1)

    try:
        load_started = time.perf_counter()
        samples, _ = load_audio(tmp_path)
        timings["audio_load_ms"] = round((time.perf_counter() - load_started) * 1000, 1)
        preprocess_started = time.perf_counter()
        processed, prep_report = preprocess(samples, sample_rate=16_000)
        timings["preprocess_ms"] = round((time.perf_counter() - preprocess_started) * 1000, 1)

        if prep_report["likely_silent"]:
            return {
                "text": "",
                "likely_silent": True,
                "preprocessing": prep_report,
                "resolution": None,
                "timing_ms": {
                    **timings,
                    "total_ms": round((time.perf_counter() - request_started) * 1000, 1),
                },
            }

        inference_started = time.perf_counter()
        result = await run_in_threadpool(
            engines.transcribe_array, processed, len(processed) / 16_000
        )
        timings["inference_wall_ms"] = round((time.perf_counter() - inference_started) * 1000, 1)
    except Exception as exc:  # noqa: BLE001 - surfaced to the caller deliberately
        raise HTTPException(500, f"Transcription failed: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    response = {
        "text": result.text,
        "seconds": result.seconds,
        "audio_seconds": result.audio_seconds,
        "realtime_factor": round(result.realtime_factor, 3),
        "checkpoint": result.checkpoint,
        "likely_silent": False,
        "preprocessing": prep_report,
        "resolution": None,
        "timing_ms": {
            **timings,
            "model_ms": round(result.seconds * 1000, 1),
            "total_ms": round((time.perf_counter() - request_started) * 1000, 1),
        },
    }
    print(f"[asr] timing_ms={response['timing_ms']}")

    if slot:
        if slot not in slot_sets:
            raise HTTPException(400, f"Unknown slot {slot!r}, expected one of {SLOT_SETS_NAMES}")
        match_result = (
            classify_intent(result.text)
            if slot == "intent"
            else resolve(result.text, slot_sets[slot])
        )
        response["resolution"] = {
            "slot": slot,
            "outcome": match_result.outcome.value,
            "key": match_result.key,
            "score": match_result.score,
            "runner_up": match_result.runner_up,
            "runner_up_score": match_result.runner_up_score,
            "confidence": getattr(match_result, "confidence", None),
        }

    return response


# --- TTS --------------------------------------------------------------------------

class TtsRequest(BaseModel):
    text: str
    key: str | None = None


@app.post("/tts")
def tts(request: TtsRequest) -> FileResponse:
    if not request.text.strip():
        raise HTTPException(400, "text is required")
    try:
        speech = engines.get_tts().speak(request.text, request.key)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Synthesis failed: {exc}") from exc
    return FileResponse(
        speech.wav_path,
        media_type="audio/wav",
        headers={"X-Tts-Source": speech.source, "X-Tts-Seconds": str(speech.seconds)},
    )


if __name__ == "__main__":
    import asyncio
    import sys

    import uvicorn

    if sys.platform == "win32":
        # WORKAROUND for a real crash hit on Windows (2026-09-20, operator's
        # machine): Python's default ProactorEventLoop on Windows can throw
        # "OSError: [WinError 64] The specified network name is no longer
        # available" out of its own socket-accept loop under certain
        # conditions (several stacked/stale connections, seen here after a
        # burst of hung curl attempts against a slow-loading server). When
        # that happens, the exception kills the accept loop silently - the
        # process keeps running and LOOKS alive, but stops accepting any new
        # connections at all. This is a known, documented Windows asyncio
        # issue, not specific to this service. The fix: use the older
        # SelectorEventLoop on Windows instead, which doesn't have this
        # failure mode. Slightly less performant under very high concurrency,
        # irrelevant for a single-kiosk sidecar.
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    print(f"MTHANDIZI Speech Service -> http://{settings.host}:{settings.port}")
    uvicorn.run(app, host=settings.host, port=settings.port)
