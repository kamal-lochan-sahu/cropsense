import pytest

from app.validation import FIELDS


def test_valid_prediction(client, valid_payload):
    response = client.post("/predict", json=valid_payload)
    assert response.status_code == 200
    body = response.get_json()
    assert body["crop"] == "rice"
    assert len(body["top"]) == 3
    assert body["top"][0]["crop"] == body["crop"]
    assert 0 < body["confidence"] <= 1
    assert "warnings" not in body


def test_numeric_strings_are_accepted(client, valid_payload):
    payload = {k: str(v) for k, v in valid_payload.items()}
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.get_json()["crop"] == "rice"


def test_missing_field(client, valid_payload):
    del valid_payload["phosphorus"]
    response = client.post("/predict", json=valid_payload)
    assert response.status_code == 422
    assert response.get_json()["fields"] == {"phosphorus": "required"}


@pytest.mark.parametrize("bad", ["abc", "nan", "inf", "1e999", None, "", True, [1], {"a": 1}])
def test_invalid_values_are_rejected(client, valid_payload, bad):
    valid_payload["temperature"] = bad
    response = client.post("/predict", json=valid_payload)
    assert response.status_code == 422
    assert "temperature" in response.get_json()["fields"]


@pytest.mark.parametrize(
    ("field", "value"),
    [("pH", 99), ("pH", -1), ("nitrogen", -5), ("humidity", 101), ("rainfall", 99999)],
)
def test_out_of_physical_range_is_rejected(client, valid_payload, field, value):
    valid_payload[field] = value
    response = client.post("/predict", json=valid_payload)
    assert response.status_code == 422
    assert field in response.get_json()["fields"]


def test_outside_training_range_returns_warning(client, valid_payload):
    valid_payload["nitrogen"] = 250
    response = client.post("/predict", json=valid_payload)
    assert response.status_code == 200
    warnings = response.get_json()["warnings"]
    assert [w["field"] for w in warnings] == ["nitrogen"]
    assert warnings[0]["code"] == "outside_training_range"


def test_non_object_body(client):
    response = client.post("/predict", json=[1, 2, 3])
    assert response.status_code == 422
    assert "_body" in response.get_json()["fields"]


def test_invalid_json(client):
    response = client.post("/predict", data="not json", content_type="application/json")
    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid JSON body"


def test_wrong_method_returns_json(client):
    response = client.get("/predict")
    assert response.status_code == 405
    assert response.get_json() == {"error": "method_not_allowed"}


def test_oversized_body(client):
    response = client.post("/predict", data="x" * 20000, content_type="application/json")
    assert response.status_code == 413
    assert response.get_json() == {"error": "request_entity_too_large"}


def test_fields_match_model_feature_order(app):
    assert app.extensions["predictor"].feature_names == [f.column for f in FIELDS]


def test_every_training_range_is_inside_hard_limits():
    for f in FIELDS:
        assert f.minimum <= f.train_min < f.train_max <= f.maximum, f.key
