import re
from functools import wraps
from pathlib import Path
from random import choice
from time import perf_counter
from traceback import format_exc
from typing import Literal

from aiohttp.client_exceptions import ClientResponseError
from arclet.alconna import Alconna, AllParam, Args
from maimai_py import LXNSProvider
from nonebot import get_driver, logger
from nonebot.adapters import Event
from nonebot.exception import FinishedException
from nonebot.params import Depends
from nonebot.rule import to_me
from nonebot_plugin_alconna import (
    AlconnaMatch,
    At,
    CommandMeta,
    Match,
    Subcommand,
    UniMessage,
    on_alconna,
)
from nonebot_plugin_alconna.uniseg import Image as UniImage
from nonebot_plugin_orm import async_scoped_session

from .config import config
from .constants import _MAI_VERSION_MAP
from .database import MaiPlayCountORM, MaiSongAliasORM, MaiSongORM, UserBindInfoORM
from .extra_proxy import (
    get_maistatus,
    run_divingfish_import_workflow,
    run_extend_score_workflow,
    run_extend_ticket_workflow,
    run_extent_force_logout,
    run_unlock_workflow,
)
from .functions.analysis import get_player_strength
from .functions.fortunate import generate_today_fortune
from .functions.maistatus import capture_maimai_status_png
from .functions.n50 import get_players_n50
from .functions.process import (
    ProcessDataError,
    get_level_process_data,
    get_plate_process_data,
)
from .functions.recommend_songs import get_player_raise_score_songs
from .functions.song_tags import SONG_TAGS_DATA_AVAILABLE, get_songs_tags
from .models.song import MaiSong
from .painters import (
    DrawScores,
    draw_player_rating_trend,
    draw_player_strength_analysis,
    image_to_bytes,
)
from .painters.process import ProcessPainter
from .renderer import PicRenderer
from .score import (
    DivingFishScoreProvider,
    LXNSScoreProvider,
    MaimaiPyScoreProvider,
    get_divingfish_provider,
    get_lxns_provider,
    get_maimaipy_provider,
)
from .score.providers.maimai import MaimaiPyParams
from .updater.songs import update_song_alias_list
from .utils import get_song_by_id_or_alias, is_float

renderer = PicRenderer()


def _build_song_info_message(user_id: str, song: MaiSong) -> UniMessage:
    """Reuseable builder for song info replies."""

    cover_dir = Path(config.static_resource_path) / "mai" / "cover"
    song_cover = None
    for cover_path in PicRenderer._cover_candidates(cover_dir, song.id):
        if cover_path.exists():
            song_cover = cover_path
            break
    if song_cover is None:
        logger.warning(f"未找到乐曲 {song.id} 的封面图片")
        song_cover = cover_dir / "0.png"

    response_difficulties_content = []

    if song.difficulties.standard:
        std_diffs = "/".join([str(diff.level_value) for diff in song.difficulties.standard])
        response_difficulties_content.append(f"定数: {std_diffs}")

        if song.difficulties.standard[0].level_fit is not None:
            fit_diffs = "/".join(
                [
                    "{:.2f}".format(diff.level_fit) if diff.level_fit is not None else f"{diff.level}"
                    for diff in song.difficulties.standard
                ]
            )
            response_difficulties_content.append(f"拟合定数: {fit_diffs}")

        if SONG_TAGS_DATA_AVAILABLE:
            song_tags_content = []
            tags_expert = get_songs_tags(song.title, "std", "expert")
            tags_master = get_songs_tags(song.title, "std", "master")
            if tags_expert:
                song_tags_content.append(f"{', '.join(tags_expert)}(Expert)")
            if tags_master:
                song_tags_content.append(f"{', '.join(tags_master)}(Master)")
            if len(song.difficulties.standard) == 5:
                tags_remaster = get_songs_tags(song.title, "std", "remaster")
                song_tags_content.append(f"{', '.join(tags_remaster)}(Re:master)" if tags_remaster else "")
            if song_tags_content:
                response_difficulties_content.append("铺面标签: " + "; ".join(song_tags_content))

    if song.difficulties.dx:
        dx_diffs = "/".join([str(diff.level_value) for diff in song.difficulties.dx])
        response_difficulties_content.append(f"定数(DX): {dx_diffs}")

        if song.difficulties.dx[0].level_fit is not None:
            fit_diffs = "/".join(
                [
                    "{:.2f}".format(diff.level_fit) if diff.level_fit is not None else f"{diff.level}"
                    for diff in song.difficulties.dx
                ]
            )
            response_difficulties_content.append(f"拟合定数(DX): {fit_diffs}")

        if SONG_TAGS_DATA_AVAILABLE:
            song_tags_content = []
            tags_expert = get_songs_tags(song.title, "dx", "expert")
            tags_master = get_songs_tags(song.title, "dx", "master")
            if tags_expert:
                song_tags_content.append(f"{', '.join(tags_expert)}(Expert)")
            if tags_master:
                song_tags_content.append(f"{', '.join(tags_master)}(Master)")
            if len(song.difficulties.dx) == 5:
                tags_remaster = get_songs_tags(song.title, "dx", "remaster")
                song_tags_content.append(f"{', '.join(tags_remaster)}(Re:master)" if tags_remaster else "")
            if song_tags_content:
                response_difficulties_content.append("铺面标签(DX): " + "; ".join(song_tags_content))

    return UniMessage(
        [
            At(flag="user", target=user_id),
            UniImage(path=song_cover),
            _MAI_SONG_INFO_TEMPLATE.format(
                title=song.title,
                id=song.id,
                artist=song.artist,
                genre=song.genre,
                bpm=song.bpm,
                version=_MAI_VERSION_MAP.get(song.version // 100, "未知版本"),
            ),
            "\n".join(response_difficulties_content),
        ]
    )


def catch_exception(reply_prefix: str = "发生了未知错误", reply_error: bool = True):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except FinishedException:
                raise
            except Exception as exc:
                logger.error(format_exc())
                reply_message = f"{reply_prefix}: {str(exc)}" if reply_error else reply_prefix
                await UniMessage(reply_message).finish()

        return wrapper

    return decorator


COMMAND_PREFIXES = [".", "/"]

_MAI_SONG_INFO_TEMPLATE = """[舞萌DX] 乐曲信息
{title}({id})
艺术家: {artist}
分类: {genre}
BPM: {bpm}
版本: {version}
"""

_DIFFICULTY_VALUE_MAP = {"BASIC": 0, "ADVANCED": 1, "EXPERT": 2, "MASTER": 3, "REMASTER": 4, "RE:MASTER": 4}

alconna_help = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "help",
        meta=CommandMeta("显示帮助信息", usage=".help"),
    ),
    priority=50,
    block=False,
    rule=to_me(),
)

alconna_bind = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "bind",
        Subcommand("help"),
        Subcommand("lxns", Args["token", str], help_text=".bind lxns <落雪咖啡屋的个人 API 密钥> 绑定落雪咖啡屋查分器"),
        Subcommand(
            "divingfish", Args["token", str], help_text=".bind divingfish <水鱼查分器的成绩导入密钥> 绑定水鱼查分器"
        ),
        meta=CommandMeta("[查分器相关]绑定游戏账号/查分器"),
    ),
    priority=10,
    block=True,
    skip_for_unmatch=False,
    rule=to_me(),
)

