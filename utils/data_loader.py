"""Loads data-driven test configuration from data/test_data.json."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TestData:
    query: str
    max_price: float
    limit: int
    currency: str
    budget_per_item: float | None = None


def load_test_data(path: str | Path = "data/test_data.json") -> TestData:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return TestData(
        query=data["query"],
        max_price=float(data["max_price"]),
        limit=int(data["limit"]),
        currency=data["currency"],
        budget_per_item=float(data.get("budget_per_item", data["max_price"])),
    )
