"""Fast local lookup for Indian pincode address details."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PincodeDetails:
    district: str
    state: str


@lru_cache(maxsize=1)
def _pincode_index() -> dict[str, PincodeDetails]:
    data_path = Path(__file__).resolve().parents[2] / "data" / "india_pincodes.csv"
    with data_path.open(encoding="utf-8-sig", newline="") as source:
        return {
            row["pincode"]: PincodeDetails(
                district=row["district"],
                state=row["state"],
            )
            for row in csv.DictReader(source)
        }


def lookup_pincode(pincode: str) -> PincodeDetails | None:
    """Return address details when *pincode* is a known six-digit Indian pincode."""

    normalized = pincode.strip()
    if len(normalized) != 6 or not normalized.isdigit():
        return None
    return _pincode_index().get(normalized)
