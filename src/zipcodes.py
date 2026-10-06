"""Look up a 5-digit U.S. ZIP code's coordinates (Census ZCTA internal point).

Used by the CLI and the Streamlit demo to turn a ZIP into origin_lat /
origin_lon. The ranking engine itself is unchanged; it still takes lat/lon.
Data: data/zcta_centroids.csv, built by scripts/build_zcta_table.py.
"""

from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

ZCTA_PATH = Path(__file__).resolve().parents[1] / "data" / "zcta_centroids.csv"
ZIP_NOT_FOUND = "ZIP not found"
# Five digits, optionally ZIP+4 ("92101-1234"); only the first five are used.
_ZIP_RE = re.compile(r"^(\d{5})(?:-\d{4})?$")


class ZipNotFoundError(ValueError):
    """Raised for a ZIP that is not 5 digits / ZIP+4 or is not in the table."""

    def __init__(self, raw: object) -> None:
        super().__init__(f"{ZIP_NOT_FOUND}: {raw!r}")
        self.raw = raw


@lru_cache(maxsize=1)
def load_zip_table(path: Path = ZCTA_PATH) -> dict[str, tuple[float, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["zip"]: (float(row["lat"]), float(row["lon"])) for row in csv.DictReader(handle)}


def normalize_zip(raw: object) -> str | None:
    """The 5-digit ZIP from "02108" or ZIP+4 "02108-1234"; None if malformed."""
    if raw is None:
        return None
    match = _ZIP_RE.match(str(raw).strip())
    return match.group(1) if match else None


def lookup_zip(raw: object) -> tuple[float, float]:
    """(lat, lon) for a 5-digit ZIP or ZIP+4; raises ZipNotFoundError otherwise.

    After trimming spaces, input must be five digits, optionally followed by
    "-" and four digits ("02108" or "02108-1234"; the +4 part is ignored).
    "2108" is rejected, so a dropped leading zero is reported, not guessed.
    """
    code = normalize_zip(raw)
    if code is None:
        raise ZipNotFoundError(raw)
    try:
        return load_zip_table()[code]
    except KeyError:
        raise ZipNotFoundError(raw) from None
