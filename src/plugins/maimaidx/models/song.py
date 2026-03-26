from dataclasses import dataclass, fields
from typing import Literal, Optional


@dataclass
class SongNotes:
    total: int
    """总物量"""
    tap: int
    """TAP 物量"""
    hold: int
    """HOLD 物量"""
    slide: int
    """SLIDE 物量"""
    touch: int
    """TOUCH 物量"""
    break_: int
    """BREAK 物量"""

    @staticmethod
    def from_dict(data: dict[str, int]) -> "SongNotes":
        """
        Initialize SongNotes from a dictionary.
        """
        return SongNotes(
            total=data.get("total", 0),
            tap=data.get("tap", 0),
            hold=data.get("hold", 0),
            slide=data.get("slide", 0),
            touch=data.get("touch", 0),
            break_=data.get("break", 0),
        )


@dataclass
class BuddyNotes:
    left: SongNotes
    """1P 谱面物量"""
    right: SongNotes
    """2P 谱面物量"""


@dataclass
class SongDifficulty:
    type: Literal["standard", "dx", "utage"]
    """谱面类型"""
    difficulty: int
    """难度"""
    level: str
    """难度标级"""
    level_value: float
    """谱面定数"""
    note_designer: str
    """谱师"""
    version: str
    """谱面首次出现版本"""
    notes: SongNotes
    """谱面物量"""
    level_fit: float = 0.0
    """拟合定数"""


@dataclass
class SongDifficultyUtage:
    kanji: str
    """谱面属性"""
    description: str
    """铺面描述"""
    is_buddy: bool
    """是否为 BUDDY 谱面"""
    notes: SongNotes | BuddyNotes


@dataclass
class SongDifficulties:
    standard: list[SongDifficulty]
    dx: list[SongDifficulty]
    utage: Optional[list[SongDifficultyUtage]]

    @staticmethod
    def init_from_dict(data: dict[str, list]) -> "SongDifficulties":
        """
        Initialize SongDifficulties from a dictionary.
        """
        standard_fields = {f.name for f in fields(SongDifficulty)}
        dx_fields = standard_fields
        utage_fields = {f.name for f in fields(SongDifficultyUtage)}

        standard_difficulties = []
        dx_difficulties = []

        for item in data.get("standard", []):
            notes = item.get("notes", {})
            item["notes"] = SongNotes.from_dict(notes) if notes else {}
            standard_difficulties.append(SongDifficulty(**{k: v for k, v in item.items() if k in standard_fields}))

        for item in data.get("dx", []):
            notes = item.get("notes", {})
            item["notes"] = SongNotes.from_dict(notes) if notes else {}
            dx_difficulties.append(SongDifficulty(**{k: v for k, v in item.items() if k in dx_fields}))

        if data.get("utage"):
            utage_difficulties = [
                SongDifficultyUtage(**{k: v for k, v in item.items() if k in utage_fields})
                for item in data.get("utage", [])
            ]
        else:
            utage_difficulties = None

        return SongDifficulties(standard=standard_difficulties, dx=dx_difficulties, utage=utage_difficulties)


@dataclass
class MaiSong:
    """曲目"""

    id: int
    """曲目 ID"""
    title: str
    """曲名"""
    artist: str
    """艺术家"""
    genre: str
    """曲目分类"""
    bpm: int
    """曲目 BPM"""
    version: int
    """曲目首次出现版本"""
    difficulties: SongDifficulties
    map: Optional[str] = None
    """曲目所属区域"""
    locked: bool = False
    """是否需要解锁"""
    disabled: bool = False
    """是否被禁用"""

    def __hash__(self) -> int:
        return hash(self.id)