alconna_import = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "import",
        Subcommand("divingfish", help_text="导入成绩到水鱼查分器"),
        Args["qr_code", str],
        meta=CommandMeta("[舞萌DX]导入游玩次数或同步成绩到查分器", usage=".import [divingfish] <qr_code>"),
    ),
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_ticket = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "ticket",
        Args["qr_code", str],
        meta=CommandMeta("[舞萌DX]发送六倍票", usage=".ticket <qr_code>"),
    ),
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_logout = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "logout",
        Args["qr_code", str],
        meta=CommandMeta("[舞萌DX]尝试强制登出", usage=".logout <qr_code>"),
    ),
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_unlock = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "unlock",
        Args["qr_code", str],
        meta=CommandMeta("[舞萌DX]解锁新框紫铺", usage=".unlock <qr_code>"),
    ),
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_unbind = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "unbind",
        Args["provider", Literal["all", "lxns", "divingfish", "maimai"]],
        meta=CommandMeta("[查分器相关]解绑查分器账号", usage=".unbind <all|lxns|divingfish|maimai>"),
    ),
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_source = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "source",
        Args["provider", str],
        meta=CommandMeta("[查分器相关]设置默认查分器", usage=".source <lxns|divingfish>"),
    ),
    priority=10,
    block=True,
    aliases={"provider"},
    rule=to_me(),
)

alconna_b50 = on_alconna(
    Alconna(COMMAND_PREFIXES, "b50", meta=CommandMeta("[舞萌DX]生成玩家 Best 50")),
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_ap50 = on_alconna(
    Alconna(COMMAND_PREFIXES, "ap50", meta=CommandMeta("[舞萌DX]生成玩家 ALL PERFECT 50")),
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_r50 = on_alconna(
    Alconna(COMMAND_PREFIXES, "r50", meta=CommandMeta("[舞萌DX]生成玩家 Recent 50 (需绑定落雪查分器)")),
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_pc50 = on_alconna(
    Alconna(
        COMMAND_PREFIXES, "pc50", meta=CommandMeta("[舞萌DX]生成玩家游玩次数 Top-50 (需使用`.import`导入游玩次数)")
    ),
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_n50 = on_alconna(
    Alconna(COMMAND_PREFIXES, "n50", meta=CommandMeta("[舞萌DX]生成玩家基于拟合系数的 Top-50")),
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_minfo = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "minfo",
        Args["name", AllParam(str)],
        meta=CommandMeta("[舞萌DX]获取乐曲信息", usage=".minfo <id|别名>"),
    ),
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_random = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "random",
        Args["filters", AllParam(str)],
        meta=CommandMeta("[舞萌DX]随机抽取乐曲", usage=".random [难度] [等级|定数]"),
    ),
    aliases={"随机乐曲", "随"},
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_alias = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "alias",
        Subcommand("help"),
        Subcommand(
            "add", Args["song_id", int], Args["alias", str], help_text=".alias add <乐曲ID> <别名> 添加乐曲别名"
        ),
        Subcommand("update", help_text=".alias update 更新本地乐曲别名列表"),
        Subcommand("query", Args["name", AllParam(str)], help_text=".alias query <id|别名> 查询该歌曲有什么别名"),
        meta=CommandMeta("[舞萌DX]乐曲别名管理"),
    ),
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_score = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "score",
        Args["name", AllParam(str)],
        meta=CommandMeta("[舞萌DX]获取单曲游玩情况", usage=".score <id|别名>"),
    ),
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_scorelist = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "scorelist",
        Args["arg", str],
        meta=CommandMeta(
            "[舞萌DX]获取指定条件的成绩列表", usage=".scorelist <level|ach|diff>", example=".scorelist ach100.4"
        ),
    ),
    aliases={"scoreslist"},
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_plate_process = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        r"re:([真超檄橙暁晓桃櫻樱紫菫堇白雪輝辉舞霸熊華华爽煌星宙祭祝双宴镜彩])([極极将舞神者]舞?)进度\s?(.+)?",
        meta=CommandMeta(
            "[舞萌DX]牌子进度",
            usage=".真极进度 / .熊将进度 难 / .紫舞舞进度",
        ),
    ),
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_level_process = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        r"re:([0-9]+\+?)\s?([abcdsfxp\+]+)\s?([\u4e00-\u9fa5]+)?进度\s?([0-9]+)?\s?(.+)?",
        meta=CommandMeta(
            "[舞萌DX]等级进度",
            usage=".13+ sss 进度 / .14 ap 进度",
        ),
    ),
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_update = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "update",
        Subcommand("songs", help_text=".update songs 更新乐曲信息数据库"),
        Subcommand("alias", help_text=".update alias 更新乐曲别名列表"),
        Subcommand("chart", help_text=".update chart 更新 music_chart.json 文件"),
        meta=CommandMeta("[舞萌DX]更新乐曲信息或别名列表"),
    ),
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_fortune = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "fortune",
        meta=CommandMeta("[舞萌DX]获取今日上机运势"),
    ),
    aliases={"今日舞萌"},
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_analysis = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "analysis",
        meta=CommandMeta("[舞萌DX]根据 B100 获取玩家成分"),
    ),
    aliases={"底力分析", "成分分析"},
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_trend = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "trend",
        meta=CommandMeta("[舞萌DX]生成玩家 DX Rating 趋势（需绑定落雪查分器）"),
    ),
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_recommend = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "recommend",
        meta=CommandMeta("[舞萌DX]生成随机推分曲目"),
    ),
    aliases={"什么推分", "推分", "推分推荐"},
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_maistatus = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "maistatus",
        meta=CommandMeta("[舞萌DX]检测服务器状态（可选渲染状态页截图）", usage=".maistatus"),
    ),
    aliases={"舞萌状态"},
    priority=10,
    block=True,
    rule=to_me(),
)

alconna_rikka = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "rikka",
        meta=CommandMeta("输出 Rikka 插件信息"),
    ),
    priority=10,
    block=True,
    rule=to_me(),
)


@alconna_help.handle()
async def handle_help(event: Event):
    user_id = event.get_user_id()

    help_text = (
        "Rikka 查分器帮助:\n"
        ".bind <查分器名称> <API密钥> 绑定查分器账号\n"
        ".unbind <查分器名称> 解绑游戏账号/查分器\n"
        ".source <查分器名称> 设置默认查分器\n"
        ".b50 获取玩家 Best 50\n"
        ".ap50 获取玩家 ALL PERFECT 50\n"
        ".r50 获取玩家 Recent 50 (需绑定落雪查分器)\n"
        ".n50 获取玩家拟合系数 Top-50\n"
        f".pc50 生成玩家游玩次数 Top50 （{'当前不可用' if not config.enable_arcade_provider else '需通过 `.import` 导入游戏成绩'})\n"
        ".random 随机获取一首乐曲（可选难度、等级、定数）\n"
        ".minfo <乐曲ID/别名> 获取乐曲信息\n"
        ".alias 管理乐曲别名（添加、查询、更新）\n"
        ".score <乐曲ID/别名> 获取单曲游玩情况\n"
        ".scorelist <level|ach|diff> 获取指定条件的成绩列表\n"
        ".update songs 更新乐曲信息数据库\n"
        ".update alias 更新乐曲别名列表\n"
        ".trend 获取玩家的 DX Rating 趋势 （需绑定落雪查分器）\n"
        f".成分分析 根据 B100 获取玩家成分分析 {'(当前不可用)' if not SONG_TAGS_DATA_AVAILABLE else ''}\n"
        ".今日舞萌 获取今日出勤运势\n"
        ".舞萌状态 检测服务器状态\n"
        f".推分推荐 生成随机推分曲目 {'(当前不可用)' if not SONG_TAGS_DATA_AVAILABLE else ''}\n"
        f".import [divingfish] <qr_code> 导入游玩次数或同步到水鱼 {'当前不可用' if not config.enable_arcade_provider else ''}\n"
        f".ticket <qr_code> 发送六倍票 {'当前不可用' if not config.enable_arcade_provider else ''}\n"
        f".logout <qr_code> 尝试强制登出 {'当前不可用' if not config.enable_arcade_provider else ''}\n"
        f".unlock <qr_code> 解锁新框紫铺 {'当前不可用' if not config.enable_arcade_provider else ''}\n"
    )

    await UniMessage(
        [
            At(flag="user", target=user_id),
            help_text,
        ]
    ).finish()


