from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Union

from PIL import Image, ImageDraw, ImageFont


def get_char_width(codepoint: int) -> int:
    widths = [
        (126, 1),
        (159, 0),
        (687, 1),
        (710, 0),
        (711, 1),
        (727, 0),
        (733, 1),
        (879, 0),
        (1154, 1),
        (1161, 0),
        (4347, 1),
        (4447, 2),
        (7467, 1),
        (7521, 0),
        (8369, 1),
        (8426, 0),
        (9000, 1),
        (9002, 2),
        (11021, 1),
        (12350, 2),
        (12351, 1),
        (12438, 2),
        (12442, 0),
        (19893, 2),
        (19967, 1),
        (55203, 2),
        (63743, 1),
        (64106, 2),
        (65039, 1),
        (65059, 0),
        (65131, 2),
        (65279, 1),
        (65376, 2),
        (65500, 1),
        (65510, 2),
        (120831, 1),
        (262141, 2),
        (1114109, 1),
    ]
    if codepoint in {0xE, 0xF}:
        return 0
    for limit, width in widths:
        if codepoint <= limit:
            return width
    return 1


def coloum_width(text: str) -> int:
    return sum(get_char_width(ord(char)) for char in text)


def change_column_width(text: str, length: int) -> str:
    current = 0
    output: list[str] = []
    for char in text:
        current += get_char_width(ord(char))
        if current <= length:
            output.append(char)
    return "".join(output)


@lru_cache(maxsize=256)
def _get_font(font_path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(font_path, size)
    except OSError:
        return ImageFont.load_default()


class DrawText:
    def __init__(self, image: ImageDraw.ImageDraw, font: Path) -> None:
        self._image = image
        self._font = str(font)

    def draw(
        self,
        pos_x: int,
        pos_y: int,
        size: int,
        text: Union[str, int, float],
        color=(255, 255, 255, 255),
        anchor: str = "lt",
        stroke_width: int = 0,
        stroke_fill=(0, 0, 0, 0),
        multiline: bool = False,
    ) -> None:
        font = _get_font(self._font, size)
        content = str(text)
        if multiline:
            self._image.multiline_text(
                (pos_x, pos_y),
                content,
                color,
                font,
                anchor,
                stroke_width=stroke_width,
                stroke_fill=stroke_fill,
            )
        else:
            self._image.text(
                (pos_x, pos_y),
                content,
                color,
                font,
                anchor,
                stroke_width=stroke_width,
                stroke_fill=stroke_fill,
            )


def image_to_bytes(image: Image.Image, format: str = "PNG") -> bytes:
    buffer = BytesIO()
    image.save(buffer, format)
    return buffer.getvalue()
