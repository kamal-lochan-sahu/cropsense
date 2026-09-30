"""Application configuration, read from environment variables (and a local .env)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


class Config:
    MODEL_PATH = str(BASE_DIR / "models" / "model.pkl")

    # Growing guides (Groq). Groq retires models regularly, so models are configurable
    # and a fallback chain is tried in order.
    GROQ_API_KEY = _env("GROQ_API_KEY")
    GROQ_MODEL = _env("GROQ_MODEL") or "openai/gpt-oss-120b"
    GROQ_FALLBACK_MODELS = [
        m.strip() for m in _env("GROQ_FALLBACK_MODELS", "qwen/qwen3.8-27b").split(",") if m.strip()
    ]
    GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
    GROQ_TIMEOUT = 20
    GUIDE_CACHE_SIZE = 1024

    # API bodies are tiny; reject anything bigger.
    MAX_CONTENT_LENGTH = 16 * 1024
