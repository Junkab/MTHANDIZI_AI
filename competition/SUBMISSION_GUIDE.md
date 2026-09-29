# MTHANDIZI — ICTAM Submission Guide

Your precise, sequenced guide from where the project stands now to a
submitted application. Follow the parts in order — each one unblocks the
next.

---

# PART 1 — Running the demo (do this first, so you know it works)

You need TWO things running at once, in TWO separate terminal windows that
you leave open.

## Terminal 1 — Speech service

```
cd C:\Users\MATHEWS JK DUBE\Desktop\18sep_mthandizi\mthandizi\speech-service
run_service.bat
```
Wait for:
```
[startup] Model loaded in ...s. Service ready.
Uvicorn running on http://0.0.0.0:8090
```
**Leave this window open.** This is your real, proven Chichewa ASR/TTS pipeline.

## Terminal 2 — Backend

First time only, install dependencies:
```
cd C:\Users\MATHEWS JK DUBE\Desktop\18sep_mthandizi\mthandizi\backend
npm install
```
Then every time:
```
npm start
```
Wait for:
```
MTHANDIZI backend listening on http://localhost:3000
```
**Leave this window open too.**

You'll also need PostgreSQL running (same as every time you've tested the
backend before) — if you haven't already, start it however you normally do
on Windows (pgAdmin, or the PostgreSQL service in Windows Services).

## Try it

Open a browser to:
```
http://localhost:3000/kiosk/
```
Start by speaking a free-form request (for example, asking to register a
child), confirm the kiosk's spoken understanding, then speak or type each
birth-registration answer, review, and submit. Then open:
```
http://localhost:3000/admin/
```
Log in and confirm your submission is there.

**If anything fails, tell me exactly what you see before moving on** —
better to catch it now than during a recorded demo.

---

# PART 2 — Pushing to GitHub

Do this from the `mthandizi` folder (the one containing `speech-lab`,
`backend`, `workflow-engine`, etc.), in **one** terminal, one command at a
time.

### 1. Check you have Git
```
git --version
```
If not found, install from git-scm.com first.

### 2. Initialize and commit
```
cd C:\Users\MATHEWS JK DUBE\Desktop\18sep_mthandizi\mthandizi
git init
git add -A
git status
```
**Read the `git status` output before committing.** You should NOT see
`node_modules/`, `venv/`, `.env`, or `*.wav` files listed — if you do,
stop and tell me, because it means a `.gitignore` isn't being respected.

If it looks clean:
```
git commit -m "MTHANDIZI: proven speech pipeline, workflow engine, backend, and integrated kiosk demo"
```

### 3. Create the GitHub repo and push

**Easiest — if you have GitHub Desktop:** open it, File → Add Local
Repository, pick this folder, then click "Publish repository." Choose
**Private** unless you want it public before submission.

**Or via command line**, if you have a GitHub account already set up:
```
git remote add origin https://github.com/YOUR-USERNAME/mthandizi.git
git branch -M main
git push -u origin main
```
(Create the empty repo first at github.com/new — don't initialize it with
a README, since you already have one.)

You'll be prompted to log in the first time — a browser window should pop
up for that.

### 4. Get your repo link

Once pushed, your repo URL is:
```
https://github.com/YOUR-USERNAME/mthandizi
```
**This is what goes in the form's "Project Website / Repo" field.**

---

# PART 3 — Recording the demo video (required field)

Follow `competition/DEMO_SCRIPT.md`, Part 1, exactly — it's already written
as a script for this. Rough shape:

1. Screen-record your browser (Windows: Win+Alt+R starts/stops a recording
   via the Xbox Game Bar, or use OBS Studio if you have it).
2. Open `http://localhost:3000/kiosk/`, walk through the birth registration
   flow by voice (mic on, speak clearly).
3. Show the reference number appear, then switch tabs to
   `http://localhost:3000/admin/` and show the same application there.
4. Optionally, briefly mention the "Moni" TTS finding and the 78%→100%
   benchmark story — both make the project look more credible, not less.
5. Keep it under 3-4 minutes. Judges skim.

Upload to YouTube (unlisted is fine) or Google Drive (set sharing to
"anyone with the link can view"), then copy that link for the form.

---

# PART 4 — The ICTAM submission form, field by field

Everything below is **pre-written and character-counted against the exact
limits shown in your screenshots.** Copy-paste directly; nothing here needs
trimming.

