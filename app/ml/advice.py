"""Soil advice: compares a farmer's N, P, K and pH with the typical values of the recommended crop.

The typical ranges come from models/crop_profiles.json, which is built from the training data
(scripts/build_crop_profiles.py). Pure local computation, no external service.
"""

from __future__ import annotations

import json
from typing import Any

# API field name -> column name used in the profiles file. Order is the order shown to the user.
SOIL_FIELDS: tuple[tuple[str, str], ...] = (
    ("nitrogen", "N"),
    ("phosphorus", "P"),
    ("potassium", "K"),
    ("pH", "ph"),
)


class Advisor:
    def __init__(self, profiles_path: str, crops: tuple[str, ...] = ()):
        with open(profiles_path, encoding="utf-8") as fh:
            self._crops: dict[str, dict[str, dict[str, float]]] = json.load(fh)["crops"]
        missing = [crop for crop in crops if crop not in self._crops]
        if missing:
            raise ValueError(f"no soil profile for: {', '.join(missing)}")

    def advise(self, crop: str, values: dict[str, float]) -> dict[str, Any] | None:
        """Status of each soil value for `crop`: 'low', 'ok' or 'high' with the typical range."""
        profile = self._crops.get(crop)
        if profile is None:
            return None
        items = []
        for field, column in SOIL_FIELDS:
            typical = profile[column]
            value = values[field]
            if value < typical["low"]:
                status = "low"
            elif value > typical["high"]:
                status = "high"
            else:
                status = "ok"
            items.append(
                {
                    "field": field,
                    "status": status,
                    "value": value,
                    "low": typical["low"],
                    "median": typical["median"],
                    "high": typical["high"],
                }
            )
        return {"crop": crop, "items": items}
