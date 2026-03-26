from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageDraw

from ..config import config
from ..database.crud import MaiSongORM
from ..score import PlayerMaiInfo, PlayerMaiScore
from ._config import (
    ACCENT_COLOR,
    BG_BOTTOM,
    BG_TOP,
    COVER_DIR,
    DIFF_COLORS,
    FONT_MAIN,
    FONT_NUM,
    ICON_DIR,
    PANEL_BG,
    PANEL_BORDER,
    PLATE_DIR,
    SUBTEXT_COLOR,
    TEXT_COLOR,
)
from .utils import DrawText, change_column_width, coloum_width


class ScoreBaseImage:
    text_color = TEXT_COLOR

    def __init__(self, image: Optional[Image.Image] = None) -> None:
        self.bg = image
        self._image_cache: dict[tuple[str, tuple[int, int] | None], Image.Image] = {}
        self.id_color = DIFF_COLORS
        self.bg_color = DIFF_COLORS

    @staticmethod
    def _rounded_rectangle(
        draw: ImageDraw.ImageDraw,
        box: tuple[int, int, int, int],
        *,
        fill: tuple[int, int, int, int],
        outline: tuple[int, int, int, int] | None = None,
        width: int = 1,
        radius: int = 28,
    ) -> None:
        draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

    def _background_image(self, width: int = 1400, height: int = 1600) -> Image.Image:
        if self.bg is not None:
            return self.bg.copy().convert("RGBA").resize((width, height))
        if config.scorelist_bg and Path(config.scorelist_bg).exists():
            return Image.open(config.scorelist_bg).convert("RGBA").resize((width, height))

        image = Image.new("RGBA", (width, height))
        draw = ImageDraw.Draw(image)
        for y in range(height):
            ratio = y / max(height - 1, 1)
            color = tuple(
                int(BG_TOP[index] + (BG_BOTTOM[index] - BG_TOP[index]) * ratio)
                for index in range(4)
            )
            draw.line((0, y, width, y), fill=color, width=1)

        for x in range(0, width, 56):
            draw.line((x, 0, x, height), fill=(255, 255, 255, 18), width=1)
        for y in range(0, height, 56):
            draw.line((0, y, width, y), fill=(255, 255, 255, 18), width=1)
        return image

    def reset_im(self, width: int = 1400, height: int = 1600) -> None:
        self._im = self._background_image(width, height)
        self._dr = ImageDraw.Draw(self._im)
        self._sy = DrawText(self._dr, FONT_MAIN)
        self._tb = DrawText(self._dr, FONT_NUM)

    def _get_image(self, path: Path, size: tuple[int, int] | None = None) -> Image.Image:
        key = (str(path), size)
        cached = self._image_cache.get(key)
        if cached is not None:
            return cached.copy()

        image = Image.open(path).convert("RGBA")
        if size is not None:
            image = image.resize(size)
        self._image_cache[key] = image
        return image.copy()

    @staticmethod
    def _candidate_cover_paths(song_id: int) -> list[Path]:
        ids = [song_id]
        if 10000 < song_id < 100000:
            ids.append(song_id - 10000)
        elif song_id < 10000:
            ids.append(song_id + 10000)

        candidates: list[Path] = []
        seen: set[Path] = set()
        for sid in ids:
            for name in (str(sid), f"{sid:05d}"):
                path = COVER_DIR / f"{name}.png"
                if path not in seen:
                    candidates.append(path)
                    seen.add(path)
        return candidates

    def _placeholder_cover(self, song_id: int, size: tuple[int, int]) -> Image.Image:
        image = Image.new("RGBA", size, (240, 244, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=20, fill=(242, 246, 255, 255))
        draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=20, outline=PANEL_BORDER, width=3)
        DrawText(draw, FONT_NUM).draw(size[0] // 2, size[1] // 2, max(18, size[1] // 4), song_id, ACCENT_COLOR, "mm")
        return image

    def _load_cover(self, song_id: int, size: tuple[int, int]) -> Image.Image:
        for path in self._candidate_cover_paths(song_id):
            if path.exists():
                cover = self._get_image(path, size)
                return cover
        return self._placeholder_cover(song_id, size)

    def _paste_profile_plate(self, player_info: PlayerMaiInfo) -> None:
        plate: Image.Image | None = None
        if player_info.name_plate:
            plate_path = PLATE_DIR / f"{player_info.name_plate.id}.png"
            if plate_path.exists():
                plate = self._get_image(plate_path, (820, 132))
        if plate is None:
            plate = Image.new("RGBA", (820, 132), (255, 255, 255, 216))
            draw = ImageDraw.Draw(plate)
            draw.rounded_rectangle((0, 0, 819, 131), radius=32, fill=(255, 255, 255, 216), outline=PANEL_BORDER, width=3)
        self._im.alpha_composite(plate, (300, 52))

    def _paste_profile_icon(self, player_info: PlayerMaiInfo) -> None:
        icon: Image.Image | None = None
        if player_info.icon:
            icon_path = ICON_DIR / f"{player_info.icon.id}.png"
            if icon_path.exists():
                icon = self._get_image(icon_path, (122, 122))
        if icon is None:
            icon = Image.new("RGBA", (122, 122), (255, 255, 255, 0))
            draw = ImageDraw.Draw(icon)
            draw.rounded_rectangle((0, 0, 121, 121), radius=30, fill=(236, 241, 255, 255), outline=PANEL_BORDER, width=3)
            DrawText(draw, FONT_MAIN).draw(61, 61, 34, "M", ACCENT_COLOR, "mm")
        self._im.alpha_composite(icon, (320, 58))

    def _draw_badge(
        self,
        x: int,
        y: int,
        text: str,
        fill: tuple[int, int, int, int],
        *,
        text_color: tuple[int, int, int, int] = (255, 255, 255, 255),
        width: int | None = None,
    ) -> None:
        width = width or max(72, len(text) * 14 + 28)
        self._rounded_rectangle(self._dr, (x, y, x + width, y + 36), fill=fill, radius=18)
        self._sy.draw(x + width // 2, y + 18, 18, text, text_color, "mm")

    def draw_profile(self, player_info: PlayerMaiInfo, all_clear_rank: Optional[Image.Image] = None) -> None:
        self._rounded_rectangle(self._dr, (20, 22, 1380, 208), fill=PANEL_BG, outline=PANEL_BORDER, width=3, radius=36)
        self._rounded_rectangle(self._dr, (20, 22, 280, 208), fill=(111, 132, 255, 255), radius=36)
        self._sy.draw(150, 70, 42, "maimai", (255, 255, 255, 255), "mm")
        self._sy.draw(150, 118, 22, "Embedded Rikka", (235, 240, 255, 255), "mm")
        self._tb.draw(150, 158, 34, f"{player_info.rating:05d}", (255, 255, 255, 255), "mm")
        self._sy.draw(150, 188, 18, "DX Rating", (230, 235, 255, 255), "mm")

        self._paste_profile_plate(player_info)
        self._paste_profile_icon(player_info)

        self._sy.draw(470, 92, 36, player_info.name, TEXT_COLOR, "lm")
        self._sy.draw(470, 132, 20, f"Friend Code: {player_info.friend_code or '-'}", SUBTEXT_COLOR, "lm")
        self._sy.draw(470, 164, 20, f"Course {player_info.course_rank or 0} / Class {player_info.class_rank or 0}", SUBTEXT_COLOR, "lm")

        badges = [("B35 + B15", ACCENT_COLOR)]
        if player_info.upload_time:
            badges.append((f"Updated {player_info.upload_time}", (97, 145, 255, 255)))
        badge_x = 870
        for text, color in badges:
            self._draw_badge(badge_x, 88, text, color)
            badge_x += max(96, len(text) * 14 + 40)

        if all_clear_rank:
            badge = all_clear_rank.copy()
            badge.thumbnail((220, 62))
            self._im.alpha_composite(badge, (1128, 130))

    def draw_footer(self) -> None:
        self._sy.draw(
            700,
            1570,
            18,
            "Generated by SuzunoBot with embedded Nonebot-Plugin-Rikka maimai implementation",
            SUBTEXT_COLOR,
            "mm",
        )

    def _score_rate_text(self, score: PlayerMaiScore) -> str:
        rate = score.rate.value.upper()
        if rate == "SP":
            rate = "S+"
        elif rate == "SSP":
            rate = "SS+"
        elif rate == "SSSP":
            rate = "SSS+"
        return rate

    def _draw_score_card(self, x: int, y: int, info: PlayerMaiScore) -> None:
        card_w = 260
        card_h = 108
        diff_color = self.bg_color[info.song_difficulty.value]
        self._rounded_rectangle(
            self._dr,
            (x, y, x + card_w, y + card_h),
            fill=(255, 255, 255, 228),
            outline=diff_color,
            width=3,
            radius=24,
        )

        cover = self._load_cover(info.song_id, (84, 84))
        self._im.alpha_composite(cover, (x + 12, y + 12))

        self._draw_badge(
            x + 12,
            y + 88,
            str(info.song_id),
            diff_color,
            width=84,
        )
        self._draw_badge(
            x + 194,
            y + 12,
            info.song_type.value.upper(),
            diff_color,
            width=52,
        )

        title = info.song_name
        if coloum_width(title) > 18:
            title = change_column_width(title, 18) + "..."
        self._sy.draw(x + 108, y + 22, 16, title, TEXT_COLOR, "lm")

        play_count = f"PC {info.play_count}" if info.play_count else "-"
        self._sy.draw(x + 108, y + 42, 13, f"Lv {info.song_level}  {play_count}", SUBTEXT_COLOR, "lm")
        self._tb.draw(x + 108, y + 66, 24, f"{info.achievements:.4f}%", diff_color, "lm")

        song_level_string = "{:.1f}".format(info.song_level_value) if info.song_level_value else info.song_level
        bottom = f"{song_level_string} -> {round(info.dx_rating)}"
        self._tb.draw(x + 108, y + 89, 15, bottom, SUBTEXT_COLOR, "lm")

        fcfs_parts = [self._score_rate_text(info)]
        if info.fc:
            fcfs_parts.append(info.fc.value.upper())
        if info.fs:
            fcfs_parts.append(info.fs.value.upper())
        self._sy.draw(x + 244, y + 41, 12, " / ".join(fcfs_parts), SUBTEXT_COLOR, "rm")

        max_dx_score: int | None = None
        song_obj = MaiSongORM.get_song_sync(info.song_id)
        if song_obj:
            diff_value = info.song_difficulty.value
            try:
                diff = song_obj.difficulties.dx[diff_value] if info.song_type.value == "dx" else song_obj.difficulties.standard[diff_value]
                max_dx_score = diff.notes.total * 3
            except IndexError:
                max_dx_score = None
        dx_text = f"DX {info.dx_score}/{max_dx_score}" if max_dx_score is not None else f"DX {info.dx_score}"
        self._tb.draw(x + 244, y + 89, 12, dx_text, SUBTEXT_COLOR, "rm")

    def whiledraw(self, data: List[PlayerMaiScore], height: int = 235) -> None:
        y = height
        for num, info in enumerate(data):
            col = num % 5
            row = num // 5
            x = 16 + col * 276
            y = height + row * 114
            self._draw_score_card(x, y, info)
