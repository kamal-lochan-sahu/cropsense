"""Growing guides: curated content shipped with the app, with the Groq API as a fallback.

Languages that have a file in app/content/guides/ are served from it, instantly and without any
external service. Other languages are generated through the Groq API (model fallback,
bounded cache).
"""

from __future__ import annotations

import json
import logging
import re
import threading
from collections import OrderedDict
from collections.abc import Iterable, Mapping
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

LANG_NAMES = {
    "en": "English", "hi": "Hindi", "or": "Odia", "mr": "Marathi", "bn": "Bengali",
    "ta": "Tamil", "te": "Telugu", "kn": "Kannada", "gu": "Gujarati", "pa": "Punjabi",
    "ml": "Malayalam", "de": "German", "it": "Italian", "ja": "Japanese", "zh": "Chinese",
    "ru": "Russian", "fr": "French", "es": "Spanish", "ar": "Arabic", "pt": "Portuguese",
    "ko": "Korean",
}  # fmt: skip

GUIDE_KEYS = ("season", "soil", "water", "fertilizer", "pests", "harvest", "tip")
MIN_GUIDE_KEYS = 5
MAX_FIELD_LENGTH = 500

PROMPT_TEMPLATE = """You are an agricultural expert helping a farmer. Write a practical growing guide for the crop "{crop}" in {language} language.

Respond ONLY with valid JSON (no markdown, no preamble) in this exact structure:
{{
  "season": "best planting season/months",
  "soil": "ideal soil type and pH range",
  "water": "irrigation needs and frequency",
  "fertilizer": "key nutrients and timing",
  "pests": "common pests/diseases and basic prevention",
  "harvest": "harvest timing and signs of readiness",
  "tip": "one practical actionable tip for small farmers"
}}

Keep each field to 1-2 short sentences. Write everything in {language}, including all field values. Respond with ONLY the JSON object, nothing else."""  # noqa: E501


def load_curated(directory: str | Path) -> dict[str, dict[str, dict[str, str]]]:
    """Read curated guides: one <lang>.json per language, {crop: {season: ..., ..., tip: ...}}.

    Raises ValueError on a malformed file, so a bad guide is caught at startup and never
    reaches a farmer.
    """
    curated: dict[str, dict[str, dict[str, str]]] = {}
    for path in sorted(Path(directory).glob("*.json")):
        lang = path.stem
        if lang not in LANG_NAMES:
            raise ValueError(f"{path.name}: unknown language code")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path.name}: expected an object of crops")
        crops: dict[str, dict[str, str]] = {}
        for crop, guide in data.items():
            if not isinstance(guide, dict):
                raise ValueError(f"{path.name}: {crop} is not an object")
            clean = {}
            for key in GUIDE_KEYS:
                value = guide.get(key)
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"{path.name}: {crop} is missing '{key}'")
                clean[key] = _clean_text(value)
            crops[crop] = clean
        curated[lang] = crops
    return curated


class GuideError(Exception):
    """Raised for failures that should be reported to the client."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.message = message
        self.status = status


class _ModelUnavailable(Exception):
    """This model cannot serve the request right now; try the next one."""


def _clean_text(value: str) -> str:
    value = re.sub(r"[<>]", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:MAX_FIELD_LENGTH]


def _parse_guide(content: str) -> str:
    try:
        data = json.loads(content)
    except (TypeError, ValueError) as exc:
        raise _ModelUnavailable("model returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise _ModelUnavailable("model returned a non-object")
    clean = {}
    for key in GUIDE_KEYS:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            clean[key] = _clean_text(value)
    if len(clean) < MIN_GUIDE_KEYS:
        raise _ModelUnavailable("model returned an incomplete guide")
    return json.dumps(clean, ensure_ascii=False)


class GuideService:
    def __init__(
        self,
        *,
        api_key: str,
        models: Iterable[str],
        url: str,
        timeout: float,
        cache_size: int,
        allowed_crops: Iterable[str],
        curated: Mapping[str, Mapping[str, Mapping[str, str]]] | None = None,
    ):
        self._api_key = api_key
        self._models = [m for m in models if m]
        self._url = url
        self._timeout = timeout
        self._cache_size = cache_size
        self._allowed_crops = frozenset(allowed_crops)
        self._curated = curated or {}
        self._cache: OrderedDict[tuple[str, str], str] = OrderedDict()
        self._lock = threading.Lock()

    @property
    def configured(self) -> bool:
        return bool(self._api_key and self._models)

    @property
    def curated_languages(self) -> list[str]:
        return sorted(self._curated)

    def get(self, crop: str, lang: str) -> tuple[str, bool, str]:
        """Return (guide_json, served_from_cache, source) where source is 'curated' or 'ai'."""
        crop_key = crop.strip().lower()
        if crop_key not in self._allowed_crops:
            raise GuideError("unknown crop", 400)
        if lang not in LANG_NAMES:
            raise GuideError("unsupported language", 400)

        curated = self._curated.get(lang, {}).get(crop_key)
        if curated is not None:
            return json.dumps(curated, ensure_ascii=False), False, "curated"

        if not self.configured:
            raise GuideError("guide service is not configured", 503)

        key = (crop_key, lang)
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                self._cache.move_to_end(key)
                return cached, True, "ai"

        guide = self._generate(crop_key, lang)

        with self._lock:
            self._cache[key] = guide
            self._cache.move_to_end(key)
            while len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)
        return guide, False, "ai"

    def _generate(self, crop: str, lang: str) -> str:
        prompt = PROMPT_TEMPLATE.format(crop=crop, language=LANG_NAMES[lang])
        for model in self._models:
            try:
                return self._call(model, prompt)
            except _ModelUnavailable as exc:
                logger.warning("guide model %s unavailable: %s", model, exc)
        raise GuideError("AI service unavailable", 502)

    def _call(self, model: str, prompt: str) -> str:
        body: dict = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
            "max_tokens": 1500,
            "response_format": {"type": "json_object"},
        }
        if model.startswith("openai/gpt-oss"):
            body["reasoning_effort"] = "low"

        try:
            response = requests.post(
                self._url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=self._timeout,
            )
        except requests.Timeout as exc:
            raise GuideError("AI service timed out", 504) from exc
        except requests.RequestException as exc:
            raise GuideError("AI service unreachable", 502) from exc

        status = response.status_code
        if status in (401, 403):
            logger.error("Groq rejected the API key (HTTP %s)", status)
            raise GuideError("AI service rejected our credentials", 502)
        if status != 200:
            # 400/404 (model retired or unsupported), 429 (rate limit), 5xx: try next model.
            raise _ModelUnavailable(f"HTTP {status}")

        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise _ModelUnavailable("unexpected response shape") from exc
        return _parse_guide(content)
