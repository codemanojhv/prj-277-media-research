from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(PROJECT_ROOT / ".env")
DATA_DIR = PROJECT_ROOT / "apps" / "api" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'prj277.db').as_posix()}")
RELEVANCE_THRESHOLD = float(os.getenv("GOI_RELEVANCE_THRESHOLD", "0.55"))
ANALYSIS_PROVIDER = os.getenv("ANALYSIS_PROVIDER", "local").strip().casefold()
TYPESAFE_API_KEY = os.getenv("TYPESAFE_API_KEY", "").strip()
TYPESAFE_API_BASE_URL = os.getenv("TYPESAFE_API_BASE_URL", "https://api.typesafe.ai").rstrip("/")
TYPESAFE_MODEL = os.getenv("TYPESAFE_MODEL", "jev-latest").strip()
TYPESAFE_TIMEOUT_SECONDS = float(os.getenv("TYPESAFE_TIMEOUT_SECONDS", "25"))
JEV_MIN_CONFIDENCE = float(os.getenv("JEV_MIN_CONFIDENCE", "0.60"))
JEV_MAX_ARTICLE_CHARS = int(os.getenv("JEV_MAX_ARTICLE_CHARS", "12000"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "25"))
GEMINI_MAX_ARTICLE_CHARS = int(os.getenv("GEMINI_MAX_ARTICLE_CHARS", "8000"))
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
