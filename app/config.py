"""Runtime configuration. Everything is overridable through environment variables or a .env file."""
import os
from pathlib import Path


def _load_env() -> None:
    p = Path(".env")
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


_load_env()

DB_PATH = os.getenv("CAREFLOW_DB", "data/careflow.db")
API_KEY = os.getenv("NEBIUS_API_KEY", "")
# Verify both the base URL and the model IDs in the Nebius Token Factory console.
BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
MODELS = {
    "nano": os.getenv("MODEL_NANO", "nvidia/nemotron-3-nano"),
    "super": os.getenv("MODEL_SUPER", "nvidia/nemotron-3-super"),
    "ultra": os.getenv("MODEL_ULTRA", "nvidia/nemotron-3-ultra"),
}
TIMEOUT = {"nano": 15, "super": 25, "ultra": 40}
STUCK_DAYS = int(os.getenv("STUCK_DAYS", "5"))

ROLES = {"Coordinator": "Priya Nair", "Nurse": "Rahul Verma", "Admin": "Compliance Officer"}
