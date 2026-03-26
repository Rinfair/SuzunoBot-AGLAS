from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from typing import Literal, Optional, TypeAlias, TypeVar, cast

from async_lru import alru_cache
from httpcore import NetworkError
from httpx import HTTPStatusError
from maimai_py import (
    ArcadeProvider,
    DivingFishPlayer,
    DivingFishProvider,
    FCType,
    InvalidPlayerIdentifierError,
    LXNSPlayer,
    LXNSProvider,
    MaimaiClient,
    MaimaiScores,
    Player,
    PlayerIdentifier,
    ScoreExtend,
)
from maimai_py import SongType as MaimaiPySongType
from maimai_py import (
    current_version,
)
from nonebot import logger
from nonebot.internal.matcher import current_event
from nonebot_plugin_alconna import At, UniMessage
from nonebot_plugin_orm import async_scoped_session, get_scoped_session

from ...config import config
from ...database import MaiPlayCountORM, UserBindInfo, UserBindInfoORM
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

_SUPPORT_PROVIDER: TypeAlias = DivingFishProvider | LXNSProvider | ArcadeProvider
S = TypeVar("S", bound=list[PlayerMaiScore] | PlayerMaiB50)

maimai_client = MaimaiClient()
_divingfish_provider = DivingFishProvider(developer_token=config.divingfish_developer_api_key)
_lxns_provider = LXNSProvider(developer_token=config.lxns_developer_api_key)
_arcade_provider = ArcadeProvider(http_proxy=config.arcade_provider_http_proxy)


@dataclass
class MaimaiPyParams:
    score_provider: _SUPPORT_PROVIDER
    identifier: PlayerIdentifier


