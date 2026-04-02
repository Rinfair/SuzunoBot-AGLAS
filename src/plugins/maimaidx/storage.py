from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Sequence

from nonebot import logger
from nonebot_plugin_orm import Model, async_scoped_session
from sqlalchemy import ForeignKey, Integer, String, inspect, select, update
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import CreateColumn
from typing_extensions import Literal, TypedDict

from .models.song import (
    MaiSong as MaiSongData,
    SongDifficulties as SongDifficultiesData,
    SongDifficulty,
    SongDifficultyUtage,
    SongNotes,
)

if TYPE_CHECKING:
    from .updater.songs import MusicAliasResponseItem

LEGACY_PROFILE_FILE = Path(__file__).resolve().parents[3] / "data" / "maimaidx" / "profile.json"


class SongDifficulties(TypedDict):
    standard: list
    dx: list
    utage: list


class UserBindInfo(Model):
    __tablename__ = "maimaidx_userbindinfo"

    user_id: Mapped[str] = mapped_column(primary_key=True)
    default_provider: Mapped[Literal["lxns", "divingfish"]] = mapped_column(String, nullable=True, default="lxns")
    friend_code: Mapped[str] = mapped_column(String, nullable=True, default="")
    lxns_api_key: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="")
    diving_fish_import_token: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="")
    diving_fish_username: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="")
    maimaipy_identifier: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="")


class MaiSongRecord(Model):
    __tablename__ = "maimaidx_maisong"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    artist: Mapped[str] = mapped_column(String, nullable=False)
    genre: Mapped[str] = mapped_column(String, nullable=False)
    bpm: Mapped[int] = mapped_column(Integer, nullable=False)
    map: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    locked: Mapped[bool] = mapped_column(nullable=True, default=False)
    disabled: Mapped[bool] = mapped_column(nullable=True, default=False)
    difficulties: Mapped[SongDifficulties] = mapped_column(String, nullable=False)

    alias_entry: Mapped["MaiSongAlias"] = relationship("MaiSongAlias", back_populates="song", uselist=False)


class MaiSongAlias(Model):
    __tablename__ = "maimaidx_maisongalias"

    song_id: Mapped[int] = mapped_column(ForeignKey("maimaidx_maisong.id"), primary_key=True)
    alias: Mapped[str] = mapped_column(String, nullable=True, default="[]")
    custom_alias: Mapped[str] = mapped_column(String, nullable=True, default="[]")

    song: Mapped["MaiSongRecord"] = relationship("MaiSongRecord", back_populates="alias_entry")


class MaiPlayCount(Model):
    __tablename__ = "maimaidx_playcount"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    song_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    difficulty: Mapped[int] = mapped_column(Integer, primary_key=True)
    play_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class MaiUserProfile(Model):
    __tablename__ = "maimaidx_userprofile"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    plate_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    preferences_json: Mapped[str] = mapped_column(String, nullable=False, default="{}")


