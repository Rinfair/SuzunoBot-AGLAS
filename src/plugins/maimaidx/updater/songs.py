from __future__ import annotations

import json
from asyncio import sleep
from dataclasses import fields
from pathlib import Path

from aiohttp import ClientResponseError, ClientSession
from nonebot import logger
from nonebot_plugin_orm import async_scoped_session
from typing_extensions import TypedDict

from ..config import config
from ..constants import USER_AGENT
from ..database import MaiSongORM
from ..models.song import MaiSong, SongDifficulties

_BASE_SONG_QUERY_URL = "https://maimai.lxns.net/api/v0/maimai/song/{song_id}"
_DIVING_FISH_CHART_STATS_URL = "https://www.diving-fish.com/api/maimaidxprober/chart_stats"

_MUSIC_CHART_PATH = Path(config.static_resource_path) / "music_chart.json"

_music_chart_updated: bool = False


async def update_local_chart_file():
    """
    从水鱼更新 `music_chart.json` 文件
    """
    _MUSIC_CHART_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with ClientSession() as session:
        async with session.get(_DIVING_FISH_CHART_STATS_URL, headers={"User-Agent": USER_AGENT}) as resp:
            resp.raise_for_status()
            content = await resp.json()

    _MUSIC_CHART_PATH.write_text(json.dumps(content, ensure_ascii=False, indent=4), encoding="utf-8")
    logger.info("已更新本地 music_chart.json 文件")

    global _MUSIC_CHART_DATA, _music_chart_updated
    _MUSIC_CHART_DATA = content
    _music_chart_updated = True


if not _MUSIC_CHART_PATH.exists():
    import asyncio

    asyncio.run(update_local_chart_file())

_MUSIC_CHART_DATA: "MusicChart" = json.loads(_MUSIC_CHART_PATH.read_text(encoding="utf-8"))


class MusicChartInfo(TypedDict):
    cnt: float
    diff: str
    """难度标级"""
    fit_diff: float
    """拟合定数"""
    avg: float
    """平均达成率"""
    avg_dx: float
    """平均 DX 分数"""
    std_dev: float
    dist: list[int]
    fc_dist: list[int]


class MusicChart(TypedDict):
    charts: dict[str, list[MusicChartInfo]]
    diff_data: dict[str, dict]


class MusicAliasResponseItem(TypedDict):
    song_id: int
    aliases: list[str]


class LXNSApiAliasResponse(TypedDict):
    aliases: list[MusicAliasResponseItem]


def get_song_fit_diff_from_local(song_id: int, difficulty: int) -> float:
    """
    从 `music_chart.json` 获取拟合定数

    :param song_id: 铺面ID
    :param difficulty: 难度类别
    """
    if not (chart_infos := _MUSIC_CHART_DATA["charts"].get(str(song_id))):
        raise ValueError(f"所请求的铺面 ID: {song_id} 不存在")

    elif len(chart_infos) < difficulty:
        raise ValueError(f"难度 {difficulty} 在铺面 {song_id} 中不存在")

    elif "fit_diff" not in chart_infos[difficulty]:
        raise ValueError(f"难度 {difficulty} 在铺面 {song_id} 中不存在拟合定数")

    return chart_infos[difficulty]["fit_diff"]


async def _update_song_fit_diff(difficulties: SongDifficulties, song_id: int):
    """
    更新曲目的拟合定数

    :param difficulties: 曲目的难度信息
    :param song_id: 曲目 ID
    """
    try:
        for index, difficulty in enumerate(difficulties.standard):
            difficulty.level_fit = get_song_fit_diff_from_local(song_id, index)
        for index, difficulty in enumerate(difficulties.dx):
            difficulty.level_fit = get_song_fit_diff_from_local(song_id + 10000, index)
    except ValueError:
        if _music_chart_updated:
            logger.error(f"曲目 {song_id} 的拟合定数获取失败，跳过该曲目拟合定数设置")
            return

        logger.warning(f"曲目 {song_id} 的拟合定数获取失败，尝试更新本地 chart 文件")
        await update_local_chart_file()
        await sleep(0.1)  # 避免重复请求过快
        try:
            for index, difficulty in enumerate(difficulties.standard):
                difficulty.level_fit = get_song_fit_diff_from_local(song_id, index)
            for index, difficulty in enumerate(difficulties.dx):
                difficulty.level_fit = get_song_fit_diff_from_local(song_id + 10000, index)
        except ValueError:
            logger.error(f"曲目 {song_id} 的拟合定数获取失败，跳过该曲目拟合定数设置")


