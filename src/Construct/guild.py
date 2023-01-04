import inspect
from typing_extensions import Literal
from typing import List, Union, Optional

from pydantic import Field, BaseModel, validator

import nonebot
from nonebot.log import logger
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.utils import escape
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.adapters.onebot.v11.event import Event, NoticeEvent, MessageEvent


class GuildMessageEvent(MessageEvent):
    __event__ = "message.guild"
    self_tiny_id: int

    message_type: Literal["guild"]
    message_id: str
    guild_id: int
    channel_id: int

    raw_message: str = Field(alias="message")
    font: None = None

    @validator('raw_message', pre=True)
    def _validate_raw_message(cls, raw_message):
        if isinstance(raw_message, str):
            return raw_message
        elif isinstance(raw_message, list):
            return str(Message(raw_message))
        raise ValueError('unknown raw message type')


class ReactionInfo(BaseModel):
    emoji_id: str
    emoji_index: int
    emoji_type: int
    emoji_name: str
    count: int
    clicked: bool

    class Config:
        extra = "allow"


class ChannelNoticeEvent(NoticeEvent):
    __event__ = "notice.channel"
    self_tiny_id: int
    guild_id: int
    channel_id: int
    user_id: int

    sub_type: None = None


class MessageReactionUpdatedNoticeEvent(ChannelNoticeEvent):
    __event__ = "notice.message_reactions_updated"
    notice_type: Literal["message_reactions_updated"]
    message_id: str
    current_reactions: Optional[List[ReactionInfo]] = None


class SlowModeInfo(BaseModel):
    slow_mode_key: int
    slow_mode_text: str
    speak_frequency: int
    slow_mode_circle: int

    class Config:
        extra = "allow"


class ChannelInfo(BaseModel):
    owner_guild_id: int
    channel_id: int
    channel_type: int
    channel_name: str
    create_time: int
    creator_id: int
    creator_tiny_id: int
    talk_permission: int
    visible_type: int
    current_slow_mode: int
    slow_modes: List[SlowModeInfo] = []

    class Config:
        extra = "allow"


class ChannelUpdatedNoticeEvent(ChannelNoticeEvent):
    __event__ = "notice.channel_updated"
    notice_type: Literal["channel_updated"]
    operator_id: int
    old_info: ChannelInfo
    new_info: ChannelInfo


class ChannelCreatedNoticeEvent(ChannelNoticeEvent):
    __event__ = "notice.channel_created"
    notice_type: Literal["channel_created"]
    operator_id: int
    channel_info: ChannelInfo


class ChannelDestoryedNoticeEvent(ChannelNoticeEvent):
    __event__ = "notice.channel_destoryed"
    notice_type: Literal["channel_destoryed"]
    operator_id: int
    channel_info: ChannelInfo


original_send = Bot.send


async def patched_send(self: Bot, event: Event,
                       message: Union[Message, MessageSegment, str], **kwargs):
    guild_id: Optional[int] = getattr(event, "guild_id", None)
    channel_id: Optional[int] = getattr(event, 'channel_id', None)
    if not (guild_id and channel_id):
        return await original_send(self, event, message, **kwargs)

    user_id: Optional[int] = getattr(event, 'user_id', None)
    message = escape(message, escape_comma=False) if isinstance(
        message, str) else message

    message_sent = message if isinstance(message, Message) else Message(message)
    if user_id and kwargs.get('at_sender', False):
        message_sent = MessageSegment.at(user_id) + ' ' + message_sent

    return await self.send_guild_channel_msg(guild_id=guild_id,
                                             channel_id=channel_id,
                                             message=message_sent)


driver = nonebot.get_driver()


@driver.on_startup
def patch():
    import nonebot.adapters.onebot.v11.event as events

    Bot.send = patched_send

    for model in globals().values():
        if not inspect.isclass(model) or not issubclass(model, Event):
            continue
        events._t["." + model.__event__] = model

    logger.debug('Patch for NoneBot2 guild adaptation has been applied.')