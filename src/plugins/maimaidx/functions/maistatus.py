from __future__ import annotations

from typing import TypedDict

from ..browser import get_browser, get_page_semaphore


class Viewport(TypedDict):
    width: int
    height: int


async def capture_webpage_png(
    url: str,
    *,
    viewport: Viewport = Viewport(width=1400, height=900),
    full_page: bool = True,
    timeout_ms: int = 30_000,
    wait_ms: int = 500,
) -> bytes:
    """Capture a webpage screenshot as PNG bytes.

    Notes:
        - This relies on Playwright + Chromium.
        - If you see errors about missing browser executables, run:
          `python -m playwright install chromium`
    """
    if not url.startswith("http://") and not url.startswith("https://"):
        raise ValueError("url 必须以 http:// 或 https:// 开头")

    page_semaphore = await get_page_semaphore()
    async with page_semaphore:
        browser = await get_browser()
        context = await browser.new_context(viewport=viewport)
        try:
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            if wait_ms > 0:
                await page.wait_for_timeout(wait_ms)
            return await page.screenshot(
                type="png",
                full_page=full_page,
                clip=(
                    None
                    if full_page
                    else {
                        "x": 0,
                        "y": 0,
                        "width": viewport["width"],
                        "height": viewport["height"],
                    }
                ),
            )
        finally:
            await context.close()


async def capture_maimai_status_png(maimai_status_url: str) -> bytes:
    """Capture maimai status page screenshot."""

    return await capture_webpage_png(
        maimai_status_url,
        viewport={"width": 1200, "height": 850},
        full_page=False,
        timeout_ms=20_000,
        wait_ms=800,
    )
