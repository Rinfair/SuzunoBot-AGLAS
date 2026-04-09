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
from . import storage  # noqa: E402, F401
from .storage import MaiSongORM, ensure_database_schema  # noqa: E402
from .updater.songs import update_song_alias_list, update_song_database  # noqa: E402


@get_driver().on_startup
async def initialize_song_cache():
    session = get_scoped_session()
    logger.debug("检查 maimaidx 数据库结构中...")
    await ensure_database_schema(session)
    logger.debug("更新乐曲缓存中...")
    await MaiSongORM.refresh_cache(session)
    if not MaiSongORM._cache:
        logger.warning("本地乐曲数据库为空，正在自动初始化歌曲与别名数据...")
        await update_song_database(session)
        await update_song_alias_list(session)
        await MaiSongORM.refresh_cache(session)


__plugin_meta__ = PluginMetadata(
    name="SuzunoBot Embedded Maimai",
    description="SuzunoBot-AGLAS 舞萌插件，命令逻辑整理自 Rikka，图片渲染基于 maimaiDX 资源方案",
    usage=".b50",
    type="application",
    config=Config,
    homepage="https://github.com/Yuri-YuzuChaN/maimaiDX",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)
