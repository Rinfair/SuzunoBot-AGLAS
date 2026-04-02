from dataclasses import dataclass, fields
from typing import Optional, TypedDict

from nonebot import logger
from nonebot_plugin_orm import get_scoped_session

from ...constants import _MAI_VERSION_MAP
from ...storage import MaiSongORM
from .._base import BaseScoreProvider
from .._schema import (
    PlayerMaiB50,
    PlayerMaiInfo,
    PlayerMaiScore,
    ScoreFCType,
    ScoreFSType,
    ScoreRateType,
    SongDifficulty,
    SongType,
)


class DivingFishCharts(TypedDict):
    sd: list[dict]
    dx: list[dict]


class DivingFishBest50Response(TypedDict):
    additional_rating: int
    """段位信息"""
    charts: DivingFishCharts
    nickname: str
    """用户的昵称"""
    plate: str
    """用户的牌子信息"""
    rating: int
    user_general_data: None
    """占位符"""
    username: str
    """水鱼用户名"""


class DivingFishPlayerRecordsResponse(TypedDict):
    additional_rating: int
    """段位信息"""
    records: list[dict]
    nickname: str
    """用户的昵称"""
    plate: str
    """用户的牌子信息"""
    rating: int
    username: str
    """水鱼用户名"""


@dataclass
class DivingFishParams:
    username: Optional[str] = None
    import_token: Optional[str] = None
    qq: Optional[str] = None


class DivingFishScoreProvider(BaseScoreProvider[DivingFishParams]):
    provider = "diving-fish"
    base_url = "https://www.diving-fish.com/api/maimaidxprober/"
    ParamsType = DivingFishParams

    def _build_headers(self, auth_token: Optional[str]) -> dict:
        # diving-fish 使用 Import-Token 作为鉴权头
        return {"Import-Token": auth_token} if auth_token else {}

    @staticmethod
    def _score_unpack(raw_score: dict) -> PlayerMaiScore:
        raw_score["song_difficulty"] = SongDifficulty(raw_score["level_index"])
        raw_score["fc"] = ScoreFCType(raw_score["fc"]) if raw_score.get("fc") else None
        raw_score["fs"] = ScoreFSType(raw_score["fs"]) if raw_score.get("fs") else None
        raw_score["rate"] = ScoreRateType(raw_score["rate"])
        raw_score["song_type"] = SongType("standard" if raw_score["type"] == "SD" else "dx")

        valid_keys = {f.name for f in fields(PlayerMaiScore)}
        filtered = {k: v for k, v in raw_score.items() if k in valid_keys}
        filtered["song_name"] = raw_score["title"]
        filtered["song_level"] = raw_score["level"]
        filtered["dx_score"] = raw_score["dxScore"]
        filtered["dx_rating"] = raw_score["ra"]
        filtered["dx_star"] = 0  # unsupported.

        return PlayerMaiScore(**filtered)

    async def fetch_player_info(self, params: DivingFishParams) -> PlayerMaiInfo:
        """
        获取玩家信息(水鱼不支持获取收藏品信息)
        """
        if params.username:
            endpoint = "query/player"
            req_params = {"username": params.username, "b50": 1}
        elif params.qq:
            endpoint = "query/player"
            req_params = {"qq": params.qq, "b50": 1}
        else:
            raise ValueError("必须提供 username 或 qq")

        data: DivingFishBest50Response = await self._post_resp(endpoint, req_params)
        return PlayerMaiInfo(data["nickname"], data["rating"], 0, 0, qq=params.qq)

    async def fetch_player_b50(self, params: DivingFishParams) -> PlayerMaiB50:
        """
        获得玩家 Best50 信息
        """
        if params.username:
            endpoint = "query/player"
            req_params = {"username": params.username, "b50": 1}
        elif params.qq:
            endpoint = "query/player"
            req_params = {"qq": params.qq, "b50": 1}
        else:
            raise ValueError("必须提供 username 或 qq 用于查询 Best50")

        data: DivingFishBest50Response = await self._post_resp(endpoint, req_params)

        standard_scores = []
        dx_scores = []

        for raw_score in data["charts"]["sd"]:
            score = self._score_unpack(raw_score)
            standard_scores.append(score)

        for raw_score in data["charts"]["dx"]:
            score = self._score_unpack(raw_score)
            dx_scores.append(score)

        b50 = PlayerMaiB50(standard=standard_scores, dx=dx_scores)
        return b50

    async def fetch_player_records_by_import_token(self, import_token: str) -> DivingFishPlayerRecordsResponse:
        """
        通过 import-token 获取玩家游玩记录
        """
        endpoint = "player/records"

        data: DivingFishPlayerRecordsResponse = await self._get_resp(endpoint, import_token)

        return data

    async def fetch_player_ap50(self, params: DivingFishParams) -> PlayerMaiB50:
        """
        获取玩家 AP 50

        需要: import_token
        """
        if params.import_token is None:
            raise ValueError("必须提供 import_token")

        _CURRENT_VERSION = list(_MAI_VERSION_MAP.keys())[-1]

        logger.debug("通过水鱼查分器间接查询 AP 50...")
        logger.debug("1/2 获取完整游玩记录")

        datas = await self.fetch_player_records_by_import_token(params.import_token)
        records = datas["records"]
        ap_records = [record for record in records if record["fc"] in ["ap", "app"]]

        logger.debug("2/2 划分版本信息")

        session = get_scoped_session()
        old_version_records = []
        current_vesion_records = []

        for record in ap_records:
            song_id = record["song_id"] if record["type"].lower() != "dx" else record["song_id"] - 10000
            song = await MaiSongORM.get_song_info(session, song_id)
            is_current_version = song.version // 100 == _CURRENT_VERSION

            if is_current_version:
                current_vesion_records.append(record)
            else:
                old_version_records.append(record)

        old_version_records.sort(key=lambda x: x["ra"], reverse=True)
        current_vesion_records.sort(key=lambda x: x["ra"], reverse=True)

        standard_scores = [self._score_unpack(record) for record in old_version_records[:35]]
        dx_scores = [self._score_unpack(record) for record in current_vesion_records[:15]]

        ap50 = PlayerMaiB50(standard=standard_scores, dx=dx_scores)
        return ap50
