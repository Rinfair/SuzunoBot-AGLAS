from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Iterable, Sequence
from urllib import request

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..config import config
from ..constants import _MAI_VERSION_MAP
from ..storage import MaiSongORM
from ..functions.recommend_songs import RecommendSong
from ..models.song import MaiSong
from ..score import PlayerMaiB50, PlayerMaiInfo, PlayerMaiScore
from .utils import DrawText, change_column_width, coloum_width

STATIC_DIR = Path(config.static_resource_path)
MAI_DIR = STATIC_DIR / "mai"
PIC_DIR = MAI_DIR / "pic"
COVER_DIR = MAI_DIR / "cover"
PLATE_DIR = MAI_DIR / "plate"
ICON_DIR = MAI_DIR / "icon"

SIYUAN = STATIC_DIR / "ResourceHanRoundedCN-Bold.ttf"
SHANGGU = STATIC_DIR / "ShangguMonoSC-Regular.otf"
TBFONT = STATIC_DIR / "Torus SemiBold.otf"

BOT_LABEL = "SuzunoBot"

TEXT_COLOR = (124, 129, 255, 255)
TITLE_COLORS = [
    (255, 255, 255, 255),
    (255, 255, 255, 255),
    (255, 255, 255, 255),
    (255, 255, 255, 255),
    (138, 0, 226, 255),
]
ID_COLORS = [
    (129, 217, 85, 255),
    (245, 189, 21, 255),
    (255, 129, 141, 255),
    (159, 81, 220, 255),
    (138, 0, 226, 255),
]
BG_COLORS = [
    (111, 212, 61, 255),
    (248, 183, 9, 255),
    (255, 129, 141, 255),
    (159, 81, 220, 255),
    (219, 170, 255, 255),
]
SONG_GENRE_MAP = {
    "POPSアニメ": "anime",
    "POPS & ANIME": "anime",
    "POPS&ANIME": "anime",
    "流行&动漫": "anime",
    "niconicoボーカロイド": "niconico",
    "niconico & VOCALOID": "niconico",
    "niconico&VOCALOID": "niconico",
    "东方Project": "touhou",
    "東方Project": "touhou",
    "游戏&综艺": "game",
    "游戏バラエティ": "game",
    "ゲームバラエティ": "game",
    "maimai": "maimai",
    "オンゲキCHUNITHM": "ongeki",
    "音击&中二节奏": "ongeki",
}
VERSION_PICTURE_MAP = {
    100: "maimai.png",
    110: "maimai PLUS.png",
    120: "maimai GreeN.png",
    130: "maimai GreeN PLUS.png",
    140: "maimai ORANGE.png",
    150: "maimai ORANGE PLUS.png",
    160: "maimai PiNK.png",
    170: "maimai PiNK PLUS.png",
    180: "maimai MURASAKi.png",
    185: "maimai MURASAKi PLUS.png",
    190: "maimai MiLK.png",
    195: "MiLK PLUS.png",
    199: "maimai FiNALE.png",
    200: "maimai でらっくす.png",
    210: "maimai でらっくす Splash.png",
    220: "maimai でらっくす UNiVERSE.png",
    230: "maimai でらっくす FESTiVAL.png",
    240: "maimai でらっくす BUDDiES.png",
    250: "maimai でらっくす PRiSM.png",
}
SCORE_RANK_L = {
    "d": "D",
    "c": "C",
    "b": "B",
    "bb": "BB",
    "bbb": "BBB",
    "a": "A",
    "aa": "AA",
    "aaa": "AAA",
    "s": "S",
    "sp": "Sp",
    "ss": "SS",
    "ssp": "SSp",
    "sss": "SSS",
    "sssp": "SSSp",
}
FCL = {"fc": "FC", "fcp": "FCp", "ap": "AP", "app": "APp"}
FSL = {"fs": "FS", "fsp": "FSp", "fsd": "FSD", "fsdp": "FSDp", "sync": "Sync"}


