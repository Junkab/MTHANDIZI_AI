# Phase 0 recording script

Record each line below as a **separate WAV file** into `audio/recordings/`, using the
filename given in the first column. Then fill in `audio/manifest.csv`.

## How to record

- **Quiet set first** (filenames `q01`–`q24`): quiet room, phone or laptop mic, ~15cm away.
- **Noisy set second** (filenames `n01`–`n12`, pick any 12 of the same phrases):
  record with background noise — a radio, people talking, a fan. This is what a
  hospital hall actually sounds like, and judges will ask.
- Mono, 16000 Hz if your recorder allows it. If not, any WAV is fine — the loader
  resamples. **Do not use MP3** for the reference set.
- Speak naturally at normal pace. Do not over-enunciate. We are measuring reality.
- **Get at least two different speakers** if you can — one male, one female, ideally
  one older. Single-speaker results will flatter the model.

Windows Voice Recorder saves `.m4a`; convert with ffmpeg, or use Audacity and
**File → Export → Export as WAV**.

---

## Service intents (the opening question: "Ndingakuthandizeni bwanji lero?")

| File | Chichewa | English | slot | expected |
|---|---|---|---|---|
| q01 | Ndikufuna kulembetsa mwana wanga | I want to register my child | intent | BIRTH_REGISTRATION |
| q02 | Ndikufuna kalata ya kubadwa | I want a birth certificate | intent | BIRTH_REGISTRATION |
| q03 | Mwana wanga wabadwa, ndikufuna kulembetsa | My child was born, I want to register | intent | BIRTH_REGISTRATION |
| q04 | Ndikufuna kuonana ndi dokotala | I want to see a doctor | intent | HOSPITAL_QUEUE |
| q05 | Ndikudwala | I am sick | intent | HOSPITAL_QUEUE |
| q06 | Ndabwera ku chipatala | I have come to the hospital | intent | HOSPITAL_QUEUE |
| q07 | Ndikufuna chiphaso cha dziko | I want a national ID | intent | NATIONAL_ID |
| q08 | Ndataya chiphaso changa | I lost my ID | intent | NATIONAL_ID |
| q09 | Ndikufuna pasipoti | I want a passport | intent | IMMIGRATION |
| q10 | Ndikufuna kupita kunja | I want to travel abroad | intent | IMMIGRATION |

## Yes / no (the most safety-critical recognition in the whole system)

| File | Chichewa | English | slot | expected |
|---|---|---|---|---|
| q11 | Inde | Yes | yesno | YES |
| q12 | Eya | Yes | yesno | YES |
| q13 | Ndithu | Certainly | yesno | YES |
| q14 | Ayi | No | yesno | NO |
| q15 | Iyayi | No | yesno | NO |
| q16 | Sindikufuna | I don't want to | yesno | NO |

## Districts

| File | Chichewa | English | slot | expected |
|---|---|---|---|---|
| q17 | Lilongwe | Lilongwe | district | Lilongwe |
| q18 | Blantyre | Blantyre | district | Blantyre |
| q19 | Ku Mzuzu | In Mzuzu | district | Mzuzu |
| q20 | Mangochi | Mangochi | district | Mangochi |
| q21 | Thyolo | Thyolo | district | Thyolo |

## Months

| File | Chichewa | English | slot | expected |
|---|---|---|---|---|
| q22 | Malichi | March | month | 03 |
| q23 | Okutobala | October | month | 10 |
| q24 | Disembala | December | month | 12 |

---

## Also record these — no expected value, they test free dictation

These have no closed set. They exist to measure raw WER honestly, and to prove the
point that we should never rely on free dictation.

| File | Chichewa |
|---|---|
| f01 | Dzina langa ndine Mathews Dube |
| f02 | Ndinabadwa pa tsiku la khumi la mwezi wa Malichi |
| f03 | Ndimakhala ku mudzi wa Chilinde, mfumu Kabudula |
| f04 | Sindinamve bwino, bwerezani chonde |

Leave `slot` and `expected` blank for these rows in the manifest.
