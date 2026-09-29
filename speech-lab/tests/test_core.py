"""
Phase 0 unit tests. These run with NO model, NO network, NO GPU.

The noisy-transcript fixtures below are the important part: they are realistic
corruptions of real Chichewa utterances, of the kind a ~0.12 CER model produces.
If the matcher survives these, the kiosk survives a real user.
"""

import pytest
import hashlib

from lab.chichewa_text import fold, normalise, similarity, stem_tokens
from lab.matching import (
    DISTRICTS,
    MONTHS,
    SERVICE_INTENTS,
    YES_NO,
    Outcome,
    contains_any,
    classify_intent,
    match,
)
from lab.metrics import aggregate, character_error_rate, word_error_rate
from lab.tts import SynthTts


def test_synth_tts_reuses_cached_wav_without_loading_model(tmp_path):
    text = "Dzina la mwana ndi ndani?"
    cache_id = hashlib.sha256(f"\0{text}".encode("utf-8")).hexdigest()
    cached_wav = tmp_path / f"synth_{cache_id}.wav"
    cached_wav.write_bytes(b"cached wav")
    tts = SynthTts(out_dir=tmp_path)

    speech = tts.speak(text)

    assert speech.wav_path == cached_wav
    assert speech.seconds == 0.0
    assert speech.source == "synth-cache"
    assert tts._model is None


# --- normalisation -------------------------------------------------------------

def test_normalise_lowercases_and_strips_punctuation():
    assert normalise("Ndikufuna kulembetsa mwana wanga.") == "ndikufuna kulembetsa mwana wanga"


def test_normalise_collapses_whitespace():
    assert normalise("  moni   bwanji  ") == "moni bwanji"


def test_normalise_handles_empty():
    assert normalise("") == ""
    assert normalise(None) == ""


def test_fold_collapses_aspiration():
    # 'phiri' and 'piri' must be indistinguishable to the matcher
    assert fold("phiri") == fold("piri")


def test_fold_collapses_r_and_l():
    assert fold("Malichi") == fold("Maritchi".replace("tch", "ch"))
    assert fold("rembetsa") == fold("lembetsa")


def test_fold_collapses_ch_ts_variants():
    assert fold("kulembetsa") == fold("kulembecha")


def test_stem_tokens_strips_noun_class_prefix():
    # 'ku Lilongwe' and 'Lilongwe' must reduce to the same stem
    assert stem_tokens("ku Lilongwe") == stem_tokens("Lilongwe")


def test_stem_tokens_keeps_short_words_intact():
    # 'ndi' must not be stripped to nothing
    assert stem_tokens("ndi") == ["ndi"]


# --- metrics -------------------------------------------------------------------

def test_wer_perfect_match_is_zero():
    ref = "ndikufuna kulembetsa mwana wanga"
    assert word_error_rate(ref, ref).rate == 0.0


def test_wer_counts_one_substitution():
    er = word_error_rate("ndikufuna kulembetsa mwana wanga",
                         "ndikufuna kulembetsa mwana wathu")
    assert er.errors == 1
    assert er.total == 4
    assert er.rate == 0.25


def test_cer_is_lower_than_wer_for_near_misses():
    """The whole MTHANDIZI thesis in one test: near-miss words wreck WER but not CER."""
    ref = "ndikufuna kulembetsa mwana wanga"
    hyp = "ndikufuna kulembecha mwana wanga"   # one character different
    wer = word_error_rate(ref, hyp).rate
    cer = character_error_rate(ref, hyp).rate
    assert wer == 0.25          # a whole word counted wrong
    assert cer < 0.10           # but only 2 characters in 31 are wrong
    assert cer < wer / 3        # CER is dramatically kinder than WER here


def test_aggregate_pools_errors_not_averages_rates():
    pairs = [
        ("moni", "moni"),                                    # 1 word, 0 errors
        ("ndikufuna kulembetsa mwana wanga", "ine sindikudziwa"),  # 4 words, 4 errors
    ]
    result = aggregate(pairs)
    assert result["words"] == 5
    assert result["word_errors"] == 4
    assert result["wer"] == 0.8      # NOT (0.0 + 1.0)/2 = 0.5


