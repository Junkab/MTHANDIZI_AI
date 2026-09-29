"""
MTHANDIZI Phase 0 gate — ASR benchmark.

Runs every recording listed in audio/manifest.csv through one or more checkpoints
and reports the three numbers that decide the architecture:

    WER            - free-dictation accuracy      (expect ~0.40, this is fine)
    CER            - character closeness          (expect ~0.12, this is the opportunity)
    SLOT ACCURACY  - how often the noisy transcript still resolves to the RIGHT
                     closed-set answer after phonetic folding
                     (this is the number that predicts whether the kiosk works,
                      and the number to put in front of judges)

Plus latency, because a kiosk that takes 8 seconds to answer is a kiosk nobody uses.

USAGE
-----
    python benchmark.py                       # default checkpoint, all recordings
    python benchmark.py --checkpoints 307h 68h
    python benchmark.py --limit 5             # quick smoke test

Writes reports/benchmark_<timestamp>.json and prints a table.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from lab.asr import CHECKPOINTS, AsrEngine
from lab.config import settings
from lab.matching import DISTRICTS, MONTHS, SERVICE_INTENTS, YES_NO, Outcome, classify_intent, resolve
from lab.metrics import aggregate, character_error_rate, word_error_rate

# Which closed set to resolve against, per manifest 'slot' column.
SLOT_SETS = {
    "intent": SERVICE_INTENTS,
    "district": DISTRICTS,
    "month": MONTHS,
    "yesno": YES_NO,
}


def read_manifest(path: Path) -> list[dict]:
    if not path.exists():
        sys.exit(
            f"\nNo manifest at {path}\n\n"
            "Record your utterances first, then create audio/manifest.csv with columns:\n"
            "  file,reference,slot,expected\n\n"
            "See UTTERANCES.md for the list of phrases to record, and\n"
            "audio/manifest.example.csv for the format.\n"
        )
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row.get("file")]
    if not rows:
        sys.exit(f"Manifest {path} has no rows.")
    return rows


def run_checkpoint(name: str, model_id: str, rows: list[dict]) -> dict:
    print(f"\n{'=' * 70}\nCheckpoint: {name}  ({model_id})\n{'=' * 70}")
    engine = AsrEngine(model_id)

    print("Loading model (first run downloads weights — this can take a while)...")
    load_started = time.perf_counter()
    engine.load()
    print(f"Model loaded in {time.perf_counter() - load_started:.1f}s")

    pairs: list[tuple[str, str]] = []
    details: list[dict] = []
    slot_hits = slot_total = 0
    latencies: list[float] = []

    for index, row in enumerate(rows, start=1):
        audio_path = Path(row["file"])
        if not audio_path.is_absolute():
            audio_path = settings.audio_dir / audio_path
        if not audio_path.exists():
            print(f"  [{index:>3}] MISSING FILE: {audio_path}")
            continue

        result = engine.transcribe_file(audio_path)
        reference = (row.get("reference") or "").strip()
        pairs.append((reference, result.text))
        latencies.append(result.seconds)

        wer = word_error_rate(reference, result.text)
        cer = character_error_rate(reference, result.text)

        slot_outcome = None
        slot_correct = None
        slot_name = (row.get("slot") or "").strip().lower()
        expected = (row.get("expected") or "").strip()
        if slot_name in SLOT_SETS and expected:
            slot_total += 1
            m = (
                classify_intent(result.text)
                if slot_name == "intent"
                else resolve(result.text, SLOT_SETS[slot_name])
            )
            slot_outcome = m.outcome.value
            slot_correct = (m.key == expected)
            if slot_correct:
                slot_hits += 1

        flag = "OK " if wer.rate == 0 else ("~  " if wer.rate <= 0.34 else "XX ")
        if slot_correct is False:
            flag = "!! "
        print(f"  [{index:>3}] {flag} wer={wer.percent:>6.2f}% cer={cer.percent:>6.2f}% "
              f"{result.seconds:>5.2f}s rtf={result.realtime_factor:>4.2f}")
        print(f"        ref: {reference}")
        print(f"        hyp: {result.text}")
        if slot_name in SLOT_SETS and expected:
            mark = "correct" if slot_correct else f"WRONG (got {m.key})"
            print(f"        slot[{slot_name}] expected={expected} -> {slot_outcome} {mark}")

        details.append({
            "file": str(audio_path.name),
            "reference": reference,
            "hypothesis": result.text,
            "wer": wer.rate, "cer": cer.rate,
            "seconds": result.seconds,
            "audio_seconds": result.audio_seconds,
            "realtime_factor": round(result.realtime_factor, 3),
            "slot": slot_name or None,
            "expected": expected or None,
            "slot_outcome": slot_outcome,
            "slot_correct": slot_correct,
        })

    corpus = aggregate(pairs)
    summary = {
        "checkpoint": name,
        "model_id": model_id,
        "load_seconds": round(engine.load_seconds or 0.0, 2),
        **corpus,
        "slot_accuracy": round(slot_hits / slot_total, 4) if slot_total else None,
        "slot_correct": slot_hits,
        "slot_total": slot_total,
        "mean_latency": round(sum(latencies) / len(latencies), 3) if latencies else None,
        "max_latency": round(max(latencies), 3) if latencies else None,
    }

    print(f"\n  ---- {name} summary ----")
    print(f"  utterances     : {summary['utterances']}")
    print(f"  WER            : {summary['wer']:.4f}   ({summary['word_errors']}/{summary['words']} words)")
    print(f"  CER            : {summary['cer']:.4f}   ({summary['char_errors']}/{summary['chars']} chars)")
    if summary["slot_accuracy"] is not None:
        print(f"  SLOT ACCURACY  : {summary['slot_accuracy']:.4f}   "
              f"({summary['slot_correct']}/{summary['slot_total']})  <-- the number that matters")
    print(f"  mean latency   : {summary['mean_latency']}s   (max {summary['max_latency']}s)")

    return {"summary": summary, "details": details}


def main() -> None:
    parser = argparse.ArgumentParser(description="MTHANDIZI Phase 0 ASR benchmark")
    parser.add_argument("--checkpoints", nargs="+", default=["307h"],
                        choices=sorted(CHECKPOINTS.keys()))
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    manifest_path = Path(args.manifest) if args.manifest else settings.audio_dir / "manifest.csv"
    rows = read_manifest(manifest_path)
    if args.limit:
        rows = rows[: args.limit]

    print(f"MTHANDIZI Phase 0 benchmark — {len(rows)} utterances "
          f"from {manifest_path}")

    results = [run_checkpoint(name, CHECKPOINTS[name], rows) for name in args.checkpoints]

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = settings.reports_dir / f"benchmark_{stamp}.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'=' * 70}\nCOMPARISON\n{'=' * 70}")
    header = f"{'checkpoint':<10}{'WER':>9}{'CER':>9}{'SLOT ACC':>11}{'latency':>10}"
    print(header)
    print("-" * len(header))
    for entry in results:
        s = entry["summary"]
        slot = f"{s['slot_accuracy']:.3f}" if s["slot_accuracy"] is not None else "n/a"
        print(f"{s['checkpoint']:<10}{s['wer']:>9.3f}{s['cer']:>9.3f}"
              f"{slot:>11}{s['mean_latency'] or 0:>9.2f}s")

    print(f"\nFull report: {out_path}")
    print("\nPASTE THIS TABLE BACK TO ME — it decides the checkpoint and the thresholds.")


if __name__ == "__main__":
    main()
