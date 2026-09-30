import pytest
import requests

from app import create_app

VALID = {
    "nitrogen": 90,
    "phosphorus": 42,
    "potassium": 43,
    "temperature": 20.8,
    "humidity": 82,
    "pH": 6.5,
    "rainfall": 202,
}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("tests must not call the network")

    monkeypatch.setattr(requests, "post", blocked)


@pytest.fixture
def config():
    return {
        "TESTING": True,
        "GROQ_API_KEY": "test-key",
        "GROQ_MODEL": "openai/gpt-oss-120b",
        "GROQ_FALLBACK_MODELS": ["qwen/qwen3.8-27b"],
    }


@pytest.fixture
def app(config):
    return create_app(config)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def valid_payload():
    return dict(VALID)