# --- matching: the fixtures that matter ----------------------------------------

NOISY_INTENTS = [
    # (what the ASR produced, what the citizen actually meant)
    ("ndikufuna kulembetsa mwana wanga", "BIRTH_REGISTRATION"),   # verified perfect case
    ("ndikufuna kulembecha mwana wanga", "BIRTH_REGISTRATION"),
    ("ndikufuna kurembetsa mwana wanga", "BIRTH_REGISTRATION"),
    ("ndikufuna kulembetsa mwana",       "BIRTH_REGISTRATION"),
    ("kulembetsa mwana wanga",           "BIRTH_REGISTRATION"),
    ("karata ya kubadwa",                "BIRTH_REGISTRATION"),
    ("ndikufuna kuonana ndi dokotala",   "HOSPITAL_QUEUE"),
    ("ndikufuna kuonana ndi dokotara",   "HOSPITAL_QUEUE"),
    ("ndikudwala",                       "HOSPITAL_QUEUE"),
    ("ndikudwara",                       "HOSPITAL_QUEUE"),
    ("ndikufuna pasipoti",               "IMMIGRATION"),
    ("ndikufuna pasiposi",               "IMMIGRATION"),
    ("ndikufuna kupita kunja",           "IMMIGRATION"),
    ("ndataya ID yanga",                 "NATIONAL_ID"),
    ("ndataya aidi yanga",               "NATIONAL_ID"),
    ("ndikufuna chipaso cha dziko",      "NATIONAL_ID"),
]


@pytest.mark.parametrize("transcript,expected", NOISY_INTENTS)
def test_noisy_intents_resolve_correctly(transcript, expected):
    result = match(transcript, SERVICE_INTENTS)
    assert result.outcome is not Outcome.REJECT, f"rejected: {transcript}"
    assert result.key == expected, (
        f"{transcript!r} -> {result.key} (score {result.score}, "
        f"runner-up {result.runner_up} {result.runner_up_score})"
    )


OPEN_ENDED_INTENTS = [
    ("Ndikufuna kulembetsa mwana wanga", "BIRTH_REGISTRATION"),
    ("Mwana wanga wabadwa, ndithandizeni", "BIRTH_REGISTRATION"),
    ("Ndikufuna kalata ya kubadwa", "BIRTH_REGISTRATION"),
    ("Ndikudwala ndipo ndikufuna dokotala", "HOSPITAL_QUEUE"),
    ("Ndabwera ku chipatala", "HOSPITAL_QUEUE"),
    ("Ndikufuna chithandizo ku chipatala", "HOSPITAL_QUEUE"),
    ("ndabwala kuchipatala", "HOSPITAL_QUEUE"),  # observed ASR transcript in x06.wav
    ("Ndikufuna pasipoti yatsopano", "IMMIGRATION"),
    ("Ndikupita kunja, ndikufuna chikalata cha ulendo", "IMMIGRATION"),
    ("Pasipoti yanga yawonongeka", "IMMIGRATION"),
    ("ndikufuna pasports", "IMMIGRATION"),  # observed ASR transcript in x09.wav
    ("Ndataya chiphaso changa cha dziko", "NATIONAL_ID"),
    ("Ndikufuna national ID", "NATIONAL_ID"),
    ("Ndikufuna chiphaso cha nzika", "NATIONAL_ID"),
    ("Ndikufuna kulembetsa malo anga", "LAND_REGISTRATION"),
    ("Ndikufuna chikalata cha malo", "LAND_REGISTRATION"),
    ("Ndikufuna kulembetsa nthaka", "LAND_REGISTRATION"),
    ("Chipatala chapafupi chili kuti?", "HEALTH_FACILITY_INFO"),
    ("Kodi chipatala chili kuti?", "HEALTH_FACILITY_INFO"),
    ("Ndikufuna kudziwa komwe kuli chipatala", "HEALTH_FACILITY_INFO"),
]


