from typing import Optional

from nonebot_plugin_orm import Model
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing_extensions import Literal, TypedDict


class SongDifficulties(TypedDict):
    standard: list
    """曲目标准谱面难度列表"""
    dx: list
    """曲目 DX 谱面难度列表"""
    utage: list
    """可选，宴会场曲目谱面难度列表"""


class UserBindInfo(Model):
    __tablename__ = "maimaidx_userbindinfo"

    user_id: Mapped[str] = mapped_column(primary_key=True)
    default_provider: Mapped[Literal["lxns", "divingfish"]] = mapped_column(String, nullable=True, default="lxns")
    friend_code: Mapped[str] = mapped_column(String, nullable=True, default="")
    lxns_api_key: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="")
    diving_fish_import_token: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="")
    diving_fish_username: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="")
    maimaipy_identifier: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="")


class MaiSong(Model):
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

    song: Mapped["MaiSong"] = relationship("MaiSong", back_populates="alias_entry")


class MaiPlayCount(Model):
    """玩家铺面游玩次数"""

    __tablename__ = "maimaidx_playcount"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    song_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    difficulty: Mapped[int] = mapped_column(Integer, primary_key=True)
    play_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
