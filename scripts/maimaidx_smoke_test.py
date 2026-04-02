#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Optional

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import bot  # noqa: F401
from maimai_py import DivingFishProvider, PlayerIdentifier
from nonebot_plugin_orm import get_scoped_session

from src.plugins.maimaidx.config import config
from src.plugins.maimaidx.storage import MaiSongAliasORM, MaiSongORM, ensure_database_schema
from src.plugins.maimaidx.functions.analysis import get_player_strength
from src.plugins.maimaidx.functions.fortunate import generate_today_fortune_parts
from src.plugins.maimaidx.functions.maistatus import capture_maimai_status_png
from src.plugins.maimaidx.functions.process import get_level_process_data, get_plate_process_data
from src.plugins.maimaidx.functions.recommend_songs import get_player_raise_score_songs
from src.plugins.maimaidx.renderer import PicRenderer
from src.plugins.maimaidx.score._schema import (
    PlayerMaiB50,
    PlayerMaiInfo,
    PlayerMaiScore,
    ScoreRateType,
    SongDifficulty,
    SongType,
)
from src.plugins.maimaidx.score.providers.diving_fish import DivingFishParams, DivingFishScoreProvider
from src.plugins.maimaidx.score.providers.lxns import LXNSParams, LXNSScoreProvider
from src.plugins.maimaidx.score.providers.maimai import MaimaiPyParams, MaimaiPyScoreProvider
from src.plugins.maimaidx.updater.songs import update_local_chart_file, update_song_alias_list, update_song_database


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str


async def run_check(
    results: list[CheckResult],
    name: str,
    func: Callable[[], Awaitable[str]],
    *,
    allow_fail: bool = False,
) -> None:
    try:
        detail = await func()
    except Exception as exc:
        status = "WARN" if allow_fail else "FAIL"
        results.append(CheckResult(name, status, f"{type(exc).__name__}: {exc}"))
        return

    results.append(CheckResult(name, "PASS", detail))