class UserBindInfoORM:
    @staticmethod
    async def get_user_bind_info(session: async_scoped_session, user_id: str) -> Optional[UserBindInfo]:
        result = await session.execute(select(UserBindInfo).where(UserBindInfo.user_id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def set_user_friend_code(session: async_scoped_session, user_id: str, friend_code: str) -> None:
        bind_info = await UserBindInfoORM.get_user_bind_info(session, user_id)
        if bind_info:
            await session.execute(
                update(UserBindInfo).where(UserBindInfo.user_id == user_id).values(friend_code=friend_code)
            )
        else:
            session.add(UserBindInfo(user_id=user_id, friend_code=friend_code))
        await session.commit()

    @staticmethod
    async def set_lxns_api_key(session: async_scoped_session, user_id: str, api_key: str) -> None:
        bind_info = await UserBindInfoORM.get_user_bind_info(session, user_id)
        if bind_info:
            await session.execute(
                update(UserBindInfo).where(UserBindInfo.user_id == user_id).values(lxns_api_key=api_key)
            )
        else:
            session.add(UserBindInfo(user_id=user_id, lxns_api_key=api_key))
        await session.commit()

    @staticmethod
    async def set_diving_fish_import_token(
        session: async_scoped_session,
        user_id: str,
        import_token: str,
        diving_fish_username: str,
    ) -> None:
        bind_info = await UserBindInfoORM.get_user_bind_info(session, user_id)
        if bind_info:
            await session.execute(
                update(UserBindInfo)
                .where(UserBindInfo.user_id == user_id)
                .values(diving_fish_import_token=import_token, diving_fish_username=diving_fish_username)
            )
        else:
            session.add(
                UserBindInfo(
                    user_id=user_id,
                    diving_fish_import_token=import_token,
                    diving_fish_username=diving_fish_username,
                )
            )
        await session.commit()

    @staticmethod
    async def set_maimaipy_identifier(session: async_scoped_session, user_id: str, maimaipy_identifier: str) -> None:
        bind_info = await UserBindInfoORM.get_user_bind_info(session, user_id)
        if bind_info:
            await session.execute(
                update(UserBindInfo)
                .where(UserBindInfo.user_id == user_id)
                .values(maimaipy_identifier=maimaipy_identifier)
            )
        else:
            session.add(UserBindInfo(user_id=user_id, maimaipy_identifier=maimaipy_identifier))
        await session.commit()

    @staticmethod
    async def set_default_provider(
        session: async_scoped_session,
        user_id: str,
        provider: Literal["lxns", "divingfish"],
    ) -> None:
        bind_info = await UserBindInfoORM.get_user_bind_info(session, user_id)
        if not bind_info:
            raise ValueError("用户未绑定任何查分器账号，无法设置默认查分器")
        if provider == "lxns" and not bind_info.lxns_api_key:
            raise ValueError("用户未设置落雪咖啡屋 API 密钥，无法设置为默认查分器")
        if provider == "divingfish" and not bind_info.diving_fish_import_token:
            raise ValueError("用户未设置水鱼查分器导入密钥，无法设置为默认查分器")
        await session.execute(
            update(UserBindInfo).where(UserBindInfo.user_id == user_id).values(default_provider=provider)
        )
        await session.commit()

    @staticmethod
    async def unset_user_bind_info(
        session: async_scoped_session,
        user_id: str,
        provider: Optional[Literal["lxns", "divingfish", "maimai"]] = None,
    ) -> None:
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
    _cache: dict[int, MaiSongData] = {}

    @classmethod
    def get_song_sync(cls, song_id: int) -> Optional[MaiSongData]:
        return cls._cache.get(song_id)

    @classmethod
    def update_cache(cls, song: MaiSongData) -> None:
        cls._cache[song.id] = song

    @staticmethod
    async def refresh_cache(session: async_scoped_session) -> None:
        result = await session.execute(select(MaiSongRecord))
        rows = result.scalars().all()
        MaiSongORM._cache.clear()
        for row in rows:
            song = MaiSongORM._convert(row)
            MaiSongORM.update_cache(song)

    @staticmethod
    def _convert(row: MaiSongRecord) -> MaiSongData:
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

        diffs = row.difficulties if isinstance(row.difficulties, dict) else json.loads(row.difficulties)
        standard_difficulties = [convert_difficulty(d) for d in diffs.get("standard", [])]
        dx_difficulties = [convert_difficulty(d) for d in diffs.get("dx", [])]
        utage_difficulties = [SongDifficultyUtage(**d) for d in diffs.get("utage", [])] if diffs.get("utage") else None
        return MaiSongData(
            id=row.id,
            title=row.title,
            artist=row.artist,
            genre=row.genre,
            bpm=row.bpm,
            map=row.map,
            version=row.version,
            difficulties=SongDifficultiesData(
                standard=standard_difficulties,
                dx=dx_difficulties,
                utage=utage_difficulties,
            ),
        )

    @staticmethod
    async def save_song_info(session: async_scoped_session, song: MaiSongData) -> None:
        difficulties_dict = {
            "standard": [asdict(d) for d in song.difficulties.standard],
            "dx": [asdict(d) for d in song.difficulties.dx],
            "utage": [asdict(d) for d in song.difficulties.utage] if song.difficulties.utage else [],
        }
        song_obj = MaiSongRecord(
            id=song.id,
            title=song.title,
            artist=song.artist,
            genre=song.genre,
            bpm=song.bpm,
            map=song.map,
            version=song.version,
            difficulties=json.dumps(difficulties_dict, ensure_ascii=False),
        )
        session.add(song_obj)
        await session.commit()
        MaiSongORM.update_cache(song)

    @staticmethod
    async def save_song_info_batch(session: async_scoped_session, songs: list[MaiSongData]) -> None:
        if not songs:
            return

        song_ids = [song.id for song in songs]
        result = await session.execute(select(MaiSongRecord).where(MaiSongRecord.id.in_(song_ids)))
        existing_map = {song.id: song for song in result.scalars().all()}

        for song in songs:
            difficulties_dict = {
                "standard": [asdict(d) for d in song.difficulties.standard],
                "dx": [asdict(d) for d in song.difficulties.dx],
                "utage": [asdict(d) for d in song.difficulties.utage] if song.difficulties.utage else [],
            }
            difficulties_json = json.dumps(difficulties_dict, ensure_ascii=False)

            if song.id in existing_map:
                existing = existing_map[song.id]
                existing.title = song.title
                existing.artist = song.artist
                existing.genre = song.genre
                existing.bpm = song.bpm
                existing.map = song.map
                existing.version = song.version
                existing.difficulties = difficulties_json  # type: ignore[assignment]
            else:
                session.add(
                    MaiSongRecord(
                        id=song.id,
                        title=song.title,
                        artist=song.artist,
                        genre=song.genre,
                        bpm=song.bpm,
                        map=song.map,
                        version=song.version,
                        difficulties=difficulties_json,
                    )
                )

        await session.commit()
        for song in songs:
            MaiSongORM.update_cache(song)

    @staticmethod
    async def get_song_info(session: async_scoped_session, song_id: int) -> MaiSongData:
        if song_id in MaiSongORM._cache:
            return MaiSongORM._cache[song_id]

        result = await session.execute(select(MaiSongRecord).where(MaiSongRecord.id == song_id))
        song_row = result.scalar_one_or_none()
        if song_row:
            song = MaiSongORM._convert(song_row)
            MaiSongORM.update_cache(song)
            return song

        logger.warning(f"曲目 ID {song_id} 不存在于数据库，正在从远程获取...")
        from .updater.songs import fetch_song_info

        song_info = await fetch_song_info(song_id)
        await MaiSongORM.save_song_info(session, song_info)
        return song_info

    @staticmethod
    async def get_songs_info_by_ids(session: async_scoped_session, song_ids: list[int]) -> list[MaiSongData]:
        if not song_ids:
            return []

        ordered_unique_ids: list[int] = []
        seen_ids: set[int] = set()
        for sid in song_ids:
            sid_int = int(sid)
            if sid_int not in seen_ids:
                seen_ids.add(sid_int)
                ordered_unique_ids.append(sid_int)

        result = await session.execute(select(MaiSongRecord).where(MaiSongRecord.id.in_(ordered_unique_ids)))
        rows = result.scalars().all()

        id_to_song: dict[int, MaiSongData] = {}
        for row in rows:
            song = MaiSongORM._convert(row)
            id_to_song[row.id] = song
            MaiSongORM.update_cache(song)

        missing_ids = [sid for sid in ordered_unique_ids if sid not in id_to_song]
        for missing_id in missing_ids:
            logger.warning(f"曲目 ID {missing_id} 不存在于数据库，正在从远程获取...")
            from .updater.songs import fetch_song_info

            fetched = await fetch_song_info(missing_id)
            await MaiSongORM.save_song_info(session, fetched)
            id_to_song[missing_id] = fetched

        return [id_to_song[sid] for sid in ordered_unique_ids if sid in id_to_song]

    @staticmethod
    async def get_song_info_by_name_or_alias(session: async_scoped_session, name_or_alias: str) -> list[MaiSongData]:
        result = await session.execute(select(MaiSongRecord).where(MaiSongRecord.title.ilike(f"%{name_or_alias}%")))
        song_rows = result.scalars().all()
        if song_rows:
            songs = [MaiSongORM._convert(row) for row in song_rows]
            for song in songs:
                MaiSongORM.update_cache(song)
        else:
            songs = await MaiSongAliasORM.find_song_by_alias(session, name_or_alias)

        for song in songs:
            if song.title == name_or_alias:
                return [song]
        return songs

    @staticmethod
    async def get_all_song_ids(session: async_scoped_session) -> Sequence[int]:
        result = await session.execute(select(MaiSongRecord.id))
        return result.scalars().all()


class MaiSongAliasORM:
    @staticmethod
    async def get_aliases(session: async_scoped_session, song_id: int) -> list[str]:
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
        session: async_scoped_session,
        song_id: int,
        aliases: list[str],
        commit: bool = True,
    ) -> None:
        await session.execute(
            update(MaiSongAlias)
            .where(MaiSongAlias.song_id == song_id)
            .values(alias=json.dumps(aliases, ensure_ascii=False))
        )
        if commit:
            await session.commit()

    @staticmethod
    async def add_custom_alias(session: async_scoped_session, song_id: int, custom_alias: str) -> None:
        result = await session.execute(select(MaiSongAlias).where(MaiSongAlias.song_id == song_id))
        alias_entry = result.scalar_one_or_none()
        if alias_entry:
            current_custom_aliases = json.loads(alias_entry.custom_alias) if alias_entry.custom_alias else []
            if custom_alias not in current_custom_aliases:
                current_custom_aliases.append(custom_alias)
                alias_entry.custom_alias = json.dumps(current_custom_aliases, ensure_ascii=False)
                session.add(alias_entry)
        else:
            session.add(MaiSongAlias(song_id=song_id, alias="[]", custom_alias=json.dumps([custom_alias], ensure_ascii=False)))
        await session.commit()

    @staticmethod
    async def add_alias_batch(session: async_scoped_session, song_to_aliases: "list[MusicAliasResponseItem]") -> None:
        for item in song_to_aliases:
            song_id = item["song_id"]
            aliases = item["aliases"]
            if not aliases:
                continue

            existing = await session.execute(select(MaiSongAlias).where(MaiSongAlias.song_id == song_id))
            if existing.scalar_one_or_none():
                await MaiSongAliasORM.update_aliases(session, song_id, aliases, commit=False)
                continue

            session.add(MaiSongAlias(song_id=song_id, alias=json.dumps(aliases, ensure_ascii=False)))

        await session.commit()

    @staticmethod
    async def find_song_by_alias(session: async_scoped_session, alias: str) -> list[MaiSongData]:
        result = await session.execute(select(MaiSongAlias.song_id).where(MaiSongAlias.alias.like(f"%{alias}%")))
        song_ids = result.scalars().all()
        if not song_ids:
            return []
        return await MaiSongORM.get_songs_info_by_ids(session, [int(song_id) for song_id in song_ids])


class MaiPlayCountORM:
    @staticmethod
    async def upsert_user_play_counts(
        session: async_scoped_session,
        user_id: str,
        records: list[tuple[int, int, int]],
    ) -> int:
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
        session: async_scoped_session,
        user_id: str,
        song_ids: list[int],
    ) -> dict[tuple[int, int], int]:
        if not song_ids:
            return {}

        result = await session.execute(
            select(MaiPlayCount).where(MaiPlayCount.user_id == user_id, MaiPlayCount.song_id.in_(song_ids))
        )
        rows = result.scalars().all()
        return {(row.song_id, row.difficulty): row.play_count for row in rows}

    @staticmethod
    async def get_all_user_play_counts(session: async_scoped_session, user_id: str) -> Sequence[MaiPlayCount]:
        result = await session.execute(select(MaiPlayCount).where(MaiPlayCount.user_id == user_id))
        return result.scalars().all()


