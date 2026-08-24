"""Runtime configuration. Secrets come from the environment, never from source."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("AISTUDIO_DATA", ROOT / "data"))
DB_PATH = Path(os.environ.get("AISTUDIO_DB", DATA_DIR / "aistudio.db"))
SECRET = os.environ.get("AISTUDIO_SECRET", "dev-secret-change-me")
SEED_PATH = Path(__file__).resolve().parent / "seed.json"
TOKEN_TTL_SECONDS = int(os.environ.get("AISTUDIO_TOKEN_TTL", str(7 * 24 * 3600)))

DEMO_EMAIL = os.environ.get("AISTUDIO_DEMO_EMAIL", "katharina.vogel@meridian.example")
DEMO_PASSWORD = os.environ.get("AISTUDIO_DEMO_PASSWORD", "Meridian2026!")
DEMO_NAME = os.environ.get("AISTUDIO_DEMO_NAME", "Dr. Katharina Vogel")
DEMO_ROLE = os.environ.get("AISTUDIO_DEMO_ROLE", "cfo")

HOST = os.environ.get("AISTUDIO_HOST", "0.0.0.0")
PORT = int(os.environ.get("AISTUDIO_PORT", "8123"))
