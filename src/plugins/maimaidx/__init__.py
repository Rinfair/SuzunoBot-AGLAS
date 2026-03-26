from nonebot import logger, require

require("nonebot_plugin_alconna")
require("nonebot_plugin_orm")

from nonebot.plugin import PluginMetadata, inherit_supported_adapters  # noqa: E402

from .config import Config  # noqa: E402
from .utils import init_logger  # noqa: E402

init_logger()

from nonebot import get_driver  # noqa: E402
from nonebot_plugin_orm import get_scoped_session  # noqa: E402

from . import alconna  # noqa: E402, F401
from . import database  # noqa: E402, F401
from .database import MaiSongORM  # noqa: E402


@get_driver().on_startup
async def initialize_song_cache():
    session = get_scoped_session()
    logger.debug("更新乐曲缓存中...")
    await MaiSongORM.refresh_cache(session)


__plugin_meta__ = PluginMetadata(
    name="SuzunoBot Embedded Maimai",
    description="嵌入式舞萌成绩查询插件，基于 Nonebot-Plugin-Rikka 重构",
    usage=".rikka",
    type="application",
    config=Config,
    homepage="https://github.com/Moemu/Nonebot-Plugin-Rikka",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)
