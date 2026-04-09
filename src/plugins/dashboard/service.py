from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import nonebot
import psutil

from .config import config

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TEMPLATE_DIR = BASE_DIR / "templates"
PROJECT_ROOT = BASE_DIR.parents[2]
BOOT_TIMESTAMP = time.time()


class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def load_text(filename: str) -> str:
    return (TEMPLATE_DIR / filename).read_text(encoding="utf-8")


def load_json(filename: str) -> dict[str, Any]:
    return json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))


def format_text(template_text: str, **values: Any) -> str:
    return template_text.format_map(_SafeFormatDict(values))


def render_template(filename: str, **values: Any) -> str:
    return format_text(load_text(filename), **values)


def format_bytes(num_bytes: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num_bytes)
    for unit in units:
        if abs(value) < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"


def format_duration(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours or parts:
        parts.append(f"{hours}h")
    if minutes or parts:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def format_sequence(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, (list, tuple, set)):
        parts = [str(item) if str(item) else "<空前缀>" for item in value]
        return " / ".join(parts) if parts else "-"
    text = str(value)
    return text if text else "<空前缀>"


def now_text() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def boot_time_text() -> str:
    return datetime.fromtimestamp(BOOT_TIMESTAMP).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def _run_git_command(*args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    output = proc.stdout.strip()
    return output or None


def load_project_meta() -> dict[str, Any]:
    return load_json("project.json")


def resolve_project_version(meta: dict[str, Any]) -> str:
    return _run_git_command("describe", "--tags", "--always") or str(meta.get("version_fallback", "unknown"))


def resolve_branch_name() -> str:
    return _run_git_command("rev-parse", "--abbrev-ref", "HEAD") or "unknown"


def resolve_commit_id() -> str:
    return _run_git_command("rev-parse", "--short", "HEAD") or "unknown"


def loaded_plugin_names() -> set[str]:
    return {plugin.name for plugin in nonebot.get_loaded_plugins()}


def list_loaded_plugins() -> list[dict[str, str]]:
    plugins = []
    for plugin in sorted(nonebot.get_loaded_plugins(), key=lambda item: ((item.name or ""), getattr(item, "module_name", ""))):
        module_name = getattr(plugin, "module_name", None)
        if not module_name and getattr(plugin, "module", None):
            module_name = plugin.module.__name__
        plugins.append(
            {
                "name": plugin.name or (module_name or "unknown"),
                "module_name": module_name or "unknown",
            }
        )
    return plugins


def get_feature_flags() -> dict[str, str]:
    flags = {
        "arcade_provider_note": "当前未启用机台源",
        "song_tags_note": "当前未加载标签数据",
        "status_page_note": "当前未配置状态页地址",
    }

    try:
        from src.plugins.maimaidx.config import config as maimai_config

        if maimai_config.enable_arcade_provider:
            flags["arcade_provider_note"] = ""
        if maimai_config.maistatus_url:
            flags["status_page_note"] = ""
    except Exception:
        pass

    try:
        from src.plugins.maimaidx.functions.song_tags import SONG_TAGS_DATA_AVAILABLE

        if SONG_TAGS_DATA_AVAILABLE:
            flags["song_tags_note"] = ""
    except Exception:
        pass

    return flags


def _format_optional_line(label: str, value: str | None) -> str:
    if not value:
        return ""
    return f"\n{label}{value}"


def build_runtime_context() -> dict[str, str]:
    meta = load_project_meta()
    driver = nonebot.get_driver()
    adapters = format_sequence(sorted(nonebot.get_adapters().keys()))
    nicknames = format_sequence(getattr(driver.config, "nickname", None))
    command_start = format_sequence(getattr(driver.config, "command_start", ["", ".", "/"]))
    plugins = list_loaded_plugins()

    return {
        "project_name": str(meta.get("name", "SuzunoBot-AGLAS")),
        "project_description": str(meta.get("description", "-")),
        "project_authors": format_sequence(meta.get("authors", [])),
        "project_repository": str(meta.get("repository", "-")),
        "project_homepage": str(meta.get("homepage", meta.get("repository", "-"))),
        "project_version": resolve_project_version(meta),
        "project_branch": resolve_branch_name(),
        "project_commit": resolve_commit_id(),
        "environment": str(getattr(driver.config, "environment", os.getenv("ENVIRONMENT", "unknown"))),
        "command_start": command_start,
        "nicknames": nicknames,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "hostname": socket.gethostname(),
        "adapters": adapters,
        "plugin_count": str(len(plugins)),
        "boot_time": boot_time_text(),
        "bot_uptime": format_duration(time.time() - BOOT_TIMESTAMP),
        "cwd": str(PROJECT_ROOT),
        "now": now_text(),
    }


def render_about_message() -> str:
    return render_template("about.txt", **build_runtime_context()).strip()


def render_help_message() -> str:
    runtime = build_runtime_context()
    flags = get_feature_flags()
    catalog = load_json("commands.json")
    active_plugins = loaded_plugin_names()

    sections: list[str] = []
    for section in catalog.get("sections", []):
        section_plugin = section.get("plugin")
        if section_plugin and section_plugin not in active_plugins:
            continue

        items: list[str] = []
        for command in section.get("commands", []):
            values = {
                "trigger": format_text(str(command.get("trigger", "")), **runtime, **flags).strip(),
                "usage": format_text(str(command.get("usage", "")), **runtime, **flags).strip(),
                "summary": format_text(str(command.get("summary", "")), **runtime, **flags).strip(),
                "aliases_line": _format_optional_line(
                    "  别名: ",
                    format_text(str(command.get("aliases", "")), **runtime, **flags).strip() or None,
                ),
                "notes_line": _format_optional_line(
                    "  备注: ",
                    format_text(str(command.get("notes", "")), **runtime, **flags).strip() or None,
                ),
            }
            items.append(render_template("help_item.txt", **values).rstrip())

        if not items:
            continue

        sections.append(
            render_template(
                "help_section.txt",
                title=format_text(str(section.get("title", "")), **runtime, **flags).strip(),
                items="\n".join(items).rstrip(),
            ).rstrip()
        )

    return render_template("help.txt", sections="\n\n".join(sections), **runtime).strip()


def render_status_message() -> str:
    runtime = build_runtime_context()
    process = psutil.Process()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(config.dashboard_disk_usage_path)

    try:
        load_avg_raw = os.getloadavg()
        load_average = " / ".join(f"{value:.2f}" for value in load_avg_raw)
    except (AttributeError, OSError):
        load_average = "N/A (当前平台不支持)"

    handle_count_func = getattr(process, "num_handles", None)
    handle_count = str(handle_count_func()) if callable(handle_count_func) else "N/A"

    values = {
        **runtime,
        "system_uptime": format_duration(time.time() - psutil.boot_time()),
        "cpu_percent": f"{psutil.cpu_percent(interval=0.05):.1f}",
        "cpu_count": str(psutil.cpu_count(logical=True) or 0),
        "memory_used": format_bytes(memory.used),
        "memory_total": format_bytes(memory.total),
        "memory_percent": f"{memory.percent:.1f}",
        "disk_path": str(config.dashboard_disk_usage_path),
        "disk_used": format_bytes(disk.used),
        "disk_total": format_bytes(disk.total),
        "disk_percent": f"{disk.percent:.1f}",
        "process_rss": format_bytes(process.memory_info().rss),
        "process_memory_percent": f"{process.memory_percent():.2f}",
        "thread_count": str(process.num_threads()),
        "handle_count": handle_count,
        "pid": str(process.pid),
        "load_average": load_average,
    }
    return render_template("status.txt", **values).strip()


def render_plugins_message() -> str:
    runtime = build_runtime_context()
    plugin_lines = "\n".join(
        render_template("plugin_item.txt", **plugin).rstrip()
        for plugin in list_loaded_plugins()
    )
    return render_template("plugins.txt", plugin_lines=plugin_lines, **runtime).strip()


def render_ping_message(process_ms: float) -> str:
    runtime = build_runtime_context()
    values = {
        **runtime,
        "process_ms": f"{process_ms:.2f}",
        "pid": str(psutil.Process().pid),
    }
    return render_template("ping.txt", **values).strip()
