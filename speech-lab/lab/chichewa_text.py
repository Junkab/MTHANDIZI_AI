"""
MTHANDIZI — Chichewa text normalisation and phonetic folding.

WHY THIS FILE EXISTS
--------------------
The CLEAR Global ASR model measures ~0.40 WER but only ~0.12 CER. In plain terms:
whole words are often "wrong", but the characters are usually *close*. That gap is
the entire opportunity. If we compare a noisy transcript to a small set of expected
answers using a phonetically-folded form, near-misses collapse onto the right answer.

Nothing in this file needs a model, a GPU, or a network connection. It is pure logic,
fully unit tested, and it runs identically here and inside the Android app once ported
to Kotlin.

ORTHOGRAPHY NOTE
----------------
Standard Malawian Chichewa orthography. Zambian Nyanja differs in places (e.g. 'ny'
vs 'n'). Folding rules below are deliberately conservative: they fold distinctions
that ASR commonly confuses, not distinctions that carry meaning across our closed sets.
"""

from __future__ import annotations

import re
import unicodedata

# Prefixes that attach to Chichewa stems. When comparing a spoken answer to a
# closed-set candidate ("Lilongwe"), the speaker may say "ku Lilongwe" / "kuLilongwe".
# We strip these only for STEM comparison, never from displayed text.
NOUN_CLASS_PREFIXES = (
    "ndikufuna", "ndikuti", "ndine", "ndili",
    "kwathu", "kuno", "kuli",
    "ndi", "ku", "mu", "pa", "chi", "ma", "mwa", "wa", "ya", "za", "la", "a",
)

# Ordered longest-first so multi-character rules apply before single-character ones.
_PHONETIC_RULES: list[tuple[str, str]] = [
    ("ph", "p"),   # aspiration is unreliably transcribed
    ("th", "t"),
    ("kh", "k"),
    ("tch", "c"),
    ("ch", "c"),
    ("ts", "c"),
    ("dz", "z"),
    ("ny", "n"),
    ("ng'", "g"),  # velar nasal, often written ŋ or ng'
    ("ng", "g"),
    ("sh", "s"),
    ("zh", "z"),
    ("b", "v"),    # b/v/w cluster is a common confusion
    ("w", "v"),
    ("r", "l"),    # r/l are not phonemically distinct for many speakers
]

_WS = re.compile(r"\s+")
_NON_WORD = re.compile(r"[^a-z0-9' ]+")


def strip_accents(text: str) -> str:
    """Remove combining marks; Chichewa is written without tone marks in practice."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalise(text: str) -> str:
    """
    Surface normalisation applied to BOTH sides of every comparison, and to
    reference transcripts before scoring WER/CER.

    Lowercase, strip accents and punctuation, collapse whitespace.
    Does NOT fold phonetics — use fold() for that.
    """
    if not text:
        return ""
    text = strip_accents(text.lower())
    text = text.replace("’", "'").replace("`", "'")
    text = _NON_WORD.sub(" ", text)
    return _WS.sub(" ", text).strip()


def fold(text: str) -> str:
    """
    Phonetic folding for fuzzy matching. Aggressive and lossy by design.

    Never display folded text to a user. It exists only to make
    'ndikufuna kulembetsa' and 'ndikufuna kulembeca' compare as equal.
    """
    text = normalise(text)
    for src, dst in _PHONETIC_RULES:
        text = text.replace(src, dst)
    text = re.sub(r"(.)\1+", r"\1", text)      # collapse doubled letters
    text = text.replace("'", "")
    return _WS.sub(" ", text).strip()


def strip_prefixes(word: str) -> str:
    """
    Reduce a folded word to its stem by removing one leading noun-class prefix.

    Only strips if a reasonable stem remains (>= 3 chars), so 'ndi' itself
    survives intact rather than vanishing to ''.
    """
    for prefix in sorted(NOUN_CLASS_PREFIXES, key=len, reverse=True):
        folded_prefix = fold(prefix)
        if word.startswith(folded_prefix) and len(word) - len(folded_prefix) >= 3:
            return word[len(folded_prefix):]
    return word


def stem_tokens(text: str) -> list[str]:
    """
    Folded, prefix-stripped tokens. The comparison form for closed-set matching.

    Handles prefixes written as separate words too ('ku Lilongwe' == 'Lilongwe'),
    but only drops a standalone prefix when other tokens remain — so the single
    word 'ndi' survives as itself.
    """
    folded_prefixes = {fold(p) for p in NOUN_CLASS_PREFIXES}
    tokens = [tok for tok in fold(text).split() if tok]
    if len(tokens) > 1:
        kept = [tok for tok in tokens if tok not in folded_prefixes]
        if kept:
            tokens = kept
    return [strip_prefixes(tok) for tok in tokens]


def levenshtein(a: str, b: str) -> int:
    """Classic edit distance. Small inputs, so the simple DP is fine."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(min(
                previous[j] + 1,        # deletion
                current[j - 1] + 1,     # insertion
                previous[j - 1] + (ca != cb),  # substitution
            ))
        previous = current
    return previous[-1]


def similarity(a: str, b: str) -> float:
    """Normalised similarity in [0.0, 1.0] over the folded forms."""
    fa, fb = fold(a), fold(b)
    if not fa and not fb:
        return 1.0
    longest = max(len(fa), len(fb))
    if longest == 0:
        return 1.0
    return 1.0 - (levenshtein(fa, fb) / longest)


def stem_similarity(a: str, b: str) -> float:
    """Similarity over prefix-stripped stems — best for single-word closed sets."""
    sa = " ".join(stem_tokens(a))
    sb = " ".join(stem_tokens(b))
    if not sa and not sb:
        return 1.0
    longest = max(len(sa), len(sb))
    if longest == 0:
        return 1.0
    return 1.0 - (levenshtein(sa, sb) / longest)
