from abc import ABC, abstractmethod
from typing import Any, ClassVar, Generic, Optional, Type, TypeVar

from aiohttp import ClientResponseError, ClientSession

from ._schema import PlayerMaiB50, PlayerMaiInfo

P = TypeVar("P")


class BaseScoreProvider(ABC, Generic[P]):
    provider: str
    """查分器名称"""

    base_url: str
    """查分器的 API 接口"""

    ParamsType: ClassVar[Type[Any]]

    def __init__(self) -> None:
        self._session: Optional[ClientSession] = None

    async def _get_session(self) -> ClientSession:
        """获取或创建共享的 aiohttp 会话"""
        if self._session is None or self._session.closed:
            self._session = ClientSession()
        return self._session

    def _build_headers(self, auth_token: Optional[str]) -> dict:
        """构造请求头，子类可覆盖以适配不同鉴权字段。"""
        return {"Authorization": auth_token} if auth_token else {}

    async def _get_resp(self, endpoint: str, auth_token: Optional[str] = None) -> Any:
        """发起 GET 请求，自动拼接 URL 并附带鉴权。"""
        session = await self._get_session()
        headers = self._build_headers(auth_token)
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        try:
            async with session.get(url, headers=headers) as resp:
                resp.raise_for_status()
                return await resp.json()
        except ClientResponseError as e:
            # 轻量异常映射：给调用方更清晰的语义（保留最小化改动）
            if e.status in (401, 403):
                raise PermissionError(f"鉴权失败: {e.status} {url}") from e
            if e.status == 404:
                raise LookupError(f"未找到资源: {url}") from e
            if e.status == 429:
                raise RuntimeError("请求过于频繁(429): 请稍后重试") from e
            raise

    async def _post_resp(self, endpoint: str, params: dict, auth_token: Optional[str] = None) -> Any:
        """发起 POST 请求，自动拼接 URL 并附带鉴权。"""
        session = await self._get_session()
        headers = self._build_headers(auth_token)
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        try:
            async with session.post(url, headers=headers, json=params) as resp:
                resp.raise_for_status()
                return await resp.json()
        except ClientResponseError as e:
            if e.status in (401, 403):
                raise PermissionError(f"鉴权失败: {e.status} {url}") from e
            if e.status == 404:
                raise LookupError(f"未找到资源: {url}") from e
            if e.status == 429:
                raise RuntimeError("请求过于频繁(429): 请稍后重试") from e
            raise

    async def close(self):
        """手动关闭 session"""
        if self._session and not self._session.closed:
            await self._session.close()

    @abstractmethod
    async def fetch_player_info(self, params: P) -> PlayerMaiInfo:
        raise NotImplementedError

    @abstractmethod
    async def fetch_player_b50(self, params: P) -> PlayerMaiB50:
        raise NotImplementedError

    @abstractmethod
    async def fetch_player_ap50(self, params: P) -> PlayerMaiB50:
        raise NotImplementedError
