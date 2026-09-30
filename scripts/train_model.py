"""Train the crop recommendation model.

Usage:
    python scripts/train_model.py                 # writes models/model.pkl + models/metrics.json
    python scripts/train_model.py --out-dir /tmp  # write somewhere else (safe experiments)

Needs the dev dependencies (pandas): pip install -r requirements-dev.txt
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
from pathlib import Path

import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "Crop_recommendation.csv"
FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
SEED = 42


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=ROOT / "models")
    args = parser.parse_args()

    df = pd.read_csv(DATA_PATH)
    print("Data loaded:", df.shape)
    X, y = df[FEATURES], df["label"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED)
    model = RandomForestClassifier(n_estimators=100, random_state=SEED)
    model.fit(X_train, y_train)
    holdout = accuracy_score(y_test, model.predict(X_test))
    print(f"Hold-out accuracy: {holdout * 100:.2f}%")

    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    cv = cross_val_score(
        RandomForestClassifier(n_estimators=100, random_state=SEED), X, y, cv=folds
    )
    print(f"5-fold CV accuracy: {cv.mean() * 100:.2f}% +/- {cv.std() * 100:.2f}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with open(args.out_dir / "model.pkl", "wb") as fh:
        pickle.dump(model, fh)

    metrics = {
        "holdout_accuracy": round(float(holdout), 4),
        "cv_accuracy_mean": round(float(cv.mean()), 4),
        "cv_accuracy_std": round(float(cv.std()), 4),
        "samples": int(len(df)),
        "classes": sorted(map(str, model.classes_)),
        "features": FEATURES,
        "sklearn_version": sklearn.__version__,
        "dataset_sha256": hashlib.sha256(DATA_PATH.read_bytes()).hexdigest(),
    }
    (args.out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print("Saved model.pkl and metrics.json to", args.out_dir)


if __name__ == "__main__":
    main()
