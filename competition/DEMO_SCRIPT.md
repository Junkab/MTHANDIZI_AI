# MTHANDIZI — Demo Script

**Read this first:** the Android kiosk app itself has not been built yet —
this sandbox's toolchain cannot reach Android's dependency infrastructure
(`dl.google.com`, `services.gradle.org` — checked directly, both return
`403`, same as several other blocked services documented in `BUILD_LOG.md`).

**What HAS been built since that gap was identified: a browser-based kiosk
demo (`backend/public/kiosk/index.html`, served at `/kiosk/`) that genuinely
bridges the previously-separate, previously-proven pieces** — real speech
recognition and matching (Phase 0), a real backend (Phase 11) — into one
connected flow a person can actually walk through: describe a need in their
own words, confirm the kiosk's understanding, answer by voice or touch,
review, submit, and see it land in the real admin dashboard.
This is not the final Android kiosk, and the demo page says so on screen —
but it is the first time this project's components have been shown working
*together*, not just independently. Full technical honesty about what's
real vs. simplified is in that file's own header comment and in
`BUILD_LOG.md`.

**Everything in Part 1 below is real, running, and can be shown live,
exactly as described.** Part 2 describes the target Android kiosk
experience once that final client is built — clearly labeled as
not-yet-built, not blended in as if it already exists.

---

## Part 1 — Live demo (what's real today, ~5–6 minutes)

### Step 1: The integrated kiosk flow, live (2–3 minutes) — the centerpiece

Start `speech-service` and `backend` (both already built and tested), open
`http://localhost:3000/kiosk/` in a browser. Walk through birth
registration for real:

1. The kiosk asks how it can help. Tap the mic and say
   "Ndikufuna kulembetsa mwana wanga." Confirm the kiosk's understanding by
   saying "Inde"; no service list is shown or read aloud.
2. Say the child's name — the real transcript appears, and
   the page asks you to confirm it before moving on (Section 4.4's "names
   are never trusted to speech alone" principle, actually enforced, not
   just described in a document).
3. For the district question specifically, say a district name — **this is
   the moment to narrate the real number**: the underlying matcher was
   measured at 100% slot accuracy on real benchmark recordings after a real
   bug was found and fixed (`BUILD_LOG.md`, Phase 0).
4. Reach the review screen, showing every real answer collected. Tap
   Confirm.
5. **Show the reference number appear, then immediately switch to
   `http://localhost:3000/admin/` and show the same application there** —
   real data, same database, arriving through the exact flow the audience
   just watched. This is the single strongest moment in the demo: proof
   the pieces are actually connected, not just each independently working.

The browser demo currently implements a complete workflow only for birth
registration. The other five intents are classified, confirmed, then given a
spoken staff-assistance fallback; do not present them as completed workflows.

**Fallback if the room is noisy or the mic misbehaves:** every voice step
has a working touch/typed fallback built into the same page — use it
without breaking stride, and say so plainly; it's a designed fallback, not
a trick.

### Step 2: The matcher handling REAL noisy speech (45s)

Show the actual benchmark result table (`BUILD_LOG.md`, Phase 0's "FIRST
REAL BENCHMARK RUN" and follow-up fix). Narrate the real number: **the
first real run measured 78% slot accuracy; after finding and fixing a real
bug live during testing, a second real run measured 100%.** This is the
evidence behind what the audience just watched work in Step 1.

### Step 3: The deterministic workflow engine's proof, on the side (30–45s)

Mention (don't necessarily re-demo live, time permitting): the Kotlin
workflow engine has 45 automated tests, including one that builds a
completely new, fifth government service as a raw text file at test time
and proves it works with zero code changes — the config-not-code
architecture claim, actually proven. The kiosk demo just shown uses the
same underlying service definitions.

### Step 4: The Chichewa voice, honestly (30s)

If not already covered while narrating Step 1's TTS: mention the "Moni"
finding plainly. "This word didn't synthesize clearly, so we found that
live, tested it three different ways to confirm it wasn't just bad luck,
and removed it rather than fake a fix." **A found-and-fixed problem, shown
openly, builds more credibility than pretending everything was perfect.**

---

## Part 2 — Target Android kiosk experience (NOT YET BUILT)

*Presented as the vision this foundation — including the browser demo in
Part 1, which proves the integration works — is built toward.*

A citizen walks up to a tablet mounted in a hospital waiting area. A camera
notices presence (no identification, no storage — just a boolean) and the
screen wakes with:

> **Mthandizi:** "Moni. Ndine Mthandizi. Ndingakuthandizeni bwanji lero?"

The citizen says, in their own words, that they want to register their
child. Mthandizi confirms that understanding, then asks — in Chichewa, one question at a time — for the
child's name, date of birth, and village, confirming each answer as it
goes, with a large touch-screen fallback whenever speech struggles. At the
end, it reads everything back, the citizen confirms, and they receive a
reference number and a QR code — clearly marked as a prepared application
awaiting officer verification, not an issued document. The whole
interaction happened with **no internet connection at all**; the record
syncs automatically once connectivity is available, and appears on the
admin dashboard shown live in Part 1.

**The gap between Part 1 and Part 2 is now narrower than it looks.** Part 1
already proves every hard technical question — does the speech pipeline
work, does the matching hold up, does a real submission flow through to a
real backend — with a person actually able to walk through it end to end.
What remains for Part 2 is porting that same proven flow onto Android
hardware with a native camera and offline storage, not answering open
research questions.

## What stands between here and there

Stated plainly, since a judge will ask: the pure-logic engine, the speech
pipeline, the backend, and — as of this demo — the integration between them
are all proven, with a person able to click through the real thing. What
remains is the Android client itself (this exact flow, on kiosk hardware,
working with zero internet), plus the camera-presence, on-device
encryption, and QR/PDF generation pieces named in the original build plan's
later phases. None of that is a research risk at this point — every hard
technical question has already been answered with evidence, not
assumption, and now with a working end-to-end demonstration to match.

