from nonebot.plugin import PluginMetadata

from .config import Config
from . import handler as handler

__plugin_meta__ = PluginMetadata(
    name="SuzunoBot BA Tarot",
    description="碧蓝档案塔罗牌占卜，本地资源发送版",
    usage="使用命令：ba塔罗牌、ba占卜、ba运势、ba塔罗牌解读",
    type="application",
    config=Config,
    homepage="https://github.com/Perseus037/nonebot_plugin_batarot",
)
