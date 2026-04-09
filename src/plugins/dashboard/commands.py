from nonebot import on_command

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