class MaiUserProfileORM:
    @staticmethod
    def _normalize_plate_number(plate_number: object) -> int:
        try:
            value = int(plate_number)
        except (TypeError, ValueError):
            return 1
        return value if value > 0 else 1

    @staticmethod
    async def get_user_profile(session: async_scoped_session, user_id: str) -> Optional[MaiUserProfile]:
        result = await session.execute(select(MaiUserProfile).where(MaiUserProfile.user_id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_or_create_user_profile(session: async_scoped_session, user_id: str) -> MaiUserProfile:
        profile = await MaiUserProfileORM.get_user_profile(session, user_id)
        if profile is not None:
            return profile

        profile = MaiUserProfile(user_id=user_id, plate_number=1, preferences_json="{}")
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        return profile

    @staticmethod
    async def get_user_plate_number(session: async_scoped_session, user_id: str) -> int:
        result = await session.execute(select(MaiUserProfile.plate_number).where(MaiUserProfile.user_id == user_id))
        plate_number = result.scalar_one_or_none()
        if plate_number is None:
            session.add(MaiUserProfile(user_id=user_id, plate_number=1, preferences_json="{}"))
            await session.commit()
            return 1
        return MaiUserProfileORM._normalize_plate_number(plate_number)

    @staticmethod
    async def set_user_plate_number(session: async_scoped_session, user_id: str, plate_number: int) -> int:
        normalized_plate_number = MaiUserProfileORM._normalize_plate_number(plate_number)
        profile = await MaiUserProfileORM.get_user_profile(session, user_id)
        if profile is None:
            session.add(
                MaiUserProfile(
                    user_id=user_id,
                    plate_number=normalized_plate_number,
                    preferences_json="{}",
                )
            )
        else:
            await session.execute(
                update(MaiUserProfile)
                .where(MaiUserProfile.user_id == user_id)
                .values(plate_number=normalized_plate_number)
            )
        await session.commit()
        return normalized_plate_number


async def get_user_profile_plate(session: async_scoped_session, user_id: str) -> int:
    return await MaiUserProfileORM.get_user_plate_number(session, user_id)


async def set_user_profile_plate(session: async_scoped_session, user_id: str, plate_number: int) -> int:
    return await MaiUserProfileORM.set_user_plate_number(session, user_id, plate_number)


def load_legacy_profile_data() -> dict[str, dict[str, int]]:
    if not LEGACY_PROFILE_FILE.exists():
        return {}
    try:
        data = json.loads(LEGACY_PROFILE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def legacy_profile_file() -> Path:
    return LEGACY_PROFILE_FILE


async def ensure_database_schema(session: async_scoped_session) -> None:
    async with session.bind.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)
        await conn.run_sync(_repair_missing_columns)
    await migrate_legacy_profile_data(session)


def _repair_missing_columns(sync_conn) -> None:
    inspector = inspect(sync_conn)
    existing_tables = set(inspector.get_table_names())
    for table in Model.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue

        existing_columns = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing_columns or column.primary_key:
                continue

            column_sql = str(CreateColumn(column).compile(dialect=sync_conn.dialect)).strip()
            if not column_sql:
                continue

            logger.warning(f"检测到表 {table.name} 缺少列 {column.name}，正在自动补齐")
            sync_conn.exec_driver_sql(f"ALTER TABLE {table.name} ADD COLUMN {column_sql}")


async def migrate_legacy_profile_data(session: async_scoped_session) -> None:
    legacy_data = load_legacy_profile_data()
    if not legacy_data:
        return

    migrated_count = 0
    for user_id, payload in legacy_data.items():
        if not isinstance(payload, dict):
            continue
        plate_number = payload.get("plate_number", 1)
        profile = await MaiUserProfileORM.get_user_profile(session, user_id)
        if profile is not None:
            continue
        await MaiUserProfileORM.set_user_plate_number(session, user_id, int(plate_number))
        migrated_count += 1

    if migrated_count:
        logger.info(f"已从 legacy profile.json 迁移 {migrated_count} 条用户自定义配置")


__all__ = [
    "UserBindInfo",
    "MaiSongRecord",
    "MaiSongAlias",
    "MaiPlayCount",
    "MaiUserProfile",
    "UserBindInfoORM",
    "MaiSongORM",
    "MaiSongAliasORM",
    "MaiPlayCountORM",
    "MaiUserProfileORM",
    "get_user_profile_plate",
    "set_user_profile_plate",
    "load_legacy_profile_data",
    "legacy_profile_file",
    "ensure_database_schema",
]
