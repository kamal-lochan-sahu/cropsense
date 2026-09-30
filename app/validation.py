"""Input validation for the prediction API."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    key: str  # name in the JSON API
    column: str  # feature name the model was trained with
    minimum: float  # physically plausible lower bound (hard limit)
    maximum: float  # physically plausible upper bound (hard limit)
    train_min: float  # range seen in the training data (soft limit)
    train_max: float


# Order matters: it must match the model's feature order.
FIELDS: tuple[Field, ...] = (
    Field("nitrogen", "N", 0, 300, 0, 140),
    Field("phosphorus", "P", 0, 300, 5, 145),
    Field("potassium", "K", 0, 500, 5, 205),
    Field("temperature", "temperature", -20, 60, 8.83, 43.68),
    Field("humidity", "humidity", 0, 100, 14.26, 99.98),
    Field("pH", "ph", 0, 14, 3.5, 9.94),
    Field("rainfall", "rainfall", 0, 5000, 20.21, 298.56),
)


class ValidationError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__("validation failed")
        self.errors = errors


def parse_features(payload: object) -> tuple[list[float], list[dict[str, str]]]:
    """Validate a request payload.

    Returns the feature values in model order plus a list of warnings for values that are
    valid but outside the range the model was trained on. Raises ValidationError otherwise.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"_body": "expected a JSON object"})

    errors: dict[str, str] = {}
    values: list[float] = []
    warnings: list[dict[str, str]] = []

    for field in FIELDS:
        raw = payload.get(field.key)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            errors[field.key] = "required"
            continue
        if isinstance(raw, bool):
            errors[field.key] = "must be a number"
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            errors[field.key] = "must be a number"
            continue
        if not math.isfinite(value):
            errors[field.key] = "must be a finite number"
            continue
        if not field.minimum <= value <= field.maximum:
            errors[field.key] = f"must be between {field.minimum:g} and {field.maximum:g}"
            continue

        values.append(value)
        if not field.train_min <= value <= field.train_max:
            warnings.append(
                {
                    "field": field.key,
                    "code": "outside_training_range",
                    "message": (
                        f"{field.key} is outside the range the model was trained on "
                        f"({field.train_min:g} to {field.train_max:g}); "
                        "the result may be unreliable"
                    ),
                }
            )

    if errors:
        raise ValidationError(errors)
    return values, warnings
