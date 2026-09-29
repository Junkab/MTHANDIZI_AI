"""
MTHANDIZI - one-shot TTS listening test.

Confirms facebook/mms-tts-nya actually resolves and produces audio - the
one thing in this whole project that has never been verified, across every
phase so far, because Hugging Face is unreachable from the authoring
sandbox. This has to run on a real machine. Run this file directly:

    python tts_test.py
"""
import os
import sys

from lab.tts import TtsEngine

PHRASES = [
    ("greeting", "Moni. Ndine Mthandizi. Ndingakuthandizeni bwanji lero?"),
    ("yes", "Inde"),
    ("thanks", "Zikomo"),
]

print("Synthesizing Chichewa speech via facebook/mms-tts-nya.")
print("First run downloads the model (~290MB - much smaller than the ASR")
print("model, should be quick even on a slow connection).\n")

engine = TtsEngine()
results = []
for key, text in PHRASES:
    print(f"  synthesizing: {text!r} ...")
    try:
        speech = engine.speak(text, key=None)  # force synth, no recorded prompt exists yet
        results.append((text, speech))
        print(f"    -> {speech.wav_path}  ({speech.seconds}s, source={speech.source})")
    except Exception as exc:
        print(f"    FAILED: {exc}")
        sys.exit(1)

print(f"\n{len(results)} file(s) synthesized successfully.")
print("Opening the first one now - listen and judge for yourself:")
print("does this sound like real Chichewa, or garbled/wrong-language noise?\n")

first_path = results[0][1].wav_path
if sys.platform == "win32":
    os.startfile(first_path)
else:
    print(f"(auto-open only implemented for Windows - open this manually: {first_path})")

print("\nOther generated files, if you want to check more than one phrase:")
for text, speech in results[1:]:
    print(f"  {text!r} -> {speech.wav_path}")
