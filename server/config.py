import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_PATH = DATA_DIR / "agent.db"

LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.xiaomimimo.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "sk-cc6c6kuej4n21dswiasbnv9fb35l8o3mgezqtko7m3fp6zsi")
LLM_MODEL = os.getenv("LLM_MODEL", "mimo-v2.5")

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
