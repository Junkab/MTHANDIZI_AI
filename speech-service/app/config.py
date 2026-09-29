"""
MTHANDIZI Speech Service — configuration.

ARCHITECTURAL DECISION: this service imports the `lab` package from ../speech-lab
rather than duplicating asr.py / tts.py / matching.py / chichewa_text.py here.

Why: Phase 0's benchmark run found and fixed a real, dangerous bug (the
sindikudziwa/sindikufuna collision - see BUILD_LOG.md) inside the matching logic.
If that logic were copy-pasted into a second project, a future fix would have to
be applied twice, and it is exactly the kind of thing that gets missed once.
One matcher, one ASR wrapper, one TTS wrapper - speech-lab owns them, this
service depends on them. speech-lab remains the R&D/benchmark tool; this folder
is what actually runs on the kiosk.

Same single-env-loading-point rule as speech-lab/lab/config.py: nothing else in
this project reads os.environ or a .env file directly.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # .../speech-service
PROJECT_ROOT = ROOT.parent                              # .../mthandizi
SPEECH_LAB = PROJECT_ROOT / "speech-lab"

if not SPEECH_LAB.exists():
    raise RuntimeError(
        f"Expected to find ../speech-lab next to this service at {SPEECH_LAB}, "
        "but it's not there. speech-service depends on speech-lab's lab/ package "
        "(asr.py, tts.py, matching.py) rather than duplicating it - both folders "
        "need to stay siblings under the same mthandizi/ project root."
    )
sys.path.insert(0, str(SPEECH_LAB))


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


@dataclass(frozen=True)
class ServiceSettings:
    host: str = os.environ.get("MTHANDIZI_SERVICE_HOST", "0.0.0.0")
    port: int = int(os.environ.get("MTHANDIZI_SERVICE_PORT", "8090"))

    # Uploaded audio is written here before being read back for transcription,
    # rather than to the OS's default Temp folder. Reason (found on the
    # operator's machine, 2026-09-20): a single 3.5s clip took 216 seconds to
    # transcribe over HTTP - 60x realtime - versus 3-4s for the SAME model on
    # the SAME machine via benchmark.py, which reads files directly from
    # speech-lab/audio/recordings/. The one meaningful difference: this
    # service was writing to Windows' default Temp folder, which sits OUTSIDE
    # any Defender exclusion the operator added for the project folder -
    # antivirus real-time scanning very plausibly does synchronous, expensive
    # scanning on brand-new files there. Keeping temp uploads inside this
    # project's own folder tree means they're covered by the same exclusion
    # the operator already set up, without depending on them remembering to
    # exclude the OS Temp folder too. See BUILD_LOG.md for the full story and
    # whether this actually explains the slowdown once re-tested.
    tmp_dir: Path = ROOT / "tmp"

    # Eager load = correct kiosk behaviour (no citizen waits 2 minutes for the
    # first request while the model loads). Lazy load = faster dev iteration.
    # Default eager; override for local development only.
    eager_load_asr: bool = os.environ.get("MTHANDIZI_EAGER_LOAD", "true").lower() == "true"

    asr_checkpoint: str = os.environ.get(
        "MTHANDIZI_ASR_CHECKPOINT",
        "CLEAR-Global/w2v-bert-2.0-chichewa_34_307h",
    )

    # CORS: the Android and Windows clients call this over a private LAN, never
    # the public internet. Wide open by IP-origin is acceptable here because the
    # network itself is the security boundary (see SECURITY.md, Phase 15) - this
    # is not a public-internet-facing service.
    cors_allow_origins: tuple[str, ...] = ("*",)

    max_upload_bytes: int = int(os.environ.get("MTHANDIZI_MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))


settings = ServiceSettings()
settings.tmp_dir.mkdir(parents=True, exist_ok=True)
