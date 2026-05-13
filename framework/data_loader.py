from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "testdata"


def load_json(name: str) -> Any:
    path = DATA_DIR / name if not name.endswith(".json") else DATA_DIR / name
    if not name.endswith(".json"):
        path = DATA_DIR / f"{name}.json"
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_csv(name: str) -> list[dict[str, str]]:
    path = DATA_DIR / (name if name.endswith(".csv") else f"{name}.csv")
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))
