# MTHANDIZI Speech Service — API Contract

Both the Android client and the Windows/PC client are built against THIS
document, not against each other's source code or assumptions. When either
client changes what it sends or expects, this file changes in the same commit.
See the build prompt's quality-bar section: "cross-check every client/server
contract... against the other side's actual source" - this file IS that check,
written down so both sides get built against the same thing.

Base URL: `http://<kiosk-LAN-IP>:8090` (default port 8090, see
`app/config.py::ServiceSettings.port`, overridable via `MTHANDIZI_SERVICE_PORT`).

No authentication. This is a private-LAN-only service (see SECURITY.md, once
written in Phase 15) — it is not exposed to the public internet and the network
itself is the trust boundary.

---

## GET /health

Liveness and model-status check. Clients should poll this before assuming the
service is ready, especially right after the kiosk boots (model load can take
~2 minutes on first start).

**Response 200:**
```json
{
  "status": "ok",
  "uptime_seconds": 143.2,
  "asr_checkpoint": "CLEAR-Global/w2v-bert-2.0-chichewa_34_307h",
  "asr_loaded": true,
  "asr_load_seconds": 128.4,
  "eager_load": true
}
```

`asr_loaded: false` means /asr will incur a one-time load delay on its next
call (only possible if `eager_load` is false — the kiosk's real launcher,
`run_service.bat`, always eager-loads).

---

## GET /models

Which ASR checkpoints exist and which one is active. Informational only -
switching checkpoints requires a service restart with
`MTHANDIZI_ASR_CHECKPOINT` set; there is no runtime hot-swap.

**Response 200:**
```json
{
  "active": "CLEAR-Global/w2v-bert-2.0-chichewa_34_307h",
  "available": {
    "307h": "CLEAR-Global/w2v-bert-2.0-chichewa_34_307h",
    "136h": "CLEAR-Global/w2v-bert-2.0-chichewa_34_136h",
    "102h": "CLEAR-Global/w2v-bert-2.0-chichewa_34_102h",
    "68h":  "CLEAR-Global/w2v-bert-2.0-chichewa_34_68h",
    "34h":  "CLEAR-Global/w2v-bert-2.0-chichewa_34_34h"
  },
  "note": "..."
}
```

---

## POST /asr

Transcribe a spoken clip, optionally resolved against a closed answer set.

**Request:** `multipart/form-data`
- `audio` (file, required): WAV, any sample rate/channel count (server
  resamples to 16kHz mono). Max size: 15 MB (`MTHANDIZI_MAX_UPLOAD_BYTES`).
- `slot` (query string, optional): one of `intent`, `district`, `month`,
  `yesno`. Omit for a raw transcript with no matcher resolution (e.g. a name
  or free-text field).

**Response 200 (silent clip - detected BEFORE the model runs, so this is
fast):**
```json
{
  "text": "",
  "likely_silent": true,
  "preprocessing": { "...": "see below" },
  "resolution": null
}
```

**Response 200 (normal transcription, no slot):**
```json
{
  "text": "ndikudwala",
  "seconds": 2.66,
  "audio_seconds": 2.6,
  "realtime_factor": 1.02,
  "checkpoint": "CLEAR-Global/w2v-bert-2.0-chichewa_34_307h",
  "likely_silent": false,
  "timing_ms": {
    "upload_read_ms": 0.2,
    "temp_write_ms": 0.4,
    "audio_load_ms": 25.0,
    "preprocess_ms": 8.0,
    "inference_wall_ms": 3200.0,
    "model_ms": 3100.0,
    "total_ms": 3250.0
  },
  "preprocessing": {
    "original_seconds": 3.1,
    "trimmed_seconds": 2.6,
    "silence_trimmed_seconds": 0.5,
    "peak_before_agc": 0.31,
    "peak_after_agc": 0.7,
    "agc_applied": true,
    "likely_silent": false
  },
  "resolution": null
}
```

`timing_ms` reports the server-side cost of upload reading, temporary-file
writing, audio loading, preprocessing, queued inference wall time, model time,
and total request time. It is intended to distinguish speech-model latency from
service and audio-pipeline overhead.

**Response 200 (with `?slot=yesno`), same shape plus `resolution`:**
```json
{
  "...": "same fields as above, plus:",
  "resolution": {
    "slot": "yesno",
    "outcome": "ACCEPT",
    "key": "NO",
    "score": 1.0,
    "runner_up": "YES",
    "runner_up_score": 0.25
  }
}
```

`outcome` is one of `ACCEPT`, `DISAMBIGUATE`, `REJECT` - see
`speech-lab/lab/matching.py` for the full semantics. **The client's workflow
logic must handle all three**, not just ACCEPT:
- `ACCEPT` → fill the slot with `key`.
- `DISAMBIGUATE` → ask the citizen to confirm `key` specifically (e.g. "Did
  you mean Blantyre?"), don't silently accept it.
- `REJECT` (`key: null`) → re-ask, following the three-strike escalation in
  the build prompt (Section 4.5).

**Error responses:**
- `400` - empty upload, or an unrecognised `slot` value.
- `413` - upload exceeds `MTHANDIZI_MAX_UPLOAD_BYTES`.
- `500` - transcription failed (model error). Message included in the body.

**ON "N-BEST":** there is no separate multi-hypothesis list in this response.
`resolution.key` + `resolution.runner_up` + the score gap between them IS the
practical n-best signal this project uses - see the module docstring in
`app/main.py` for why a literal ASR-level n-best decoder was deliberately not
built in this phase.

---

## POST /tts

Synthesise or retrieve a spoken prompt.

**Request:** `application/json`
```json
{ "text": "Moni. Ndine Mthandizi.", "key": "greeting_idle" }
```
`key` (optional): a language-pack prompt ID (see `chichewa_pack.json`'s
`speech.*.audio` field names, minus the `.wav`). If a matching pre-recorded
file exists, it's served directly (fast, perfect pronunciation). If omitted or
not found, `text` is synthesised via `facebook/mms-tts-nya`.

**Response 200:** raw `audio/wav` bytes.

Response headers:
- `X-Tts-Source`: `"recorded"` or `"synth"` - clients can use this to decide
  whether to cache the result (a synthesised clip is deterministic per-text
  given the fixed seed in `TtsEngine`, so caching is safe; a recorded clip
  never needs re-fetching once cached).
- `X-Tts-Seconds`: synthesis time (`0` for recorded prompts - no synthesis
  happened).

**Error responses:**
- `400` - empty/whitespace-only `text`.
- `500` - synthesis failed.

**STATUS: UNTESTED END-TO-END.** `facebook/mms-tts-nya` has never actually
been confirmed to resolve or produce audible Chichewa - see BUILD_LOG.md,
Phase 0's still-open gaps. This endpoint's request/response *shape* is
implemented and covered by a mocked test, but nobody has listened to real
output from it yet. Do not treat this endpoint as proven the way /asr now is.

---

## Versioning

No version prefix in the URL yet (single-client, single-deployment stage).
When a breaking change is needed, this file's diff is the signal to bump
`app.main:app`'s `version=` and coordinate both clients' update together
rather than silently drifting.