@alconna_bind.assign("lxns")
@catch_exception("尝试连接到落雪服务器时遇到错误")
async def handle_bind_lxns(
    event: Event,
    db_session: async_scoped_session,
    score_provider: LXNSScoreProvider = Depends(get_lxns_provider),
    token: Match[str] = AlconnaMatch("token"),
):
    user_id = event.get_user_id()

    if not token.available:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "请输入有效的落雪咖啡屋 API 密钥",
            ]
        ).finish()
        return

    lxns_token = token.result

    logger.debug("尝试验证玩家 API 密钥是否正确")
    try:
        player_info = await score_provider.fetch_player_info_by_user_token(lxns_token)
    except ClientResponseError as e:
        logger.warning(f"玩家提供的 API 可能有误: {e.message}")
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "请输入有效的落雪咖啡屋 API 密钥",
            ]
        ).finish()
        return

    await UserBindInfoORM.set_user_friend_code(db_session, user_id, player_info.friend_code)  # type: ignore
    await UserBindInfoORM.set_lxns_api_key(db_session, user_id, lxns_token)

    await UniMessage(
        [
            At(flag="user", target=user_id),
            f"已绑定至游戏账号: {player_info.name} ⭐",
        ]
    ).finish()


@alconna_bind.assign("divingfish")
async def handle_bind_divingfish(
    event: Event,
    db_session: async_scoped_session,
    score_provider: DivingFishScoreProvider = Depends(get_divingfish_provider),
    token: Match[str] = AlconnaMatch("token"),
):
    user_id = event.get_user_id()

    if not token.available:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "请输入有效的水鱼查分器成绩导入密钥",
            ]
        ).finish()
        return

    import_token = token.result

    logger.debug("尝试验证玩家 API 密钥是否正确")
    try:
        player_info = await score_provider.fetch_player_records_by_import_token(import_token)
    except ClientResponseError as e:
        logger.warning(f"玩家提供的 import_token 可能有误: {e.message}")
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "请输入有效的水鱼查分器成绩导入密钥",
            ]
        ).finish()
        return

    await UserBindInfoORM.set_diving_fish_import_token(db_session, user_id, import_token, player_info["username"])

    await UniMessage(
        [
            At(flag="user", target=user_id),
            f"已绑定至水鱼账号: {player_info['username']} ⭐",
        ]
    ).finish()


@alconna_bind.assign("help")
async def handle_bind_help(event: Event):
    user_id = event.get_user_id()

    help_text = (
        "查分器绑定帮助:\n"
        ".bind lxns <落雪咖啡屋的个人 API 密钥> 绑定落雪咖啡屋查分器\n"
        ".bind divingfish <水鱼查分器的成绩导入密钥> 绑定水鱼查分器\n"
    )

    await UniMessage(
        [
            At(flag="user", target=user_id),
            help_text,
        ]
    ).finish()


@alconna_bind.assign("$main")
async def handle_bind_main(event: Event, db_session: async_scoped_session):
    user_id = event.get_user_id()
    user_bind_info = await UserBindInfoORM.get_user_bind_info(db_session, user_id)
    lxns_binded = False
    divingfish_binded = False
    default_source = "未设置"
    if user_bind_info:
        if user_bind_info.lxns_api_key and user_bind_info.friend_code:
            lxns_binded = True
        if user_bind_info.diving_fish_import_token:
            divingfish_binded = True
        if user_bind_info.default_provider:
            default_source = "落雪" if user_bind_info.default_provider == "lxns" else "水鱼"

    lxns = "已绑定" if lxns_binded else "未绑定"
    divingfish = "已绑定" if divingfish_binded else "未绑定"
    user_bind_detail = (
        f"查分器绑定情况:\n- 落雪查分器: {lxns}\n - 水鱼查分器: {divingfish}\n\n当前默认查分源: {default_source}"
    )

    await UniMessage(
        [
            At(flag="user", target=user_id),
            user_bind_detail,
        ]
    ).send()

    return await handle_bind_help(event)


@alconna_import.assign("$main")
@catch_exception("导入游玩次数失败")
async def handle_import_play_count(
    event: Event,
    db_session: async_scoped_session,
    qr_code: Match[str] = AlconnaMatch("qr_code"),
):
    user_id = event.get_user_id()

    if not config.enable_arcade_provider:
        await UniMessage([At(flag="user", target=user_id), "机台源不可用，无法执行该操作"]).finish()
        return

    if not qr_code.available or not qr_code.result:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "请提供二维码内容: .import <qr_code>",
            ]
        ).finish()
        return

    workflow_result = await run_extend_score_workflow(qr_code.result)

    records: list[tuple[int, int, int]] = []
    for item in workflow_result:
        if not isinstance(item, dict):
            continue
        try:
            song_id = int(item["musicId"])
            difficulty = int(item["level"])
            play_count = int(item["playCount"])
        except (KeyError, TypeError, ValueError):
            continue
        records.append((song_id, difficulty, play_count))

    if not records:
        await UniMessage([At(flag="user", target=user_id), "未获取到可用的游玩次数数据"]).finish()
        return

    imported = await MaiPlayCountORM.upsert_user_play_counts(db_session, user_id, records)

    await UniMessage(
        [
            At(flag="user", target=user_id),
            f"已导入 {imported} 条游玩次数记录",
        ]
    ).finish()


@alconna_import.assign("divingfish")
@catch_exception("更新水鱼查分器失败")
async def handle_import_divingfish(
    event: Event, db_session: async_scoped_session, qr_code: Match[str] = AlconnaMatch("qr_code")
):
    user_id = event.get_user_id()

    if not config.enable_arcade_provider:
        await UniMessage([At(flag="user", target=user_id), "机台源不可用，无法执行该操作"]).finish()
        return

    if not qr_code.available or not qr_code.result:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "请提供二维码内容: .import <qr_code>",
            ]
        ).finish()
        return

    # 检查是否绑定了水鱼 Token
    bind_info = await UserBindInfoORM.get_user_bind_info(db_session, user_id)
    if not bind_info or not bind_info.diving_fish_import_token:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "未绑定水鱼查分器导入 Token，请使用 .bind divingfish <Token> 命令绑定",
            ]
        ).finish()
        return  # 防止 mypy 报错 bind_info 可能为 None 的情况

    import_token = bind_info.diving_fish_import_token

    await run_divingfish_import_workflow(qr_code.result, import_token)

    await UniMessage([At(flag="user", target=user_id), "水鱼查分器更新成功！"]).finish()


@alconna_ticket.handle()
@catch_exception("发票失败")
async def handle_ticket(
    event: Event,
    qr_code: Match[str] = AlconnaMatch("qr_code"),
):
    user_id = event.get_user_id()

    if not qr_code.available or not qr_code.result:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "请提供二维码内容: .ticket <qr_code>",
            ]
        ).finish()
        return

    await run_extend_ticket_workflow(qr_code.result)

    await UniMessage([At(flag="user", target=user_id), "已成功发送了 6 倍票"]).finish()


