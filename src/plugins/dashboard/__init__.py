from nonebot import get_driver, require
from nonebot.plugin import PluginMetadata

require("nonebot_plugin_orm")

from .config import Config
from . import handler as handler
from . import storage as storage
from .storage import ensure_dashboard_database_schema, start_poke_reset_task, stop_poke_reset_task

from nonebot_plugin_orm import get_scoped_session  # noqa: E402


@get_driver().on_startup
async def initialize_dashboard_storage() -> None:
    session = get_scoped_session()
    await ensure_dashboard_database_schema(session)
    start_poke_reset_task()


@get_driver().on_shutdown
async def shutdown_dashboard_storage() -> None:
    stop_poke_reset_task()

__plugin_meta__ = PluginMetadata(
    name="SuzunoBot Dashboard",
    description="项目级帮助、项目信息与系统状态模块",
    usage="帮助 / 项目信息 / 系统状态 / 插件列表 / ping / 帮选 / 本群戳一戳情况",
    type="application",
    config=Config,
    homepage="https://github.com/Rinfair-CSP-A016/SuzunoBot-AGLAS",
)
