import json
from dataclasses import asdict
from typing import TYPE_CHECKING, Literal, Optional, Sequence

from nonebot import logger
from nonebot_plugin_orm import async_scoped_session
from sqlalchemy import select, update

from ..models.song import (
    MaiSong,
    SongDifficulties,
    SongDifficulty,
    SongDifficultyUtage,
    SongNotes,
)
from .orm_models import MaiPlayCount
from .orm_models import MaiSong as MaiSongORMModel
from .orm_models import MaiSongAlias, UserBindInfo

if TYPE_CHECKING:
    from ..updater.songs import MusicAliasResponseItem


class UserBindInfoORM:
    @staticmethod
    async def get_user_bind_info(session: async_scoped_session, user_id: str) -> Optional[UserBindInfo]:
        """获取用户绑定信息"""
        result = await session.execute(select(UserBindInfo).where(UserBindInfo.user_id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def set_user_friend_code(session: async_scoped_session, user_id: str, friend_code: str) -> None:
        """
        设置用户好友码
        """
        bind_info = await UserBindInfoORM.get_user_bind_info(session, user_id)
        if bind_info:
            await session.execute(
                update(UserBindInfo).where(UserBindInfo.user_id == user_id).values(friend_code=friend_code)
            )
        else:
            new_bind_info = UserBindInfo(user_id=user_id, friend_code=friend_code)
            session.add(new_bind_info)
        await session.commit()

    @staticmethod
    async def set_lxns_api_key(session: async_scoped_session, user_id: str, api_key: str) -> None:
        """设置用户的落雪咖啡屋 API 密钥"""
        bind_info = await UserBindInfoORM.get_user_bind_info(session, user_id)
        if bind_info:
            await session.execute(
                update(UserBindInfo).where(UserBindInfo.user_id == user_id).values(lxns_api_key=api_key)
            )
        else:
            new_bind_info = UserBindInfo(user_id=user_id, lxns_api_key=api_key)
            session.add(new_bind_info)
        await session.commit()

    @staticmethod
    async def set_diving_fish_import_token(
        session: async_scoped_session, user_id: str, import_token: str, diving_fish_username: str
    ) -> None:
        """设置用户的水鱼查分器导入密钥"""
        bind_info = await UserBindInfoORM.get_user_bind_info(session, user_id)
        if bind_info:
            await session.execute(
                update(UserBindInfo)
                .where(UserBindInfo.user_id == user_id)
                .values(diving_fish_import_token=import_token, diving_fish_username=diving_fish_username)
            )
        else:
            new_bind_info = UserBindInfo(
                user_id=user_id, diving_fish_import_token=import_token, diving_fish_username=diving_fish_username
            )
            session.add(new_bind_info)
        await session.commit()

    @staticmethod
    async def set_maimaipy_identifier(session: async_scoped_session, user_id: str, maimaipy_identifier: str):
        """
        设置用户的 Maimai.py 鉴权凭证
        """
        bind_info = await UserBindInfoORM.get_user_bind_info(session, user_id)
        if bind_info:
            await session.execute(
                update(UserBindInfo)
                .where(UserBindInfo.user_id == user_id)
                .values(maimaipy_identifier=maimaipy_identifier)
            )
        else:
            new_bind_info = UserBindInfo(user_id=user_id, maimaipy_identifier=maimaipy_identifier)
            session.add(new_bind_info)
        await session.commit()

    @staticmethod
    async def set_default_provider(
        session: async_scoped_session, user_id: str, provider: Literal["lxns", "divingfish"]
    ) -> None:
        """
        设置默认查分器

        :raise ValueError: 如果用户未绑定对应查分器账号则抛出该异常
        """
        bind_info = await UserBindInfoORM.get_user_bind_info(session, user_id)
        if not bind_info:
            raise ValueError("用户未绑定任何查分器账号，无法设置默认查分器")
        elif provider == "lxns" and not bind_info.lxns_api_key:
            raise ValueError("用户未设置落雪咖啡屋 API 密钥，无法设置为默认查分器")
        elif provider == "divingfish" and not bind_info.diving_fish_import_token:
            raise ValueError("用户未设置水鱼查分器导入密钥，无法设置为默认查分器")
        await session.execute(
            update(UserBindInfo).where(UserBindInfo.user_id == user_id).values(default_provider=provider)
        )
        await session.commit()

    @staticmethod
    async def unset_user_bind_info(
        session: async_scoped_session, user_id: str, provider: Optional[Literal["lxns", "divingfish", "maimai"]] = None
    ) -> None:
        """
        解绑用户查分器账号

        :param provider: 指定解绑的查分器，若为 None 则解绑所有查分器
        """
        bind_info = await UserBindInfoORM.get_user_bind_info(session, user_id)
        if not bind_info:
            return

        if provider is None:
            await session.delete(bind_info)
        elif provider == "lxns":
            await session.execute(update(UserBindInfo).where(UserBindInfo.user_id == user_id).values(lxns_api_key=None))
        elif provider == "divingfish":
            await session.execute(
                update(UserBindInfo)
                .where(UserBindInfo.user_id == user_id)
                .values(diving_fish_import_token=None, diving_fish_username=None)
            )
        elif provider == "maimai":
            await session.execute(
                update(UserBindInfo).where(UserBindInfo.user_id == user_id).values(maimaipy_identifier=None)
            )

        await session.commit()


class MaiSongORM:
    _cache: dict[int, MaiSong] = {}

    @classmethod
    def get_song_sync(cls, song_id: int) -> Optional[MaiSong]:
        """
        同步获取曲目信息（仅从缓存）
        """
        return cls._cache.get(song_id)

    @classmethod
    def update_cache(cls, song: MaiSong) -> None:
        cls._cache[song.id] = song

    @staticmethod
    async def refresh_cache(session: async_scoped_session) -> None:
        """
        刷新缓存，从数据库加载所有曲目信息
        """
        result = await session.execute(select(MaiSongORMModel))
        rows = result.scalars().all()
        for row in rows:
            song = MaiSongORM._convert(row)
            MaiSongORM.update_cache(song)

    @staticmethod
    def _convert(row: MaiSongORMModel) -> MaiSong:
        """
        反序列化 MaiSongORMModel 为 MaiSong
        """

        def convert_difficulty(diffs_data: dict) -> SongDifficulty:
            diff_note = diffs_data.get("notes", {})
            diffs_data["notes"] = SongNotes(
                total=diff_note.get("total", 0),
                tap=diff_note.get("tap", 0),
                touch=diff_note.get("touch", 0),
                hold=diff_note.get("hold", 0),
                slide=diff_note.get("slide", 0),
                break_=diff_note.get("break", 0),
            )
            return SongDifficulty(**diffs_data)

        # 数据库存储为字符串列，需要反序列化为字典
        diffs = row.difficulties if isinstance(row.difficulties, dict) else json.loads(row.difficulties)
        standard_difficulties = [convert_difficulty(d) for d in diffs.get("standard", [])]
        dx_difficulties = [convert_difficulty(d) for d in diffs.get("dx", [])]
        utage_difficulties = [SongDifficultyUtage(**d) for d in diffs.get("utage", [])] if diffs.get("utage") else None
        return MaiSong(
            id=row.id,
            title=row.title,
            artist=row.artist,
            genre=row.genre,
            bpm=row.bpm,
            map=row.map,
            version=row.version,
            difficulties=SongDifficulties(standard=standard_difficulties, dx=dx_difficulties, utage=utage_difficulties),
        )

    @staticmethod
    async def save_song_info(session: async_scoped_session, song: MaiSong) -> None:
        """
        保存曲目信息到数据库
        """
        difficulties_dict = {
            "standard": [asdict(d) for d in song.difficulties.standard],
            "dx": [asdict(d) for d in song.difficulties.dx],
            "utage": [asdict(d) for d in song.difficulties.utage] if song.difficulties.utage else [],
        }
        song_obj = MaiSongORMModel(
            id=song.id,
            title=song.title,
            artist=song.artist,
            genre=song.genre,
            bpm=song.bpm,
            map=song.map,
            version=song.version,
            # ORM 列为 String，这里序列化为 JSON 字符串
            difficulties=json.dumps(difficulties_dict, ensure_ascii=False),
        )
        session.add(song_obj)
        await session.commit()
        MaiSongORM.update_cache(song)

    @staticmethod
    async def save_song_info_batch(session: async_scoped_session, songs: list[MaiSong]) -> None:
        """
        批量保存曲目信息到数据库，如果存在则更新
        """
        if not songs:
            return

        # 查询已存在的记录
        song_ids = [song.id for song in songs]
        result = await session.execute(select(MaiSongORMModel).where(MaiSongORMModel.id.in_(song_ids)))
        existing_map = {s.id: s for s in result.scalars().all()}

        for song in songs:
            difficulties_dict = {
                "standard": [asdict(d) for d in song.difficulties.standard],
                "dx": [asdict(d) for d in song.difficulties.dx],
                "utage": [asdict(d) for d in song.difficulties.utage] if song.difficulties.utage else [],
            }
            difficulties_json = json.dumps(difficulties_dict, ensure_ascii=False)

            if song.id in existing_map:
                # 更新现有记录
                existing_obj = existing_map[song.id]
                existing_obj.title = song.title
                existing_obj.artist = song.artist
                existing_obj.genre = song.genre
                existing_obj.bpm = song.bpm
                existing_obj.map = song.map
                existing_obj.version = song.version
                existing_obj.difficulties = difficulties_json  # type: ignore
            else:
                # 插入新记录
                song_obj = MaiSongORMModel(
                    id=song.id,
                    title=song.title,
                    artist=song.artist,
                    genre=song.genre,
                    bpm=song.bpm,
                    map=song.map,
                    version=song.version,
                    # ORM 列为 String，这里序列化为 JSON 字符串
                    difficulties=difficulties_json,
                )
                session.add(song_obj)

        await session.commit()
        for song in songs:
            MaiSongORM.update_cache(song)

    @staticmethod
    async def get_song_info(session: async_scoped_session, song_id: int) -> MaiSong:
        """
        获取曲目信息，如果数据库中不存在则从远程获取并保存

        :param song_id: 曲目 ID
        """
        if song_id in MaiSongORM._cache:
            return MaiSongORM._cache[song_id]

        result = await session.execute(select(MaiSongORMModel).where(MaiSongORMModel.id == song_id))
        song_row = result.scalar_one_or_none()
        if song_row:
            return MaiSongORM._convert(song_row)

        logger.warning(f"曲目 ID {song_id} 不存在于数据库，正在从远程获取...")
        from ..updater.songs import fetch_song_info

        song_info = await fetch_song_info(song_id)
        await MaiSongORM.save_song_info(session, song_info)
        return song_info

    @staticmethod
    async def get_songs_info_by_ids(session: async_scoped_session, song_ids: list[int]) -> list[MaiSong]:
        """
        批量获取曲目信息：
        - 先用 IN 查询一次性取回数据库中已有的记录；
        - 对缺失的 ID 再调用远程接口获取并落库；
        - 返回顺序与传入的 song_ids 一致，并去重。
        """
        if not song_ids:
            return []

        # 去重但保持原始顺序
        ordered_unique_ids: list[int] = []
        seen_ids: set[int] = set()
        for sid in song_ids:
            sid_int = int(sid)
            if sid_int not in seen_ids:
                seen_ids.add(sid_int)
                ordered_unique_ids.append(sid_int)

        result = await session.execute(select(MaiSongORMModel).where(MaiSongORMModel.id.in_(ordered_unique_ids)))
        rows = result.scalars().all()

        # 已有记录映射
        id_to_song: dict[int, MaiSong] = {row.id: MaiSongORM._convert(row) for row in rows}

        # 远程补齐缺失记录
        missing_ids = [sid for sid in ordered_unique_ids if sid not in id_to_song]
        for mid in missing_ids:
            logger.warning(f"曲目 ID {mid} 不存在于数据库，正在从远程获取...")
            from ..updater.songs import fetch_song_info

            fetched = await fetch_song_info(mid)
            await MaiSongORM.save_song_info(session, fetched)
            id_to_song[mid] = fetched

        return [id_to_song[sid] for sid in ordered_unique_ids if sid in id_to_song]

    @staticmethod
    async def get_song_info_by_name_or_alias(session: async_scoped_session, name_or_alias: str) -> list[MaiSong]:
        """
        通过乐曲名称或别名获取曲目信息

        :param name_or_alias: 乐曲名称或别名
        :return: 曲目信息 或 None
        """
        # 先尝试通过乐曲名称查找
        result = await session.execute(select(MaiSongORMModel).where(MaiSongORMModel.title.ilike(f"%{name_or_alias}%")))
        song_rows = result.scalars().all()
        songs = []
        if song_rows:
            songs = [MaiSongORM._convert(row) for row in song_rows]
        else:
            # 如果名称查找失败，则通过别名查找
            songs = await MaiSongAliasORM.find_song_by_alias(session, name_or_alias)

        for song in songs:
            # 如果存在精确匹配的结果，直接忽略别的模糊匹配结果
            if song.title == name_or_alias:
                return [song]

        return songs

    @staticmethod
    async def get_all_song_ids(session: async_scoped_session) -> Sequence[int]:
        """
        获取数据库中所有曲目的 ID 列表
        """
        result = await session.execute(select(MaiSongORMModel.id))
        song_ids = result.scalars().all()
        return song_ids


class MaiSongAliasORM:
    @staticmethod
    async def get_aliases(session: async_scoped_session, song_id: int) -> list[str]:
        """
        获取曲目的所有别名

        :param song_id: 曲目 ID
        """
        result = await session.execute(
            select(MaiSongAlias.alias, MaiSongAlias.custom_alias).where(MaiSongAlias.song_id == song_id)
        )
        alias_row = result.one_or_none()
        if not alias_row:
            return []
        aliases = json.loads(alias_row[0]) if alias_row[0] else []
        custom_aliases = json.loads(alias_row[1]) if alias_row[1] else []
        return list(set(aliases + custom_aliases))

    @staticmethod
    async def update_aliases(
        session: async_scoped_session, song_id: int, aliases: list[str], commit: bool = True
    ) -> None:
        """
        更新曲目的别名列表

        :param song_id: 曲目 ID
        :param aliases: 新的别名列表
        :param commit: 是否在更新后提交事务
        """
        await session.execute(
            update(MaiSongAlias)
            .where(MaiSongAlias.song_id == song_id)
            .values(alias=json.dumps(aliases, ensure_ascii=False))
        )

        if commit:
            await session.commit()

    @staticmethod
    async def add_custom_alias(session: async_scoped_session, song_id: int, custom_alias: str) -> None:
        """
        添加自定义别名到曲目

        :param song_id: 曲目 ID
        :param custom_alias: 自定义别名
        """
        result = await session.execute(select(MaiSongAlias).where(MaiSongAlias.song_id == song_id))
        alias_entry = result.scalar_one_or_none()
        if alias_entry:
            current_custom_aliases = json.loads(alias_entry.custom_alias) if alias_entry.custom_alias else []
            if custom_alias not in current_custom_aliases:
                current_custom_aliases.append(custom_alias)
                alias_entry.custom_alias = json.dumps(current_custom_aliases, ensure_ascii=False)
                session.add(alias_entry)
        else:
            new_alias_entry = MaiSongAlias(
                song_id=song_id, alias="[]", custom_alias=json.dumps([custom_alias], ensure_ascii=False)
            )
            session.add(new_alias_entry)
        await session.commit()

    @staticmethod
    async def add_alias_batch(session: async_scoped_session, song_to_aliases: "list[MusicAliasResponseItem]") -> None:
        """
        批量添加曲目别名

        :param song_to_aliases: 曲目 ID 到别名列表的映射
        """
        for item in song_to_aliases:
            song_id = item["song_id"]
            aliases = item["aliases"]
            if not aliases:
                continue

            # 如果已有记录则更新别名列表
            if (
                await session.execute(select(MaiSongAlias).where(MaiSongAlias.song_id == song_id))
            ).scalar_one_or_none():
                await MaiSongAliasORM.update_aliases(session, song_id, aliases, commit=False)
                continue

            alias_entry = MaiSongAlias(song_id=song_id, alias=json.dumps(aliases, ensure_ascii=False))
            session.add(alias_entry)

        await session.commit()

    @staticmethod
    async def find_song_by_alias(session: async_scoped_session, alias: str) -> list[MaiSong]:
        """
        通过别名查找曲目信息

        :param alias: 曲目别名
        :return: 曲目信息 或 None
        """
        # 仅选择需要的列，避免在异步环境中触发 ORM 懒加载（MissingGreenlet）
        result = await session.execute(select(MaiSongAlias.song_id).where(MaiSongAlias.alias.like(f"%{alias}%")))
        song_ids = result.scalars().all()
        if not song_ids:
            return []

        # 批量获取已存在的记录，并保持输入顺序
        return await MaiSongORM.get_songs_info_by_ids(session, [int(sid) for sid in song_ids])


class MaiPlayCountORM:
    @staticmethod
    async def upsert_user_play_counts(
        session: async_scoped_session, user_id: str, records: list[tuple[int, int, int]]
    ) -> int:
        """
        批量写入用户游玩次数。

        :param records: (song_id, difficulty, play_count)
        :return: 实际处理的记录数量
        """
        if not records:
            return 0

        unique_map: dict[tuple[int, int], int] = {}
        for song_id, difficulty, play_count in records:
            unique_map[(song_id, difficulty)] = play_count

        updated = len(unique_map)

        song_ids = [key[0] for key in unique_map]
        result = await session.execute(
            select(MaiPlayCount).where(MaiPlayCount.user_id == user_id, MaiPlayCount.song_id.in_(song_ids))
        )
        existing_rows = result.scalars().all()
        existing_map = {(row.song_id, row.difficulty): row for row in existing_rows}

        for (song_id, difficulty), play_count in unique_map.items():
            row = existing_map.get((song_id, difficulty))
            if row and row.play_count != play_count:
                row.play_count = play_count
            elif not row:
                session.add(
                    MaiPlayCount(
                        user_id=user_id,
                        song_id=song_id,
                        difficulty=difficulty,
                        play_count=play_count,
                    )
                )
            else:
                updated -= 1

        await session.commit()
        return updated

    @staticmethod
    async def get_user_play_count_map(
        session: async_scoped_session, user_id: str, song_ids: list[int]
    ) -> dict[tuple[int, int], int]:
        """
        获取用户游玩次数映射
        """
        if not song_ids:
            return {}

        result = await session.execute(
            select(MaiPlayCount).where(MaiPlayCount.user_id == user_id, MaiPlayCount.song_id.in_(song_ids))
        )
        rows = result.scalars().all()
        return {(row.song_id, row.difficulty): row.play_count for row in rows}

    @staticmethod
    async def get_all_user_play_counts(session: async_scoped_session, user_id: str) -> Sequence[MaiPlayCount]:
        """
        获取用户所有游玩次数记录
        """
        result = await session.execute(select(MaiPlayCount).where(MaiPlayCount.user_id == user_id))
        rows = result.scalars().all()
        return rows
