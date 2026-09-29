"""
MTHANDIZI — ASR accuracy metrics.

Word Error Rate and Character Error Rate, computed the standard way
(edit distance against the reference, divided by reference length).

We report BOTH because they tell different stories for Chichewa:
  - WER  = how often whole words are wrong. Drives "can we do free dictation?" (no)
  - CER  = how close the characters are.    Drives "can we fuzzy-match?" (yes)

We also report a third, MTHANDIZI-specific number:
  - Slot accuracy = how often the noisy transcript still resolves to the CORRECT
    closed-set answer after phonetic folding. This is the number that actually
    predicts whether the kiosk works, and it is the one to quote to judges.
"""

from __future__ import annotations

from dataclasses import dataclass

from .chichewa_text import levenshtein, normalise


@dataclass(frozen=True)
class ErrorRate:
    errors: int
    total: int

    @property
    def rate(self) -> float:
        return self.errors / self.total if self.total else 0.0

    @property
    def percent(self) -> float:
        return round(self.rate * 100, 2)


def _token_levenshtein(ref: list[str], hyp: list[str]) -> int:
    if ref == hyp:
        return 0
    previous = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, start=1):
        current = [i]
        for j, h in enumerate(hyp, start=1):
            current.append(min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + (r != h),
            ))
        previous = current
    return previous[-1]


def word_error_rate(reference: str, hypothesis: str) -> ErrorRate:
    ref = normalise(reference).split()
    hyp = normalise(hypothesis).split()
    return ErrorRate(_token_levenshtein(ref, hyp), len(ref))


def character_error_rate(reference: str, hypothesis: str) -> ErrorRate:
    ref = normalise(reference)
    hyp = normalise(hypothesis)
    return ErrorRate(levenshtein(ref, hyp), len(ref))


def aggregate(pairs: list[tuple[str, str]]) -> dict[str, float]:
    """
    Corpus-level WER/CER. Errors and lengths are pooled across all utterances
    (the correct way) rather than averaging per-utterance rates (the wrong way
    that flatters short utterances).
    """
    w_err = w_tot = c_err = c_tot = 0
    for reference, hypothesis in pairs:
        w = word_error_rate(reference, hypothesis)
        c = character_error_rate(reference, hypothesis)
        w_err += w.errors
        w_tot += w.total
        c_err += c.errors
        c_tot += c.total
    return {
        "utterances": len(pairs),
        "wer": round(w_err / w_tot, 4) if w_tot else 0.0,
        "cer": round(c_err / c_tot, 4) if c_tot else 0.0,
        "word_errors": w_err,
        "words": w_tot,
        "char_errors": c_err,
        "chars": c_tot,
    }
