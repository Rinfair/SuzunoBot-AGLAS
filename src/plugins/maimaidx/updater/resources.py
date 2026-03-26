from functools import partial
from pathlib import Path

from ..browser import get_browser, get_page_semaphore
from ..constants import USER_AGENT

_BASE_RESOURCE_URL = "https://assets2.lxns.net/maimai"


async def download_resource(
    file_id: str, file_type: str, postfix: str = ".png", save_dir: str = "./static/mai/cover"
) -> str:
    """
    下载游戏资源文件

    :param file_id: 资源文件 ID
    :param file_type: 资源文件类型，包括 `icon`, `plate`, `frame`, `jacket`, `music`
    :param postfix: 资源文件后缀，默认为 `.png`
    :param save_dir: 资源文件保存目录，默认为 `./static/mai/cover`
    """
    url = f"{_BASE_RESOURCE_URL}/{file_type}/{file_id}{postfix}"
    save_path = Path(save_dir) / f"{file_id}{postfix}"

    if save_path.exists():
        return str(save_path.resolve())

    page_semaphore = await get_page_semaphore()
    async with page_semaphore:
        browser = await get_browser()
        context = await browser.new_context(
            user_agent=USER_AGENT,
            locale="zh-CN",
            extra_http_headers={
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9",
            },
        )
        try:
            page = await context.new_page()
            resp = await page.goto(url, wait_until="load", timeout=30_000)
            if resp is None:
                raise RuntimeError("下载失败：浏览器未返回响应")
            if resp.status >= 400:
                raise RuntimeError(f"下载失败：HTTP {resp.status}")
            content = await resp.body()
        finally:
            await context.close()

    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(content)
    return str(save_path.resolve())


download_icon = partial(download_resource, file_type="icon", postfix=".png", save_dir="./static/mai/icon")
download_plate = partial(download_resource, file_type="plate", postfix=".png", save_dir="./static/mai/plate")
download_frame = partial(download_resource, file_type="frame", postfix=".png", save_dir="./static/mai/frame")
download_jacket = partial(download_resource, file_type="jacket", postfix=".png", save_dir="./static/mai/cover")
download_music = partial(download_resource, file_type="music", postfix=".mp3", save_dir="./static/mai/music")
