import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from nonebot import logger

from ..models.song import MaiSong, SongDifficulty
from ..score import PlayerMaiScore
from ..score._schema import SongType

plate_json_file = Path("static/maimaidxplate.json")

PLATE_DATA: dict[str, list[int]] = {}

if plate_json_file.exists():
    PLATE_DATA = json.loads(plate_json_file.read_text(encoding="utf-8"))
else:
    import asyncio

    from ..updater.songs import get_plate_data

    try:
        PLATE_DATA = asyncio.run(get_plate_data())
        plate_json_file.write_text(json.dumps(PLATE_DATA, ensure_ascii=False, indent=4), encoding="utf-8")
    except Exception as e:
        logger.warning(f"无法获取牌子数据: {e}")


class ProcessDataError(RuntimeError):
    """进度计算失败（用于替代返回错误字符串）。"""


class PlateProcessError(ProcessDataError):
    pass


class LevelProcessError(ProcessDataError):
    pass


@dataclass
class UnfinishedSong:
    song: MaiSong
    difficulty: int
    level_value: float
    status: str  # "未游玩" 或 "98.5000%" 或 "FC" 等当前成绩


@dataclass
class PlateProcessData:
    ver_name: str
    plan: str
    basic_left: List[UnfinishedSong]
    advanced_left: List[UnfinishedSong]
    expert_left: List[UnfinishedSong]
    master_left: List[UnfinishedSong]
    remaster_left: List[UnfinishedSong]
    difficult_left: List[UnfinishedSong]  # DS > 13.6
    total_left: int
    played_count: int
    total_count: int


@dataclass
class LevelProcessData:
    level: str
    plan: str
    completed: List[Tuple[MaiSong, Optional[PlayerMaiScore], int]]  # Song, Score, DiffIndex
    unfinished: List[Tuple[MaiSong, Optional[PlayerMaiScore], int]]
    not_played: List[Tuple[MaiSong, int]]  # Song, DiffIndex
    counts: Dict[str, int]  # total, completed, unfinished, not_played


PLATE_VER_MAPPING = {
    "真": [100, 110],
    "初": [100, 110],
    "超": [120],
    "檄": [130],
    "橙": [140],
    "晓": [150],
    "暁": [150],
    "桃": [160],
    "樱": [170],
    "櫻": [170],
    "紫": [180],
    "菫": [185],
    "堇": [185],
    "白": [190],
    "雪": [195],
    "辉": [199],
    "輝": [199],
    "熊": [200],
    "华": [200],
    "華": [200],
    "爽": [210],
    "煌": [210],
    "宙": [220],
    "星": [220],
    "祭": [230],
    "祝": [230],
    "双": [240],
    "宴": [240],
    "镜": [250],
    "彩": [250],
}


def _get_plate_data_key(plate_char: str) -> str | None:
    """将输入的牌子字符映射到 maimaidxplate.json 的 key。"""

    # SD
    if plate_char in ["真", "初"]:
        return "真"
    if plate_char in ["超"]:
        return "超"
    if plate_char in ["檄"]:
        return "檄"
    if plate_char in ["橙"]:
        return "橙"
    if plate_char in ["晓", "暁"]:
        return "暁"
    if plate_char in ["桃"]:
        return "桃"
    if plate_char in ["樱", "櫻"]:
        return "櫻"
    if plate_char in ["紫"]:
        return "紫"
    if plate_char in ["菫", "堇"]:
        return "菫"
    if plate_char in ["白"]:
        return "白"
    if plate_char in ["雪"]:
        return "雪"
    if plate_char in ["辉", "輝"]:
        return "輝"

    # 舞/霸：使用同一份曲目 ID 列表，Re:Master 再单独清洗。
    if plate_char in ["舞", "霸"]:
        return "舞"

    # DX
    if plate_char in ["熊", "华", "華"]:
        return "熊&华"
    if plate_char in ["爽", "煌"]:
        return "爽&煌"
    if plate_char in ["宙", "星"]:
        return "宙&星"
    if plate_char in ["祭", "祝"]:
        return "祭&祝"
    if plate_char in ["双", "宴"]:
        return "双&宴"
    if plate_char in ["镜", "彩"]:
        return "镜&彩"

    return None


def _is_dx_plate(plate_char: str) -> bool:
    key = _get_plate_data_key(plate_char)
    return bool(key and "&" in key)


