from nonebot import on_command, on_notice
from nonebot.adapters.onebot.v11 import Bot, NoticeEvent

help_command = on_command("help", aliases={"帮助", "菜单", "命令帮助"}, priority=40, block=True)
about_command = on_command(
    "项目信息",
    aliases={"about", "info", "botinfo", "关于", "版本"},
    priority=40,
    block=True,
)
status_command = on_command(
    "系统状态",
    aliases={"status", "主机负载", "bot状态"},
    priority=40,
    block=True,
)
plugins_command = on_command(
    "插件列表",
    aliases={"plugins", "模块列表"},
    priority=40,
    block=True,
)
ping_command = on_command("ping", aliases={"存活", "在线检测"}, priority=40, block=True)
select_command = on_command("帮选", aliases={"帮我选"}, priority=40, block=True)
poke_rank_command = on_command(
    "本群戳一戳情况",
    aliases={"戳一戳排行", "戳一戳排行榜"},
    priority=40,
    block=True,
)


async def _is_group_poke(bot: Bot, event: NoticeEvent) -> bool:
    return (
        getattr(event, "notice_type", None) == "notify"
        and getattr(event, "sub_type", None) == "poke"
        and getattr(event, "group_id", None) is not None
        and str(getattr(event, "target_id", "")) == str(bot.self_id)
    )


poke_notice = on_notice(rule=_is_group_poke, priority=40, block=True)
