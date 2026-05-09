from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

from aiohttp import ClientSession, ClientTimeout
from typing_extensions import TypedDict

from ..config import config
from ..constants import USER_AGENT

_SONG_TAGS_FILE = Path(config.static_resource_path) / "combined_tags.json"
SONG_TAGS_SOURCE_URL = "https://miruku.dxrating.net/api/v1/tags"


class DxRatingTag(TypedDict):
    id: int
    localized_name: dict[str, str]
    localized_description: dict[str, str]
    group_id: int


class DxRatingTagGroup(TypedDict):
    id: int
    localized_name: dict[str, str]


class DxRatingTagSong(TypedDict):
    song_id: str
    """In fact, this is song name."""
    sheet_type: Literal["dx", "std"]
    sheet_difficulty: Literal["remaster", "master", "expert"]
    tag_id: int


class DxRatingCombinedTags(TypedDict):
    tags: list[DxRatingTag]
    tagGroups: list[DxRatingTagGroup]
    tagSongs: list[DxRatingTagSong]


_EMPTY_SONG_TAGS_DATA: DxRatingCombinedTags = {
    "tags": [],
    "tagGroups": [],
    "tagSongs": [],
}
_SONG_TAGS_DATA: DxRatingCombinedTags = _EMPTY_SONG_TAGS_DATA
_SONG_TAGS_LOAD_ERROR: str | None = None


def _validate_song_tags_data(data: object) -> DxRatingCombinedTags:
    if not isinstance(data, dict):
        raise ValueError("乐曲标签数据格式错误：根对象必须是 JSON object")

    for key in ("tags", "tagGroups", "tagSongs"):
        if not isinstance(data.get(key), list):
            raise ValueError(f"乐曲标签数据格式错误：缺少列表字段 {key}")

    return data  # type: ignore[return-value]


def _set_song_tags_data(data: DxRatingCombinedTags) -> None:
    global _SONG_TAGS_DATA, _SONG_TAGS_LOAD_ERROR
    _SONG_TAGS_DATA = data
    _SONG_TAGS_LOAD_ERROR = None


def load_song_tags_data() -> bool:
    """Load song tag data from static/combined_tags.json."""

    global _SONG_TAGS_DATA, _SONG_TAGS_LOAD_ERROR

    if not _SONG_TAGS_FILE.exists() or _SONG_TAGS_FILE.stat().st_size <= 0:
        _SONG_TAGS_DATA = _EMPTY_SONG_TAGS_DATA
        _SONG_TAGS_LOAD_ERROR = f"未找到乐曲标签文件: {_SONG_TAGS_FILE}"
        return False

    try:
        data = json.loads(_SONG_TAGS_FILE.read_text(encoding="utf-8"))
        _set_song_tags_data(_validate_song_tags_data(data))
    except Exception as exc:
        _SONG_TAGS_DATA = _EMPTY_SONG_TAGS_DATA
        _SONG_TAGS_LOAD_ERROR = str(exc)
        return False

    return True


class _SongTagsAvailability:
    def __bool__(self) -> bool:
        return bool(_SONG_TAGS_DATA.get("tags") and _SONG_TAGS_DATA.get("tagSongs"))

    def __repr__(self) -> str:
        return str(bool(self))

    def __str__(self) -> str:
        return str(bool(self))


SONG_TAGS_DATA_AVAILABLE = _SongTagsAvailability()


def get_song_tags_file_path() -> Path:
    return _SONG_TAGS_FILE


def get_song_tags_load_error() -> str | None:
    return _SONG_TAGS_LOAD_ERROR


async def download_song_tags_data(source_url: str = SONG_TAGS_SOURCE_URL) -> DxRatingCombinedTags:
    """Download DXRating song tags into static/combined_tags.json and reload them."""

    timeout = ClientTimeout(total=45)
    headers = {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }

    async with ClientSession(timeout=timeout, headers=headers) as session:
        async with session.get(source_url) as response:
            if response.status >= 400:
                raise RuntimeError(f"下载乐曲标签失败：HTTP {response.status}")
            data = await response.json(content_type=None)

    validated = _validate_song_tags_data(data)
    _SONG_TAGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SONG_TAGS_FILE.write_text(json.dumps(validated, ensure_ascii=False), encoding="utf-8")
    _set_song_tags_data(validated)
    return validated


load_song_tags_data()


def get_songs_tags(
    song_name: str, song_type: Literal["dx", "std"], song_difficulty: Literal["remaster", "master", "expert"]
) -> list[str]:
    if not SONG_TAGS_DATA_AVAILABLE:
        return []

    tags = []
    for tag_song in _SONG_TAGS_DATA.get("tagSongs", []):
        if (
            tag_song["song_id"] == song_name
            and tag_song["sheet_type"] == song_type
            and tag_song["sheet_difficulty"] == song_difficulty.lower()
        ):
            tag_id = tag_song["tag_id"]
            for tag in _SONG_TAGS_DATA.get("tags", []):
                if tag["id"] == tag_id:
                    tags.append(tag["localized_name"].get("zh-Hans", "未知标签"))
                    break
    return tags


def get_song_by_tags(
    tags: list[str],
    song_type: Optional[Literal["dx", "std"]] = None,
    song_difficulty: Optional[Literal["remaster", "master", "expert"]] = None,
) -> list[str]:
    if not SONG_TAGS_DATA_AVAILABLE:
        return []

    song_names = []
    tag_ids = []
    for tag in _SONG_TAGS_DATA.get("tags", []):
        if tag["localized_name"].get("zh-Hans", "未知标签") in tags:
            tag_ids.append(tag["id"])
    for tag_song in _SONG_TAGS_DATA.get("tagSongs", []):
        if tag_song["tag_id"] in tag_ids:
            if song_type and tag_song["sheet_type"] != song_type:
                continue
            if song_difficulty and tag_song["sheet_difficulty"] != song_difficulty:
                continue
            song_names.append(tag_song["song_id"])
    return list(set(song_names))
