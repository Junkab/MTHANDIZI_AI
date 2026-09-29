# MTHANDIZI — Workflow Engine (Phase 3)

Pure Kotlin/JVM. Zero Android dependency, zero speech dependency. This is the
deterministic core the build prompt's non-negotiable principle is about: the
AI/speech layer only ever fills in a form. This engine decides what fields
exist, what's valid, and what happens next — driven purely by `(value, accepted)`
tuples, never by anything that knows a microphone exists.

## No Gradle, no Maven — on purpose, and why that's fine

Maven Central is unreachable from the environment this was built in (confirmed:
a direct request to `repo1.maven.org` returns 403 — the same pattern as Hugging
Face being blocked earlier in this project). Rather than write code depending on
libraries that can't be proven to actually download and compile, this phase:

- **Hand-rolls a small JSON parser** (`src/main/Json.kt`) instead of pulling in
  `kotlinx.serialization`. ~200 lines, fully tested, covers exactly the subset
  the service-definition files need.
- **Hand-rolls a minimal test runner** (`src/test/Check.kt`) instead of JUnit.
  Same reasoning.
- **Uses the standalone `kotlinc` compiler directly** rather than a Gradle
  project. `kotlinc`'s own release zip is hosted on GitHub (reachable), so it
  was downloaded and used with zero Maven dependency resolution at all.

**This is not a permanent architecture decision** — when the real Android app
is built (Phase 5+), it will use Gradle with real Maven access (Moshi for JSON,
JUnit/a real Android test runner), and `Json.kt`/`Check.kt` here become
unnecessary. The one place this matters going forward: `ServiceDefinition.fromJson()`
is the only function that touches the hand-rolled parser directly — swapping it
for Moshi later is a localised change, not a rewrite of the engine.

**If you have Maven/Gradle access in your own environment**, none of this is a
constraint on you — this workaround exists because of a specific limitation of
the authoring sandbox, not because Kotlin can't have real dependencies.

## Building and running

You need `kotlinc` and a JDK (`java`) on your PATH.

```
./build.sh        # or build.bat on Windows
./run_tests.sh     # or run_tests.bat
```

Must be run **from this directory** — tests load the real `services/*.json`
files via a relative path, deliberately, so a broken JSON file actually fails
a test rather than being silently skipped.

**Getting `kotlinc` without Gradle/Maven**, if you don't already have it:
download `kotlin-compiler-<version>.zip` from
[github.com/JetBrains/kotlin/releases](https://github.com/JetBrains/kotlin/releases),
unzip it, and add its `bin/` folder to your PATH. No installer, no package
manager, no Maven dependency resolution needed for this step.

## What's here

```
workflow-engine/
  src/main/
    Json.kt              hand-rolled JSON parser
    Definitions.kt        SlotType, SlotDefinition, ServiceDefinition (+ fromJson)
    Validation.kt          per-slot-type semantic validation (dates, closed sets, names)
    WorkflowEngine.kt       the state machine itself
  src/test/
    Check.kt                hand-rolled test runner
    JsonTests.kt, ValidationTests.kt, DefinitionTests.kt, EngineTests.kt
    RunTests.kt              entry point
  services/
    birth_registration.json    the four real services, as pure config
    hospital_queue.json
    national_id.json
    immigration.json
```

## The architectural claim this phase proves

**"Adding a service is a config change, not an engine change."** One test
(`a brand-new fifth service works with ZERO engine code changes`) constructs a
throwaway fifth service (`LAND_INFO`) purely as a JSON string at test time —
not one of the four real files — and runs it through the exact same
`WorkflowEngine` class the other four use. No branch anywhere in
`WorkflowEngine.kt` or `Validation.kt` mentions any specific service by name.

## A real bug the tests caught

`goBack()`'s first implementation cleared the attempt count for the slot being
**landed on**, but not the slot being **abandoned** — so a failed attempt on a
slot you back away from stayed stuck in memory, and silently resurfaced later
if you walked forward past it again. Caught by
`goBack returns to the previous slot and resets its attempt count`, which
failed on the very first test run (44/45, not a suspicious clean pass). Fixed
by clearing attempts for both the abandoned slot and the destination slot.
Full story in `BUILD_LOG.md`.

## What this phase deliberately does NOT do

- **No persistence.** State lives in memory only, per `WorkflowEngine`
  instance. Saving/restoring a partially-completed application (needed for
  Phase 9, offline storage) is out of scope here.
- **No reference-number robustness.** `referenceNumber()` is a hash-based
  placeholder good enough to assert on in tests. Real generation (persisted
  counters, collision-proofing, human-readable format) is Phase 10 territory.
- **No connection to the real speech layer.** This engine has literally never
  imported anything from `speech-lab` or `speech-service`, and that's the
  point — but it also means the `(value, accepted)` tuples in every test are
  hand-written, not actually produced by the real matcher. Wiring the real
  `/asr?slot=X` response into calls to `submitAttempt()` is Android/client
  work (Phase 5+), not this phase's job.

## Phase 3 gate

- [x] Deterministic state machine, zero speech dependencies (no import of
      anything from speech-lab/speech-service anywhere in `src/main/`)
- [x] Service definitions as JSON, all four real services loading correctly
- [x] Slot types (CLOSED_SET, OPEN_NAME, NUMBER, DATE, FREE_TEXT) with
      real semantic validation, not just type-checking
- [x] Optional-field skip path (father_name), tested
- [x] Invalid-date handling, tested (Feb 30, month 13, leap-year edge cases
      including the 1900-vs-2000 divisible-by-100-vs-400 distinction)
- [x] Back navigation, tested, including the real bug found and fixed
- [x] Three-strike escalation to touch, tested, including "no double
      escalation" and "success after escalation still works"
- [x] Review-and-edit fast path (`editField`), tested
- [x] The "add a fifth service = config only" claim, actually proven with a
      throwaway service, not just asserted
- [x] 45/45 tests passing, actually executed, output shown in `BUILD_LOG.md`
