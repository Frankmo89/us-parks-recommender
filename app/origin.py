"""Turn the quiz's ZIP box into an origin. Pure helpers, no Streamlit calls.

Empty box = "Anywhere": no origin and no drive limit. A valid 5-digit ZIP in
the Census ZCTA table (or ZIP+4, first five digits) gives (lat, lon). Anything else is "ZIP not found".
"""

from __future__ import annotations

from dataclasses import dataclass

from src.zipcodes import ZIP_NOT_FOUND, ZipNotFoundError, lookup_zip, normalize_zip

ANYWHERE = "anywhere"
FOUND = "found"
NOT_FOUND = "not_found"


@dataclass(frozen=True)
class ZipOrigin:
    status: str  # ANYWHERE | FOUND | NOT_FOUND
    zip_code: str = ""
    lat: float | None = None
    lon: float | None = None

    @property
    def message(self) -> str:
        return ZIP_NOT_FOUND if self.status == NOT_FOUND else ""


def zip_origin(raw: str | None) -> ZipOrigin:
    text = (raw or "").strip()
    if not text:
        return ZipOrigin(ANYWHERE)
    try:
        lat, lon = lookup_zip(text)
    except ZipNotFoundError:
        return ZipOrigin(NOT_FOUND, zip_code=text)
    return ZipOrigin(FOUND, zip_code=normalize_zip(text) or text, lat=lat, lon=lon)


def drive_limit(origin: ZipOrigin, max_hours: float) -> float | None:
    """The drive limit only applies when a valid ZIP is set."""
    return float(max_hours) if origin.status == FOUND else None
