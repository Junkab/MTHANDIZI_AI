# MTHANDIZI — Limitations

Judges trust teams that name their own weaknesses. This document does that
directly, organized by how serious each limitation actually is.

## Real, measured technical limitations

- **Word error rate on free-form Chichewa speech: 36.1%** (39 wrong words
  out of 108, real benchmark, real recordings — `BUILD_LOG.md`, Phase 0).
  The kiosk now accepts a free-form opening request and uses a deterministic,
  offline phrase classifier to identify one of six service intents. That
  classifier has synthetic/text unit coverage, but the existing measured WER
  is a real risk: ASR can omit or alter the very words that distinguish an
  intent. Low-confidence or conflicting matches trigger spoken clarification;
  this reduces guessing but does not establish real-world intent accuracy.
  Character error rate (9.1%) is lower than word error rate, but that does not
  prove this new open-intent flow works across accents or noisy settings.
- **Text-to-speech has one confirmed, narrow failure mode.** The word
  "Moni" (Hello) was consistently mispronounced by the synthesis model
  across 5 different random seeds and 6 capitalization/punctuation
  variants — a genuine, reproducible model limitation, not a bug in this
  project's code. Removed from the one affected prompt; the fix for any
  similar case going forward is a short human-recorded prompt, which the
  system was already architected to prefer for short, fixed, important
  phrases.
- **Short, isolated closed-set answers (yes/no, single-word district names)
  are measurably harder for the speech model than full sentences.** Before
  a real matcher bug was found and fixed, this specific weakness accounted
  for the entire gap between 78% and 100% slot accuracy on the same real
  benchmark data. Documented with the exact before/after numbers in
  `BUILD_LOG.md`, not glossed over.

## Scope limitations, stated up front

- **This is a prototype with no live connection to any government
  database.** It does not issue national IDs, birth certificates, or
  passports. It prepares an application and generates a reference number
  for a human officer to verify — and the kiosk says so, in both Chichewa
  and English, on the completion screen.
- **The four government-service field lists (what a birth registration or
  passport application actually asks for) are a reasonable first draft**,
  written from general knowledge of what such forms typically require —
  **not verified against actual Malawian government forms.** Before any
  real deployment, these should be checked against NRB, Ministry of Health,
  and Immigration Department requirements directly. The architecture makes
  this a configuration change (editing a JSON file), not an engineering
  project — demonstrated directly by building a throwaway fifth service
  with zero changes to the underlying engine.
- **The district list used for closed-set matching has not been checked
  against an official gazetteer.**
- **The Chichewa language pack has been reviewed by one native speaker.**
  A single reviewer, however careful, is one perspective — broader review
  (regional dialect variation, additional native speakers) would strengthen
  this further before any real deployment.
- **The TTS voice (`facebook/mms-tts-nya`) is licensed CC-BY-NC-4.0 —
  non-commercial.** Fine for a prototype and competition demonstration; a
  commercial deployment would need either a different TTS solution or a
  licensing conversation with the model's provider.

## What has genuinely not been built yet

- **The Android client itself.** The speech pipeline and the workflow
  engine are both independently proven; the Android app that wires them
  together into an on-device kiosk experience has not been started. This
  sandbox's own toolchain could not reach Android's dependency
  infrastructure (`dl.google.com`, `services.gradle.org` both confirmed
  returning `403`), so this genuinely requires development on real hardware
  with real tooling access — not a gap in effort, a gap in what this
  particular environment could reach.
- **Camera-based presence detection, on-device encrypted storage, offline
  sync queueing, QR/PDF generation, and demo mode** are all designed and
  specified in the original build plan but not yet implemented — they
  depend on the Android client existing first.
- **No load or concurrency testing.** The backend has been tested
  correctly under normal single-request use; behaviour under many
  simultaneous kiosks has not been characterized. Reasonable for a
  single-kiosk pilot; worth revisiting before a multi-kiosk rollout.

## What is NOT a limitation, stated for contrast

To be clear about where real evidence already exists, so it isn't
undersold alongside the honest gaps above: the core claim that Chichewa
voice interaction can be made reliable through slot-constrained matching is
not a hypothesis — it was measured, found to have real weak points, fixed,
and re-measured, all on real speech data, with the full trail in
`BUILD_LOG.md`.