async def fetch_song_info(song_id: int, interval: float = 0.3) -> MaiSong:
    """
    获取曲目信息

    :param song_id: 曲目 ID
    :param interval: 请求间隔时间

    :raise ValueError: 指定的乐曲信息不存在
    :raise ClientResponseError: 上游服务出现问题
    """
    url = _BASE_SONG_QUERY_URL.format(song_id=song_id)

    try:
        async with ClientSession() as session:
            async with session.get(url, headers={"User-Agent": USER_AGENT}) as resp:
                resp.raise_for_status()
                content = await resp.json()
                await sleep(interval)  # 避免请求过于频繁
    except ClientResponseError as exc:
        if exc.code == 404:
            raise ValueError("指定的乐曲信息不存在!")

        logger.warning(f"上游服务出现了问题无法获取曲目信息: {exc}")
        raise

    song_info_fields = {f.name for f in fields(MaiSong)}
    song_info_dict = {k: v for k, v in content.items() if k in song_info_fields}
    song_info_dict["difficulties"] = SongDifficulties.init_from_dict(content.get("difficulties", {}))

    await _update_song_fit_diff(song_info_dict["difficulties"], song_id)

    song_info = MaiSong(**song_info_dict)

    return song_info


async def update_song_alias_list(db_session: async_scoped_session):
    """
    通过落雪查分器更新别名表
    """
    _BASE_URL = "https://maimai.lxns.net/api/v0/maimai/alias/list"
    async with ClientSession() as session:
        async with session.get(_BASE_URL, headers={"User-Agent": USER_AGENT}) as resp:
            resp.raise_for_status()
            content: LXNSApiAliasResponse = await resp.json()

    from ..database import MaiSongAliasORM

    await MaiSongAliasORM.add_alias_batch(db_session, content["aliases"])


async def update_song_database(db_session: async_scoped_session) -> int:
    """
    通过落雪查分器更新曲目数据库

    :param db_session: 数据库会话对象
    :type db_session: async_scoped_session

    :return: 更新的曲目数量
    :rtype: int
    """
    _BASE_URL = "https://maimai.lxns.net/api/v0/maimai/song/list?notes=true"

    async with ClientSession() as session:
        async with session.get(_BASE_URL, headers={"User-Agent": USER_AGENT}) as resp:
            resp.raise_for_status()
            content = await resp.json()

    songs = content["songs"]
    songs_obj = []
    song_info_fields = {f.name for f in fields(MaiSong)}

    for song in songs:
        song_info_dict = {k: v for k, v in song.items() if k in song_info_fields}
        song_info_dict["difficulties"] = SongDifficulties.init_from_dict(song.get("difficulties", {}))

        # 获取拟合定数
        await _update_song_fit_diff(song_info_dict["difficulties"], song_info_dict["id"])

        song_info = MaiSong(**song_info_dict)
        songs_obj.append(song_info)

    await MaiSongORM.save_song_info_batch(db_session, songs_obj)

    return len(songs_obj)


async def get_plate_data() -> dict:
    """
    获取牌子数据
    """
    _BASE_URL = "https://www.yuzuchan.moe/api/maimaidx/maimaidxplate"

    async with ClientSession() as session:
        async with session.get(_BASE_URL, headers={"User-Agent": USER_AGENT}) as resp:
            resp.raise_for_status()
            content = await resp.json()

    data = content["content"]

    return data