@alconna_logout.handle()
@catch_exception(reply_prefix="强制登出失败")
async def handle_logout(
    event: Event,
    qr_code: Match[str] = AlconnaMatch("qr_code"),
):
    user_id = event.get_user_id()

    if not qr_code.available or not qr_code.result:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "请提供二维码内容: .logout <qr_code>",
            ]
        ).finish()
        return

    await run_extent_force_logout(qr_code.result)
    await UniMessage([At(flag="user", target=user_id), "已尝试强制登出，请尝试重新登录"]).finish()


@alconna_unlock.handle()
@catch_exception()
async def handle_rikka_unlock(
    event: Event,
    qr_code: Match[str] = AlconnaMatch("qr_code"),
):
    user_id = event.get_user_id()

    if not config.enable_arcade_provider:
        await UniMessage([At(flag="user", target=user_id), "机台源不可用，无法执行该操作"]).finish()

    if not qr_code.available or not qr_code.result:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "请提供二维码内容: .unlock <qr_code>",
            ]
        ).finish()
        return

    await run_unlock_workflow(qr_code.result)
    await UniMessage([At(flag="user", target=user_id), "解锁成功！"]).finish()


@alconna_unbind.handle()
async def handle_unbind(
    event: Event,
    db_session: async_scoped_session,
    provider: Match[Literal["all", "lxns", "divingfish", "maimai"]] = AlconnaMatch("provider"),
):
    user_id = event.get_user_id()

    if not provider.available or provider.result not in ["all", "lxns", "divingfish", "maimai"]:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "请输入有效的查分器名称: all, lxns, divingfish 或 maimai",
            ]
        ).finish()
        return

    provider_name = provider.result if provider.result != "all" else None

    try:
        await UserBindInfoORM.unset_user_bind_info(db_session, user_id, provider_name)
    except ValueError as e:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                str(e),
            ]
        ).finish()
        return

    await UniMessage(
        [
            At(flag="user", target=user_id),
            f"已解绑查分器: {provider.result}",
        ]
    ).finish()


@alconna_source.handle()
async def handle_source(
    event: Event,
    db_session: async_scoped_session,
    provider: Match[str] = AlconnaMatch("provider"),
):
    user_id = event.get_user_id()

    if not provider.available or provider.result not in ["lxns", "divingfish"]:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "请输入有效的查分器名称: lxns 或 divingfish",
            ]
        ).finish()
        return

    try:
        await UserBindInfoORM.set_default_provider(db_session, user_id, provider.result)  # type: ignore
    except ValueError as e:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                str(e),
            ]
        ).finish()
        return

    await UniMessage(
        [
            At(flag="user", target=user_id),
            f"已将默认查分器设置为: {provider.result} ⭐",
        ]
    ).finish()


@alconna_b50.handle()
@catch_exception()
async def handle_mai_b50(
    event: Event,
    db_session: async_scoped_session,
    score_provider: MaimaiPyScoreProvider = Depends(get_maimaipy_provider),
):
    user_id = event.get_user_id()
    provider = await MaimaiPyScoreProvider.auto_get_score_provider(db_session, user_id)

    logger.info(f"[{user_id}] 获取玩家 Best50, 查分器类型: {type(provider)}")
    logger.debug(f"[{user_id}] 1/4 获得用户鉴权凭证...")

    identifier = await MaimaiPyScoreProvider.auto_get_player_identifier(db_session, user_id, provider)
    params = score_provider.ParamsType(provider, identifier)

    logger.debug(f"[{user_id}] 2/4 发起 API 请求玩家信息...")
    player_info = await score_provider.fetch_player_info(params)

    logger.debug(f"[{user_id}] 3/4 发起 API 请求玩家 Best50...")
    player_b50 = await score_provider.fetch_player_b50(params)

    logger.debug(f"[{user_id}] 4/4 渲染玩家数据...")
    pic = await renderer.render_mai_player_best50(player_b50, player_info)

    await UniMessage([At(flag="user", target=user_id), UniImage(raw=pic)]).finish()


@alconna_ap50.handle()
@catch_exception()
async def handle_mai_ap50(
    event: Event,
    db_session: async_scoped_session,
    score_provider: MaimaiPyScoreProvider = Depends(get_maimaipy_provider),
):
    user_id = event.get_user_id()
    provider = await MaimaiPyScoreProvider.auto_get_score_provider(db_session, user_id)

    logger.info(f"[{user_id}] 获取玩家 AP50, 查分器类型: {type(score_provider)}")
    logger.debug(f"[{user_id}] 1/4 获得用户鉴权凭证...")

    identifier = await MaimaiPyScoreProvider.auto_get_player_identifier(db_session, user_id, provider)
    params = score_provider.ParamsType(provider, identifier)

    logger.debug(f"[{user_id}] 2/4 发起 API 请求玩家信息...")
    player_info = await score_provider.fetch_player_info(params)

    logger.debug(f"[{user_id}] 3/4 发起 API 请求玩家 AP 50...")
    if isinstance(provider, LXNSProvider):
        user_bind_info = await UserBindInfoORM.get_user_bind_info(db_session, user_id)
        if user_bind_info is None or user_bind_info.lxns_api_key is None:
            await UniMessage("你还没有绑定任何查分器喵，请先用 /bind 绑定一个查分器谢谢喵").finish()
            return  # Avoid TypeError.

        identifier.credentials = user_bind_info.lxns_api_key
        params = score_provider.ParamsType(provider, identifier)

    player_ap50 = await score_provider.fetch_player_ap50(params)

    logger.debug(f"[{user_id}] 4/4 渲染玩家数据...")
    pic = await renderer.render_mai_player_best50(player_ap50, player_info)

    await UniMessage([At(flag="user", target=user_id), UniImage(raw=pic)]).finish()


@alconna_r50.handle()
@catch_exception()
async def handle_mai_r50(
    event: Event, db_session: async_scoped_session, score_provider: LXNSScoreProvider = Depends(get_lxns_provider)
):
    user_id = event.get_user_id()

    logger.info(f"[{user_id}] 获取玩家 Recent 50, 查分器名称: {score_provider.provider}")
    logger.debug(f"[{user_id}] 1/4 尝试从数据库中获取玩家绑定信息...")

    user_bind_info = await UserBindInfoORM.get_user_bind_info(db_session, user_id)

    new_player_friend_code = None
    if user_bind_info is None:
        logger.warning(f"[{user_id}] 未能获取玩家码，数据库中不存在绑定的玩家数据")
        logger.debug(f"[{user_id}] 1/4 尝试通过 QQ 请求玩家数据")
        try:
            player_info = await score_provider.fetch_player_info_by_qq(user_id)
            new_player_friend_code = player_info.friend_code
        except ClientResponseError as e:
            logger.warning(f"[{user_id}] 无法通过 QQ 号请求玩家数据: {e.code}: {e.message}")

            await UniMessage(
                [
                    At(flag="user", target=user_id),
                    "查询 Recent 50 的操作需要绑定落雪查分器喵，还请使用 /bind 指令进行绑定喵呜",
                ]
            ).finish()

            return

    friend_code = new_player_friend_code or user_bind_info.friend_code  # type: ignore
    if not friend_code:
        logger.warning(f"[{user_id}] 无法获取好友码，无法继续查询。")
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "无法获取好友码，请确认已绑定或查分器可用。",
            ]
        ).finish()
        return
    logger.debug(f"[{user_id}] 2/4 发起 API 请求玩家信息...")
    params = score_provider.ParamsType(friend_code=friend_code)
    player_info = await score_provider.fetch_player_info(params)

    logger.debug(f"[{user_id}] 3/4 发起 API 请求玩家 Recent 50...")
    player_r50 = await score_provider.fetch_player_r50(friend_code)

    logger.debug(f"[{user_id}] 4/4 渲染玩家数据...")
    pic = await renderer.render_mai_player_scores(player_r50, player_info, title="Recent 50")

    await UniMessage([At(flag="user", target=user_id), UniImage(raw=pic)]).finish()