## Submission Category

Your options: Fintech and Digital Economy, Agritech, eHealth, Emerging
Technologies, SheCodes Spotlight, Open Source.

**Recommended: Emerging Technologies.** MTHANDIZI's core innovation is the
speech/voice-AI technology itself, applied across four services, not a
health-specific tool — this is the closest honest fit. **eHealth is a
reasonable second choice** if you want to lean into the hospital-queue
angle specifically, but I'd only pick it if you have a specific reason to
believe eHealth judging favors you (e.g. less competition in that
category) — that's a strategic call only you can make, not something I can
verify from here.

## Project Title
```
MTHANDIZI — Voice-First Chichewa Kiosk for Government Services
```
*(62 characters)*

## Description — 1500 char limit (must cover: The Innovation, Target Audience, Impact & Outcomes)
*(1,377 characters — 123 to spare)*
```
MTHANDIZI is a voice-first kiosk letting Malawian citizens register a birth, join a hospital queue, apply for a national ID, or request a passport by speaking Chichewa — no smartphone, no internet, no literacy required.

THE INNOVATION: A speech pipeline (fine-tuned wav2vec-BERT ASR) runs offline on kiosk hardware, resolving noisy real Chichewa speech against constrained answer sets via phonetic fuzzy-matching rather than open transcription. That technique took real, measured slot-resolution accuracy from 78% to 100% on benchmark recordings after a live-found bug was fixed. A deterministic Kotlin engine keeps every government service as pure configuration — proven by adding a brand-new fifth service with zero code changes. A working browser kiosk demo already bridges real speech recognition into a real PostgreSQL backend and admin dashboard.

TARGET AUDIENCE: Malawi's 81.2% rural population, where mobile coverage reaches 87% but only 12.5% actually use mobile internet and 33% own a smartphone (GSMA, Aug 2026) — citizens app-first digital government leaves out, plus the officers verifying applications via the dashboard.

IMPACT & OUTCOMES: Shorter queues, fewer wasted trips for missing paperwork, and proof low-resource African languages can power real public infrastructure — backed by 290 automated tests and a documented trail of real bugs found and fixed.
```

## Problem Statement — 500 char limit
*(482 characters)*
```
Malawi's digital divide isn't network coverage — it's usage. 87% of the population has 4G coverage, but only 12.5% actually use mobile internet and 33% own a smartphone (GSMA, Aug 2026). Adult literacy sits around 62–66%. Government services still assume a smartphone, a data plan, English literacy, and comfort with forms — four assumptions that together exclude the citizens who need these services most: the 81.2% living rurally, in their own language, without a personal device.
```

## Solution & Innovation — 2000 char limit
*(1,368 characters — 632 to spare)*
```
MTHANDIZI is a shared kiosk, not a personal app — matching how Malawians already access technology (mobile money reaches most adults; mobile internet reaches 12.5% — the gap is devices, not willingness). A citizen speaks Chichewa; the kiosk asks one question at a time, confirms every answer, and falls back to touch whenever speech struggles.

The core innovation is architectural: real Chichewa speech recognition measures ~36% word error rate on free speech, so MTHANDIZI never asks an open-ended question it must parse freely. Every answer is matched against a constrained set via phonetic fuzzy-matching — the actual reliability mechanism. Real benchmark testing found a matcher bug live, fixed it, and re-measured 100% slot-resolution accuracy on the same real recordings.

Government-service logic lives in a deterministic Kotlin engine driven entirely by JSON configuration — adding a service is a config change, not new code, proven by building a throwaway fifth service with zero engine modifications during testing.

The pipeline runs with zero internet — speech inference happens locally on kiosk hardware, the same pattern ATMs use — and syncs to a Node/PostgreSQL backend with a real admin dashboard once connectivity is available. A working browser-based demo already shows this connected end to end: real voice in, a real record in a real database out.
```

## Project Stage
**Development/Prototype Stage.** (Not Concept/Idea — far more is built than
that; not Deployment/Market — nothing is live with real users yet.)

## Tools & Technologies Used — 500 char limit
*(470 characters)*
```
Python (FastAPI, transformers, PyTorch) for the speech service; CLEAR Global's w2v-bert-2.0 Chichewa ASR model; Meta's MMS-TTS (VITS) for speech synthesis; a phonetic fuzzy-matcher for closed-set resolution; Kotlin/JVM for the deterministic workflow engine; Node.js, Express, and PostgreSQL for the backend; vanilla HTML/JS for the admin dashboard and kiosk demo; pytest and Node's test runner for 290 automated tests, several run against real infrastructure, not mocks.
```

