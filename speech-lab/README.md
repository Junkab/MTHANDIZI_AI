# MTHANDIZI — Speech Lab (Phase 0)

*Lankhulani. Mthandizi akuthandizeni.*

This is **Phase 0** of MTHANDIZI. There is deliberately **no Android code here yet**.

The previous attempt at this project failed because speech was left until late and the
app got built around a keyword matcher pretending to be Chichewa recognition. This
phase exists to make that impossible: we prove the Chichewa speech stack works, with
measured numbers, **before** a single line of Kotlin is written.

---

## What this proves, and what it doesn't

| Component | Status |
|---|---|
| Text normalisation, phonetic folding, stemming | **Verified** — 59 unit tests pass |
| WER / CER metrics | **Verified** — tested against hand-computed cases |
| Closed-set matcher + six-service intent classifier | **Unit-tested** — see current test run; classifier is deterministic and local |
| ASR model integration (`lab/asr.py`) | **Written, not executed here** — Hugging Face is unreachable from the authoring sandbox. You run it. |
| TTS integration (`lab/tts.py`) | **Written, not executed here** — same reason |
| Lab web server | **Written, not executed here** — needs the models |

That distinction is honoured everywhere in this project. Nothing is described as
working unless it was actually run. See `BUILD_LOG.md`.

---

## Setup on Windows

### 1. Python 3.13

