# MTHANDIZI

*Lankhulani. Mthandizi akuthandizeni.* — Speak. Mthandizi will help you.

An offline-capable, Chichewa-speaking government-service kiosk prototype for the
ICTAM Malawi Innovative Competition.

## Run the browser kiosk demo on Windows

This starts three local components: PostgreSQL for saved applications, the speech
service for Chichewa ASR/TTS, and the Express backend that serves the kiosk page.
Use **three separate PowerShell terminals** and leave each running. Commands below
assume the project is at `C:\Users\MATHEWS JK DUBE\Desktop\19spt_MTHANDIZI\mthandizi`.

### 1. One-time prerequisites

- Install **Python 3.13 x64**, **Node.js**, and **Docker Desktop**. Docker is the
   quickest way to start the project's PostgreSQL 16 database. If using an existing
   PostgreSQL installation instead, create a database/user that match `backend/.env`.
- Open PowerShell at the project root:

   ```powershell
   Set-Location 'C:\Users\MATHEWS JK DUBE\Desktop\19spt_MTHANDIZI\mthandizi'
   py -3.13 --version
   node --version
   docker --version
   ```

   Confirm Python reports 3.13.x. The workspace's separate `.venv` may use a newer
   Python; the speech model's pinned dependencies are intended for Python 3.13.
- Create a dedicated speech environment (do this once):

   ```powershell
   py -3.13 -m venv speech-lab\venv313
   & .\speech-lab\venv313\Scripts\python.exe -m pip install --upgrade pip
   & .\speech-lab\venv313\Scripts\python.exe -m pip install -r speech-lab\requirements.txt
   ```

   PyTorch and the ASR model are large downloads. Allow time and disk space. The
   machine needs internet access for the first model download; later starts can work
   offline if the ASR and TTS models have already been cached. TTS is downloaded
   lazily the first time a prompt is synthesized.
- In a separate terminal, make sure npm dependencies are installed once:

   ```powershell
   Set-Location 'C:\Users\MATHEWS JK DUBE\Desktop\19spt_MTHANDIZI\mthandizi\backend'
   npm install
   ```

### 2. Start PostgreSQL — Terminal 1

Start Docker Desktop, then:

```powershell
Set-Location 'C:\Users\MATHEWS JK DUBE\Desktop\19spt_MTHANDIZI\mthandizi\backend'
docker compose up -d postgres
docker compose ps
```

Wait until the `postgres` service is healthy. Compose creates database `mthandizi`,
user `mthandizi`, and development password `devpassword`, matching the provided
`.env.example`. If port 5432 is already in use, stop the other PostgreSQL instance
or configure one database server consistently; don't run both on the same port.

### 3. Start the speech service — Terminal 2

Open a new PowerShell window:

```powershell
Set-Location 'C:\Users\MATHEWS JK DUBE\Desktop\19spt_MTHANDIZI\mthandizi\speech-service'
..\speech-lab\venv313\Scripts\python.exe -m app.main
```

Wait for the model-loading message and `Uvicorn running on http://0.0.0.0:8090`.
The first ASR model load can take minutes and may download weights. On the first
start, the service also synthesizes the fixed kiosk prompts into a reusable WAV
cache; this adds a one-time wait before it is ready. Do not close this window.
In a third temporary PowerShell window, check readiness:

```powershell
Invoke-RestMethod http://localhost:8090/health | Format-List
```

Continue only when `status` is `ok`, `asr_loaded` is `True`, and
`tts_prompts_ready` is `True`. A false value means model loading or prompt warm-up
is still in progress, or the lazy development launcher is running. For a quick
real-audio check from the project root:

```powershell
curl.exe -F "audio=@speech-lab/audio/recordings/q01.wav" "http://localhost:8090/asr?slot=intent"
```

Expect a transcript plus a `resolution` for `BIRTH_REGISTRATION`, an outcome, score,
and confidence. This posts the actual recording through ASR; the first request may
be slow. The `seconds` field is model time, not full browser round-trip latency.

### 4. Configure and start the backend — Terminal 3

Open another PowerShell window:

```powershell
Set-Location 'C:\Users\MATHEWS JK DUBE\Desktop\19spt_MTHANDIZI\mthandizi\backend'
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
Get-Content .env
npm start
```