@alconna_pc50.handle()
@catch_exception()
async def handle_pc50(
    event: Event,
    db_session: async_scoped_session,
    score_provider: MaimaiPyScoreProvider = Depends(get_maimaipy_provider),
):
    user_id = event.get_user_id()
    provider = await MaimaiPyScoreProvider.auto_get_score_provider(db_session, user_id)

    if not config.enable_arcade_provider:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "管理员未启用pc数查询喵呜",
            ]
        ).finish()

    logger.info(f"[{user_id}] 获取玩家 PC50, 查分器类型: {type(provider)}")

    logger.debug(f"[{user_id}] 1/4 获得用户鉴权凭证...")

    identifier = await MaimaiPyScoreProvider.auto_get_player_identifier(db_session, user_id, provider)
    params = score_provider.ParamsType(provider, identifier)

    logger.debug(f"[{user_id}] 2/4 发起 API 请求玩家信息...")
    player_info = await score_provider.fetch_player_info(params)

    logger.debug(f"[{user_id}] 3/4 发起 API 请求玩家所有成绩...")
    if isinstance(provider, LXNSProvider):
        user_bind_info = await UserBindInfoORM.get_user_bind_info(db_session, user_id)
        if user_bind_info is None or user_bind_info.lxns_api_key is None:
            await UniMessage("你还没有绑定任何查分器喵，请先用 /bind 绑定一个查分器谢谢喵").finish()
            return  # Avoid TypeError.

        identifier.credentials = user_bind_info.lxns_api_key
        params = score_provider.ParamsType(provider, identifier)

    player_scores = await score_provider.fetch_player_pc50(params)

    logger.debug(f"[{user_id}] 4/4 渲染玩家数据...")
    pic = await renderer.render_mai_player_best50(player_scores, player_info)

    await UniMessage([At(flag="user", target=user_id), UniImage(raw=pic)]).finish()


@alconna_n50.handle()
@catch_exception()
async def handle_n50(
    event: Event,
    db_session: async_scoped_session,
    score_provider: MaimaiPyScoreProvider = Depends(get_maimaipy_provider),
):
    user_id = event.get_user_id()
    provider = await MaimaiPyScoreProvider.auto_get_score_provider(db_session, user_id)

    logger.info(f"[{user_id}] 获取玩家 N50, 查分器类型: {type(provider)}")
    logger.debug(f"[{user_id}] 1/5 获得用户鉴权凭证...")

    identifier = await MaimaiPyScoreProvider.auto_get_player_identifier(db_session, user_id, provider)
    params = score_provider.ParamsType(provider, identifier)

    logger.debug(f"[{user_id}] 2/5 发起 API 请求玩家信息...")
    player_info = await score_provider.fetch_player_info(params)

    logger.debug(f"[{user_id}] 3/5 发起 API 请求玩家所有成绩")
    if isinstance(provider, LXNSProvider):
        user_bind_info = await UserBindInfoORM.get_user_bind_info(db_session, user_id)
        if user_bind_info is None or user_bind_info.lxns_api_key is None:
            await UniMessage("你还没有绑定任何查分器喵，请先用 /bind 绑定一个查分器谢谢喵").finish()
            return  # Avoid TypeError.

        identifier.credentials = user_bind_info.lxns_api_key
        params = score_provider.ParamsType(provider, identifier)
    player_scores = await score_provider.fetch_player_scoreslist(params)

    logger.debug(f"[{user_id}] 4/5 计算 N50...")
    player_n50 = get_players_n50(player_scores)
    player_info.rating = player_n50.rating

    logger.debug(f"[{user_id}] 5/5 渲染玩家数据...")
    pic = await renderer.render_mai_player_best50(player_n50, player_info, calc_song_level_value=False)

    await UniMessage([At(flag="user", target=user_id), UniImage(raw=pic)]).finish()


@alconna_minfo.handle()
@catch_exception()
async def handle_minfo(
    event: Event,
    db_session: async_scoped_session,
    name: Match[UniMessage] = AlconnaMatch("name"),
):
    user_id = event.get_user_id()

    if not name.available:
        await UniMessage([At(flag="user", target=user_id), "请输入有效的乐曲ID/名称/别名！"]).finish()

    raw_query = name.result.extract_plain_text()
    logger.info(f"[{user_id}] 查询乐曲信息, 查询内容: {raw_query}")

    logger.debug(f"[{user_id}] 1/4 通过乐曲ID/别名查询乐曲信息...")
    try:
        song = await get_song_by_id_or_alias(db_session, raw_query)
    except ValueError as e:
        await UniMessage([At(flag="user", target=user_id), str(e)]).finish()
        return

    logger.debug(f"[{user_id}] 2/2 构建乐曲信息模板...")
    response_content = _build_song_info_message(user_id, song)

    await response_content.finish()


@alconna_random.handle()
@catch_exception()
async def handle_random(
    event: Event,
    db_session: async_scoped_session,
    filters: Match[UniMessage] = AlconnaMatch("filters"),
):
    user_id = event.get_user_id()

    raw_filters = filters.result.extract_plain_text().strip() if filters.available else ""
    tokens = [tok for tok in raw_filters.split() if tok]

    if len(tokens) > 2:
        await UniMessage([At(flag="user", target=user_id), "参数过多，最多填写难度与等级/定数两个条件哦~"]).finish()
        return

    diff_value = None
    diff_name = None
    level_value = None
    level_const = None
    invalid_tokens: list[str] = []

    for tok in tokens:
        up_tok = tok.upper()
        up_tok = "REMASTER" if up_tok == "RE:MASTER" else up_tok
        if up_tok in _DIFFICULTY_VALUE_MAP:
            if diff_value is not None:
                invalid_tokens.append(tok)
                continue
            diff_value = _DIFFICULTY_VALUE_MAP[up_tok]
            diff_name = up_tok
            continue

        if re.fullmatch(r"\d+\+?", tok):
            if level_value is not None:
                invalid_tokens.append(tok)
                continue
            level_value = tok
            continue

        if "." in tok and re.fullmatch(r"\d+(?:\.\d+)?", tok):
            if level_const is not None:
                invalid_tokens.append(tok)
                continue
            try:
                level_const = float(tok)
            except ValueError:
                invalid_tokens.append(tok)
            continue

        invalid_tokens.append(tok)

    if invalid_tokens:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                f"以下参数无法识别: {' '.join(invalid_tokens)}，请使用难度(BASIC~RE:MASTER)、等级(如12+)或定数(如12.7)重试~",
            ]
        ).finish()
        return

    logger.info(f"[{user_id}] 随机抽取乐曲, 条件 diff={diff_name}, level={level_value}, const={level_const}")

    song_ids = await MaiSongORM.get_all_song_ids(db_session)
    songs = await MaiSongORM.get_songs_info_by_ids(db_session, list(song_ids))

    def match_song(song: MaiSong) -> bool:
        candidates = list(song.difficulties.standard) + list(song.difficulties.dx)
        for d in candidates:
            if diff_value is not None and d.difficulty != diff_value:
                continue
            if level_value and d.level != level_value:
                continue
            if level_const is not None and abs(d.level_value - level_const) > 1e-6:
                continue
            return True
        return False

    filtered_songs = [s for s in songs if match_song(s)]

    if not filtered_songs:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "未找到符合条件的乐曲喵，试试放宽条件再来一次吧~",
            ]
        ).finish()
        return

    song = choice(filtered_songs)
    response = _build_song_info_message(user_id, song)

    await response.finish()


