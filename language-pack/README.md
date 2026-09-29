# MTHANDIZI — Language Pack (Phase 1)

One file, `pack/chichewa_pack.json`, holds every string the citizen sees or hears.
No user-facing text exists anywhere else in the app. That rule is what stops this
project from quietly turning back into "an English app with Chichewa labels" —
the exact failure mode of the previous build.

## What's here

- `pack/chichewa_pack.json` — 51 entries across greeting, intent clarification, all four workflows'
  questions, review/confirm flow, errors, UI labels, and the lexicon (yes/no,
  districts, months, service names, intents).
- `tool/lint_pack.py` — structural linter. Dev mode checks the pack is well-formed;
  `--strict` additionally blocks release until every entry is `reviewed: true`.
- `tool/review.html` — open this directly in a browser (no server needed). Load the
  pack, play each recording if one exists, edit the Chichewa, approve or reject,
  export `chichewa_pack.reviewed.json`.
- `tests/test_lint.py` — 15 tests, including two regression tests for real bugs
  the linter caught on its own pack (see below) and one that will fail on purpose
  until the pack is actually reviewed — don't delete it when it goes red, that's it
  doing its job.

## Running it on Windows

No new setup needed if you did Phase 0 — same venv.
```
python -m pytest tests\ -v          REM expect 15 passed
python tool\lint_pack.py            REM dev check — should print "Clean."
python tool\lint_pack.py --strict   REM release check — will currently FAIL, correctly
```

## Getting it reviewed

1. Open `tool\review.html` in any browser (double-click it).
2. Click "Load", pick `pack\chichewa_pack.json`.
3. Hand the laptop to a native Chichewa speaker. For each card: read the Chichewa,
   fix it in the box if it's wrong, hit Approve or Reject.
4. Click "Export reviewed pack" — downloads `chichewa_pack.reviewed.json`.
5. Replace `pack\chichewa_pack.json` with the reviewed version.
6. Re-run `python tool\lint_pack.py --strict`. Once it says Clean, the pack is
   release-ready.

If you don't have access to a native speaker yet, that's fine — dev mode already
confirms the pack is structurally complete, and strict mode will simply keep
reminding you what's still open. Nothing downstream is blocked by an unreviewed
pack; only a *release build* should be gated on `--strict`.

## Bugs the tooling itself caught

Building the linter surfaced two real defects before either shipped:

1. **False positive on the brand name.** `"Mthandizi"` == `"Mthandizi"` in both
   languages tripped `IDENTICAL_TO_EN`, correctly — that check exists to catch
   forgotten translations, and a brand name IS identical on purpose. Fixed by
   adding an explicit `"exempt_identical": true` flag rather than weakening the
   check, so real untranslated strings still get caught.
2. **Leaf-detection missed entries with no `chi` at all.** The walker only
   recursed into an entry if `"chi" in node`; an entry with `"en"` but no `"chi"`
   has neither triggered detection nor been flagged — it was silently invisible,
   which is worse than a loud failure. Fixed by triggering on `"chi" or "en"`.

Both are now regression tests in `test_lint.py`.

## Known gaps — honest, not hidden

- **Zero entries are reviewed.** `reviewed_by` and `reviewed_on` in `meta` are
  empty. This pack has not been in front of a native speaker yet.
- **Audio does not exist yet.** Every `audio` path points at a file that isn't
  there — `prompts/greeting_idle.wav` etc. Phase 2's recorded-TTS strategy depends
  on these being recorded once the text is approved. Recording before approval
  would mean re-recording after edits.
- **District list is unverified** against any official source (inherited from
  Phase 0, noted again here since it lives in this file now).
- **`ChichewaFormatter`** (numbers, ordinal dates spoken naturally) referenced in
  the original build spec is NOT yet built — it's a Phase-3/4 item once the
  workflow engine exists to drive it. This pack has the raw month names it needs.

## Phase 1 gate

- [x] Every workflow has its questions in the pack
- [x] Lint passes in dev mode (0 structural problems)
- [x] Lint correctly blocks strict/release mode (0/49 reviewed)
- [x] Review tool loads, edits, exports
- [x] 15/15 tests pass
- [ ] A native speaker has actually reviewed it — **your action item**
- [ ] Prompt audio recorded for the reviewed text — **after** review, not before

Phase 1's code is done. The remaining checkbox is yours and needs a person, not code.
