"""
舞萌今日运势生成类
"""

import random
from datetime import datetime
from pathlib import Path

from nonebot import logger
from nonebot_plugin_alconna import UniMessage
from nonebot_plugin_alconna.uniseg import At, Image
from nonebot_plugin_orm import get_scoped_session

from ..config import config
from ..database import MaiSongORM

_activates = ["拼机", "推分", "下埋", "打新曲", "开随机段位", "打旧框"]

_TEMPLATE = """今日人品值: {luck_value}
{fortunate_activates}
今日推荐歌曲：
{title}({id})
"""


async def generate_today_fortune(user_id: str) -> UniMessage:
    """
    生成用户的今日运势
    """
    # 确保当日同一用户获取到同一的测评结果
    user_seed = hash(user_id + datetime.strftime(datetime.now(), "%d%m%Y"))
    random.seed(user_seed)

    # 人品值
    luck_value = random.randint(1, 101)

    # 推荐活动
    available_activates = _activates.copy()
    lucky_activates = random.sample(available_activates, k=random.randint(0, len(available_activates)))
    available_activates = [item for item in available_activates if item not in lucky_activates]
    unlucky_activates = random.sample(available_activates, k=random.randint(0, len(available_activates)))
    fortunate_activates = "\n".join(
        [f"宜 {item}" for item in lucky_activates] + [f"忌 {item}" for item in unlucky_activates]
    )

    # 推荐乐曲
    session = get_scoped_session()
    song_ids = await MaiSongORM.get_all_song_ids(session)
    lucky_song_id = random.choice(song_ids)
    lucky_song = await MaiSongORM.get_song_info(session, lucky_song_id)

    # 重置随机种子
    random.seed()

    # 处理乐曲信息
    song_cover = Path(config.static_resource_path) / "mai" / "cover" / f"{lucky_song.id}.png"

    if not song_cover.exists():
        dx_song_id = lucky_song.id + 10000  # DX 版封面
        song_cover = Path(config.static_resource_path) / "mai" / "cover" / f"{dx_song_id}.png"
        if not song_cover.exists():
            logger.warning(f"未找到乐曲 {lucky_song.id} 的封面图片")
            song_cover = Path(config.static_resource_path) / "mai" / "cover" / "0.png"

    response_difficulties_content = []

    if lucky_song.difficulties.standard:
        std_diffs = "/".join([str(diff.level_value) for diff in lucky_song.difficulties.standard])
        response_difficulties_content.append(f"定数: {std_diffs}")

        if lucky_song.difficulties.standard[0].level_fit is not None:
            fit_diffs = "/".join(
                [
                    "{:.2f}".format(diff.level_fit) if diff.level_fit is not None else f"{diff.level}"
                    for diff in lucky_song.difficulties.standard
                ]
            )
            response_difficulties_content.append(f"拟合定数: {fit_diffs}")

    if lucky_song.difficulties.dx:
        dx_diffs = "/".join([str(diff.level_value) for diff in lucky_song.difficulties.dx])
        response_difficulties_content.append(f"定数(DX): {dx_diffs}")

        if lucky_song.difficulties.dx[0].level_fit is not None:
            fit_diffs = "/".join(
                [
                    "{:.2f}".format(diff.level_fit) if diff.level_fit is not None else f"{diff.level}"
                    for diff in lucky_song.difficulties.dx
                ]
            )
            response_difficulties_content.append(f"拟合定数(DX): {fit_diffs}")

    return UniMessage(
        [
            At(flag="user", target=user_id),
            Image(path=song_cover),
            _TEMPLATE.format(
                luck_value=luck_value,
                fortunate_activates=fortunate_activates,
                title=lucky_song.title,
                id=lucky_song.id,
            ),
            "\n".join(response_difficulties_content),
        ]
    )
