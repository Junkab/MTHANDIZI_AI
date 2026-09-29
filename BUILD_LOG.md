# MTHANDIZI — Build Log

The honest record. Every phase: what was built, what was actually executed, what the
output was, and what remains unverified. This file feeds the competition write-up
directly — "here is what we verified and how" is a stronger claim than any demo.

---

## Correction — Python version changed from 3.11 to 3.13

**Date:** 2026-09-17, mid-Phase-0 (before the operator had run anything on Windows)

The original guidance told the operator to install Python 3.11, reasoning it would
be the "safe, boring" choice for an ML stack. That was wrong, and the operator
caught it: as of [PEP 664](https://peps.python.org/pep-0664/), Python 3.11 has been
in security-fixes-only mode since October 2025 — **3.11.9 (April 2024) was the last
binary Windows installer ever released for the 3.11 line.** Every release since is
source-only. There was never going to be a "3.11.16 Windows installer" to download.

Rather than guess a replacement version, PyPI's JSON API was checked directly for
real Windows wheel availability before re-pinning anything:

```
torch 2.4.1  -> 0 Windows cp313 wheels   (what was originally pinned)
torch 2.5.1  -> 0 Windows cp313 wheels
torch 2.6.0  -> 1 Windows cp313 wheel    <- first version that supports 3.13
```

`torch` was the one package in the whole stack that actually would have broken on
3.13 with the old pins — every other pinned package (`transformers`, `librosa`,
`soundfile`) ships as a universal `py3-none-any` wheel and was never at risk.
`numpy` and `scipy` needed a minor bump for the same reason as `torch` (their old
pins predate 3.13 wheels); `pydantic-core` was checked and is fine at its existing
pin. Full versions in `speech-lab/requirements.txt`.

`torchaudio` has been dropped entirely — nothing in this project imports it; the
custom `load_audio()` in `lab/asr.py` uses `librosa` directly, so `torchaudio` was
carried over from habit rather than being an actual dependency.

**Lesson applied going forward:** verify package/platform compatibility against the
package index directly rather than reasoning from general knowledge about "which
Python version is safe" — that kind of claim ages out from under a project quickly,
and it did here within the same week.

---


## Phase 0 — Speech Lab

**Date:** 2026-09-17
**Environment:** Linux sandbox, Python 3.12.3, no GPU, **Hugging Face unreachable (HTTP 403)**

### Built

| File | Purpose |
|---|---|
| `lab/config.py` | Single env-loading point |
| `lab/chichewa_text.py` | Normalisation, phonetic folding, prefix stemming, edit distance |
| `lab/metrics.py` | WER, CER, corpus aggregation |
| `lab/matching.py` | Closed-set matcher, intent router, standard answer sets |
| `lab/asr.py` | CLEAR Global ASR wrapper, 5 checkpoints, 16kHz loader, silence trim |
| `lab/tts.py` | Recorded-first TTS with MMS-VITS fallback |
| `benchmark.py` | Phase 0 gate — WER/CER/slot-accuracy/latency report |
| `lab_server.py` + `static/index.html` | Browser lab for recording and listening |
| `tests/test_core.py` | 59 tests |

### Actually executed

```
$ python3 -m pytest tests/ -q
59 passed in 0.41s
```

Live matcher check, executed:

```
'ndikufuna kulembeca mwana wanga'  -> ACCEPT  BIRTH_REGISTRATION (1.0)
'ndikudwara'                       -> ACCEPT  HOSPITAL_QUEUE     (1.0)
'zzz qqq'                          -> REJECT  None               (0.1667)
'Lirongwe'                         -> ACCEPT  Lilongwe           (1.0)
'Musuzu'                           -> ACCEPT  Mzuzu              (0.6667)
'Burantayala'                      -> ACCEPT  Blantyre           (0.6364)
```

### Bugs found by writing tests first

Four failures on the first run. All were real defects in the logic, not bad tests:

1. **`stem_tokens` could not handle prefixes written as separate words.**
   `"ku Lilongwe"` tokenised to `["ku", "lilogve"]` and never matched `"Lilongwe"`.
   Fixed by dropping standalone prefix tokens when other tokens remain — while
   keeping the single word `"ndi"` intact.

2. **Prefix-stripping caused false rejections.** `"Musuzu"` (a plausible mishearing of
   `"Mzuzu"`) was stripped to `"suzu"` and scored 0.60, below the 0.62 accept
   threshold — rejected. Fixed by scoring both the stemmed and unstemmed forms and
   keeping the better of the two. Now 0.667, accepted.

3. **`contains_any` produced a false YES.** The sliding-character-window version
   matched `"indi"` inside `"sindikudziwa"` ("I don't know") against `"inde"` ("yes")
   at exactly the 0.75 threshold. **This is the single most dangerous error the system
   can make** — reading a refusal as consent. Fixed by comparing whole-token n-grams
   instead of arbitrary character windows, which removes the class entirely.

4. A CER assertion was too tight (asserted <5%, actual 6.5% for 2 edits in 31 chars).
   The test threshold was wrong, not the metric. Corrected.

### NOT verified — you must run these

- **The ASR model has never been loaded in this environment.** Hugging Face returns
  403 from the sandbox. `lab/asr.py` is written against the `transformers` pipeline
  API you already ran successfully on your own machine, but the code itself is
  untested. First run on your Windows machine is the real test.
- **TTS has never been run.** `facebook/mms-tts-nya` has not been confirmed to
  resolve. If it 404s, fall back to CLEAR Global's TTS or recorded human prompts.
- **`lab_server.py` has never been started.** FastAPI/uvicorn are not installed here.
- **Browser mic capture is untested.** Note that `getUserMedia` requires either
  `localhost` or HTTPS — it will not work over a plain-HTTP LAN IP without a cert.
- **No real audio has been benchmarked.** All accuracy claims so far are against
  synthetic corruptions written by hand. They prove the matcher logic, not the model.

### Prior evidence carried forward

The operator independently verified on Windows, CPU, before this phase began:
`CLEAR-Global/w2v-bert-2.0-chichewa_34_307h` transcribed a real 4.03s recording of
*"Ndikufuna kulembetsa mwana wanga"* word-for-word correctly. That is the foundation
this entire architecture rests on.

### Open decisions

- Checkpoint (307h vs a smaller one) — **blocked on benchmark data**
- Matcher thresholds, possibly per-slot — **blocked on benchmark data**
- TTS strategy (synth vs recorded human) — **blocked on listening test**

---

## Architecture note — kiosk targets both PC and phone

Operator confirmed the kiosk will run on **both PC and phone**, not phone alone.
This changes one thing and confirms another:

- **Confirms:** the local speech sidecar (Phase 0, Section 2.3) is the right call.
  A phone cannot run a 2.4GB ASR model; it was never going to.
- **Changes:** there will be two kiosk *clients* sharing one workflow engine and one
  speech-service API — an Android client (tablet/phone) and a Windows/desktop client
  (PC kiosk). Both talk to the same FastAPI sidecar. On a PC kiosk the sidecar can run
  on the same machine (localhost); on a phone kiosk it runs on a nearby PC/mini-PC
  over LAN. This gets designed explicitly into the workflow engine (Phase 3, pure
  Kotlin/JVM, no platform dependency) and the client layer is platform-specific UI
  on top of it. Flagged here so it isn't a surprise at Phase 5.

---

## Phase 1 — Chichewa Language Pack

**Date:** 2026-09-17
**Environment:** same sandbox as Phase 0, no network dependency for this phase

### Built

| File | Purpose |
|---|---|
| `pack/chichewa_pack.json` | 49 entries: greeting, all 4 workflows' questions, review/confirm, errors, UI, lexicon |
| `tool/lint_pack.py` | Structural linter, dev + `--strict` (release-blocking) modes |
| `tool/review.html` | Native-speaker review tool: load, listen, edit, approve/reject, export |
| `tests/test_lint.py` | 15 tests |

### Actually executed

```
$ python3 -m pytest tests/ -q
15 passed in 0.01s

$ python3 tool/lint_pack.py
49 entries, 0/49 reviewed
mode: dev (structural only)
Clean.

$ python3 tool/lint_pack.py --strict
49 entries, 0/49 reviewed
mode: STRICT (release)
UNREVIEWED  x49
exit: 1
```

Both outcomes are correct: the pack is structurally sound, and release mode
correctly refuses to pass because no human has approved anything yet.

### Bugs found by writing tests first

1. **False positive on the brand name.** `app_name: "Mthandizi"` in both languages
   tripped `IDENTICAL_TO_EN` — correctly, since that check exists for forgotten
   translations, but a brand name is legitimately identical. Fixed with an explicit
   `"exempt_identical": true` flag rather than weakening the check.
2. **Leaf-detector missed entries missing `chi` entirely.** `walk_leaves` only
   recursed on `"chi" in node`; an entry with `en` but no `chi` was invisible to the
   linter rather than flagged. Silent > loud is the wrong failure mode for a lint
   tool. Fixed by triggering on `"chi" in node or "en" in node`.

Both are now regression tests.

### NOT verified — you must run these

- No native speaker has reviewed any of the 49 entries. This is the single most
  important open item in the whole project so far — everything downstream assumes
  Chichewa correctness that has not yet been checked by a human who speaks it.
- No prompt audio has been recorded. Recording happens **after** review, once text
  is stable, to avoid re-recording.
- `tool/review.html` has not been opened in a real browser in this environment
  (sandbox has no GUI). Logic was tested by reading the code carefully, not by
  running it — flagged honestly rather than claimed as verified.

### Open decisions

- Who reviews the pack, and by when — operator has not yet confirmed access to a
  native speaker. Workable either way (see README) but timeline-relevant.

---

## Phase 2 — Speech Service (FastAPI sidecar)

*Not started. Gated on Phase 0 benchmark data (checkpoint choice affects sidecar
sizing) and informed by the PC+phone architecture note above.*
