"""
MTHANDIZI - TTS capitalization diagnostic.

Follow-up to a real finding (2026-09-20): "Moni" synthesized consistently as
something like "poli" across 5 different random seeds - ruling out bad luck
with the seed (a genuinely useful negative result). This tests whether
CAPITALIZATION is the actual cause: many TTS tokenizers are trained mostly
on lowercase text and can mishandle a capitalized first letter differently
than the same word in lowercase.

If lowercase "moni" comes out clear and "Moni"/"MONI" don't, the fix is
trivial (lowercase text before synthesis). If none of them are clear, this
confirms a genuine model-level limitation for this specific word, and the
pre-recorded human-voice fallback (already designed into TtsEngine) is the
right call - not something to keep chasing.
"""
import os
import sys

import torch
from lab.tts import SynthTts

VARIANTS = ["Moni", "moni", "MONI", "Moni.", "moni.", "Moni,"]

print(f"Synthesizing {len(VARIANTS)} case/punctuation variants of the same word...\n")

engine = SynthTts()
engine.load()

results = []
for i, text in enumerate(VARIANTS):
    torch.manual_seed(1337)  # same seed throughout - isolating case/punctuation, not seed variance
    key = f"case_variant_{i}"
    speech = engine.speak(text, key=key)
    results.append((text, speech))
    print(f"  {text!r:10} -> {speech.wav_path}")

print(f"\n{len(results)} files written. Opening each a few seconds apart.\n")

if sys.platform == "win32":
    import time
    for text, speech in results:
        print(f"  opening {text!r} ...")
        os.startfile(speech.wav_path)
        time.sleep(3)
else:
    for text, speech in results:
        print(f"  {text!r} -> {speech.wav_path}")

print("\nListen to each. Does ANY variant sound like a clear 'Moni'?")
