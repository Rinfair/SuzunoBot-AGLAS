import os
import sys
import time
from contextvars import ContextVar
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from nonebot import logger
from nonebot.adapters import Event
from nonebot.internal.matcher import current_event
from nonebot.log import default_filter, logger_id
from nonebot_plugin_alconna import At
from nonebot_plugin_orm import async_scoped_session

from .config import config
from .storage import MaiSongORM
from .models.song import MaiSong

event_context: ContextVar[Event] = ContextVar("event")


def init_logger():
    console_handler_level = config.log_level

    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)

    log_file_path = f"{log_dir}/{time.strftime('%Y-%m-%d')}.log"

    # 移除 NoneBot 默认的日志处理器
    try:
        logger.remove(logger_id)
        # 添加新的日志处理器
        logger.add(
            sys.stdout,
            level=console_handler_level,
            diagnose=True,
            format="<lvl>[{level}] {function}: {message}</lvl>",
            filter=default_filter,
            colorize=True,
        )

        logger.add(
            log_file_path,
            level="DEBUG",
            format="[{time:YYYY-MM-DD HH:mm:ss}] [{level}] {function}: {message}",
            encoding="utf-8",
            rotation="1 day",
            retention="7 days",
        )
    # 如果遇到其他日志处理器已处理，则跳过
    except ValueError:
        logger.debug("日志处理器已存在，跳过初始化")


def get_version() -> str:
    """
    获取当前版本号

    优先尝试从已安装包中获取版本号, 否则从 `pyproject.toml` 读取
    """
    package_name = "suzunobot-embedded-maimaidx"

    try:
        return version(package_name)
    except PackageNotFoundError:
        pass

    toml_path = os.path.join(os.path.dirname(__file__), "../pyproject.toml")

    if not os.path.isfile(toml_path):
        return "embedded-rikka"

    try:
        if sys.version_info >= (3, 11):
            import tomllib

            with open(toml_path, "rb") as f:
                pyproject_data = tomllib.load(f)

        else:
            import toml

            with open(toml_path, "r", encoding="utf-8") as f:
                pyproject_data = toml.load(f)

        # 返回版本号
        return pyproject_data["tool"]["pdm"]["version"]

    except (FileNotFoundError, KeyError, ModuleNotFoundError):
        return "embedded-rikka"


def is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


async def get_song_by_id_or_alias(session: async_scoped_session, name: str) -> MaiSong:
    """
    通过乐曲 ID/别名 获取乐曲对象

    :param session: 数据库会话对象
    :type session: async_scoped_session
    :param name: 乐曲 ID/名称/别名
    :type name: str
    :return: 乐曲对象
    :rtype: MaiSong

    :raise ValueError: 未找到相关乐曲信息/找到多条乐曲信息
    """
    song_id = int(name) if name.isdigit() else None
    song_name = name if song_id is None else None
    songs = []

    if song_id is not None:
        logger.debug(f"1/2 通过乐曲ID {song_id} 查询乐曲信息...")
        song_id = song_id if song_id < 10000 or song_id > 100000 else song_id % 10000
        try:
            songs = [await MaiSongORM.get_song_info(session, song_id)]
        except ValueError:
            logger.warning("通过乐曲ID获取乐曲对象失败，该ID可能是乐曲标题")
            song_name = str(song_id)

    if song_name is not None and not songs:
        logger.debug(f"1/2 通过乐曲名称/别名 {song_name} 查询乐曲信息...")
        songs = await MaiSongORM.get_song_info_by_name_or_alias(session, song_name)

    if not songs:
        raise ValueError(f"未找到与 '{name}' 相关的乐曲信息！")

    if len(songs) > 1:
        logger.debug("2/2 找到多条乐曲信息，提前返回向用户确定具体乐曲ID")
        contents = [
            f"找到多条与 '{name}' 相关的乐曲信息，请指定你想查询的乐曲ID：",
        ]
        for song in songs:
            contents.append(f"\nID: {song.id} 标题: {song.title} 艺术家: {song.artist}")

        raise ValueError("\n".join(contents))

    logger.debug(f"2/2 乐曲信息查询完毕，{name} -> ID {songs[0].id}")
    return songs[0]


def get_event() -> Event:
    try:
        return event_context.get()
    except LookupError as exc:
        # Provide a clearer error when called outside of an event context
        raise RuntimeError(
            "get_event() called outside of an event context. "
            "Ensure set_ctx(event) has been called in this context before using get_event()."
        ) from exc


def set_ctx(event: Event):
    """
    注册 Nonebot 中的上下文信息
    """
    event_context.set(event)


def reply_user_segment(user_id: str) -> Any:
    """
    群聊中返回 @ 用户段，私聊中返回空字符串，避免私聊发送 At 失败。
    """
    try:
        event = current_event.get()
    except LookupError:
        return ""

    if getattr(event, "message_type", None) == "group":
        return At(flag="user", target=user_id)
    return ""