By default the kiosk expects the speech service on the same PC at
`http://localhost:8090`. If the ASR computer is a different PC on the local
network, set `MTHANDIZI_SPEECH_SERVICE_URL` in `backend/.env` to that PC's LAN
address (for example `http://192.168.1.20:8090`) and restart the backend. Allow
port 8090 through that PC's firewall for the private network only.

The provided development `.env` values should match Docker Compose. If you use a
different PostgreSQL username/password/database, edit `.env` to match it, then
restart `npm start`. The backend applies database migrations automatically. Wait
for `MTHANDIZI backend listening on http://localhost:3000`. Verify in another
window:

```powershell
Invoke-RestMethod http://localhost:3000/health | Format-List
```

Expect `status: ok`. Keep both service windows open.

### 5. Exercise the kiosk

In a browser on the same computer, open **http://localhost:3000/kiosk/**. Allow
microphone access if asked. For a truly hands-free kiosk, configure its browser
to allow microphone capture and autoplay for this local site before opening the
page; ordinary browsers may block spoken audio until a user gesture. Once enabled,
the kiosk speaks each prompt, listens automatically after speaking, and stops
listening after a short pause. No tap-to-speak control or camera permission is
required during the conversation. The page should greet you and ask how it can
help; it should not display a service-selection list.

1. Say **“Ndikufuna kulembetsa mwana wanga.”** Mthandizi repeats the request;
   answer **“Inde”** or **“Ayi.”**
2. Answer each question after Mthandizi finishes speaking. For the date of birth,
   say the day, month, and four-digit year, for example **“10 Malichi 2024.”**
   Mthandizi repeats each recognized answer for confirmation. Impossible or
   unclear dates are rejected rather than saved.
3. Listen to the read-back of the completed application. Say **“Inde”** to submit
   or **“Ayi”** to start the form again. A reference should be spoken and shown
   after a successful submission.
4. Open **http://localhost:3000/admin/** to inspect the application. If no local
   demo admin exists, open another terminal at `backend` and run
   `node create_admin.mjs`. For this development-only helper the credentials are
   `officer1` / `correcthorsebattery`; do not use that account or password
   outside this local demo.
5. To try uncertainty handling, say two needs in one utterance, for example a
    passport and birth-registration request. The kiosk should ask a conversational
    follow-up rather than present a numbered menu. Nonsense or silence should prompt
    it to ask again, then direct the user to staff after repeated recognition failures.

**Current scope:** only birth registration has a complete workflow in this browser
demo. The other five intents (hospital queue, immigration, national ID, land
registration, and health-facility information) can be identified and confirmed but
then receive a staff-assistance message; they do not yet complete applications.

### 6. Measure performance on the supplied recordings

With the speech service either running or available to load the model, open another
PowerShell window at the project root and run:

```powershell
& .\speech-lab\venv313\Scripts\python.exe speech-lab\benchmark.py --checkpoints 307h
```

This re-runs ASR on the labeled benchmark clips, reports WER/CER, intent/slot
accuracy, and per-clip latency, then saves a JSON report under
`speech-lab\reports\`. It can take several minutes. Compare the *new* report with
the checked-in historical baseline, not as if it were a current measurement. The
browser microphone run is also worth timing separately: model `seconds` omit
recording, upload, preprocessing, and TTS playback time.

### Troubleshooting

- **Python/model import or DLL error:** confirm Terminal 2 uses
   `speech-lab\venv313\Scripts\python.exe`, Python 3.13, and completed dependency
   installation. Do not use the root `.venv` unless its Python/dependencies match.
- **Model download error / no network:** first-run ASR/TTS requires downloading
   weights. Connect to the internet and retry; offline startup works only after the
   model files are cached locally.
- **Speech health is unavailable:** confirm the service terminal has no traceback,
   port 8090 is free, then retry `/health`.
- **Backend says password authentication failed:** check Docker is healthy on
   port 5432 and that `backend/.env` database credentials match the running database.
- **Browser cannot record:** grant microphone permission and use `localhost` (not a
   remote non-HTTPS IP origin); see the page's permission/error message.
- **No synthesized voice:** the first TTS call downloads its model separately. Check
   the speech-service terminal for errors. TTS quality/licensing are still known
   limitations; do not assume it has been native-speaker approved.

For test and implementation history, see `BUILD_LOG.md`, [speech-service/README.md](speech-service/README.md),
and [backend/README.md](backend/README.md). This is a browser demo, not the Android
kiosk client.
