"""
MTHANDIZI — closed-set resolution and intent routing.

THE CENTRAL IDEA
----------------
The entry question is open-ended and conversational. `classify_intent()` uses local,
auditable phrase matching to route that transcript into one of six service intents,
or asks for clarification when evidence is weak or conflicting. Subsequent workflow
questions can still use closed-set matching for answers such as districts and yes/no.

Three outcomes, and only three:
  ACCEPT      - one candidate is clearly best        -> fill the slot
  DISAMBIGUATE- top two are close                    -> ask a yes/no question
  REJECT      - nothing is close enough              -> re-ask, then escalate to touch

This module is deliberately free of any speech or network dependency. It takes a
string and is deterministic, testable, and available offline.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .chichewa_text import fold, similarity, stem_similarity


class Outcome(str, Enum):
    ACCEPT = "ACCEPT"
    DISAMBIGUATE = "DISAMBIGUATE"
    REJECT = "REJECT"


@dataclass(frozen=True)
class Candidate:
    """One possible answer. `key` is what we store; `variants` are ways of saying it."""
    key: str
    variants: tuple[str, ...]

    @staticmethod
    def of(key: str, *variants: str) -> "Candidate":
        return Candidate(key, (key,) + variants)


@dataclass(frozen=True)
class MatchResult:
    outcome: Outcome
    key: str | None
    score: float
    runner_up: str | None
    runner_up_score: float
    transcript: str

    @property
    def accepted(self) -> bool:
        return self.outcome is Outcome.ACCEPT


# Tuned against the noisy-transcript fixture set in tests/. Revisit these with REAL
# measured data at the end of Phase 0 — do not treat them as settled.
# Originally 0.62, tuned only against synthetic corruptions written by hand.
# Real benchmark data (Phase 0, 2026-09-19, operator's own recordings through the
# actual ASR model) showed every genuine answer scoring BELOW this threshold at
# least once - the correct candidate was always rank #1, just not confident
# enough to clear 0.62. Lowered to 0.30, the lowest score seen among the 8 real
# failures ("Eya" -> "hea", 0.333) minus a small margin. Verified this does not
# introduce false accepts against gibberish/silence/refusal inputs - see
# test_real_benchmark_regressions.py.
ACCEPT_THRESHOLD = 0.30
MARGIN_THRESHOLD = 0.08      # top two closer than this -> ask which one


def _best_variant_score(transcript: str, candidate: Candidate, use_stems: bool) -> float:
    """
    Score against every way of saying this candidate, and keep the best.

    When stemming is on we take the MAX of the stemmed and unstemmed scores rather
    than stemming alone. Reason found during Phase 0 testing: prefix-stripping is a
    big win for 'ku Lilongwe', but it misfires on words that merely begin with
    prefix-like letters — 'Musuzu' (a mishearing of 'Mzuzu') was being stripped to
    'suzu' and falling below threshold. Keeping both views costs nothing and removes
    a whole class of false rejection.
    """
    scores = [similarity(transcript, v) for v in candidate.variants]
    if use_stems:
        scores += [stem_similarity(transcript, v) for v in candidate.variants]
    return max(scores)


def match(
    transcript: str,
    candidates: list[Candidate],
    *,
    use_stems: bool = True,
    accept_threshold: float = ACCEPT_THRESHOLD,
    margin_threshold: float = MARGIN_THRESHOLD,
) -> MatchResult:
    """Resolve a noisy transcript against a closed set of expected answers."""
    if not candidates:
        raise ValueError("match() requires at least one candidate")

    scored = sorted(
        ((c.key, _best_variant_score(transcript, c, use_stems)) for c in candidates),
        key=lambda pair: pair[1],
        reverse=True,
    )
    top_key, top_score = scored[0]
    second_key, second_score = scored[1] if len(scored) > 1 else (None, 0.0)

    if top_score < accept_threshold:
        outcome = Outcome.REJECT
    elif second_key is not None and (top_score - second_score) < margin_threshold:
        outcome = Outcome.DISAMBIGUATE
    else:
        outcome = Outcome.ACCEPT

    return MatchResult(
        outcome=outcome,
        key=top_key if outcome is not Outcome.REJECT else None,
        score=round(top_score, 4),
        runner_up=second_key,
        runner_up_score=round(second_score, 4),
        transcript=transcript,
    )


def _exact_match(transcript: str, candidates: list[Candidate]) -> str | None:
    """An exact (post-fold) match to real vocabulary. No scoring, no ambiguity."""
    folded_transcript = fold(transcript)
    if not folded_transcript:
        return None
    for candidate in candidates:
        for variant in candidate.variants:
            if fold(variant) == folded_transcript:
                return candidate.key
    return None


def resolve(
    transcript: str,
    candidates: list[Candidate],
    *,
    control_threshold: float = 0.70,
    **match_kwargs,
) -> MatchResult:
    """
    The entry point every real slot question should call instead of match()
    directly.

    Two checks run before any fuzzy scoring:
      1. An EXACT match (post phonetic-folding) to either CONTROL or the slot's
         own candidates always wins outright, whichever list it's in.
      2. Only if nothing is exact does fuzzy CONTROL scoring run, then fuzzy
         scoring against the slot's own candidates.

    WHY STEP 1 EXISTS - A REAL BUG, NOT A HYPOTHETICAL
    ----------------------------------------------------
    Real benchmark data (Phase 0, 2026-09-19) showed "sindikudziwa" ("I don't
    know", a HELP phrase) scoring 0.73 fuzzy-similarity against "sindikufuna"
    ("I don't want to", the pack's actual recorded NO phrase - see UTTERANCES.md
    q16) - they share the "sindiku-" negation prefix. The first attempt at a fix
    checked CONTROL before the slot's candidates, which flipped the bug instead
    of fixing it: a PERFECT recording of "sindikufuna" (proven correct in the
    real benchmark, 0% WER) started resolving to HELP, because 0.73 exceeded
    even the stricter 0.70 control_threshold.

    The collision is symmetric - checking one list before the other only decides
    which wrong answer you get, not whether you get one. The actual fix is
    priority, not order: if the transcript is an EXACT match to real vocabulary
    ANYWHERE, that wins immediately, before any fuzzy cross-list comparison runs
    at all. "sindikufuna" said clearly matches "sindikufuna" exactly (NO) and
    never reaches the fuzzy comparison against "sindikudziwa" (HELP) that caused
    the problem. Fuzzy CONTROL-first scoring remains as the fallback for
    imperfect transcriptions where nothing is an exact hit.
    """
    exact_control = _exact_match(transcript, CONTROL)
    exact_slot = _exact_match(transcript, candidates)

    if exact_control and not exact_slot:
        return MatchResult(Outcome.ACCEPT, exact_control, 1.0, None, 0.0, transcript)
    if exact_slot:
        return MatchResult(Outcome.ACCEPT, exact_slot, 1.0, None, 0.0, transcript)

    control_result = match(transcript, CONTROL, accept_threshold=control_threshold,
                           margin_threshold=match_kwargs.get("margin_threshold", MARGIN_THRESHOLD))
    if control_result.outcome is Outcome.ACCEPT:
        return control_result
    return match(transcript, candidates, **match_kwargs)


def contains_any(transcript: str, phrases: list[str], threshold: float = 0.8) -> bool:
    """
    Spot a keyword inside a longer utterance ("eee ndikuganiza kuti inde" -> yes).

    Compares whole-token n-grams, NOT arbitrary character windows. Phase 0 testing
    showed the sliding-character-window version matched 'indi' inside
    'sindikudziwa' ("I don't know") and read it as 'inde' ("yes") — a false YES,
    which is the single most dangerous error this system can make. Token-boundary
    comparison removes that class of bug entirely.
    """
    tokens = [t for t in fold(transcript).split() if t]
    if not tokens:
        return False

    for phrase in phrases:
        target = fold(phrase)
        if not target:
            continue
        span = max(1, len(target.split()))
        for start in range(0, len(tokens) - span + 1):
            chunk = " ".join(tokens[start:start + span])
            if chunk == target or similarity(chunk, target) >= threshold:
                return True
    return False


# Open-ended service intents. Keep phrases specific enough that ordinary
# conversation does not accidentally launch a workflow. These are deterministic
# and local; no network or language-model dependency is involved.
INTENT_PHRASES: dict[str, tuple[str, ...]] = {
    "BIRTH_REGISTRATION": (
        "kulembetsa mwana", "kalata ya kubadwa", "satifiketi ya kubadwa",
        "mwana wanga wabadwa", "lembetsani mwana", "chikalata cha mwana",
    ),
    "HOSPITAL_QUEUE": (
        "ndikudwala", "ndadwala", "kuonana ndi dokotala", "thandizo ku chipatala",
        "ndabwera ku chipatala", "ndabwala ku chipatala", "ndabwala kuchipatala",
        "ndikufuna dokotala",
        "kuona alidokotala", "ndikufuna chithandizo cha matenda",
    ),
    "IMMIGRATION": (
        "pasipoti", "pasporti", "pasport", "pasports", "passport", "passporti",
        "kupita kunja", "chikalata cha ulendo",
        "ndikufuna visa", "kukonza pasipoti", "ndikufuna kupita ku dziko lina",
    ),
    "NATIONAL_ID": (
        "chiphaso cha dziko", "chiphaso changa", "national id", "aidi yanga",
        "ndataya id", "ndikufuna id", "chiphaso cha nzika",
    ),
    "LAND_REGISTRATION": (
        "kulembetsa malo", "kulembetsa nthaka", "mwini wa malo", "umwini wa nthaka",
        "chikalata cha malo", "malo anga", "ndikufuna kulembetsa munda",
    ),
    "HEALTH_FACILITY_INFO": (
        "chipatala chili kuti", "chipatala chiri kuti", "chipatala chapafupi",
        "komwe kuli chipatala", "adilesi ya chipatala", "maola ogwira ntchito kuchipatala",
        "ndikufuna kudziwa chipatala",
    ),
}


@dataclass(frozen=True)
class IntentResult:
    """Intent decision with auditable numeric evidence and an uncertainty state."""
    outcome: Outcome
    key: str | None
    score: float
    runner_up: str | None
    runner_up_score: float
    transcript: str

    @property
    def confidence(self) -> str:
        if self.outcome is Outcome.ACCEPT and self.score >= 0.95:
            return "high"
        if self.outcome is Outcome.ACCEPT:
            return "medium"
        if self.outcome is Outcome.DISAMBIGUATE:
            return "ambiguous"
        return "low"


def _intent_phrase_score(transcript: str, phrases: tuple[str, ...]) -> float:
    """Score phrase evidence on word boundaries, including short ASR drift."""
    tokens = fold(transcript).split()
    if not tokens:
        return 0.0

    best = 0.0
    for phrase in phrases:
        target_tokens = fold(phrase).split()
        if not target_tokens:
            continue
        width = len(target_tokens)
        for start in range(len(tokens) - width + 1):
            chunk = " ".join(tokens[start:start + width])
            target = " ".join(target_tokens)
            score = similarity(chunk, target)
            # One-token generic words (e.g. "malo") are matched exactly only;
            # fuzzy matching is reserved for phrases with enough context.
            if width == 1 and chunk != target:
                continue
            best = max(best, score)
    return best


def classify_intent(
    transcript: str,
    *,
    accept_threshold: float = 0.78,
    margin_threshold: float = 0.14,
) -> IntentResult:
    """Classify free-form Chichewa locally, returning accept/clarify/reject.

    Exact phrase evidence scores 1.0. Near matches use the same conservative
    phonetic folding as slot matching. Multiple strong service mentions prompt
    a conversational clarification instead of selecting one arbitrarily.
    """
    scores = sorted(
        ((intent, _intent_phrase_score(transcript or "", phrases))
         for intent, phrases in INTENT_PHRASES.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    top_key, top_score = scores[0]
    runner_up, runner_score = scores[1]

    if top_score < accept_threshold:
        outcome = Outcome.REJECT
        key = None
    # Do not treat generic shared framing words (for example "ndikufuna") as
    # cross-intent evidence. A competing intent must have a near-exact phrase
    # hit to trigger disambiguation; otherwise the best sufficiently strong
    # service phrase wins.
    elif runner_score >= 0.90:
        outcome = Outcome.DISAMBIGUATE
        key = top_key
    else:
        outcome = Outcome.ACCEPT
        key = top_key

    return IntentResult(
        outcome=outcome,
        key=key,
        score=round(top_score, 4),
        runner_up=runner_up if runner_score > 0 else None,
        runner_up_score=round(runner_score, 4),
        transcript=transcript or "",
    )


# --- Standard answer sets shared across every workflow -------------------------

YES_NO = [
    Candidate.of("YES", "inde", "eya", "ee", "ndi choncho", "zoona", "ndithu", "chabwino"),
    # "sindikufuna" kept - it's the phrase UTTERANCES.md actually asks people to
    # say for NO, and real benchmark data (Phase 0, 2026-09-19, q16) confirms it
    # transcribes and matches correctly. It DOES collide (0.73 similarity) with
    # "sindikudziwa" ("I don't know") on raw character similarity - both share the
    # "sindiku-" negation prefix. The fix is not deleting real vocabulary; it's
    # resolve() below, which checks CONTROL words first and correctly routes
    # "sindikudziwa" to HELP before it ever reaches this list.
    Candidate.of("NO", "ayi", "iyayi", "ndikukana", "si choncho", "sindikufuna"),
]

CONTROL = [
    Candidate.of("REPEAT", "bwerezani", "ndibwerezeni", "sindinamve", "nenaninso"),
    Candidate.of("BACK", "bwererani", "kumbuyo", "ndibwerere"),
    Candidate.of("HELP", "thandizeni", "sindikudziwa", "ndithandizeni"),
    Candidate.of("CANCEL", "siyani", "ndikusiya", "basi"),
]

SERVICE_INTENTS = [
    Candidate.of(
        "BIRTH_REGISTRATION",
        "ndikufuna kulembetsa mwana wanga",
        "kulembetsa mwana",
        "kalata ya kubadwa",
        "satifiketi ya kubadwa",
        "mwana wanga wabadwa",
    ),
    Candidate.of(
        "HOSPITAL_QUEUE",
        "ndikufuna kuonana ndi dokotala",
        "ndikudwala",
        "ndikufuna chithandizo ku chipatala",
        "ndabwera ku chipatala",
    ),
    Candidate.of(
        "NATIONAL_ID",
        "ndikufuna chiphaso cha dziko",
        "ndataya ID yanga",
        "ndikufuna national ID",
        "chiphaso changa chatha",
    ),
    Candidate.of(
        "IMMIGRATION",
        "ndikufuna pasipoti",
        "ndikufuna kupita kunja",
        "ndikufuna kukonza pasipoti",
        "pasipoti yanga",
    ),
    Candidate.of(
        "LAND_REGISTRATION",
        "ndikufuna kulembetsa malo",
        "ndikufuna kulembetsa nthaka",
        "chikalata cha malo",
        "umwini wa nthaka",
    ),
    Candidate.of(
        "HEALTH_FACILITY_INFO",
        "chipatala chili kuti",
        "chipatala chapafupi",
        "komwe kuli chipatala",
        "adilesi ya chipatala",
    ),
]

# A first-draft district list. NOT verified against an official gazetteer —
# validate before deployment (see LIMITATIONS.md).
DISTRICTS = [
    Candidate.of(name) for name in (
        "Lilongwe", "Blantyre", "Mzuzu", "Zomba", "Kasungu", "Mangochi",
        "Salima", "Dedza", "Ntcheu", "Nkhotakota", "Mchinji", "Dowa",
        "Thyolo", "Mulanje", "Chikwawa", "Nsanje", "Balaka", "Machinga",
        "Phalombe", "Chiradzulu", "Neno", "Karonga", "Rumphi", "Nkhata Bay",
        "Mzimba", "Chitipa", "Likoma", "Ntchisi",
    )
]

MONTHS = [
    Candidate.of("01", "Januwale", "Januware"),
    Candidate.of("02", "Febuluwale", "Febuluware"),
    Candidate.of("03", "Malichi"),
    Candidate.of("04", "Epulo", "Epulou"),
    Candidate.of("05", "Meyi", "Mei"),
    Candidate.of("06", "Juni"),
    Candidate.of("07", "Julayi"),
    Candidate.of("08", "Ogasiti", "Ogasti"),
    Candidate.of("09", "Seputembala"),
    Candidate.of("10", "Okutobala"),
    Candidate.of("11", "Novembala"),
    Candidate.of("12", "Disembala"),
]