## Unique Selling Point (USP) — 500 char limit
*(467 characters)*
```
Most "AI for local languages" projects stop at a proof-of-concept transcript. MTHANDIZI has 290 automated tests, a real native-speaker language review, and a documented trail of ten real bugs found and fixed — including one caught live during benchmark testing that took slot accuracy from 78% to 100%. Architected for zero internet and config-driven service expansion, proven not just claimed, with a working demo connecting real speech to a real backend end to end.
```

## Impact — 800 char limit
*(785 characters)*
```
MTHANDIZI targets the population digital government currently misses: Malawi's 81.2% rural residents, the ~87% with network coverage who still don't use mobile internet, and the roughly one-third to two-fifths of adults with limited literacy in English or written Chichewa forms (UNESCO/World Bank estimates vary 62–66%).

Direct impact: shorter physical queues at hospitals and government offices, fewer rejected applications from missing or illegible paperwork, and a self-service option for citizens currently dependent on intermediaries to navigate English-language forms.

Broader impact: real, tested proof that Chichewa — and other under-resourced African languages, via the same config-driven architecture — can power functioning public infrastructure, not just research demos.
```

## Expected Outcomes — 500 char limit
*(471 characters)*
```
Near-term (post-Android build): a single working kiosk pilot in one hospital or NRB office, handling real birth-registration or queue intake, with officer-verified accuracy tracked via the admin dashboard.

Measurable targets: average intake time per citizen, percentage of interactions completed without staff help, citizen-reported ease of use versus paper, and slot-resolution accuracy on real queue data, compared against the 100% already measured on recorded speech.
```

## Potential Challenges — 500 char limit
*(496 characters)*
```
Government-service fields are a first draft, not verified against actual NRB, Health, or Immigration forms — needs official validation before deployment. The TTS voice license (CC-BY-NC-4.0) is non-commercial; a commercial rollout needs a different model or licensing talks. Hardware costs (~$300–550/kiosk) need real supplier quotes beyond one sourced figure. The Android client — what makes this a physical kiosk, not a browser demo — isn't built yet; the clear next task, not an open question.
```

## Revenue Model — 500 char limit
*(497 characters — read the note below before pasting)*
```
Primary: B2G — per-kiosk licensing and deployment contracts with government agencies (NRB, Health, Immigration) or hosting districts/hospitals, plus an optional annual maintenance fee. Secondary: grant and development-partner funding (active digital-ID and e-government programmes in Malawi fit naturally) to subsidize hardware, with government covering ongoing costs once a pilot proves value. Not yet validated with a real customer conversation — the next commercial step, not a confirmed model.
```
**Note:** this is a reasonable, honest draft I wrote based on the project's
nature (a government-facing tool) — not something I can verify the way I
verified test results. If you have your own view on how this should be
monetized, use yours instead; this is a starting point, not a claim.

## Project Timeline — 500 char limit
*(486 characters)*
```
Done: real Chichewa ASR/TTS pipeline benchmarked on live recordings (100% slot accuracy); Kotlin workflow engine for all four services; Node/PostgreSQL backend with dashboard; reviewed language pack; working browser kiosk demo connecting speech to backend end to end. 290 automated tests passing.

Next 4–6 weeks: Android client porting this flow onto kiosk hardware; validate service fields against real forms.

Next 2–3 months: camera-presence, encryption, QR/PDF; single-kiosk pilot.
```

## Video Demo Link
Paste your YouTube/Drive link from Part 3 above. **This field is required —
the form won't let you proceed without it.**

## Project Website / Repo
Paste your GitHub repo URL from Part 2 above.

---

# Final checklist before you click "Next: Verify Email"

- [ ] Speech service and backend both actually run on your machine (Part 1)
- [ ] Repo is pushed to GitHub, link works, no `.env`/`node_modules` visible in it
- [ ] Demo video recorded and uploaded, link works and is set to viewable
- [ ] Every field above pasted in, none showing a "required" error
- [ ] You've personally watched your own demo video once, start to finish,
      to make sure the audio/screen actually recorded correctly

Once all of those are true, you're ready to submit.
