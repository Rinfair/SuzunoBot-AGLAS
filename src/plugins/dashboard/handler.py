from __future__ import annotations

import time

from nonebot.matcher import Matcher

from .commands import about_command, help_command, ping_command, plugins_command, status_command
from .service import (
    render_about_message,
    render_help_message,
    render_ping_message,
    render_plugins_message,
    render_status_message,
)


@help_command.handle()
async def handle_help(matcher: Matcher) -> None:
    await matcher.finish(render_help_message())


@about_command.handle()
async def handle_about(matcher: Matcher) -> None:
    await matcher.finish(render_about_message())


@status_command.handle()
async def handle_status(matcher: Matcher) -> None:
    await matcher.finish(render_status_message())


@plugins_command.handle()
async def handle_plugins(matcher: Matcher) -> None:
    await matcher.finish(render_plugins_message())


@ping_command.handle()
async def handle_ping(matcher: Matcher) -> None:
    started = time.perf_counter()
    message = render_ping_message((time.perf_counter() - started) * 1000)
    await matcher.finish(message)