@alconna_alias.assign("update")
async def handle_alias_update(
    event: Event,
    db_session: async_scoped_session,
):
    user_id = event.get_user_id()
    nb_config = get_driver().config

    if user_id not in nb_config.superusers:
        await UniMessage("更新乐曲别名需要管理员权限哦").finish()

    logger.info(f"[{user_id}] 更新乐曲别名列表")

    await update_song_alias_list(db_session)

    logger.info(f"[{user_id}] 乐曲别名列表更新完成")

    await UniMessage(
        [
            At(flag="user", target=user_id),
            "乐曲别名列表已更新完成 ⭐",
        ]
    ).finish()


@alconna_alias.assign("add")
async def handle_alias_add(
    event: Event,
    db_session: async_scoped_session,
    name: Match[str] = AlconnaMatch("alias"),
    song_id: Match[int] = AlconnaMatch("song_id"),
):
    user_id = event.get_user_id()

    if config.add_alias_need_admin:
        nb_config = get_driver().config

        if user_id not in nb_config.superusers:
            await UniMessage("更新乐曲别名需要管理员权限哦").finish()

    logger.info(f"[{user_id}] 添加乐曲别名, 乐曲ID: {song_id.result}, 别名: {name.result}")

    await MaiSongAliasORM.add_custom_alias(db_session, song_id.result, name.result)

    await UniMessage(
        [
            At(flag="user", target=user_id),
            f"已为乐曲 ID {song_id.result} 添加别名: {name.result} ⭐",
        ]
    ).finish()


@alconna_alias.assign("query")
async def handle_alias_query(
    event: Event,
    db_session: async_scoped_session,
    name: Match[UniMessage] = AlconnaMatch("name"),
):
    user_id = event.get_user_id()

    if not name.available:
        await UniMessage([At(flag="user", target=user_id), "请输入有效的乐曲ID/名称/别名！"]).finish()

    raw_query = name.result.extract_plain_text()

    logger.info(f"[{user_id}] 查询乐曲别名, 查询内容: {raw_query}")

    logger.debug(f"[{user_id}] 1/4 通过乐曲ID/别名查询乐曲信息...")
    try:
        song = await get_song_by_id_or_alias(db_session, raw_query)
    except ValueError as e:
        await UniMessage([At(flag="user", target=user_id), str(e)]).finish()
        return

    logger.debug(f"[{user_id}] 2/4 获取乐曲别名列表...")
    aliases = await MaiSongAliasORM.get_aliases(db_session, song.id)

    logger.debug(f"[{user_id}] 3/4 构建乐曲别名模板...")

    if not aliases:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                f"乐曲 ID {song.id} ('{song.title}') 暂无别名记录！",
            ]
        ).finish()
        return

    alias_list_content = ", ".join(aliases)
    await UniMessage(
        [
            At(flag="user", target=user_id),
            f"乐曲 ID {song.id} ('{song.title}') 的别名列表如下：\n{alias_list_content}",
        ]
    ).finish()


@alconna_alias.assign("help")
async def handle_alias_help(event: Event):
    user_id = event.get_user_id()

    help_text = (
        "乐曲别名管理帮助:\n"
        ".alias add <乐曲ID> <别名> 添加乐曲别名\n"
        ".alias update 更新本地乐曲别名列表\n"
        ".alias query <id|别名> 查询该歌曲有什么别名\n"
    )

    await UniMessage(
        [
            At(flag="user", target=user_id),
            help_text,
        ]
    ).finish()


@alconna_alias.assign("$main")
async def handle_alias_main(event: Event):
    return await handle_alias_help(event)


@alconna_score.handle()
@catch_exception()
async def handle_score(
    event: Event,
    db_session: async_scoped_session,
    name: Match[UniMessage] = AlconnaMatch("name"),
    score_provider: MaimaiPyScoreProvider = Depends(get_maimaipy_provider),
):
    user_id = event.get_user_id()

    if not name.available:
        await UniMessage([At(flag="user", target=user_id), "请输入有效的乐曲ID/名称/别名！"]).finish()

    raw_query = name.result.extract_plain_text()
    logger.info(f"[{user_id}] 查询单曲游玩情况, 查询内容: {raw_query}")

    logger.debug(f"[{user_id}] 1/5 通过乐曲ID/别名查询乐曲信息...")
    try:
        song = await get_song_by_id_or_alias(db_session, raw_query)
    except ValueError as e:
        await UniMessage([At(flag="user", target=user_id), str(e)]).finish()
        return

    logger.debug(f"[{user_id}] 2/5 推断获取的是 DX 铺面还是标准铺面")
    if raw_query.isdigit():
        if int(raw_query) > 10000 or not song.difficulties.standard:
            is_dx = True
        else:
            is_dx = False
    else:
        is_dx = len(song.difficulties.dx) > 0
    logger.debug(f"[{user_id}] 2/5 推断为 {'DX' if is_dx else '标准'} 铺面")

    logger.debug(f"[{user_id}] 3/5 获得用户鉴权凭证...")
    provider = await MaimaiPyScoreProvider.auto_get_score_provider(db_session, user_id)
    identifier = await MaimaiPyScoreProvider.auto_get_player_identifier(db_session, user_id, provider)
    params = score_provider.ParamsType(provider, identifier)

    logger.debug(f"[{user_id}] 4/5 发起 API 请求玩家信息...")
    scores = await score_provider.fetch_player_minfo(params, song.id, "dx" if is_dx else "standard")

    if not scores:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                f"未找到乐曲 '{song.title}' 的游玩记录喵~不如先去挑战一下吧~",
            ]
        ).finish()
        return

    logger.debug(f"[{user_id}] 5/5 渲染玩家数据...")
    pic = await renderer.render_mai_player_song_info(song, scores)

    await UniMessage([At(flag="user", target=user_id), UniImage(raw=pic)]).finish()


@alconna_scorelist.handle()
@catch_exception()
async def handle_scorelist(
    event: Event,
    db_session: async_scoped_session,
    arg: Match[str] = AlconnaMatch("arg"),
    score_provider: MaimaiPyScoreProvider = Depends(get_maimaipy_provider),
):
    user_id = event.get_user_id()

    if not arg.available or not arg.result:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                (
                    ".scorelist 使用帮助\n"
                    ".scorelist <level> 获取指定等级的成绩列表\n"
                    ".scorelist ach<float> 获取指定达成率的成绩列表\n"
                    ".scorelist <diff> 获取指定铺面难度的成绩列表\n"
                    "eg.\n"
                    ".scorelist 12+\n"
                    ".scorelist ach100.8"
                    ".scorelist expert"
                ),
            ]
        ).finish()

    raw_query = arg.result
    logger.info(f"[{user_id}] 查询指定条件的成绩列表, 查询内容: {raw_query}")
    level = None
    ach = None
    diff = None
    if raw_query.isdigit() or (raw_query.endswith("+") and raw_query[:-1].isdigit()):
        level = raw_query
        title = f"{level} 成绩列表"
    elif raw_query.startswith("ach") and is_float(raw_query[3:]):
        ach = float(raw_query[3:])
        title = f"达成率 {ach} 成绩列表"
    elif raw_query.upper() in ["BASIC", "ADVANCED", "EXPERT", "MASTER", "REMASTER", "RE:MASTER"]:
        diff = raw_query.upper()
        diff = "REMASTER" if diff == "RE:MASTER" else diff
        title = f"铺面等级 {diff} 成绩列表"
    else:
        await UniMessage([At(flag="user", target=user_id), "命令格式错误，请检查后重新输入！"]).finish()
        return

    logger.debug(f"[{user_id}] 1/4 获得用户鉴权凭证...")
    provider = await MaimaiPyScoreProvider.auto_get_score_provider(db_session, user_id)
    identifier = await MaimaiPyScoreProvider.auto_get_player_identifier(
        db_session, user_id, provider, use_personal_api=True
    )
    params = score_provider.ParamsType(provider, identifier)
    logger.debug(f"[{user_id}] 1/4 鉴权参数: {params}")

    logger.debug(f"[{user_id}] 2/4 发起 API 请求玩家信息...")
    player_info = await score_provider.fetch_player_info(params)

    logger.debug(f"[{user_id}] 3/4 发起 API 请求玩家全部成绩...")
    scores = await score_provider.fetch_player_scoreslist(params, level, ach, diff)  # type: ignore

    if not scores:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "呜呜，未找到符合条件的游玩记录喵",
            ]
        ).finish()
        return

    logger.debug(f"[{user_id}] 4/4 渲染玩家数据...")
    pic = await renderer.render_mai_player_scores(scores[:50], player_info, title)

    await UniMessage([At(flag="user", target=user_id), UniImage(raw=pic)]).finish()


