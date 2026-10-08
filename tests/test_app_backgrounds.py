"""Quiz background photos (app/static)."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
STEPS = ["welcome", "terrain", "vibe", "pace", "when", "from", "results"]


def background_photos() -> dict[str, str]:
    source = (APP_DIR / "streamlit_app.py").read_text()
    block = re.search(r"BACKGROUNDS = \{(.*?)\n\}", source, re.S).group(1)
    return dict(re.findall(r'"(\w+)": "([\w-]+)"', block))


def test_every_step_has_a_photo_in_app_static():
    photos = background_photos()
    assert list(photos) == STEPS
    for name in photos.values():
        assert (APP_DIR / "static" / f"{name}.jpg").is_file(), name


def test_photos_carry_no_metadata():
    for path in (APP_DIR / "static").glob("*.jpg"):
        assert not Image.open(path).getexif(), f"{path.name} has EXIF data (GPS, device)"


def test_static_serving_is_on():
    assert "enableStaticServing = true" in (ROOT / ".streamlit" / "config.toml").read_text()


def test_no_remote_media_in_the_app():
    source = (APP_DIR / "streamlit_app.py").read_text()
    assert "unsplash" not in source and "pexels" not in source
