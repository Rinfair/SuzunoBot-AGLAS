from pathlib import Path
from typing import Dict, Iterable

from ..config import config

STATIC_DIR = Path(config.static_resource_path)
MAI_DIR = STATIC_DIR / "mai"
PIC_DIR = MAI_DIR / "pic"
COVER_DIR = MAI_DIR / "cover"
PLATE_DIR = MAI_DIR / "plate"
ICON_DIR = MAI_DIR / "icon"


def _pick_existing(paths: Iterable[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    return next(iter(paths))


FONT_MAIN = _pick_existing(
    [
        Path(config.scorelist_font_main) if config.scorelist_font_main else STATIC_DIR / "ResourceHanRoundedCN-Bold.ttf",
        STATIC_DIR / "adobe_simhei.otf",
        STATIC_DIR / "HOS_Bold.ttf",
        Path("C:/Windows/Fonts/msyh.ttc"),
    ]
)
FONT_NUM = _pick_existing(
    [
        Path(config.scorelist_font_num) if config.scorelist_font_num else STATIC_DIR / "Torus SemiBold.otf",
        STATIC_DIR / "ExoM.ttf",
        STATIC_DIR / "Poppins.otf",
        FONT_MAIN,
    ]
)

TEXT_COLOR = (74, 90, 180, 255)
BG_TOP = (237, 244, 255, 255)
BG_BOTTOM = (247, 249, 255, 255)
PANEL_BG = (255, 255, 255, 225)
PANEL_BORDER = (172, 190, 255, 255)
SUBTEXT_COLOR = (90, 104, 152, 255)
ACCENT_COLOR = (102, 128, 255, 255)

DIFF_COLORS = [
    (98, 196, 88, 255),
    (255, 195, 64, 255),
    (255, 120, 122, 255),
    (158, 102, 255, 255),
    (220, 174, 255, 255),
]

SCORE_RANK_L: Dict[str, str] = {
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
FCL: Dict[str, str] = {"fc": "FC", "fcp": "FCp", "ap": "AP", "app": "APp"}
FSL: Dict[str, str] = {"fs": "FS", "fsp": "FSp", "fsd": "FSD", "fsdp": "FSDp", "sync": "Sync"}
GENRE_MAPPING: Dict[str, str] = {
    "POPSアニメ": "anime",
    "niconicoボーカロイド": "niconico",
    "東方Project": "touhou",
    "ゲームバラエティ": "game",
    "maimai": "maimai",
    "オンゲキCHUNITHM": "ongeki",
}
