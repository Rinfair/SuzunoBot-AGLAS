from __future__ import annotations

import random
import time

from nonebot.adapters.onebot.v11 import ActionFailed, Bot, GroupMessageEvent, Message, MessageEvent, NoticeEvent
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_orm import get_scoped_session

from .commands import (
    about_command,
    help_command,
    ping_command,
    plugins_command,
    poke_notice,
    poke_rank_command,
    select_command,
    status_command,
)
from .service import (
    render_about_message,
    render_help_message,
    render_ping_message,
    render_plugins_message,
    render_status_message,
)
from .storage import get_group_poke_ranking, increment_poke_count


@help_command.handle()
async def handle_help(matcher: Matcher) -> None:
    await matcher.finish(render_help_message())


@about_command.handle()
async def handle_about(matcher: Matcher) -> None:
    await matcher.finish(render_about_message())


@status_command.handle()
async def handle_status(matcher: Matcher) -> None:
    await matcher.finish(render_status_message())


@plugins_command.handle()
async def handle_plugins(matcher: Matcher) -> None:
    await matcher.finish(render_plugins_message())


@ping_command.handle()
async def handle_ping(matcher: Matcher) -> None:
    started = time.perf_counter()
    message = render_ping_message((time.perf_counter() - started) * 1000)
    await matcher.finish(message)


@select_command.handle()
async def handle_select(matcher: Matcher, message: Message = CommandArg()) -> None:
    options = message.extract_plain_text().strip().split()
    if len(options) <= 1:
        await matcher.finish("▿ 帮选 - 参数不足\n选你🐎。")
        return

    choice_seed = random.randint(0, 20)
    if choice_seed == 1:
        await matcher.finish("▾ 帮选\n选你🐎，自己选去。")
        return
    if 16 <= choice_seed <= 18:
        await matcher.finish("▾ 帮选\n我都不选。")
        return
    if choice_seed > 18:
        await matcher.finish("▾ 帮选\n小孩子才做选择，成年人我都要。")
        return

    await matcher.finish(f"▾ 帮选\n我选 {random.choice(options)}。")


async def _bot_can_ban(bot: Bot, group_id: int) -> bool:
    try:
        info = await bot.get_group_member_info(group_id=group_id, user_id=int(bot.self_id), no_cache=True)
    except ActionFailed:
        return False
    except Exception:
        return False
    return info.get("role") in {"owner", "admin"}


@poke_notice.handle()
async def handle_group_poke(bot: Bot, event: NoticeEvent) -> None:
    group_id = getattr(event, "group_id", None)
    user_id = getattr(event, "user_id", None)
    if group_id is None or user_id is None:
        return

    session = get_scoped_session()
    poke_count = await increment_poke_count(session, str(group_id), str(user_id))
    if poke_count == 1:
        await bot.send_group_msg(group_id=int(group_id), message="戳你🐎")
        return
    if poke_count == 2:
        await bot.send_group_msg(group_id=int(group_id), message="一天到晚就知道戳戳戳，戳自己肚皮不行吗？")
        return
    if poke_count == 3:
        await bot.send_group_msg(group_id=int(group_id), message="再戳铃乃就要生气了！")
        return
    if poke_count != 4:
        return

    if await _bot_can_ban(bot, int(group_id)):
        duration = random.randint(60, 600)
        try:
            await bot.set_group_ban(group_id=int(group_id), user_id=int(user_id), duration=duration)
        except ActionFailed:
            pass
        except Exception:
            pass

    await bot.send_group_msg(group_id=int(group_id), message="这么喜欢铃乃骂你吗？请冷静一下哦~")


async def _resolve_group_member_name(bot: Bot, group_id: int, user_id: str) -> str:
    try:
        member = await bot.get_group_member_info(group_id=group_id, user_id=int(user_id), no_cache=True)
    except ActionFailed:
        return user_id
    except Exception:
        return user_id

    card = str(member.get("card") or "").strip()
    nickname = str(member.get("nickname") or "").strip()
    display_name = card or nickname or user_id
    return f"{display_name}({user_id})"


@poke_rank_command.handle()
async def handle_poke_rank(bot: Bot, matcher: Matcher, event: MessageEvent) -> None:
    if not isinstance(event, GroupMessageEvent):
        await matcher.finish("戳一戳排行榜仅支持群聊查看。")
        return

    session = get_scoped_session()
    ranking = await get_group_poke_ranking(session, str(event.group_id))
    if not ranking:
        await matcher.finish("▾ 戳一戳排行榜\n当前统计周期内还没有人戳铃乃。")
        return

    lines = [
        "▾ 戳一戳排行榜",
        "统计周期: 每天 06:00 - 次日 05:59",
    ]
    for index, record in enumerate(ranking, start=1):
        member_name = await _resolve_group_member_name(bot, event.group_id, record.user_id)
        lines.append(f"TOP {index} | {member_name} | {record.poke_count} 次")

    await matcher.finish("\n".join(lines))
