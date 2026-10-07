import json
from pathlib import Path

import pytest
import requests

from app import create_app
from app.services.guides import LANG_NAMES, load_curated

# A language without curated content, so these tests keep exercising the Groq fallback.
UNCURATED = next(
    lang
    for lang in LANG_NAMES
    if lang
    not in load_curated(Path(__file__).resolve().parent.parent / "app" / "content" / "guides")
)

GOOD_GUIDE = {
    "season": "June to August",
    "soil": "Clay loam, pH 5.5-7",
    "water": "Keep fields flooded",
    "fertilizer": "Split nitrogen doses",
    "pests": "Watch for stem borer",
    "harvest": "When grains turn golden",
    "tip": "Level the field",
}


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def ok(guide):
    content = guide if isinstance(guide, str) else json.dumps(guide)
    return FakeResponse(200, {"choices": [{"message": {"content": content}}]})


@pytest.fixture
def groq(monkeypatch):
    """Queue fake Groq responses; records every request body."""
    queue, calls = [], []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json)
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(requests, "post", fake_post)
    return type("Groq", (), {"queue": queue, "calls": calls})


def ask(client, crop="rice", lang=UNCURATED):
    return client.post("/crop-guide", json={"crop": crop, "lang": lang})


def test_guide_success_then_cache(client, groq):
    groq.queue.append(ok(GOOD_GUIDE))
    first = ask(client)
    assert first.status_code == 200
    assert first.get_json()["cached"] is False
    assert json.loads(first.get_json()["guide"])["season"] == "June to August"

    second = ask(client, crop="Rice ")  # normalised to the same cache key
    assert second.get_json()["cached"] is True
    assert len(groq.calls) == 1


def test_reasoning_effort_only_for_gpt_oss(client, groq):
    groq.queue.extend([FakeResponse(404, {}), ok(GOOD_GUIDE)])
    assert ask(client).status_code == 200
    first, second = groq.calls
    assert first["model"] == "openai/gpt-oss-120b"
    assert first["reasoning_effort"] == "low"
    assert second["model"] == "qwen/qwen3.8-27b"
    assert "reasoning_effort" not in second


@pytest.mark.parametrize("status", [400, 404, 429, 500, 503])
def test_falls_back_when_model_unavailable(client, groq, status):
    groq.queue.extend([FakeResponse(status, {}), ok(GOOD_GUIDE)])
    assert ask(client).status_code == 200
    assert len(groq.calls) == 2


def test_all_models_fail(client, groq):
    groq.queue.extend([FakeResponse(404, {}), FakeResponse(404, {})])
    response = ask(client)
    assert response.status_code == 502
    assert response.get_json() == {"error": "AI service unavailable"}


def test_invalid_model_output_triggers_fallback(client, groq):
    groq.queue.extend([ok("this is not json"), ok({"season": "only one field"})])
    assert ask(client).status_code == 502
    assert len(groq.calls) == 2


def test_html_is_stripped_from_guide(client, groq):
    dirty = dict(GOOD_GUIDE, tip="<img src=x onerror=alert(1)>Level the field")
    groq.queue.append(ok(dirty))
    guide = json.loads(ask(client).get_json()["guide"])
    assert "<" not in guide["tip"] and ">" not in guide["tip"]


def test_timeout_returns_504(client, groq):
    groq.queue.append(requests.Timeout())
    assert ask(client).status_code == 504
    assert len(groq.calls) == 1


def test_bad_credentials_do_not_try_other_models(client, groq):
    groq.queue.append(FakeResponse(401, {}))
    assert ask(client).status_code == 502
    assert len(groq.calls) == 1


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ({"crop": "unobtainium", "lang": "en"}, 400),
        ({"crop": "rice", "lang": "xx"}, 400),
        ({"crop": 5, "lang": "en"}, 400),
        ({"lang": "en"}, 400),
        ([], 400),
    ],
)
def test_bad_requests_never_reach_groq(client, payload, status):
    response = client.post("/crop-guide", json=payload)
    assert response.status_code == status


def test_unconfigured_service_returns_503(config):
    config["GROQ_API_KEY"] = ""
    client = create_app(config).test_client()
    assert ask(client).status_code == 503


def test_cache_is_bounded(config, groq):
    config["GUIDE_CACHE_SIZE"] = 1
    client = create_app(config).test_client()
    groq.queue.extend([ok(GOOD_GUIDE), ok(GOOD_GUIDE), ok(GOOD_GUIDE)])
    ask(client, crop="rice")
    ask(client, crop="maize")
    assert ask(client, crop="rice").get_json()["cached"] is False  # evicted
