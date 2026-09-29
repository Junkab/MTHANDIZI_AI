"""
MTHANDIZI - TTS seed diagnostic.

Follow-up to a real listening-test finding (2026-09-20): the greeting
"Moni. Ndine Mthandizi. Ndingakuthandizeni bwanji lero?" came back with everything
AFTER "Moni." sounding clear, but "Moni." itself unclear/garbled.

VITS (the model architecture behind mms-tts-nya) has a STOCHASTIC duration
predictor - the very first word in an utterance has no preceding context to
establish rhythm from, so it's more sensitive to random variation than words
that follow it. This script isolates the word "Moni" alone, synthesized at
several different random seeds, to find out whether this is:
  (a) a systematic problem with this specific word/model, or
  (b) just an unlucky random draw that a different seed avoids

Run this, listen to all 5 files, and report back which ones (if any) sound
clear. If MOST seeds sound fine, it's (b) - pin a working seed as the
default. If ALL seeds sound similarly off, it's (a) - the pre-recorded
human-voice fallback (already designed into TtsEngine from Phase 0) is the
right call for short standalone words like this, not a bug to keep chasing.
"""
import os
import sys

import torch
from lab.tts import SynthTts

WORD = "Moni"
SEEDS = [1337, 1, 42, 100, 2024]

print(f"Synthesizing {WORD!r} at {len(SEEDS)} different seeds...\n")

engine = SynthTts()
engine.load()  # load once, then reseed manually before each call below

results = []
for seed in SEEDS:
    torch.manual_seed(seed)
    speech = engine.speak(WORD, key=f"moni_seed_{seed}")
    results.append((seed, speech))
    print(f"  seed={seed:<6} -> {speech.wav_path}")

print(f"\n{len(results)} files written. Opening all of them now, a few seconds apart")
print("so you can listen to each one and compare.\n")

if sys.platform == "win32":
    import time
    for seed, speech in results:
        print(f"  opening seed={seed} ...")
        os.startfile(speech.wav_path)
        time.sleep(3)
else:
    print("(auto-open only implemented for Windows)")
    for seed, speech in results:
        print(f"  seed={seed} -> {speech.wav_path}")

print("\nListen to each. Which seed number(s) sound clear for 'Moni'?")