**Correction from an earlier version of this README:** it originally called for
Python 3.11, on the assumption that would be the safe/boring choice for the ML
stack. That was wrong for a reason discovered mid-project: as of
[PEP 664](https://peps.python.org/pep-0664/), Python 3.11 is in
security-fixes-only mode — the 3.11.9 installer (April 2024) was the **last**
binary Windows installer ever released for it. Every 3.11 release since is
source-only. So 3.13 it is.

**This mattered in practice, not just in theory.** `torch` 2.4.1 and 2.5.1 —
what this project was originally pinned to — have **no Windows wheel for
Python 3.13 at all**; only `torch` 2.6.0 onward does. `requirements.txt` is
pinned to 2.6.0 for exactly this reason. Every package pin in this project was
checked against PyPI's JSON API to confirm a real `win_amd64` wheel exists for
`cp313` before being pinned — not assumed. See `BUILD_LOG.md`.

If you already downloaded Python 3.13.15, that's the right one — use it.

Verify:
```
py -3.13 --version
```
Expect `Python 3.13.15` (or newer 3.13.x — that's fine, only the 3.13 vs 3.11/3.12/3.14 line matters).

### 2. Create the virtual environment

From the `speech-lab` folder:
```
py -3.13 -m venv venv
venv\Scripts\activate
```
Your prompt should now start with `(venv)`.

### 3. Install dependencies

```
python -m pip install --upgrade pip
pip install -r requirements.txt
```
This pulls ~2GB of PyTorch. Slow connection: leave it running. If `torch` fails
to find a wheel and starts trying to compile from source, something is wrong —
stop and send me the exact error; do not let it attempt a source build.

### 4. Run the tests — do this before anything else

```
python -m pytest tests\ -v   REM works the same regardless of Python version
```
**Expect 59 passed.** These need no model and no network. If they fail, stop and send
me the output; something is wrong with the environment, not the models.

### 5. Set up the model cache

So the models live somewhere predictable and the kiosk can run offline later:
```
setx HF_HOME "%USERPROFILE%\.mthandizi\hf"
```
Close and reopen the terminal, reactivate the venv.

Optional but recommended — a Hugging Face token removes the rate-limit warning you
saw and downloads faster. Get one free at huggingface.co → Settings → Access Tokens:
```
setx HF_TOKEN "hf_your_token_here"
```

### 6. Enable Developer Mode (fixes the symlink warning)

The warning you saw about symlinks means model files are duplicated on disk rather
than linked — it wastes space but works. To fix it: Windows Settings → *System* →
*For developers* → turn on **Developer Mode**.

---

## Running it

### The lab

```
python lab_server.py
```
Open <http://localhost:8077>. Hold the button, speak Chichewa, watch the transcript
and see how it resolves against each closed set.

The **first** transcription downloads and loads the model — expect several minutes.
Every one after that is fast.

### The benchmark — this is the Phase 0 gate

First record your utterances. `UTTERANCES.md` lists exactly what to say and what to
name each file. Put the WAVs in `audio\recordings\`, then copy
`audio\manifest.example.csv` to `audio\manifest.csv` and fill in every row.

Then:
```
python benchmark.py --checkpoints 307h
```
Or compare checkpoints:
```
python benchmark.py --checkpoints 307h 68h
```

It prints a table and writes `reports\benchmark_<timestamp>.json`.

**Paste that table back to me.** It decides three things: which checkpoint ships,
what the matcher thresholds should be, and whether the kiosk needs a faster model.

---

## The three numbers that matter

**WER** — how often whole words are wrong. Expect around 0.40. The kiosk now starts
with an open Chichewa question; the deterministic phrase classifier routes clear
service requests and asks conversational follow-ups for uncertain ones. This is
still exposed to ASR errors and needs testing on varied real speakers. Follow-up
workflow slots continue to use closed-set matching where appropriate.

**CER** — how close the characters are. Expect around 0.12. This is the opportunity:
a near-miss word is still recoverable.

**SLOT ACCURACY** — how often a noisy transcript still resolves to the *correct*
closed-set answer after phonetic folding. **This is the real headline number** and the
one to quote to judges. On synthetic fixtures the matcher is at 100%; real audio will
be lower, and we need to know by how much.

---

## Project layout

```
speech-lab/
  lab/
    config.py         one place env is loaded - never load .env elsewhere
    chichewa_text.py  normalisation, phonetic folding, stemming, edit distance
    metrics.py        WER / CER / corpus aggregation
    matching.py       open intent classification, closed-set slot resolution
    asr.py            CLEAR Global Chichewa ASR wrapper
    tts.py            recorded-first, synth-fallback TTS
  tests/test_core.py  59 tests, no model or network needed
  benchmark.py        the Phase 0 gate
  lab_server.py       FastAPI lab + browser recorder
  static/index.html   the lab UI
  UTTERANCES.md       what to record
  audio/              recordings, prompts, manifest
```

---

## Known issues and honest limitations

- **Matcher thresholds are provisional.** `ACCEPT_THRESHOLD = 0.62` was tuned against
  synthetic corruptions, not real ASR output. Two fixtures (`Musuzu`→Mzuzu at 0.667,
  `Burantayala`→Blantyre at 0.636) sit uncomfortably close to it. Real benchmark data
  will move this number, and it may need to be per-slot rather than global.
- **The district list is a first draft**, not checked against an official gazetteer.
- **Chichewa in this repo is unreviewed.** Every phrase here needs a native speaker's
  approval before it goes near a user. That is Phase 1.
- **Single-speaker benchmarks flatter the model.** Get two or three voices.
- **`facebook/mms-tts-nya` is CC-BY-NC** — non-commercial. Fine for the competition,
  not for a commercial deployment. Confirm the model ID resolves before relying on it.
- **No noise testing has happened yet.** Hospital halls are loud. The `n01`–`n12`
  recordings in `UTTERANCES.md` exist to find out how bad it gets.

---

## Phase 0 gate — we move on when all of these are true

- [ ] Python 3.13 venv created, `pip install -r requirements.txt` succeeded
- [ ] `pytest` shows 59 passed
- [ ] At least 24 quiet + 12 noisy Chichewa utterances recorded, 2+ speakers
- [ ] `audio\manifest.csv` filled in
- [ ] `benchmark.py` run against 307h and one smaller checkpoint
- [ ] WER, CER, slot accuracy and latency reported for both
- [ ] TTS listened to, verdict given: synth is good enough / we record a human
- [ ] Checkpoint chosen **with data**

Nothing proceeds to Phase 1 until this is green.
