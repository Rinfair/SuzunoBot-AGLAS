"""
绘图模块
提供生成 Best 50、成绩列表、单曲详情等图片的功能

参考自: - maimaidx_draw (https://github.com/Yuri-YuzuChaN/nonebot-plugin-maimaidx)
"""

from .analysis import draw_player_strength_analysis
from .b50 import DrawBest
from .score import DrawScores
from .song import draw_music_info
from .trend import draw_player_rating_trend
from .utils import image_to_bytes

__all__ = [
    "DrawBest",
    "DrawScores",
    "draw_music_info",
    "image_to_bytes",
    "draw_player_strength_analysis",
    "draw_player_rating_trend",
]