@alconna_plate_process.handle()
@catch_exception()
async def handle_plate_process(
    event: Event,
    db_session: async_scoped_session,
    score_provider: MaimaiPyScoreProvider = Depends(get_maimaipy_provider),
):
    user_id = event.get_user_id()

    raw_text = event.get_plaintext().strip()
    for p in COMMAND_PREFIXES:
        if raw_text.startswith(p):
            raw_text = raw_text[len(p) :]
            break

    m = re.match(
        r"^([真超檄橙暁晓桃櫻樱紫菫堇白雪輝辉舞霸熊華华爽煌星宙祭祝双宴镜彩])([極极将舞神者]舞?)进度\s?(.+)?$",
        raw_text,
    )
    if not m:
        await UniMessage([At(flag="user", target=user_id), "命令解析失败，请检查输入格式"]).finish()
        return

    ver_char, plan, extra_text = m.group(1), m.group(2), (m.group(3) or "")
    use_difficult = "难" in extra_text

    if f"{ver_char}{plan}" == "真将":
        await UniMessage([At(flag="user", target=user_id), "真系没有真将哦"]).finish()
        return

    logger.info(f"[{user_id}] 查询牌子进度: {ver_char}{plan} {'难' if use_difficult else ''}")

    logger.debug(f"[{user_id}] 1/3 获得用户鉴权凭证...")
    provider = await MaimaiPyScoreProvider.auto_get_score_provider(db_session, user_id)
    identifier = await MaimaiPyScoreProvider.auto_get_player_identifier(
        db_session, user_id, provider, use_personal_api=True
    )

    songs = list(MaiSongORM._cache.values())
    if not songs:
        await MaiSongORM.refresh_cache(db_session)
        songs = list(MaiSongORM._cache.values())

    logger.debug(f"[{user_id}] 2/3 发起 API 请求玩家所有成绩")
    scores = await score_provider.fetch_player_scoreslist(
        MaimaiPyParams(score_provider=provider, identifier=identifier)
    )
    try:
        data = get_plate_process_data(songs, scores, ver_char, plan)
    except ProcessDataError as e:
        await UniMessage([At(flag="user", target=user_id), str(e)]).finish()
        return

    logger.debug(f"[{user_id}] 3/3 渲染玩家数据...")
    img = ProcessPainter(data).draw_plate(use_difficult=use_difficult)
    await UniMessage([At(flag="user", target=user_id), UniImage(raw=img.getvalue())]).finish()


@alconna_level_process.handle()
@catch_exception()
async def handle_level_process(
    event: Event,
    db_session: async_scoped_session,
    score_provider: MaimaiPyScoreProvider = Depends(get_maimaipy_provider),
):
    user_id = event.get_user_id()

    raw_text = event.get_plaintext().strip()
    for p in COMMAND_PREFIXES:
        if raw_text.startswith(p):
            raw_text = raw_text[len(p) :]
            break

    m = re.match(r"^([0-9]+\+?)\s?([abcdsfxp\+]+)\s?([\u4e00-\u9fa5]+)?进度\s?([0-9]+)?\s?(.+)?$", raw_text)
    if not m:
        await UniMessage([At(flag="user", target=user_id), "命令解析失败，请检查输入格式"]).finish()
        return

    raw_level = m.group(1)
    raw_plan = m.group(2)

    logger.info(f"[{user_id}] 查询等级进度: {raw_level} {raw_plan}")

    logger.debug(f"[{user_id}] 1/3 获得用户鉴权凭证...")
    provider = await MaimaiPyScoreProvider.auto_get_score_provider(db_session, user_id)
    identifier = await MaimaiPyScoreProvider.auto_get_player_identifier(
        db_session, user_id, provider, use_personal_api=True
    )

    songs = list(MaiSongORM._cache.values())
    if not songs:
        await MaiSongORM.refresh_cache(db_session)
        songs = list(MaiSongORM._cache.values())

    logger.debug(f"[{user_id}] 2/3 发起 API 请求玩家所有成绩")
    scores = await score_provider.fetch_player_scoreslist(
        MaimaiPyParams(score_provider=provider, identifier=identifier)
    )
    try:
        data = get_level_process_data(songs, scores, raw_level, raw_plan)
    except ProcessDataError as e:
        await UniMessage([At(flag="user", target=user_id), str(e)]).finish()
        return

    logger.debug(f"[{user_id}] 3/3 渲染玩家数据...")
    img = ProcessPainter(data).draw_level()
    await UniMessage([At(flag="user", target=user_id), UniImage(raw=img.getvalue())]).finish()


@alconna_update.assign("songs")
@catch_exception()
async def handle_update_songs(
    event: Event,
    db_session: async_scoped_session,
):
    user_id = event.get_user_id()
    nb_config = get_driver().config

    if user_id not in nb_config.superusers:
        await UniMessage("更新乐曲信息需要管理员权限哦").finish()

    logger.info(f"[{user_id}] 更新乐曲信息数据库")

    from .updater.songs import update_song_database

    updated_count = await update_song_database(db_session)

    logger.info(f"[{user_id}] 乐曲信息数据库更新完成，共更新 {updated_count} 首乐曲")

    await UniMessage(
        [
            At(flag="user", target=user_id),
            f"乐曲信息数据库已更新完成，共更新 {updated_count} 首乐曲 ⭐",
        ]
    ).finish()


@alconna_update.assign("alias")
async def handle_update_aliases(
    event: Event,
    db_session: async_scoped_session,
):
    await handle_alias_update(event, db_session)


@alconna_update.assign("chart")
async def handle_update_chart(event: Event):
    from .updater.songs import update_local_chart_file

    await update_local_chart_file()

    await UniMessage(
        [
            At(flag="user", target=event.get_user_id()),
            "music_chart.json 文件已更新完成⭐",
        ]
    ).finish()


@alconna_fortune.handle()
async def handle_fortune(
    event: Event,
):
    user_id = event.get_user_id()

    logger.info(f"[{user_id}] 获取今日舞萌运势")

    fortune_message = await generate_today_fortune(user_id)

    await fortune_message.finish()


