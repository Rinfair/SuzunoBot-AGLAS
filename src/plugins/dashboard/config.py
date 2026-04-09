from pathlib import Path

from nonebot import get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    dashboard_disk_usage_path: str = str(Path(__file__).resolve().parents[3])
    """系统状态命令统计磁盘占用时使用的路径。"""


config = get_plugin_config(Config)
