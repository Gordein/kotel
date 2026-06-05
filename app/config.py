import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
    DB_PATH = os.environ.get("KOTEL_DB", str(BASE_DIR / "kotel.db"))
    TZ = "Europe/Warsaw"
    TESTING = False