@lru_cache(maxsize=1024)
def _load_image(path_str: str) -> Image.Image:
    return Image.open(path_str).convert("RGBA")


def get_image(path: Path) -> Image.Image:
    return _load_image(str(path)).copy()


def safe_font(path: Path, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def tricolor_gradient(
    width: int,
    height: int,
    color1: tuple[int, int, int] = (124, 129, 255),
    color2: tuple[int, int, int] = (193, 247, 225),
    color3: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    array = np.zeros((height, width, 3), dtype=np.uint8)
    split = max(1, int(height * 0.4))
    for y in range(height):
        if y < split:
            ratio = y / max(split, 1)
            color = (1 - ratio) * np.array(color1) + ratio * np.array(color2)
        else:
            ratio = (y - split) / max(height - split, 1)
            color = (1 - ratio) * np.array(color2) + ratio * np.array(color3)
        array[y, :] = np.clip(color, 0, 255)
    return Image.fromarray(array).convert("RGBA")


def build_maimai_background(width: int, height: int) -> Image.Image:
    image = tricolor_gradient(width, height)

    aurora = PIC_DIR / "aurora.png"
    if aurora.exists():
        image.alpha_composite(get_image(aurora).resize((width, 220)), (0, 0))

    shines = PIC_DIR / "bg_shines.png"
    if shines.exists():
        image.alpha_composite(get_image(shines), (34, 0))

    rainbow = PIC_DIR / "rainbow.png"
    if rainbow.exists():
        image.alpha_composite(get_image(rainbow), (319, max(0, height - 643)))

    rainbow_bottom = PIC_DIR / "rainbow_bottom.png"
    if rainbow_bottom.exists():
        image.alpha_composite(get_image(rainbow_bottom).resize((1200, 200)), (100, max(0, height - 343)))

    pattern = PIC_DIR / "pattern.png"
    if pattern.exists():
        pattern_image = get_image(pattern)
        for idx in range((height // 358) + 1):
            image.alpha_composite(pattern_image, (0, (358 + 7) * idx))

    return image


def music_picture(song_id: int | str) -> Path:
    music_id = int(song_id)
    if (path := COVER_DIR / f"{music_id}.png").exists():
        return path
    if music_id > 100000:
        music_id -= 100000
        if (path := COVER_DIR / f"{music_id}.png").exists():
            return path
    if 1000 < music_id < 10000 or 10000 < music_id <= 11000:
        for cid in [music_id + 10000, music_id - 10000]:
            if (path := COVER_DIR / f"{cid}.png").exists():
                return path
    if (path := PIC_DIR / "noimage.png").exists():
        return path
    return COVER_DIR / "11000.png"


def dx_star_count(percent: float) -> int:
    if percent <= 85:
        return 0
    if percent <= 90:
        return 1
    if percent <= 93:
        return 2
    if percent <= 95:
        return 3
    if percent <= 97:
        return 4
    return 5


def _normalize_song_id(song_id: int) -> int:
    if 10000 < song_id < 100000:
        return song_id - 10000
    if song_id > 100000:
        return song_id - 100000
    return song_id


def full_dx_score(score: PlayerMaiScore) -> int:
    song = MaiSongORM.get_song_sync(_normalize_song_id(score.song_id))
    if song is None:
        return max(score.dx_score, 1)
    try:
        chart = (
            song.difficulties.dx[score.song_difficulty.value]
            if score.song_type.value == "dx"
            else song.difficulties.standard[score.song_difficulty.value]
        )
    except Exception:
        return max(score.dx_score, 1)
    return max(chart.notes.total * 3, 1)


def song_type_short(score: PlayerMaiScore) -> str:
    return "DX" if score.song_type.value == "dx" else "SD"


def rank_asset_name(score: PlayerMaiScore) -> str:
    return SCORE_RANK_L.get(score.rate.value, score.rate.value.upper())


def score_ra(score: PlayerMaiScore) -> int:
    return int(round(score.dx_rating))


def score_ds_text(score: PlayerMaiScore) -> str:
    if score.song_level_value is not None:
        return f"{score.song_level_value:.1f}"
    return str(score.song_level)


def player_rating_plate(rating: int) -> Path:
    if rating < 1000:
        num = "01"
    elif rating < 2000:
        num = "02"
    elif rating < 4000:
        num = "03"
    elif rating < 7000:
        num = "04"
    elif rating < 10000:
        num = "05"
    elif rating < 12000:
        num = "06"
    elif rating < 13000:
        num = "07"
    elif rating < 14000:
        num = "08"
    elif rating < 14500:
        num = "09"
    elif rating < 15000:
        num = "10"
    else:
        num = "11"
    return PIC_DIR / f"UI_CMN_DXRating_{num}.png"


def player_match_plate(player_info: PlayerMaiInfo) -> Path | None:
    rank = int(player_info.course_rank)
    if rank < 0:
        return None
    for number in (rank, rank + 1):
        path = PIC_DIR / f"UI_DNM_DaniPlate_{number:02d}.png"
        if path.exists():
            return path
    return None


def player_class_plate(player_info: PlayerMaiInfo) -> Path | None:
    candidates = []
    if player_info.class_rank >= 0:
        candidates.append(PIC_DIR / f"UI_FBR_Class_{player_info.class_rank:02d}.png")
        candidates.append(PIC_DIR / f"UI_FBR_Class_{player_info.class_rank:03d}.png")
    candidates.append(PIC_DIR / "UI_FBR_Class_00.png")
    for path in candidates:
        if path.exists():
            return path
    return None


def player_plate_image(player_info: PlayerMaiInfo) -> Image.Image:
    candidates: list[Path] = []
    if player_info.profile_plate > 0:
        candidates.append(PIC_DIR / f"plate_{player_info.profile_plate}.png")
    if player_info.name_plate:
        candidates.append(PLATE_DIR / f"{player_info.name_plate.id}.png")
    candidates.append(PIC_DIR / "UI_Plate_300501.png")
    candidates.append(PIC_DIR / "plate_1.png")
    for path in candidates:
        if path.exists():
            return get_image(path).resize((800, 130))
    return Image.new("RGBA", (800, 130), (255, 255, 255, 0))


def qq_avatar_image(qq: str | None, size: tuple[int, int] = (120, 120)) -> Image.Image | None:
    if not qq or not str(qq).isdigit():
        return None
    try:
        with request.urlopen(f"https://q1.qlogo.cn/g?b=qq&nk={qq}&s=140", timeout=10) as resp:
            avatar = Image.open(BytesIO(resp.read())).convert("RGBA")
    except Exception:
        return None
    return avatar.resize(size)


def player_icon_image(player_info: PlayerMaiInfo) -> Image.Image:
    if player_info.icon:
        icon_path = ICON_DIR / f"{player_info.icon.id}.png"
        if icon_path.exists():
            return get_image(icon_path).resize((120, 120))
    qq_avatar = qq_avatar_image(player_info.qq)
    if qq_avatar is not None:
        return qq_avatar
    fallback = PIC_DIR / "UI_Icon_309503.png"
    if fallback.exists():
        return get_image(fallback).resize((120, 120))
    return Image.new("RGBA", (120, 120), (255, 255, 255, 0))


def status_icon(token: str | None) -> Image.Image | None:
    if not token:
        return None
    token = token.lower()
    if token in FCL:
        path = PIC_DIR / f"UI_MSS_MBase_Icon_{FCL[token]}.png"
    elif token in FSL:
        path = PIC_DIR / f"UI_MSS_MBase_Icon_{FSL[token]}.png"
    else:
        return None
    return get_image(path).resize((34, 34)) if path.exists() else None


def play_bonus_icon(token: str | None) -> Image.Image | None:
    if not token:
        return None
    token = token.lower()
    if token in FCL:
        path = PIC_DIR / f"UI_CHR_PlayBonus_{FCL[token]}.png"
    elif token in FSL:
        path = PIC_DIR / f"UI_CHR_PlayBonus_{FSL[token]}.png"
    else:
        return None
    return get_image(path) if path.exists() else None


def rank_icon(score: PlayerMaiScore, *, width: int = 63, height: int = 28) -> Image.Image | None:
    path = PIC_DIR / f"UI_TTR_Rank_{rank_asset_name(score)}.png"
    return get_image(path).resize((width, height)) if path.exists() else None


def dx_score_icon(score: PlayerMaiScore, *, width: int = 47, height: int = 26) -> Image.Image | None:
    maximum = full_dx_score(score)
    star = dx_star_count(score.dx_score / maximum * 100)
    if star <= 0:
        return None
    path = PIC_DIR / f"UI_GAM_Gauge_DXScoreIcon_0{star}.png"
    return get_image(path).resize((width, height)) if path.exists() else None


def type_picture(song_type: str) -> Path | None:
    short = "DX" if song_type == "dx" else "SD"
    path = PIC_DIR / f"{short}.png"
    return path if path.exists() else None


def version_picture(version: int) -> Path | None:
    value = version
    if value not in VERSION_PICTURE_MAP:
        candidates = [key for key in VERSION_PICTURE_MAP if key <= value]
        value = max(candidates) if candidates else 100
    name = VERSION_PICTURE_MAP.get(value)
    if not name:
        return None
    path = PIC_DIR / name
    return path if path.exists() else None


def genre_picture(genre: str) -> Path | None:
    mapped = SONG_GENRE_MAP.get(genre, "maimai")
    path = PIC_DIR / f"info-{mapped}.png"
    return path if path.exists() else None


def draw_rating_digits(image: Image.Image, rating: int, pos: tuple[int, int], size: tuple[int, int] = (17, 20)) -> None:
    text = f"{rating:05d}"
    x, y = pos
    for idx, digit in enumerate(text):
        path = PIC_DIR / f"UI_NUM_Drating_{digit}.png"
        if not path.exists():
            continue
        image.alpha_composite(get_image(path).resize(size), (x + 15 * idx, y))


def footer_design(image: Image.Image, text: str, *, bottom: int = 110, width: int = 1000) -> None:
    design = PIC_DIR / "design.png"
    if not design.exists():
        return
    draw = ImageDraw.Draw(image)
    sy = DrawText(draw, SIYUAN)
    design_image = get_image(design)
    design_image = design_image.resize((width, int(design_image.height * width / design_image.width)))
    image.alpha_composite(design_image, ((image.width - width) // 2, image.height - bottom))
    sy.draw(image.width // 2, image.height - bottom + 37, 22, text, TEXT_COLOR, "mm")


def add_maimai_frame(image: Image.Image) -> None:
    overlay = PIC_DIR / "UI_TTR_BG_Base.png"
    if overlay.exists():
        image.alpha_composite(get_image(overlay).resize(image.size), (0, 0))


def section_title(image: Image.Image, text: str, *, y: int, x: int = 475, lengthen: bool = True, size: int = 28) -> None:
    bg_path = PIC_DIR / ("title-lengthen.png" if lengthen else "title.png")
    if not bg_path.exists():
        return
    bg = get_image(bg_path)
    image.alpha_composite(bg, (x, y))
    draw = ImageDraw.Draw(image)
    DrawText(draw, SIYUAN).draw(x + bg.width // 2, y + 47, size, text, TEXT_COLOR, "mm")


def blur_cover_background(song_id: int, size: tuple[int, int]) -> Image.Image:
    cover = get_image(music_picture(song_id)).resize(size)
    dark = Image.new("RGBA", size, (0, 0, 0, 90))
    cover = cover.filter(ImageFilter.GaussianBlur(4))
    cover.alpha_composite(dark)
    return cover


def not_played_grid(
    image: Image.Image,
    songs: Sequence[tuple[int, int, str]],
    *,
    start_y: int,
    title: str,
    show_footer: bool = False,
) -> int:
    section_title(image, title, y=max(0, start_y - 110))
    draw = ImageDraw.Draw(image)
    tb = DrawText(draw, TBFONT)
    x = 55
    y = start_y
    step_y = 65
    bar_cache = [Image.new("RGBA", (55, 10), color) for color in BG_COLORS]
    for index, (song_id, diff_idx, _status) in enumerate(songs):
        if index % 20 == 0:
            x = 55
            y += step_y if index != 0 else 0
        else:
            x += 65
        cover = get_image(music_picture(song_id)).resize((55, 55))
        image.alpha_composite(cover, (x, y))
        image.alpha_composite(bar_cache[diff_idx], (x, y + 45))
        tb.draw(x + 27, y + 50, 10, song_id, TITLE_COLORS[diff_idx], "mm")
    return y + 65 if songs else start_y


class MaimaiScorePainter:
    def __init__(self, image: Image.Image) -> None:
        self._im = image
        self._dr = ImageDraw.Draw(self._im)
        self._sy = DrawText(self._dr, SIYUAN)
        self._tb = DrawText(self._dr, TBFONT)
        self._diff = [
            get_image(PIC_DIR / "b50_score_basic.png"),
            get_image(PIC_DIR / "b50_score_advanced.png"),
            get_image(PIC_DIR / "b50_score_expert.png"),
            get_image(PIC_DIR / "b50_score_master.png"),
            get_image(PIC_DIR / "b50_score_remaster.png"),
        ]
        self._rise = [
            get_image(PIC_DIR / "rise_score_basic.png"),
            get_image(PIC_DIR / "rise_score_advanced.png"),
            get_image(PIC_DIR / "rise_score_expert.png"),
            get_image(PIC_DIR / "rise_score_master.png"),
            get_image(PIC_DIR / "rise_score_remaster.png"),
        ]

    def draw_score_card(self, x: int, y: int, score: PlayerMaiScore) -> None:
        diff_idx = score.song_difficulty.value
        cover = get_image(music_picture(score.song_id)).resize((75, 75))
        version_path = type_picture(score.song_type.value)
        version = get_image(version_path).resize((37, 14)) if version_path else None

        base = self._diff[diff_idx].copy()
        self._im.alpha_composite(base, (x, y))
        self._im.alpha_composite(cover, (x + 12, y + 12))
        if version is not None:
            self._im.alpha_composite(version, (x + 51, y + 91))

        rate = rank_icon(score)
        if rate is not None:
            self._im.alpha_composite(rate, (x + 92, y + 78))

        fc = status_icon(score.fc.value if score.fc else None)
        if fc is not None:
            self._im.alpha_composite(fc, (x + 154, y + 77))

        fs = status_icon(score.fs.value if score.fs else None)
        if fs is not None:
            self._im.alpha_composite(fs, (x + 185, y + 77))

        dx_icon = dx_score_icon(score)
        if dx_icon is not None:
            self._im.alpha_composite(dx_icon, (x + 217, y + 80))

        displayed_song_id = score.song_id
        if score.song_type.value == "dx" and score.song_id < 10000:
            displayed_song_id += 10000

        self._tb.draw(x + 26, y + 98, 13, displayed_song_id, ID_COLORS[diff_idx], anchor="mm")

        title = score.song_name
        if coloum_width(title) > 18:
            title = change_column_width(title, 17) + "..."
        self._sy.draw(x + 93, y + 14, 14, title, TITLE_COLORS[diff_idx], anchor="lm")
        self._tb.draw(x + 93, y + 38, 30, f"{score.achievements:.4f}%", TITLE_COLORS[diff_idx], anchor="lm")

        maximum = full_dx_score(score)
        self._tb.draw(x + 219, y + 65, 15, f"{score.dx_score}/{maximum}", TITLE_COLORS[diff_idx], anchor="mm")
        self._tb.draw(
            x + 93,
            y + 65,
            15,
            f"{score_ds_text(score)} -> {score_ra(score)}",
            TITLE_COLORS[diff_idx],
            anchor="lm",
        )

    def draw_cards(self, scores: Iterable[PlayerMaiScore], start_x: int, start_y: int, columns: int = 5) -> None:
        score_list = list(scores)
        step_x = 276
        step_y = 114
        for idx, score in enumerate(score_list):
            row = idx // columns
            col = idx % columns
            self.draw_score_card(start_x + col * step_x, start_y + row * step_y, score)

    def draw_rise_card(self, x: int, y: int, song: RecommendSong, low_score: int) -> None:
        diff_idx = song.level_index
        base = self._rise[diff_idx].copy()
        cover = get_image(music_picture(song.song_id)).resize((80, 80))
        version_path = type_picture(song.type)
        version = get_image(version_path).resize((60, 22)) if version_path else None
        rate_path = PIC_DIR / f"UI_TTR_Rank_{SCORE_RANK_L.get(self._rate_name(song.target_achievements).lower(), self._rate_name(song.target_achievements))}.png"
        rate = get_image(rate_path).resize((63, 28)) if rate_path.exists() else None

        self._im.alpha_composite(base, (x + 30, y))
        self._im.alpha_composite(cover, (x + 55, y + 40))
        if version is not None:
            self._im.alpha_composite(version, (x + 240, y + 114))
        if rate is not None:
            self._im.alpha_composite(rate, (x + 305, y + 82))

        title = song.title
        if coloum_width(title) > 26:
            title = change_column_width(title, 25) + "..."
        self._sy.draw(x + 142, y + 44, 17, title, TITLE_COLORS[diff_idx], "lm")
        self._tb.draw(x + 145, y + 124, 18, f"ID: {song.song_id}", ID_COLORS[diff_idx], "lm")
        self._tb.draw(x + 210, y + 71, 25, f"{song.old_achievements:.4f}%", TITLE_COLORS[diff_idx], anchor="mm")
        self._tb.draw(x + 245, y + 96, 17, f"Ra: {song.old_dx_rating}", TITLE_COLORS[diff_idx], anchor="mm")
        self._tb.draw(x + 370, y + 71, 25, f"{song.target_achievements:.4f}%", TITLE_COLORS[diff_idx], anchor="mm")
        self._tb.draw(x + 415, y + 96, 17, f"Ra: {song.target_dx_rating}", TITLE_COLORS[diff_idx], anchor="mm")
        self._tb.draw(x + 315, y + 124, 18, f"ds:{song.difficulty_value:.1f}", ID_COLORS[diff_idx], anchor="lm")
        gain = song.target_dx_rating - (song.old_dx_rating if song.old_dx_rating > low_score else low_score)
        self._tb.draw(x + 390, y + 124, 18, f"Ra +{max(gain, 0)}", ID_COLORS[diff_idx], "lm")

    @staticmethod
    def _rate_name(achievement: float) -> str:
        if achievement < 50:
            return "D"
        if achievement < 60:
            return "C"
        if achievement < 70:
            return "B"
        if achievement < 75:
            return "BB"
        if achievement < 80:
            return "BBB"
        if achievement < 90:
            return "A"
        if achievement < 94:
            return "AA"
        if achievement < 97:
            return "AAA"
        if achievement < 98:
            return "S"
        if achievement < 99:
            return "Sp"
        if achievement < 99.5:
            return "SS"
        if achievement < 100:
            return "SSp"
        if achievement < 100.5:
            return "SSS"
        return "SSSp"


class BestRatingMixin:
    @staticmethod
    def total_rating(best50: PlayerMaiB50) -> tuple[int, int]:
        return (
            sum(score_ra(score) for score in best50.standard[:35]),
            sum(score_ra(score) for score in best50.dx[:15]),
        )


def song_version_name(version: int) -> str:
    return _MAI_VERSION_MAP.get(version, str(version))


def crop_height(image: Image.Image, height: int) -> Image.Image:
    return image.crop((0, 0, image.width, height))
