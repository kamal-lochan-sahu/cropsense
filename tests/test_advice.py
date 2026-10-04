import importlib.util
import json
from pathlib import Path

import pytest

from app.ml.advice import SOIL_FIELDS, Advisor

ROOT = Path(__file__).resolve().parent.parent
PROFILES = ROOT / "models" / "crop_profiles.json"

# Typical rice values from the training data (see models/crop_profiles.json).
RICE_OK = {"nitrogen": 80, "phosphorus": 47, "potassium": 40, "pH": 6.4}


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_crop_profiles", ROOT / "scripts" / "build_crop_profiles.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def advisor():
    return Advisor(str(PROFILES))


def statuses(advice):
    return {item["field"]: item["status"] for item in advice["items"]}


def test_profiles_cover_every_crop_the_model_knows(app):
    classes = app.extensions["predictor"].classes
    crops = json.loads(PROFILES.read_text())["crops"]
    assert set(crops) == set(classes)


def test_profile_ranges_are_ordered():
    crops = json.loads(PROFILES.read_text())["crops"]
    for crop, columns in crops.items():
        for column, typical in columns.items():
            assert typical["low"] <= typical["median"] <= typical["high"], f"{crop}.{column}"


def test_committed_profiles_match_the_dataset():
    builder = load_builder()
    assert builder.build_profiles() == json.loads(PROFILES.read_text()), (
        "models/crop_profiles.json is stale: run python scripts/build_crop_profiles.py"
    )


def test_advisor_refuses_a_model_class_without_a_profile(tmp_path):
    path = tmp_path / "profiles.json"
    path.write_text(json.dumps({"crops": {"rice": {}}}))
    with pytest.raises(ValueError, match="maize"):
        Advisor(str(path), ("rice", "maize"))


def test_typical_values_are_ok(advisor):
    advice = advisor.advise("rice", RICE_OK)
    assert advice["crop"] == "rice"
    assert [item["field"] for item in advice["items"]] == [f for f, _ in SOIL_FIELDS]
    assert set(statuses(advice).values()) == {"ok"}


def test_low_and_high_values_are_flagged(advisor):
    values = {**RICE_OK, "nitrogen": 10, "potassium": 90, "pH": 4.0}
    assert statuses(advisor.advise("rice", values)) == {
        "nitrogen": "low",
        "phosphorus": "ok",
        "potassium": "high",
        "pH": "low",
    }


def test_range_edges_count_as_ok(advisor):
    crops = json.loads(PROFILES.read_text())["crops"]["rice"]
    low = {
        "nitrogen": crops["N"]["low"],
        "phosphorus": crops["P"]["low"],
        "potassium": crops["K"]["low"],
        "pH": crops["ph"]["low"],
    }
    high = {
        "nitrogen": crops["N"]["high"],
        "phosphorus": crops["P"]["high"],
        "potassium": crops["K"]["high"],
        "pH": crops["ph"]["high"],
    }
    assert set(statuses(advisor.advise("rice", low)).values()) == {"ok"}
    assert set(statuses(advisor.advise("rice", high)).values()) == {"ok"}


def test_item_carries_value_and_typical_range(advisor):
    item = advisor.advise("rice", {**RICE_OK, "nitrogen": 10})["items"][0]
    assert item["value"] == 10
    assert item["low"] < item["median"] < item["high"]


def test_unknown_crop_gives_no_advice(advisor):
    assert advisor.advise("dragonfruit", RICE_OK) is None


def test_predict_returns_advice_for_the_top_crop(client, valid_payload):
    body = client.post("/predict", json=valid_payload).get_json()
    assert body["advice"]["crop"] == body["crop"] == "rice"
    assert [item["field"] for item in body["advice"]["items"]] == [f for f, _ in SOIL_FIELDS]
    assert all(item["status"] in {"low", "ok", "high"} for item in body["advice"]["items"])


def test_predict_advice_uses_the_submitted_values(client, valid_payload):
    valid_payload["nitrogen"] = 5
    body = client.post("/predict", json=valid_payload).get_json()
    typical = json.loads(PROFILES.read_text())["crops"][body["crop"]]["N"]
    nitrogen = next(item for item in body["advice"]["items"] if item["field"] == "nitrogen")
    assert nitrogen["value"] == 5
    assert (nitrogen["low"], nitrogen["high"]) == (typical["low"], typical["high"])
    assert nitrogen["status"] == ("low" if 5 < typical["low"] else "ok")


def test_invalid_input_still_returns_no_advice(client, valid_payload):
    valid_payload["pH"] = 99
    response = client.post("/predict", json=valid_payload)
    assert response.status_code == 422
    assert "advice" not in response.get_json()
