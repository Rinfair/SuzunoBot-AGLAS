from __future__ import annotations

import base64
import json
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image

MODULE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = MODULE_DIR / "image"


@lru_cache(maxsize=None)
def _load_json(filename: str) -> dict:
    return json.loads((MODULE_DIR / filename).read_text(encoding="utf-8"))


def load_tarot_data() -> tuple[dict, dict[str, str]]:
    tarot_data = _load_json("batarot.json")
    tarot_urls = _load_json("batarot_url.json")
    return tarot_data["cards"], tarot_urls


def load_spread_data() -> dict:
    return _load_json("batarot_spread.json")


def load_fortune_descriptions() -> dict[str, list[str]]:
    return _load_json("batarot_fortune.json")


def find_card_key(cards: dict, query: str) -> str | None:
    normalized = query.strip()
    if not normalized:
        return None

    if normalized.isdigit():
        numeric_key = str(int(normalized))
        if numeric_key in cards:
            return numeric_key

    lowered = normalized.lower()
    for key, card in cards.items():
        if card["name_cn"].lower() == lowered:
            return key
    return None


def load_image_bytes(image_name: str) -> bytes | None:
    image_path = IMAGE_DIR / image_name
    if not image_path.exists():
        return None
    return image_path.read_bytes()


def load_image_base64(image_name: str, *, rotate_180: bool = False) -> str | None:
    image_bytes = load_image_bytes(image_name)
    if image_bytes is None:
        return None

    if rotate_180:
        image = Image.open(BytesIO(image_bytes))
        output = BytesIO()
        image.transpose(Image.Transpose.ROTATE_180).save(output, format=image.format or "PNG")
        image_bytes = output.getvalue()

    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"base64://{encoded}"
