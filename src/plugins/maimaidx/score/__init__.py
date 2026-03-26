"""Score providers registry and NoneBot dependency helpers.

本模块集中完成各个查分器实现类的单例初始化，并提供可用于
NoneBot 依赖注入的获取函数，便于在对话上下文中直接获得实例。
"""

from __future__ import annotations

from typing import Dict

from nonebot import get_driver

from ._base import BaseScoreProvider
from ._schema import PlayerMaiB50, PlayerMaiInfo, PlayerMaiScore
from .providers.diving_fish import DivingFishScoreProvider
from .providers.lxns import LXNSScoreProvider
from .providers.maimai import MaimaiPyScoreProvider

# --- 单例初始化（每个实现类仅初始化一次） ---
_lxns_provider = LXNSScoreProvider()
_divingfish_provider = DivingFishScoreProvider()
_maimaipy_provider = MaimaiPyScoreProvider()


def get_lxns_provider() -> LXNSScoreProvider:
    """获取 落雪咖啡屋 查分器的单例实例。

    可用于 NoneBot 依赖注入：

        from nonebot.params import Depends
        from .score import get_lxns_provider

        async def handler(provider: LXNSScoreProvider = Depends(get_lxns_provider)):
            ...
    """

    return _lxns_provider


def get_divingfish_provider() -> DivingFishScoreProvider:
    """获取 水鱼 查分器的单例实例。

    可用于 NoneBot 依赖注入：

        from nonebot.params import Depends
        from .score import get_divingfish_provider

        async def handler(provider: DivingFishScoreProvider = Depends(get_divingfish_provider)):
            ...
    """

    return _divingfish_provider


def get_maimaipy_provider() -> MaimaiPyScoreProvider:
    """获取 maimai_py 的单例实例。

    可用于 NoneBot 依赖注入：

        from nonebot.params import Depends
        from .score import get_maimaipy_provider

        async def handler(provider: MaimaiPyScoreProvider = Depends(get_maimaipy_provider)):
            ...
    """
    return _maimaipy_provider


def get_all_score_providers() -> Dict[str, BaseScoreProvider]:
    """获取当前已注册的全部查分器实例。

    返回一个简单的字典映射，键为实现名，值为对应的单例实例。
    便于按需遍历或根据配置选择具体实现。
    """

    return {
        "lxns": _lxns_provider,
        "divingfish": _divingfish_provider,
        "maimaipy": _maimaipy_provider,
    }


async def auto_get_score_provider(user_id: str) -> LXNSScoreProvider | DivingFishScoreProvider:
    from nonebot_plugin_orm import get_scoped_session

    from ..database.crud import UserBindInfoORM

    session = get_scoped_session()
    bind_info = await UserBindInfoORM.get_user_bind_info(session, user_id)

    if bind_info and not bind_info.lxns_api_key and bind_info.diving_fish_import_token:
        return _divingfish_provider

    return _lxns_provider


# --- 生命周期清理：在 NoneBot 关闭时释放网络会话 ---
driver = get_driver()


@driver.on_shutdown
async def _close_score_providers():
    for provider in get_all_score_providers().values():
        await provider.close()


__all__ = [
    "BaseScoreProvider",
    "LXNSScoreProvider",
    "DivingFishScoreProvider",
    "get_lxns_provider",
    "get_all_score_providers",
    "auto_get_score_provider",
    "PlayerMaiInfo",
    "PlayerMaiB50",
    "PlayerMaiScore",
]
