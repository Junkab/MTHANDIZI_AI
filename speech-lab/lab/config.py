"""
MTHANDIZI — configuration.

ONE place loads environment config. Every entry point (lab server, benchmark script,
future FastAPI service) imports `settings` from here.

This is deliberate: the previous build of this project broke because dotenv loading
was scattered per-script, so a script run standalone picked up different config than
the server. Never load .env anywhere but here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    """Minimal .env loader — no dependency, no surprises. Real env vars win."""
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


def _path(env_key: str, default: str) -> Path:
    return Path(os.environ.get(env_key, str(ROOT / default)))


@dataclass(frozen=True)
class Settings:
    # --- models ---
    asr_checkpoint: str = os.environ.get(
        "MTHANDIZI_ASR_CHECKPOINT",
        "CLEAR-Global/w2v-bert-2.0-chichewa_34_307h",
    )
    tts_checkpoint: str = os.environ.get("MTHANDIZI_TTS_CHECKPOINT",
                                         "facebook/mms-tts-nya")
    tts_seed: int = int(os.environ.get("MTHANDIZI_TTS_SEED", "1337"))

    # --- paths ---
    audio_dir: Path = field(default_factory=lambda: _path("MTHANDIZI_AUDIO_DIR", "audio"))
    recordings_dir: Path = field(
        default_factory=lambda: _path("MTHANDIZI_RECORDINGS_DIR", "audio/recordings"))
    prompts_dir: Path = field(
        default_factory=lambda: _path("MTHANDIZI_PROMPTS_DIR", "audio/prompts"))
    tts_out_dir: Path = field(
        default_factory=lambda: _path("MTHANDIZI_TTS_OUT_DIR", "audio/tts_out"))
    reports_dir: Path = field(
        default_factory=lambda: _path("MTHANDIZI_REPORTS_DIR", "reports"))

    # --- lab server ---
    host: str = os.environ.get("MTHANDIZI_HOST", "0.0.0.0")
    port: int = int(os.environ.get("MTHANDIZI_PORT", "8077"))

    def ensure_dirs(self) -> None:
        for directory in (self.audio_dir, self.recordings_dir,
                          self.prompts_dir, self.tts_out_dir, self.reports_dir):
            directory.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