def get_plate_process_data(
    songs: List[MaiSong], scores: List[PlayerMaiScore], plate_char: str, plan: str
) -> PlateProcessData:

    plate_key = _get_plate_data_key(plate_char)
    if not plate_key:
        raise PlateProcessError(f"未知的牌子代号: {plate_char}")

    if not PLATE_DATA:
        raise PlateProcessError("未找到 static/maimaidxplate.json，无法计算牌子进度")

    plate_id_list = set(PLATE_DATA.get(plate_key, []))
    if not plate_id_list:
        raise PlateProcessError(f"牌子数据缺失：{plate_key}")

    is_dx_plate = _is_dx_plate(plate_char)

    target_songs: list[MaiSong] = [s for s in songs if s.id in plate_id_list or s.id + 10000 in plate_id_list]

    if not target_songs:
        raise PlateProcessError(f"该版本 ({plate_char}) 暂无曲目数据")

    played_map: dict[tuple[int, bool, int], PlayerMaiScore] = {}  # (song_id, is_dx, diff_idx) -> score

    target_song_ids = {s.id for s in target_songs}
    for sc in scores:
        if sc.song_id in target_song_ids:
            is_dx = sc.song_type == SongType.DX
            played_map[(sc.song_id, is_dx, int(sc.song_difficulty))] = sc

    lists: List[List[UnfinishedSong]] = [[], [], [], [], []]  # 0-4
    difficult_left = []

    remaster_whitelist = set(PLATE_DATA.get("舞ReMASTER", [])) if plate_char in ["舞", "霸"] else set()

    for s in target_songs:
        diffs: list[SongDifficulty] = s.difficulties.dx if is_dx_plate else s.difficulties.standard
        if not diffs:
            continue

        for d in diffs:
            if remaster_whitelist and d.difficulty == 4 and s.id not in remaster_whitelist:
                continue

            idx = d.difficulty
            score = played_map.get((s.id, is_dx_plate, idx))

            completed = False
            status = "未游玩"

            if score:
                status = f"{score.achievements:.4f}%"
                if plan == "将":
                    completed = score.achievements >= 100.0
                elif plan == "者":
                    completed = score.achievements >= 80.0  # Clear rank usually A (80%)
                elif plan in ["极", "極"]:
                    fc = score.fc
                    if fc is not None:
                        fc_value = fc.value
                        completed = fc_value in ["fc", "fcp", "ap", "app"]
                        status = fc_value
                elif plan == "神":
                    fc = score.fc
                    if fc is not None:
                        fc_value = fc.value
                        completed = fc_value in ["ap", "app"]
                        status = fc_value
                elif plan == "舞舞":
                    fs = score.fs
                    if fs is not None:
                        fs_value = fs.value
                        completed = fs_value in ["fsd", "fsdp"]
                        status = fs_value

            if not completed:
                item = UnfinishedSong(s, idx, d.level_value, status)
                lists[idx].append(item)
                if d.level_value > 13.6:
                    difficult_left.append(item)

    total_left = sum(len(bucket) for bucket in lists)
    total_count = 0
    for s in target_songs:
        diffs = s.difficulties.dx if is_dx_plate else s.difficulties.standard
        for d in diffs:
            if remaster_whitelist and d.difficulty == 4 and s.id not in remaster_whitelist:
                continue
            total_count += 1

    return PlateProcessData(
        ver_name=plate_char,
        plan=plan,
        basic_left=lists[0],
        advanced_left=lists[1],
        expert_left=lists[2],
        master_left=lists[3],
        remaster_left=lists[4],
        difficult_left=difficult_left,
        total_left=total_left,
        played_count=total_count - total_left,
        total_count=total_count,
    )


def get_level_process_data(
    songs: List[MaiSong],
    scores: List[PlayerMaiScore],
    level: str,
    plan: str,
) -> LevelProcessData:

    target_tasks: list[tuple[MaiSong, SongDifficulty, bool]] = []  # (Song, SongDifficulty, is_dx)

    for s in songs:
        for d in s.difficulties.standard:
            if d.level == level:
                target_tasks.append((s, d, False))
        for d in s.difficulties.dx:
            if d.level == level:
                target_tasks.append((s, d, True))

    if not target_tasks:
        raise LevelProcessError(f"未找到等级为 {level} 的曲目")

    played_map: dict[tuple[int, bool, int], PlayerMaiScore] = {}

    for player_score in scores:
        is_dx = player_score.song_type == SongType.DX
        played_map[(player_score.song_id, is_dx, int(player_score.song_difficulty))] = player_score

    completed_list: list[tuple[MaiSong, Optional[PlayerMaiScore], int]] = []
    unfinished_list: list[tuple[MaiSong, Optional[PlayerMaiScore], int]] = []
    not_played_list: list[tuple[MaiSong, int]] = []

    plan_val = 0.0
    plan_mode = "ach"  # ach, fc, fs

    plan = plan.upper()
    if plan == "SSS+":
        plan_val = 100.5
    elif plan == "SSS":
        plan_val = 100.0
    elif plan == "SS+":
        plan_val = 99.5
    elif plan == "SS":
        plan_val = 99.0
    elif plan == "S+":
        plan_val = 98.0
    elif plan == "S":
        plan_val = 97.0
    elif "FC" in plan or "AP" in plan:
        plan_mode = "fc"
    elif "FS" in plan or "SYNC" in plan:
        plan_mode = "fs"

    combo_rank_order = ["fc", "fcp", "ap", "app"]
    sync_rank_order = ["fs", "fsp", "fsd", "fsdp"]

    for s, d, is_dx in target_tasks:
        sc = played_map.get((s.id, is_dx, d.difficulty))

        if sc is None:
            not_played_list.append((s, d.difficulty))
            continue

        is_comp = False
        if plan_mode == "ach":
            is_comp = sc.achievements >= plan_val
        elif plan_mode == "fc":
            if sc.fc:
                try:
                    curr_idx = combo_rank_order.index(sc.fc.lower())
                    target_idx = -1
                    if plan.lower() in combo_rank_order:
                        target_idx = combo_rank_order.index(plan.lower())
                    if target_idx != -1:
                        is_comp = curr_idx >= target_idx
                except ValueError:
                    pass
        elif plan_mode == "fs":
            if sc.fs:
                try:
                    curr_idx = sync_rank_order.index(sc.fs.lower())
                    target_idx = -1
                    if plan.lower() in sync_rank_order:
                        target_idx = sync_rank_order.index(plan.lower())
                    if target_idx != -1:
                        is_comp = curr_idx >= target_idx
                except ValueError:
                    pass

        if is_comp:
            completed_list.append((s, sc, d.difficulty))
        else:
            unfinished_list.append((s, sc, d.difficulty))

    return LevelProcessData(
        level=level,
        plan=plan,
        completed=completed_list,
        unfinished=unfinished_list,
        not_played=not_played_list,
        counts={
            "total": len(target_tasks),
            "completed": len(completed_list),
            "unfinished": len(unfinished_list),
            "not_played": len(not_played_list),
        },
    )
