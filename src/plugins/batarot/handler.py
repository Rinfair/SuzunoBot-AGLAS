from __future__ import annotations

from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageEvent
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from .commands import tarot, tarot_fortune, tarot_reading, tarot_spread
from .config import config
from .service import build_fortune_reply, build_reading_reply, build_spread_reply, build_tarot_reply


def _build_forward_nodes(self_id: str, messages: list[Message]) -> list[dict]:
    return [
        {
            "type": "node",
            "data": {
                "name": "塔罗占卜",
                "uin": self_id,
                "content": message,
            },
        }
        for message in messages
    ]


@tarot.handle()
async def handle_tarot(matcher: Matcher) -> None:
    await matcher.finish(build_tarot_reply())


@tarot_spread.handle()
async def handle_tarot_spread(bot: Bot, event: MessageEvent) -> None:
    _, messages = build_spread_reply()
    if isinstance(event, GroupMessageEvent) and not config.batarot_forward_mode:
        try:
            await bot.send_group_forward_msg(
                group_id=event.group_id,
                messages=_build_forward_nodes(str(event.self_id), messages),
            )
        except Exception as exc:
            logger.warning("牌阵合并转发失败，回退逐条发送: {}", exc)
            for message in messages:
                await bot.send(event, message)
    else:
        for message in messages:
            await bot.send(event, message)

    await tarot_spread.finish()


@tarot_fortune.handle()
async def handle_daily_fortune(matcher: Matcher) -> None:
    await matcher.finish(build_fortune_reply())


@tarot_reading.handle()
async def handle_tarot_reading(matcher: Matcher, args: Message = CommandArg()) -> None:
    await matcher.finish(build_reading_reply(str(args).strip()))
