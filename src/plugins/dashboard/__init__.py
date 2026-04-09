from nonebot.plugin import PluginMetadata

from .config import Config
from . import handler as handler

__plugin_meta__ = PluginMetadata(
    name="SuzunoBot Dashboard",
    description="项目级帮助、项目信息与系统状态模块",
    usage="帮助 / 项目信息 / 系统状态 / 插件列表 / ping",
    type="application",
    config=Config,
    homepage="https://github.com/Rinfair-CSP-A016/SuzunoBot-AGLAS",
)
