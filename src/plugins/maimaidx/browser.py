from __future__ import annotations

import asyncio

from nonebot import get_driver, logger
from playwright.async_api import async_playwright

_driver = get_driver()

# Lazy singletons for Playwright/Chromium process reuse
_init_lock = asyncio.Lock()
_page_semaphore = asyncio.Semaphore(1)
_playwright = None
_browser = None


async def get_page_semaphore() -> asyncio.Semaphore:
    """Get the shared semaphore guarding Playwright page/context creation."""

    return _page_semaphore


async def get_browser():
    """Get (and lazily initialize) a shared Chromium browser instance."""

    global _playwright, _browser

    async with _init_lock:
        if _browser is not None:
            try:
                if not _browser.is_closed():
                    return _browser
            except Exception:
                _browser = None

        logger.debug("启动 Chromium 浏览器以供 Playwright 使用...")

        if _playwright is None:
            _playwright = await async_playwright().start()

        _browser = await _playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-software-rasterizer",
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-sync",
                "--disable-default-apps",
                "--disable-translate",
                "--disable-features=site-per-process",
                "--disable-features=IsolateOrigins",
                "--no-first-run",
                "--no-zygote",
            ],
        )
        return _browser


async def shutdown_browser() -> None:
    """Close the shared browser and stop Playwright."""

    global _playwright, _browser

    async with _init_lock:
        if _browser is not None:
            try:
                await _browser.close()
            except Exception:
                pass
            _browser = None

        if _playwright is not None:
            try:
                await _playwright.stop()
            except Exception:
                pass
            _playwright = None


@_driver.on_shutdown
async def _on_shutdown() -> None:
    await shutdown_browser()
