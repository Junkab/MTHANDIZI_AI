# MTHANDIZI — Speech Service (Phase 2)

The real, always-on speech sidecar. This is what runs on the kiosk's compute
unit and what both clients (Android and the Windows/PC client — see the
"kiosk targets both PC and phone" note in `BUILD_LOG.md`) talk to over a
private LAN link, with no internet required.

**Not a rewrite of Phase 0's lab server** — it imports the exact same
`lab/asr.py`, `lab/tts.py`, and `lab/matching.py` from `speech-lab/`, including
the collision fix proven against your real benchmark data. `speech-lab` stays
the R&D/benchmark tool; this is what actually runs.

## Running it

No separate install — this service shares `speech-lab`'s venv (see
`app/config.py` for exactly why). If Phase 0's setup is done, this works.

```
run_service.bat
```

First start eager-loads the ASR model (~2 minutes) and synthesizes/caches the
fixed birth-registration prompts. The first run can take a few extra minutes;
later service starts reuse the WAV cache. This moves the expensive TTS work out
of the citizen's conversation. For faster iteration while developing, use
`run_service_lazy.bat` instead, which skips startup warm-up.

Check it's alive:
```
curl http://localhost:8090/health
```

Wait for `asr_loaded: true` and `tts_prompts_ready: true` before starting the
kiosk. `tts_prompts_ready: false` means fixed prompts have not finished warming.

Full endpoint documentation: **`API_CONTRACT.md`** — read this before wiring
either client up to the service; it's the single source of truth both clients
get built against.

## What's new here vs. Phase 0's lab server

- **Eager model loading at startup**, not lazy — a kiosk shouldn't make its
  first real citizen eat a 2-minute delay.
- **AGC (automatic gain control)** — normalises quiet speech before it reaches
  the model (`app/audio_pipeline.py`).
- **Silence detection before the model runs** — a silent clip returns
  instantly without paying for a transcription attempt.
- **CORS enabled** — both clients call this from a browser/webview context on
  a different device; Phase 0's lab server didn't need this since it only
  served its own same-origin page.
- **`/models` endpoint** — lists available checkpoints, informational for now.
- **Real regression tests using your actual benchmark failures**, not just
  synthetic ones — see `tests/test_main.py`.

## A real bug found while building this phase

Building the audio-preprocessing tests surfaced that `trim_silence()`
(`speech-lab/lab/asr.py`) had a bare `except Exception` that silently
swallowed a missing-`librosa` `ImportError` — meaning silence trimming could
become a **permanent, silent no-op** with zero indication anything was wrong.
Fixed at the source (in `speech-lab`, not duplicated here), now warns loudly
if the dependency is missing while still failing safely on genuine per-clip
edge cases. Full story in `BUILD_LOG.md`.

## Testing

```
run_tests.bat
```

18 tests, all runnable without a model or network — the ASR/TTS engines are
mocked with canned responses so these tests prove the *service's own logic*
(routing, validation, response shape, matcher integration) rather than
re-testing the model itself. One test directly replays the real
`sindikufuna` → NO case from your benchmark run through the actual HTTP
endpoint, to prove the fix holds at the API layer, not just inside the
matcher function.

## Known gaps — honest, not hidden

- **TTS is untested end-to-end.** The endpoint's shape works (mocked test
  passes); nobody has confirmed `facebook/mms-tts-nya` actually resolves or
  sounds right. This is the same open item from Phase 0 — still open.
- **No literal ASR n-best.** See the module docstring in `app/main.py` for
  why the matcher's own top+runner-up scoring was used instead, and what a
  real n-best decoder would require if it's wanted later.
- **VAD is energy-based** (via `librosa.effects.trim`), not a trained model
  like silero-vad. Documented as a known gap with a clear TODO in
  `app/audio_pipeline.py` — a real VAD model is a drop-in replacement, not a
  redesign.
- **No hot-swap between checkpoints.** Changing `MTHANDIZI_ASR_CHECKPOINT`
  needs a restart.
- **Never load-tested.** No concurrency testing has happened — what happens
  if two citizens' clips arrive at once is unknown. The FastAPI/uvicorn
  default is fine for a single-kiosk demo; revisit if multiple kiosks ever
  share one sidecar.

## Phase 2 gate

- [x] `/health`, `/models`, `/asr`, `/tts` all implemented
- [x] AGC + silence detection running before every transcription
- [x] Real bug found and fixed (`trim_silence` silent failure) with a
      regression test
- [x] 18/18 tests passing (mocked — no model/network needed)
- [x] The real `sindikufuna`/`sindikudziwa` fix proven at the HTTP layer, not
      just the matcher layer
- [x] `API_CONTRACT.md` written — both future clients build against this
- [ ] **Never run against the real model in this environment** (Hugging Face
      unreachable from the sandbox, same as every prior phase) — operator
      needs to start `run_service.bat` and confirm `/health` shows
      `asr_loaded: true`, then POST a real recording to `/asr` and check the
      response
- [ ] TTS never listened to
- [ ] No client (Android or Windows) has called this service yet — that's
      Phase 5+ (Android foundation) and the not-yet-started Windows client
