from __future__ import annotations

import asyncio
from datetime import datetime, time as dt_time, timedelta, timezone

from nonebot import logger
from nonebot_plugin_orm import Model, async_scoped_session, get_scoped_session
from sqlalchemy import Integer, String, select, update
from sqlalchemy.orm import Mapped, mapped_column

# Use a fixed UTC+8 offset so the plugin does not depend on the optional
# `tzdata` package on Windows/Python environments.
RESET_TIMEZONE = timezone(timedelta(hours=8), name="Asia/Shanghai")
RESET_HOUR = 6

_poke_reset_task: asyncio.Task[None] | None = None


class DashboardPokeStat(Model):
    __tablename__ = "dashboard_poke_stat"

    group_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    poke_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cycle_key: Mapped[str] = mapped_column(String, nullable=False, default="")


def current_poke_cycle_key(now: datetime | None = None) -> str:
    if now is None:
        now = datetime.now(RESET_TIMEZONE)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=RESET_TIMEZONE)
    else:
        now = now.astimezone(RESET_TIMEZONE)

    cycle_date = now.date() if now.hour >= RESET_HOUR else now.date() - timedelta(days=1)
    return cycle_date.isoformat()


def seconds_until_next_reset(now: datetime | None = None) -> float:
    if now is None:
        now = datetime.now(RESET_TIMEZONE)
    else:
        now = now.astimezone(RESET_TIMEZONE)

    next_reset = datetime.combine(now.date(), dt_time(hour=RESET_HOUR), tzinfo=RESET_TIMEZONE)
    if now >= next_reset:
        next_reset += timedelta(days=1)
    return max((next_reset - now).total_seconds(), 1.0)


async def ensure_dashboard_database_schema(session: async_scoped_session) -> None:
    async with session.bind.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)


async def increment_poke_count(session: async_scoped_session, group_id: str, user_id: str) -> int:
    cycle_key = current_poke_cycle_key()
    result = await session.execute(
        select(DashboardPokeStat).where(
            DashboardPokeStat.group_id == group_id,
            DashboardPokeStat.user_id == user_id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        record = DashboardPokeStat(group_id=group_id, user_id=user_id, poke_count=1, cycle_key=cycle_key)
        session.add(record)
    else:
        record.poke_count = 1 if record.cycle_key != cycle_key else record.poke_count + 1
        record.cycle_key = cycle_key
        session.add(record)

    await session.commit()
    return record.poke_count


async def get_group_poke_ranking(
    session: async_scoped_session,
    group_id: str,
    limit: int = 10,
) -> list[DashboardPokeStat]:
    cycle_key = current_poke_cycle_key()
    result = await session.execute(
        select(DashboardPokeStat)
        .where(
            DashboardPokeStat.group_id == group_id,
            DashboardPokeStat.cycle_key == cycle_key,
            DashboardPokeStat.poke_count > 0,
        )
        .order_by(DashboardPokeStat.poke_count.desc(), DashboardPokeStat.user_id.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def reset_all_poke_counts(session: async_scoped_session) -> None:
    cycle_key = current_poke_cycle_key()
    await session.execute(update(DashboardPokeStat).values(poke_count=0, cycle_key=cycle_key))
    await session.commit()


async def _poke_reset_loop() -> None:
    try:
        while True:
            delay = seconds_until_next_reset()
            logger.debug(f"dashboard 戳一戳计数器将在 {delay:.0f}s 后执行下一次重置")
            await asyncio.sleep(delay)
            session = get_scoped_session()
            await reset_all_poke_counts(session)
            logger.info("dashboard 戳一戳计数器已按计划重置")
    except asyncio.CancelledError:
        logger.debug("dashboard 戳一戳重置任务已停止")
        raise
    except Exception:
        logger.exception("dashboard 戳一戳重置任务异常退出")


def start_poke_reset_task() -> None:
    global _poke_reset_task
    if _poke_reset_task is not None and not _poke_reset_task.done():
        return
    _poke_reset_task = asyncio.create_task(_poke_reset_loop(), name="dashboard_poke_reset_loop")


def stop_poke_reset_task() -> None:
    global _poke_reset_task
    if _poke_reset_task is None:
        return
    _poke_reset_task.cancel()
    _poke_reset_task = None
