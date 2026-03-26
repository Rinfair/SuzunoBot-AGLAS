from pathlib import Path
from typing import Literal, Optional

from nonebot import logger
from nonebot_plugin_orm import get_scoped_session
from typing_extensions import TypedDict

from .database.crud import MaiSongORM
from .models.song import MaiSong
from .painters import DrawBest, DrawScores, draw_music_info, image_to_bytes
from .score import PlayerMaiB50, PlayerMaiInfo, PlayerMaiScore
from .updater.resources import download_icon, download_jacket, download_plate


class ViewportDict(TypedDict):
    width: int
    height: int


class PicRenderer:
    def __init__(
        self,
        template_dir: Path = Path(__file__).parent / "templates",
        static_dir: str = "./static",
        default_width: int = 1400,
        default_height: int = 1600,
    ) -> None:
        """
        :param template_dir: 模板路径
        :param static_dir: Mai 静态文件路径
        """
        # 使用绝对路径，避免 Playwright 访问 file:// 相对目录时报错（ERR_FILE_NOT_FOUND）
        self.template_dir = str(template_dir.resolve())
        self.static_dir = Path(static_dir)
        self.default_viewport = {"width": default_width, "height": default_height}

        self.draw_best = DrawBest()
        self.draw_score = DrawScores()

    @staticmethod
    def _cover_candidates(base_dir: Path, song_id: int) -> list[Path]:
        ids = [song_id]
        if song_id < 10000:
            ids.append(song_id + 10000)
        elif 10000 < song_id < 100000:
            ids.append(song_id - 10000)

        candidates: list[Path] = []
        for sid in ids:
            candidates.append(base_dir / f"{sid}.png")
            candidates.append(base_dir / f"{sid:05d}.png")
        return candidates

    async def _ensure_cover(self, song_id: int) -> str:
        """
        确保封面资源存在

        :param song_id: 乐曲 id
        """
        if 10000 < song_id < 100000:
            song_id -= 10000
        elif song_id > 100000:
            song_id -= 100000

        cover_dir = Path(self.static_dir / "mai" / "cover")
        for cover in self._cover_candidates(cover_dir, song_id):
            if cover.exists():
                return cover.stem

        logger.warning(f"乐曲 {song_id} 的封面不存在!尝试从服务器下载...")

        try:
            await download_jacket(str(song_id))
            return str(song_id)
        except Exception as e:
            logger.error(f"下载乐曲 {song_id} 封面失败: {e}")

        return "0"  # 返回默认封面

    async def _validate_profile_resources(self, player_info: PlayerMaiInfo) -> bool:
        """确保玩家相关资源存在（头像/姓名框/背景框）。"""

        ok = True

        if player_info.icon:
            icon_id = player_info.icon.id
            icon_path = Path(self.static_dir / "mai" / "icon" / f"{icon_id}.png")
            if not icon_path.exists():
                logger.warning(f"头像资源 {icon_id} 不存在!尝试从服务器下载...")
                try:
                    await download_icon(str(icon_id))
                except Exception as e:
                    logger.error(f"下载头像资源 {icon_id} 失败: {e}")
                    ok = False

        if player_info.name_plate:
            plate_id = player_info.name_plate.id
            plate_path = Path(self.static_dir / "mai" / "plate" / f"{plate_id}.png")
            if not plate_path.exists():
                logger.warning(f"姓名框资源 {plate_id} 不存在!尝试从服务器下载...")
                try:
                    await download_plate(str(plate_id))
                except Exception as e:
                    logger.error(f"下载姓名框资源 {plate_id} 失败: {e}")
                    ok = False

        # if player_info.frame:
        #     frame_id = player_info.frame.id
        #     frame_path = Path(self.static_dir / "mai" / "frame" / f"{frame_id}.png")
        #     if not frame_path.exists():
        #         logger.warning(f"背景框资源 {frame_id} 不存在!尝试从服务器下载...")
        #         try:
        #             await download_frame(str(frame_id))
        #         except Exception as e:
        #             logger.error(f"下载背景框资源 {frame_id} 失败: {e}")
        #             ok = False

        return ok

    async def _get_song_level_value(
        self, song_id: int, song_type: Literal["standard", "dx", "utage"], difficulty: int
    ) -> float:
        """
        获取乐曲定数

        :param song_id: 乐曲 ID
        :param song_type: 铺面类型
        :param difficulty: 铺面难度
        """
        session = get_scoped_session()

        # DX 铺面
        if 10000 < song_id < 100000:
            song_id -= 10000

        song_info = await MaiSongORM.get_song_info(session, song_id)

        if song_type == "dx" and len(song_info.difficulties.dx) > difficulty:
            return song_info.difficulties.dx[difficulty].level_value
        elif song_type == "standard" and len(song_info.difficulties.standard) > difficulty:
            return song_info.difficulties.standard[difficulty].level_value
        elif song_type == "utage":
            return 0

        raise ValueError(f"请求的乐曲 {song_id}({song_type}) 中的难度 {difficulty} 不存在")

    async def render_mai_player_best50(
        self, player_best50: PlayerMaiB50, player_info: PlayerMaiInfo, calc_song_level_value: bool = True
    ) -> bytes:
        """
        渲染玩家 Best50 信息
        """
        # Ensure covers
        for score in player_best50.standard + player_best50.dx:
            await self._ensure_cover(score.song_id)
            if calc_song_level_value:
                score.song_level_value = await self._get_song_level_value(
                    score.song_id, score.song_type.value, score.song_difficulty.value  # type: ignore
                )

        # Ensure player assets
        await self._validate_profile_resources(player_info)

        draw_best = DrawBest()
        img = draw_best.draw(player_info, player_best50)
        return image_to_bytes(img)

    async def render_mai_player_scores(
        self, scores: list[PlayerMaiScore], player_info: PlayerMaiInfo, title: Optional[str] = None
    ) -> bytes:
        """
        渲染玩家具体成绩图
        """
        # Ensure player assets
        await self._validate_profile_resources(player_info)

        # Ensure covers
        for score in scores:
            await self._ensure_cover(score.song_id)
            score.song_level_value = await self._get_song_level_value(
                score.song_id, score.song_type.value, score.song_difficulty.value  # type: ignore
            )

        img = self.draw_score.draw_scorelist(player_info, scores, title or "Player Scores")
        return image_to_bytes(img)

    async def render_mai_player_song_info(self, song: MaiSong, scores: list[PlayerMaiScore]) -> bytes:
        """
        渲染单曲成绩详情图

        :param song: 乐曲对象
        :param scores: 该乐曲各难度成绩的列表
        """
        await self._ensure_cover(song.id)

        img = draw_music_info(song, scores)
        return image_to_bytes(img)
