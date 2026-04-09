#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import bot  # noqa: F401
import nonebot

from src.plugins.dashboard.service import (
    DATA_DIR,
    TEMPLATE_DIR,
    render_about_message,
    render_help_message,
    render_ping_message,
    render_plugins_message,
    render_status_message,
)


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
    if "dashboard" not in loaded:
        raise RuntimeError(f"dashboard plugin not found, loaded={loaded}")
    return f"loaded_plugins={len(loaded)}"


def check_template_files() -> str:
    template_files = sorted(path.name for path in TEMPLATE_DIR.glob("*.txt"))
    data_files = sorted(path.name for path in DATA_DIR.glob("*.json"))
    required_templates = {"about.txt", "help.txt", "help_item.txt", "help_section.txt", "ping.txt", "plugins.txt", "plugin_item.txt", "status.txt"}
    required_data = {"commands.json", "project.json"}
    if not required_templates.issubset(template_files):
        raise RuntimeError(f"missing templates: {sorted(required_templates - set(template_files))}")
    if not required_data.issubset(data_files):
        raise RuntimeError(f"missing data files: {sorted(required_data - set(data_files))}")
    return f"templates={len(template_files)}, data_files={len(data_files)}"


def check_about_output() -> str:
    message = render_about_message()
    if "SuzunoBot-AGLAS" not in message or "运行环境:" not in message or "Python:" not in message:
        raise RuntimeError(message)
    return "about template rendered"


def check_help_output() -> str:
    message = render_help_message()
    for expected in ("help / 帮助", "b50", "ba塔罗牌", "系统状态"):
        if expected not in message:
            raise RuntimeError(f"missing {expected} in help output")
    return "help template rendered"


def check_status_output() -> str:
    message = render_status_message()
    for expected in ("CPU:", "内存:", "磁盘[", "负载均值:"):
        if expected not in message:
            raise RuntimeError(f"missing {expected} in status output")
    return "status template rendered"


def check_plugins_output() -> str:
    message = render_plugins_message()
    for expected in ("dashboard", "maimaidx", "batarot"):
        if expected not in message:
            raise RuntimeError(f"missing {expected} in plugins output")
    return "plugins template rendered"


def check_ping_output() -> str:
    message = render_ping_message(12.34)
    if "状态: online" not in message or "12.34 ms" not in message:
        raise RuntimeError(message)
    return "ping template rendered"


if __name__ == "__main__":
    checks = [
        ("plugin_loaded", check_plugin_loaded),
        ("template_files", check_template_files),
        ("about_output", check_about_output),
        ("help_output", check_help_output),
        ("status_output", check_status_output),
        ("plugins_output", check_plugins_output),
        ("ping_output", check_ping_output),
    ]

    failed = 0
    for name, func in checks:
        if not _check(name, func):
            failed += 1

    if failed:
        print(f"\nSmoke test finished with {failed} failure(s).")
        raise SystemExit(1)

    print("\nSmoke test finished without failures.")