@pytest.mark.parametrize("transcript,expected", OPEN_ENDED_INTENTS)
def test_open_ended_intent_classifier_covers_six_services(transcript, expected):
    result = classify_intent(transcript)
    assert result.outcome is Outcome.ACCEPT, result
    assert result.key == expected
    assert result.score >= 0.78
    assert result.confidence in {"high", "medium"}


def test_open_ended_classifier_flags_two_service_mentions_as_ambiguous():
    result = classify_intent(
        "Ndikufuna pasipoti komanso kalata ya kubadwa"
    )
    assert result.outcome is Outcome.DISAMBIGUATE
    assert {result.key, result.runner_up} == {"IMMIGRATION", "BIRTH_REGISTRATION"}
    assert result.confidence == "ambiguous"


@pytest.mark.parametrize("transcript", ["zzzz qqqq xxxx", "", "ndithandizeni basi"])
def test_open_ended_classifier_rejects_nonsense_or_non_service_request(transcript):
    result = classify_intent(transcript)
    assert result.outcome is Outcome.REJECT
    assert result.key is None
    assert result.confidence == "low"


NOISY_DISTRICTS = [
    ("Lilongwe", "Lilongwe"),
    ("Lirongwe", "Lilongwe"),
    ("ku Lilongwe", "Lilongwe"),
    ("Blantyre", "Blantyre"),
    ("Burantayala", "Blantyre"),
    ("Zomba", "Zomba"),
    ("Somba", "Zomba"),
    ("Mzuzu", "Mzuzu"),
    ("Musuzu", "Mzuzu"),
    ("Mangochi", "Mangochi"),
    ("Mangoci", "Mangochi"),
    ("Kasungu", "Kasungu"),
    ("Karonga", "Karonga"),
    ("Thyolo", "Thyolo"),
    ("Tyolo", "Thyolo"),
]


@pytest.mark.parametrize("transcript,expected", NOISY_DISTRICTS)
def test_noisy_districts_resolve_correctly(transcript, expected):
    result = match(transcript, DISTRICTS)
    assert result.key == expected, (
        f"{transcript!r} -> {result.key} (score {result.score})"
    )


NOISY_YES_NO = [
    ("inde", "YES"), ("eya", "YES"), ("ee", "YES"), ("indee", "YES"),
    ("ndithu", "YES"), ("chabwino", "YES"),
    ("ayi", "NO"), ("iyayi", "NO"), ("ai", "NO"), ("sindikufuna", "NO"),
]


@pytest.mark.parametrize("transcript,expected", NOISY_YES_NO)
def test_yes_no_resolves(transcript, expected):
    assert match(transcript, YES_NO).key == expected


def test_months_resolve_with_spelling_drift():
    assert match("Malitchi", MONTHS).key == "03"
    assert match("Okutobala", MONTHS).key == "10"
    assert match("Disembala", MONTHS).key == "12"


def test_gibberish_is_rejected_not_guessed():
    """A wrong answer is far worse than asking again. This must REJECT."""
    result = match("zzzz qqqq xxxx", DISTRICTS)
    assert result.outcome is Outcome.REJECT
    assert result.key is None


def test_silence_is_rejected():
    assert match("", DISTRICTS).outcome is Outcome.REJECT


def test_contains_any_finds_yes_inside_a_longer_utterance():
    assert contains_any("eee ndikuganiza kuti inde", ["inde", "eya"])
    assert not contains_any("sindikudziwa konse", ["inde", "eya"])


def test_match_requires_candidates():
    with pytest.raises(ValueError):
        match("inde", [])


def test_similarity_is_symmetric_and_bounded():
    assert similarity("Lilongwe", "Lirongwe") == similarity("Lirongwe", "Lilongwe")
    assert 0.0 <= similarity("abc", "xyz") <= 1.0
    assert similarity("Lilongwe", "Lilongwe") == 1.0
