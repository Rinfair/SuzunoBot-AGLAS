"""
玩家底力分析
"""

from dataclasses import dataclass

from ..score import PlayerMaiScore
from .song_tags import get_songs_tags


@dataclass
class PlayerStrength:
    patterns_strengths: dict[str, int]
    difficulty_strengths: dict[str, int]
    song_evaluates: dict[str, int]


def _extract_values(source: dict, *fields: str) -> dict:
    output = {}

    for field in fields:
        output[field] = source.get(field, 0)

    return output


def get_player_strength(scores: list[PlayerMaiScore]) -> PlayerStrength:
    player_strengths: dict[str, int] = {}

    for score in scores:
        song_type = "dx" if score.song_type.value == "dx" else "std"
        song_diff = score.song_difficulty.name.lower()
        if song_diff not in ["remaster", "master", "expert"]:
            continue

        tags = get_songs_tags(score.song_name, song_type, song_diff)  # type: ignore

        for tag in tags:
            player_strengths[tag] = player_strengths.get(tag, 0) + 1

    patterns_strengths = _extract_values(
        player_strengths,
        "转圈",
        "绝赞段",
        "扫键",
        "散打",
        "交互",
        "反手",
        "一笔画",
        "错位",
        "跳拍",
        "纵连",
        "爆发",
        "拆弹",
        "定拍",
        "大位移",
    )
    difficulty_strengths = _extract_values(player_strengths, "水", "诈称谱")
    difficulty_strengths["正常铺"] = len(scores) - sum(difficulty_strengths.values())
    song_evaluates = _extract_values(player_strengths, "底力谱", "体力谱", "高物量", "键盘谱", "星星谱")

    return PlayerStrength(patterns_strengths, difficulty_strengths, song_evaluates)