async def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test for embedded maimaidx plugin")
    parser.add_argument("--with-update", action="store_true", help="Refresh chart file, song DB and alias DB")
    parser.add_argument("--divingfish-username", default="Rikka", help="Public Diving-Fish username for smoke tests")
    parser.add_argument(
        "--lxns-friend-code",
        default=os.getenv("LXNS_TEST_FRIEND_CODE"),
        help="Optional LXNS friend code for success-path tests",
    )
    parser.add_argument(
        "--divingfish-import-token",
        default=os.getenv("DIVINGFISH_TEST_IMPORT_TOKEN"),
        help="Optional Diving-Fish import token for private-score tests",
    )
    parser.add_argument(
        "--arcade-qr-data",
        default=os.getenv("ARCADE_QR_DATA"),
        help="Optional maimai QR payload for arcade-provider tests",
    )
    parser.add_argument("--user-id", default="10000", help="Synthetic user id for local-only tests")
    args = parser.parse_args()

    results: list[CheckResult] = []
    session = get_scoped_session()
    await ensure_database_schema(session)
    await MaiSongORM.refresh_cache(session)
    if not MaiSongORM._cache:
        await update_song_database(session)
        await update_song_alias_list(session)
        await MaiSongORM.refresh_cache(session)

    if args.with_update:
        await run_check(
            results,
            "update_local_chart_file",
            lambda: _check_update_chart(),
        )
        await run_check(
            results,
            "update_song_database",
            lambda: _check_update_song_database(session),
        )
        await run_check(
            results,
            "update_song_alias_list",
            lambda: _check_update_song_alias_list(session),
        )

    song_ids = await MaiSongORM.get_all_song_ids(session)
    if not song_ids:
        print("[FAIL] no songs found in database after automatic bootstrap.")
        return 1

    song = await MaiSongORM.get_song_info(session, min(song_ids))
    aliases = await MaiSongAliasORM.get_aliases(session, song.id)

    async def check_song_lookup() -> str:
        songs = await MaiSongORM.get_song_info_by_name_or_alias(session, song.title)
        return f"song_id={song.id}, aliases={len(aliases)}, title_hits={len(songs)}"

    await run_check(results, "song_lookup", check_song_lookup)

    async def check_maistatus() -> str:
        png = await capture_maimai_status_png(config.maistatus_url)
        return f"png_bytes={len(png)}"

    await run_check(results, "maistatus_capture", check_maistatus)

    async def check_renderer() -> str:
        renderer = PicRenderer(static_dir=config.static_resource_path)
        score = PlayerMaiScore(
            song_id=song.id,
            song_name=song.title,
            song_type=SongType.STANDARD,
            song_level=song.difficulties.standard[0].level,
            song_difficulty=SongDifficulty.BASIC,
            achievements=100.5,
            dx_score=1_000_000,
            dx_star=5,
            dx_rating=100.0,
            rate=ScoreRateType.SSP,
        )
        info = PlayerMaiInfo(name="SmokeTest", rating=15_000)
        song_png = await renderer.render_mai_player_song_info(song, [score])
        scores_png = await renderer.render_mai_player_scores([score], info, "Smoke Scores")
        best_png = await renderer.render_mai_player_best50(PlayerMaiB50(standard=[score], dx=[]), info)
        return f"song={len(song_png)}, scores={len(scores_png)}, best={len(best_png)}"

    await run_check(results, "renderer", check_renderer)

    if config.divingfish_developer_api_key:
        df_provider = DivingFishScoreProvider()
        mm_provider = MaimaiPyScoreProvider()
        mm_params = MaimaiPyParams(
            score_provider=DivingFishProvider(developer_token=config.divingfish_developer_api_key),
            identifier=PlayerIdentifier(username=args.divingfish_username),
        )

        async def check_df_provider() -> str:
            info = await df_provider.fetch_player_info(DivingFishParams(username=args.divingfish_username))
            b50 = await df_provider.fetch_player_b50(DivingFishParams(username=args.divingfish_username))
            return f"name={info.name}, rating={info.rating}, b50={len(b50.standard) + len(b50.dx)}"

        async def check_maimai_public() -> str:
            info = await mm_provider.fetch_player_info(mm_params)
            b50 = await mm_provider.fetch_player_b50(mm_params)
            scores = await mm_provider.fetch_player_scoreslist(mm_params)
            scores_lv = await mm_provider.fetch_player_scoreslist(mm_params, level_value=12.7)
            minfo = await mm_provider.fetch_player_minfo(mm_params, song.id, "standard")
            return (
                f"name={info.name}, rating={info.rating}, "
                f"b50={len(b50.standard) + len(b50.dx)}, "
                f"scores={len(scores)}, level_value={len(scores_lv)}, minfo={len(minfo)}"
            )

        async def check_business_logic() -> str:
            scores = await mm_provider.fetch_player_scoreslist(mm_params)
            songs = list(MaiSongORM._cache.values())
            strength = get_player_strength(scores[:100])
            rec = get_player_raise_score_songs(scores, min_dx_rating=int(scores[49].dx_rating if len(scores) > 49 else 0))
            level_data = get_level_process_data(songs, scores, "12+", "SSS")
            plate_data = get_plate_process_data(songs, scores, "舞", "神")
            fortune = await generate_today_fortune_parts(args.user_id)
            return (
                f"analysis_patterns={sum(strength.patterns_strengths.values())}, "
                f"recommend={len(rec.old_version) + len(rec.new_version)}, "
                f"level_total={level_data.counts['total']}, plate_total={plate_data.total_count}, "
                f"fortune_segments={len(fortune)}"
            )

        await run_check(results, "divingfish_provider_public", check_df_provider)
        await run_check(results, "maimai_py_public", check_maimai_public)
        await run_check(results, "business_logic_public", check_business_logic)

        if args.divingfish_import_token:
            async def check_df_private() -> str:
                ap50 = await df_provider.fetch_player_ap50(
                    DivingFishParams(username=args.divingfish_username, import_token=args.divingfish_import_token)
                )
                return f"ap50={len(ap50.standard) + len(ap50.dx)}"

            await run_check(results, "divingfish_private_ap50", check_df_private, allow_fail=True)
        else:
            results.append(
                CheckResult(
                    "divingfish_private_ap50",
                    "SKIP",
                    "DIVINGFISH_TEST_IMPORT_TOKEN not provided",
                )
            )

        await df_provider.close()
    else:
        results.append(CheckResult("divingfish_provider_public", "SKIP", "divingfish_developer_api_key not configured"))
        results.append(CheckResult("maimai_py_public", "SKIP", "divingfish_developer_api_key not configured"))
        results.append(CheckResult("business_logic_public", "SKIP", "divingfish_developer_api_key not configured"))
        results.append(CheckResult("divingfish_private_ap50", "SKIP", "divingfish_developer_api_key not configured"))

    lxns_provider = LXNSScoreProvider()
    if config.lxns_developer_api_key and args.lxns_friend_code:
        async def check_lxns_success() -> str:
            info = await lxns_provider.fetch_player_info(LXNSParams(friend_code=args.lxns_friend_code))
            b50 = await lxns_provider.fetch_player_b50(LXNSParams(friend_code=args.lxns_friend_code))
            return f"name={info.name}, rating={info.rating}, b50={len(b50.standard) + len(b50.dx)}"

        await run_check(results, "lxns_provider_public", check_lxns_success, allow_fail=True)
    elif not config.lxns_developer_api_key:
        async def check_lxns_auth_error() -> str:
            try:
                await lxns_provider.fetch_player_info_by_qq(args.user_id)
            except PermissionError as exc:
                return f"expected={type(exc).__name__}"
            raise RuntimeError("expected PermissionError when lxns_developer_api_key is missing")

        await run_check(results, "lxns_provider_missing_key", check_lxns_auth_error)
    else:
        results.append(CheckResult("lxns_provider_public", "SKIP", "LXNS_TEST_FRIEND_CODE not provided"))
    await lxns_provider.close()

    if args.arcade_qr_data and config.enable_arcade_provider and config.divingfish_developer_api_key:
        async def check_arcade() -> str:
            provider = MaimaiPyScoreProvider()
            identifier = await provider.get_player_identifier(args.arcade_qr_data)
            return f"identifier_len={len(identifier)}"

        await run_check(results, "arcade_provider", check_arcade, allow_fail=True)
    else:
        results.append(
            CheckResult(
                "arcade_provider",
                "SKIP",
                "enable_arcade_provider disabled or ARCADE_QR_DATA not provided",
            )
        )

    failed = 0
    for item in results:
        print(f"[{item.status}] {item.name}: {item.detail}")
        if item.status == "FAIL":
            failed += 1

    if failed:
        print(f"\nSmoke test finished with {failed} failure(s).")
        return 1

    print("\nSmoke test finished without failures.")
    return 0


async def _check_update_chart() -> str:
    await update_local_chart_file()
    return "music_chart.json updated"


async def _check_update_song_database(session) -> str:
    count = await update_song_database(session)
    return f"updated={count}"


async def _check_update_song_alias_list(session) -> str:
    await update_song_alias_list(session)
    return "alias database updated"


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
