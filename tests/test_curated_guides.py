import json
from pathlib import Path

import pytest
import requests

from app import create_app
from app.services.guides import (
    GUIDE_KEYS,
    LANG_NAMES,
    MAX_FIELD_LENGTH,
    _clean_text,
    load_curated,
)

GUIDES_DIR = Path(__file__).resolve().parent.parent / "app" / "content" / "guides"


def ask(client, crop="rice", lang="en"):
    return client.post("/crop-guide", json={"crop": crop, "lang": lang})


@pytest.fixture
def curated():
    return load_curated(GUIDES_DIR)


def test_curated_files_only_use_known_languages(curated):
    assert set(curated) <= set(LANG_NAMES)
    assert "en" in curated


def test_every_crop_the_model_knows_has_a_complete_guide_in_each_curated_language(app, curated):
    classes = set(app.extensions["predictor"].classes)
    for lang, crops in curated.items():
        assert set(crops) == classes, f"{lang}: crops differ from the model classes"
        for crop, guide in crops.items():
            assert list(guide) == list(GUIDE_KEYS), f"{lang}/{crop}"


def test_curated_text_is_clean_and_short(curated):
    for lang, crops in curated.items():
        raw = json.loads((GUIDES_DIR / f"{lang}.json").read_text(encoding="utf-8"))
        for crop, guide in crops.items():
            for key, value in guide.items():
                assert value == raw[crop][key], f"{lang}/{crop}/{key} is not clean text"
                assert value == _clean_text(value)
                assert 20 <= len(value) <= MAX_FIELD_LENGTH


def test_english_guide_is_served_without_any_external_call(client):
    response = ask(client)  # the autouse fixture makes any network call fail the test
    assert response.status_code == 200
    body = response.get_json()
    assert body["source"] == "curated"
    assert body["cached"] is False
    guide = json.loads(body["guide"])
    assert list(guide) == list(GUIDE_KEYS)
    assert "Kharif" in guide["season"]


def test_curated_guides_work_without_a_groq_key(config):
    config["GROQ_API_KEY"] = ""
    client = create_app(config).test_client()
    assert ask(client, crop="mango").status_code == 200


def test_crop_name_is_normalised(client):
    assert ask(client, crop=" Rice ").get_json()["source"] == "curated"


def test_unknown_crop_is_still_rejected(client):
    assert ask(client, crop="unobtainium").status_code == 400


def test_language_without_curated_guide_still_uses_the_ai(client, monkeypatch):
    class Response:
        status_code = 200

        def json(self):
            guide = {key: "text" for key in GUIDE_KEYS}
            return {"choices": [{"message": {"content": json.dumps(guide)}}]}

    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: Response())
    body = ask(client, lang="hi").get_json()
    assert body["source"] == "ai"
    assert body["cached"] is False
    assert ask(client, lang="hi").get_json()["cached"] is True


def test_language_without_curated_guide_and_without_key_is_unavailable(config):
    config["GROQ_API_KEY"] = ""
    assert ask(create_app(config).test_client(), lang="hi").status_code == 503


def test_health_lists_curated_languages(client, curated):
    assert client.get("/health").get_json()["guides_curated"] == sorted(curated)


GOOD = {key: "Some practical text." for key in GUIDE_KEYS}


def write(directory, name, data):
    (directory / name).write_text(json.dumps(data), encoding="utf-8")


def test_loader_strips_markup(tmp_path):
    write(tmp_path, "en.json", {"rice": {**GOOD, "tip": "<b>Level</b> the field"}})
    assert load_curated(tmp_path)["en"]["rice"]["tip"] == "bLevel/b the field"


def test_loader_rejects_an_unknown_language_file(tmp_path):
    write(tmp_path, "xx.json", {"rice": GOOD})
    with pytest.raises(ValueError, match="unknown language"):
        load_curated(tmp_path)


def test_loader_rejects_a_missing_field(tmp_path):
    guide = dict(GOOD)
    del guide["pests"]
    write(tmp_path, "en.json", {"rice": guide})
    with pytest.raises(ValueError, match="pests"):
        load_curated(tmp_path)


def test_loader_rejects_an_empty_field(tmp_path):
    write(tmp_path, "en.json", {"rice": {**GOOD, "water": "   "}})
    with pytest.raises(ValueError, match="water"):
        load_curated(tmp_path)


def test_loader_rejects_a_malformed_crop(tmp_path):
    write(tmp_path, "en.json", {"rice": "not an object"})
    with pytest.raises(ValueError, match="rice"):
        load_curated(tmp_path)


def test_loader_on_an_empty_folder_returns_nothing(tmp_path):
    assert load_curated(tmp_path) == {}