@alconna_analysis.handle()
@catch_exception()
async def handle_analysis(
    db_session: async_scoped_session,
    event: Event,
    score_provider: MaimaiPyScoreProvider = Depends(get_maimaipy_provider),
):
    user_id = event.get_user_id()

    if not SONG_TAGS_DATA_AVAILABLE:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "管理员未配置乐曲标签，无法使用此功能喵",
            ]
        ).finish()
        return

    provider = await MaimaiPyScoreProvider.auto_get_score_provider(db_session, user_id)

    logger.info(f"[{user_id}] 获取玩家底力表, 查分器类型: {type(provider)}")
    logger.debug(f"[{user_id}] 1/4 获得用户鉴权凭证...")

    identifier = await MaimaiPyScoreProvider.auto_get_player_identifier(db_session, user_id, provider)
    params = score_provider.ParamsType(provider, identifier)

    logger.debug(f"[{user_id}] 2/4 发起 API 请求玩家所有成绩")
    if isinstance(provider, LXNSProvider):
        user_bind_info = await UserBindInfoORM.get_user_bind_info(db_session, user_id)
        if user_bind_info is None or user_bind_info.lxns_api_key is None:
            await UniMessage("你还没有绑定任何查分器喵，请先用 /bind 绑定一个查分器谢谢喵").finish()
            return  # Avoid TypeError.

        identifier.credentials = user_bind_info.lxns_api_key
        params = score_provider.ParamsType(provider, identifier)
    player_scores = await score_provider.fetch_player_scoreslist(params)

    logger.debug(f"[{user_id}] 3/4 计算玩家成分")
    player_scores.sort(key=lambda x: x.dx_rating, reverse=True)
    player_scores = player_scores[:100]
    player_strength = get_player_strength(player_scores)

    logger.debug(f"[{user_id}] 4/4 渲染玩家数据...")
    pic = draw_player_strength_analysis(player_strength)
    byte = image_to_bytes(pic)

    await UniMessage([At(flag="user", target=user_id), UniImage(raw=byte)]).finish()


@alconna_trend.handle()
@catch_exception()
async def handle_trend(
    db_session: async_scoped_session,
    event: Event,
    score_provider: LXNSScoreProvider = Depends(get_lxns_provider),
):
    user_id = event.get_user_id()

    logger.info(f"[{user_id}] 获取玩家 Rating 趋势, 查分器类型: {type(score_provider)}")
    logger.debug(f"[{user_id}] 1/3 获得用户鉴权凭证...")

    user_bind_info = await UserBindInfoORM.get_user_bind_info(db_session, user_id)

    new_player_friend_code = None
    if user_bind_info is None:
        logger.warning(f"[{user_id}] 未能获取玩家码，数据库中不存在绑定的玩家数据")
        logger.debug(f"[{user_id}] 1/3 尝试通过 QQ 请求玩家数据")
        try:
            player_info = await score_provider.fetch_player_info_by_qq(user_id)
            new_player_friend_code = player_info.friend_code
        except ClientResponseError as e:
            logger.warning(f"[{user_id}] 无法通过 QQ 号请求玩家数据: {e.code}: {e.message}")

            await UniMessage(
                [
                    At(flag="user", target=user_id),
                    "查询 Rating 趋势的操作需要绑定落雪查分器喵，还请使用 /bind 指令进行绑定喵呜",
                ]
            ).finish()

            return

    friend_code = new_player_friend_code or user_bind_info.friend_code  # type: ignore
    if not friend_code:
        logger.warning(f"[{user_id}] 无法获取好友码，无法继续查询。")
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "无法获取好友码，请确认已绑定或查分器可用。",
            ]
        ).finish()
        return

    logger.debug(f"[{user_id}] 2/3 发起 API 请求玩家 Trend 趋势")

    trends = await score_provider.fetch_player_trend(friend_code)

    if len(trends) < 5:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "玩家 Rating 记录数据太少，无法进行渲染",
            ]
        ).finish()

    logger.debug(f"[{user_id}] 3/3 渲染玩家数据...")
    pic = draw_player_rating_trend(trends)
    byte = image_to_bytes(pic)

    await UniMessage([At(flag="user", target=user_id), UniImage(raw=byte)]).finish()


@alconna_recommend.handle()
@catch_exception()
async def handle_recommend(
    db_session: async_scoped_session,
    event: Event,
    score_provider: MaimaiPyScoreProvider = Depends(get_maimaipy_provider),
):
    user_id = event.get_user_id()
    provider = await MaimaiPyScoreProvider.auto_get_score_provider(db_session, user_id)

    logger.info(f"[{user_id}] 获取玩家推分推荐, 查分器类型: {type(provider)}")
    logger.debug(f"[{user_id}] 1/4 获得用户鉴权凭证...")

    identifier = await MaimaiPyScoreProvider.auto_get_player_identifier(db_session, user_id, provider)
    params = score_provider.ParamsType(provider, identifier)

    logger.debug(f"[{user_id}] 2/4 发起 API 请求玩家所有成绩")
    if isinstance(provider, LXNSProvider):
        user_bind_info = await UserBindInfoORM.get_user_bind_info(db_session, user_id)
        if user_bind_info is None or user_bind_info.lxns_api_key is None:
            await UniMessage("你还没有绑定任何查分器喵，请先用 /bind 绑定一个查分器谢谢喵").finish()
            return  # Avoid TypeError.

        identifier.credentials = user_bind_info.lxns_api_key
        params = score_provider.ParamsType(provider, identifier)
    player_scores = await score_provider.fetch_player_scoreslist(params)

    logger.debug(f"[{user_id}] 3/4 计算推分推荐...")
    st = perf_counter()
    player_scores.sort(key=lambda x: x.dx_rating, reverse=True)
    min_dx_score = player_scores[:50][-1].dx_rating
    recommend_songs = get_player_raise_score_songs(player_scores, round(min_dx_score))
    et = perf_counter()
    logger.debug(f"[{user_id}] 3/4 计算推分推荐用时 {(et - st):.3f}s")

    logger.debug(f"[{user_id}] 4/4 渲染玩家数据...")
    pic = DrawScores().draw_rise(recommend_songs, round(min_dx_score))
    byte = image_to_bytes(pic)

    await UniMessage([At(flag="user", target=user_id), UniImage(raw=byte)]).finish()


@alconna_maistatus.handle()
@catch_exception(reply_prefix="获取舞萌状态失败")
async def handle_maistatus(event: Event):
    user_id = event.get_user_id()

    logger.debug("正在获取舞萌服务器状态...")
    try:
        status_text = await get_maistatus()
    except Exception as e:
        status_text = f"服务器状态检测失败：{e}"

    await UniMessage([At(flag="user", target=user_id), status_text]).send()

    if not config.maistatus_url:
        return

    logger.debug("正在尝试获取舞萌状态截图...")
    try:
        st = perf_counter()
        png = await capture_maimai_status_png(config.maistatus_url)
        et = perf_counter()
        render_time_message = f"渲染用时 {et - st:.2f} 秒"
    except Exception as e:
        await UniMessage([At(flag="user", target=user_id), f"状态页截图渲染失败：{e}"]).finish()
        return

    await UniMessage([At(flag="user", target=user_id), UniImage(raw=png), render_time_message]).finish()


@alconna_rikka.handle()
async def handle_rikka(db_session: async_scoped_session, event: Event):
    from .utils import get_version

    version = get_version()
    total_songs_count = len(await MaiSongORM.get_all_song_ids(db_session))

    message = (
        "Rikka 插件信息\n"
        f"插件版本: {version}\n"
        f"Bot 乐曲数量: {total_songs_count}\n"
        f"机台源支持: {'已启用' if config.enable_arcade_provider else '未启用'}\n"
        f"标签数据: {'已启用' if SONG_TAGS_DATA_AVAILABLE else '未启用'}\n"
        f"状态页支持: {'已启用' if config.maistatus_url else '未启用'}\n"
    )

    await UniMessage(message).send()

    await handle_help(event)
