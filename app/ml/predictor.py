"""Crop prediction model wrapper."""

from __future__ import annotations

import pickle
import warnings
from typing import Any

import numpy as np

# The model was trained on a DataFrame; we predict from a plain array.
warnings.filterwarnings("ignore", message="X does not have valid feature names")


class Predictor:
    def __init__(self, model_path: str):
        # The pickle ships with this repository; never load pickles from untrusted sources.
        with open(model_path, "rb") as fh:
            self._model = pickle.load(fh)  # noqa: S301
        self.classes: tuple[str, ...] = tuple(str(c) for c in self._model.classes_)

    @property
    def feature_names(self) -> list[str]:
        return [str(n) for n in getattr(self._model, "feature_names_in_", [])]

    def predict(self, values: list[float], top_k: int = 3) -> dict[str, Any]:
        probabilities = self._model.predict_proba(np.array([values]))[0]
        order = np.argsort(probabilities)[::-1][:top_k]
        top = [
            {"crop": self.classes[i], "confidence": round(float(probabilities[i]), 4)}
            for i in order
        ]
        return {"crop": top[0]["crop"], "confidence": top[0]["confidence"], "top": top}
