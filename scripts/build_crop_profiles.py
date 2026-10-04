"""Build models/crop_profiles.json: the typical soil values of each crop in the training data.

The app compares a farmer's N, P, K and pH with these ranges to give soil advice. Everything is
computed from data/Crop_recommendation.csv, so no external service is involved.

Usage:
    python scripts/build_crop_profiles.py                 # writes models/crop_profiles.json
    python scripts/build_crop_profiles.py --out-dir /tmp  # write somewhere else

Standard library only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "Crop_recommendation.csv"
PROFILE_COLUMNS = {"N": 1, "P": 1, "K": 1, "ph": 2}  # column -> decimals kept
LOW_PERCENTILE = 10
HIGH_PERCENTILE = 90


def percentile(sorted_values: list[float], pct: float) -> float:
    """Linear-interpolated percentile of an already sorted list."""
    position = (len(sorted_values) - 1) * pct / 100
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (position - lower)


def build_profiles(data_path: Path = DATA_PATH) -> dict:
    values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    with open(data_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            for column in PROFILE_COLUMNS:
                values[row["label"]][column].append(float(row[column]))

    crops = {}
    for crop in sorted(values):
        crops[crop] = {}
        for column, decimals in PROFILE_COLUMNS.items():
            ordered = sorted(values[crop][column])
            crops[crop][column] = {
                "low": round(percentile(ordered, LOW_PERCENTILE), decimals),
                "median": round(percentile(ordered, 50), decimals),
                "high": round(percentile(ordered, HIGH_PERCENTILE), decimals),
            }
    return {
        "percentiles": [LOW_PERCENTILE, HIGH_PERCENTILE],
        "dataset_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
        "crops": crops,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=ROOT / "models")
    args = parser.parse_args()

    profiles = build_profiles()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    target = args.out_dir / "crop_profiles.json"
    target.write_text(json.dumps(profiles, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {target} ({len(profiles['crops'])} crops)")


if __name__ == "__main__":
    main()
