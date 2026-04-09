#!/usr/bin/env python3
from __future__ import annotations

import random
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import bot  # noqa: F401
import nonebot

from src.plugins.batarot.service import build_fortune_reply, build_reading_reply, build_spread_reply, build_tarot_reply
from src.plugins.batarot.utils import IMAGE_DIR, load_fortune_descriptions, load_spread_data, load_tarot_data


def _segment_types(message) -> list[str]:
    return [segment.type for segment in message]


def _check(name: str, func) -> bool:
    try:
        detail = func()
    except Exception as exc:
        print(f"[FAIL] {name}: {type(exc).__name__}: {exc}")
        return False

    print(f"[PASS] {name}: {detail}")
    return True


def check_plugin_loaded() -> str:
    loaded = sorted(plugin.name for plugin in nonebot.get_loaded_plugins())
    if "src.plugins.batarot" not in loaded and "batarot" not in loaded:
        raise RuntimeError(f"batarot plugin not found, loaded={loaded}")
    return f"loaded_plugins={len(loaded)}"


def check_data_files() -> str:
    cards, tarot_urls = load_tarot_data()
    spreads = load_spread_data()["formations"]
    fortunes = load_fortune_descriptions()
    missing = [image_name for image_name in tarot_urls.values() if not (IMAGE_DIR / image_name).exists()]
    if len(cards) != 22:
        raise RuntimeError(f"expected 22 cards, got {len(cards)}")
    if missing:
        raise RuntimeError(f"missing images: {missing[:3]}")
    return f"cards={len(cards)}, images={len(tarot_urls)}, spreads={len(spreads)}, fortune_ranges={len(fortunes)}"


def check_tarot_output() -> str:
    message = build_tarot_reply(random.Random(20260408))
    text = str(message)
    if "塔罗牌名称：" not in text or "含义：" not in text:
        raise RuntimeError(f"unexpected text: {text}")
    if "image" not in _segment_types(message):
        raise RuntimeError(f"missing image segment: {_segment_types(message)}")
    return f"segments={_segment_types(message)}"


def check_spread_output() -> str:
    spread_name, messages = build_spread_reply(random.Random(20260408))
    if len(messages) < 2:
        raise RuntimeError("spread output is empty")
    intro = str(messages[0]).strip()
    if spread_name not in intro:
        raise RuntimeError(f"spread intro mismatch: {intro}")
    if not any("image" in _segment_types(message) for message in messages[1:]):
        raise RuntimeError("spread messages missing image segment")
    return f"spread={spread_name}, messages={len(messages)}"


def check_fortune_output() -> str:
    message = build_fortune_reply(random.Random(20260408))
    text = str(message)
    if "今日运势指数：" not in text or "运势解读：" not in text:
        raise RuntimeError(f"unexpected text: {text}")
    return f"segments={_segment_types(message)}"


def check_reading_output() -> str:
    message = build_reading_reply("02")
    text = str(message)
    if "女祭司" not in text or "原作者解读：" not in text:
        raise RuntimeError(f"unexpected text: {text}")
    return f"segments={_segment_types(message)}"


def check_invalid_reading() -> str:
    message = build_reading_reply("不存在的卡牌")
    text = str(message)
    if "未找到指定的塔罗牌" not in text:
        raise RuntimeError(f"unexpected text: {text}")
    return "invalid query handled"


if __name__ == "__main__":
    checks = [
        ("plugin_loaded", check_plugin_loaded),
        ("data_files", check_data_files),
        ("tarot_output", check_tarot_output),
        ("spread_output", check_spread_output),
        ("fortune_output", check_fortune_output),
        ("reading_output", check_reading_output),
        ("invalid_reading", check_invalid_reading),
    ]

    failed = 0
    for name, func in checks:
        if not _check(name, func):
            failed += 1

    if failed:
        print(f"\nSmoke test finished with {failed} failure(s).")
        raise SystemExit(1)

    print("\nSmoke test finished without failures.")