class MaimaiPyScoreProvider(BaseScoreProvider[MaimaiPyParams]):
    provider = "maimai_py"
    ParamsType = MaimaiPyParams

    @staticmethod
    def _score_unpack(score: ScoreExtend) -> PlayerMaiScore:
        return PlayerMaiScore(
            song_id=score.id,
            song_name=score.title,
            song_type=SongType(score.type.value),
            song_level=score.level,
            song_difficulty=SongDifficulty(score.level_index.value),
            achievements=score.achievements,  # type: ignore
            dx_score=score.dx_score or 0,
            dx_star=0,  # unsupported.
            dx_rating=score.dx_rating or 0,
            rate=ScoreRateType(score.rate.name.lower()),
            fc=ScoreFCType(score.fc.name.lower()) if score.fc else None,
            fs=ScoreFSType(score.fs.name.lower()) if score.fs else None,
            play_count=score.play_count,
        )

    @staticmethod
    def _unpack_player_mai_info(player: Player | LXNSPlayer | DivingFishPlayer) -> "PlayerMaiInfo":
        if isinstance(player, LXNSPlayer):
            player_info = PlayerMaiInfo(
                name=player.name,
                rating=player.rating,
                course_rank=player.course_rank,
                class_rank=player.class_rank,
                friend_code=str(player.friend_code),
                trophy=player.trophy,
                icon=player.icon,
                name_plate=player.name_plate,
                frame=player.frame,
                upload_time=player.upload_time,
            )
        else:
            player_info = PlayerMaiInfo(
                name=player.name,
                rating=player.rating,
            )

        return player_info

    @staticmethod
    async def auto_get_score_provider(session: async_scoped_session, user_id: str) -> _SUPPORT_PROVIDER:
        """
        根据用户绑定情况自动获取合适的查分器

        选择逻辑如下：
        1. 如果仅配置了一个查分器的开发者密钥，则使用该查分器
        2. 如果用户未绑定任何查分器，默认使用 LXNS 查分器
        3. 如果用户绑定了查分器但未设置默认查分器，优先使用水鱼查分器（如果有绑定水鱼查分器），否则使用 LXNS 查分器
        """
        bind_info = await UserBindInfoORM.get_user_bind_info(session, user_id)

        if config.lxns_developer_api_key and not config.divingfish_developer_api_key:
            return _lxns_provider
        if config.divingfish_developer_api_key and not config.lxns_developer_api_key:
            return _divingfish_provider

        if not bind_info:
            return _lxns_provider

        if bind_info.default_provider is None:
            if bind_info.diving_fish_import_token:
                return _divingfish_provider
            else:
                return _lxns_provider

        if bind_info.default_provider == "lxns":
            return _lxns_provider

        elif bind_info.default_provider == "divingfish":
            return _divingfish_provider

        return _lxns_provider

    @staticmethod
    async def auto_get_player_identifier(
        session: async_scoped_session,
        user_id: str,
        score_provider: _SUPPORT_PROVIDER,
        *,
        use_personal_api: bool = False,
    ) -> PlayerIdentifier:
        """
        根据用户绑定情况自动选择鉴权方式
        """
        logger.debug(f"[{user_id}] 尝试从数据库中获取玩家绑定信息...")
        user_bind_info = await UserBindInfoORM.get_user_bind_info(session, user_id)

        # 落雪查分器
        # When user_bind_info is None, score_provider is LXNSScoreProvider.
        if isinstance(score_provider, LXNSProvider):
            new_player_friend_code = None
            if use_personal_api:
                if user_bind_info:
                    return PlayerIdentifier(credentials=user_bind_info.lxns_api_key)
                else:
                    raise ValueError("无法通过个人 API 获得用户鉴权凭证：用户未绑定落雪查分器")

            if user_bind_info is None:
                logger.warning(f"[{user_id}] 未能获取玩家码，数据库中不存在绑定的玩家数据")
                logger.debug(f"[{user_id}] 尝试通过 QQ 请求玩家数据")
                try:
                    identifier = PlayerIdentifier(qq=int(user_id))
                    player_obj = await score_provider.get_player(identifier, client=maimai_client)
                    new_player_friend_code = player_obj.friend_code
                except (HTTPStatusError, InvalidPlayerIdentifierError) as e:
                    if isinstance(e, HTTPStatusError) and e.response.status_code == 404:
                        logger.warning(f"[{user_id}] 无法通过 QQ 号请求玩家数据: 玩家不存在")
                    else:
                        logger.warning(f"[{user_id}] 无法通过 QQ 号请求玩家数据: {e}")

                    await UniMessage(
                        [
                            At(flag="user", target=user_id),
                            "你还未绑定查分器，请使用 /bind 指令进行绑定！",
                        ]
                    ).finish()

                    return
                except ValueError:
                    logger.warning(f"[{user_id}] 无法通过 QQ 号请求玩家数据: QQ 号无效 & 非 QQ 平台聊天")
                    await UniMessage(
                        [
                            At(flag="user", target=user_id),
                            "你还未绑定查分器，请使用 /bind 指令进行绑定！",
                        ]
                    ).finish()

                    return

            friend_code = new_player_friend_code or user_bind_info.friend_code  # type: ignore
            if not friend_code:
                logger.warning(f"[{user_id}] 无法获取好友码，无法继续查询。")
                await UniMessage(
                    [
                        At(flag="user", target=user_id),
                        "无法获取好友码，请确认已绑定或查分器可用。",
                    ]
                ).finish()
                return

            identifier = PlayerIdentifier(friend_code=int(friend_code))

        # 水鱼查分器
        # elif isinstance(score_provider, DivingFishScoreProvider):
        else:
            # When score_provider is DivingFish, user_bind_info and diving_fish_username is not None.
            user_bind_info = cast(UserBindInfo, user_bind_info)
            diving_fish_username = user_bind_info.diving_fish_username
            assert diving_fish_username
            identifier = PlayerIdentifier(
                username=diving_fish_username, credentials=user_bind_info.diving_fish_import_token
            )

        return identifier

    async def fetch_player_info(self, params: MaimaiPyParams) -> PlayerMaiInfo:
        player_info = await maimai_client.players(params.identifier, params.score_provider)

        return self._unpack_player_mai_info(player_info)

    async def fetch_player_b50(self, params: MaimaiPyParams) -> PlayerMaiB50:
        player_b50 = await maimai_client.bests(params.identifier, params.score_provider)

        best35 = [self._score_unpack(score) for score in player_b50.scores_b35]
        best15 = [self._score_unpack(score) for score in player_b50.scores_b15]

        return await self.fetch_player_play_counts(PlayerMaiB50(best35, best15))

    async def fetch_player_ap50(self, params: MaimaiPyParams) -> PlayerMaiB50:
        """
        获得玩家 AP 50

        注: 落雪查分器需要使用个人 token 进行鉴权
        """
        logger.debug("1/2 获取完整游玩记录")

        scores = await maimai_client.scores(params.identifier, params.score_provider)

        ap_records = scores.filter(fc=FCType.AP) + scores.filter(fc=FCType.APP)

        logger.debug("2/2 划分版本信息")

        ap50 = await MaimaiScores(maimai_client).configure(ap_records, b50_only=True)

        best35 = [self._score_unpack(score) for score in ap50.scores_b35]
        best15 = [self._score_unpack(score) for score in ap50.scores_b15]

        return await self.fetch_player_play_counts(PlayerMaiB50(best35, best15))

    async def fetch_player_pc50(self, params: MaimaiPyParams) -> PlayerMaiB50:
        """
        获得玩家 PC 50

        注：需要用户使用 `.import` 指令导入游玩记录后才能获取
        """
        logger.debug("1/3 获取完整游玩记录")
        scores = await maimai_client.scores(params.identifier, params.score_provider)

        scores_list = scores.scores.copy()
        # scores_list.sort(key=lambda x: x.play_count or 0, reverse=True)

        logger.debug("2/3 划分版本信息")
        old_version_scores: list[ScoreExtend] = []
        new_version_scores: list[ScoreExtend] = []
        song_diff_versions: dict[str, int] = await maimai_client._cache.get("versions", namespace="songs") or {}
        for score in scores_list:
            if score.type == MaimaiPySongType.UTAGE:
                continue

            # Find the version of the song, and decide whether it is b35 or b15.
            diff_key = f"{score.id} {score.type} {score.level_index}"
            if score_version := song_diff_versions.get(diff_key, None):
                (new_version_scores if score_version >= current_version.value else old_version_scores).append(score)

        logger.debug("3/3 获取游玩次数并返回结果")
        old_best = await self.fetch_player_play_counts([self._score_unpack(score) for score in old_version_scores])
        new_best = await self.fetch_player_play_counts([self._score_unpack(score) for score in new_version_scores])

        best35 = sorted(old_best, key=lambda x: x.play_count or 0, reverse=True)[:35]
        best15 = sorted(new_best, key=lambda x: x.play_count or 0, reverse=True)[:15]

        return PlayerMaiB50(standard=best35, dx=best15)

    async def fetch_player_minfo(
        self, params: MaimaiPyParams, song_id: int, song_type: Literal["standard", "dx"]
    ) -> list[PlayerMaiScore]:
        """
        获取玩家单曲游玩情况

        :param params: 鉴权参数对象
        :type params: MaimaiPyParams
        :param name: 曲目的 ID（标准曲目ID）
        :type name: str
        :param song_type: 铺面类型
        :type song_type: Literal["standard", "dx"]
        :return: 成绩列表
        :rtype: list[PlayerMaiScore]
        """

        player_song = await maimai_client.minfo(song_id, params.identifier, params.score_provider)

        if not player_song:
            return []

        raw_scores = player_song.scores
        scores = [self._score_unpack(score) for score in raw_scores if score.type.value == song_type]

        return await self.fetch_player_play_counts(scores)

    async def fetch_player_scoreslist(
        self,
        params: MaimaiPyParams,
        level: Optional[str] = None,
        ach: Optional[float] = None,
        diff: Optional[Literal["BASIC", "ADVANCED", "EXPERT", "MASTER", "REMASTER"]] = None,
    ) -> list[PlayerMaiScore]:
        """
        获得玩家指定条件的成绩列表

        :param params: 鉴权参数对象
        :type params: MaimaiPyParams
        :param level: 曲目等级，如 `11`, `12+`
        :type level: str
        :param ach: 达成率，精确一位小数
        :type ach: float
        :param diff: 铺面难度分类
        :type diff: Literal["BASIC", "ADVANCED", "EXPERT", "MASTER", "REMASTER"]

        :return: 成绩列表
        :rtype: list[PlayerMaiScore]
        """

        def trunc_1(x):
            return Decimal(str(x)).quantize(Decimal("0.0"), rounding=ROUND_DOWN)

        scores = await maimai_client.scores(params.identifier, params.score_provider)
        matched_scores: list[ScoreExtend] = []

        if level:
            matched_scores = cast(list[ScoreExtend], scores.filter(level=level))
        elif ach:
            for score in scores.scores:
                if score.achievements and trunc_1(score.achievements) == trunc_1(ach):
                    matched_scores.append(score)
        elif diff:
            for score in scores.scores:
                if score.level_index.name == diff:
                    matched_scores.append(score)
        else:
            matched_scores = scores.scores

        matched_scores.sort(key=lambda x: x.achievements or 0.0, reverse=True)

        return await self.fetch_player_play_counts([self._score_unpack(score) for score in matched_scores])

    async def get_player_identifier(self, qr_code_data: str) -> str:
        """
        获取玩家 Arcade 鉴权凭证（加密）

        :param qr_code_data: 仍在有效期内的二维码数据
        :type qr_code_data: str
        :return: Arcade 加密鉴权凭证
        :rtype: str
        """
        try:
            player = await maimai_client.identifiers(qr_code_data, provider=_arcade_provider)
        except NetworkError as exc:
            logger.warning(f"尝试通过玩家二维码获取玩家数据时发生错误: {exc}")
            raise

        return player.credentials  # type: ignore

    @alru_cache(maxsize=128, ttl=60 * 60)
    async def _fetch_player_play_counts(self, identifier: str) -> list[PlayerMaiScore]:
        """
        获取用户各铺面游玩次数
        """
        maimai_scores = await maimai_client.scores(PlayerIdentifier(credentials=identifier), _arcade_provider)

        return [self._score_unpack(score) for score in maimai_scores.scores]

    async def fetch_player_play_counts(self, scores: S) -> S:
        """
        根据玩家成绩补充游玩次数
        """
        session = get_scoped_session()
        try:
            user_id = current_event.get().get_user_id()
        except LookupError:
            # 当事件上下文不存在时，无法获取用户 ID，直接返回原始成绩列表
            return scores

        score_list = scores if isinstance(scores, list) else scores.dx + scores.standard
        if not score_list:
            return scores

        song_ids = [
            (score.song_id + 10000 if score.song_type == SongType.DX else score.song_id) for score in score_list
        ]
        play_map = await MaiPlayCountORM.get_user_play_count_map(session, user_id, song_ids)

        for score in score_list:
            song_key = score.song_id + 10000 if score.song_type == SongType.DX else score.song_id
            play_count = play_map.get((song_key, score.song_difficulty.value))
            if play_count is not None:
                score.play_count = play_count

        return scores
