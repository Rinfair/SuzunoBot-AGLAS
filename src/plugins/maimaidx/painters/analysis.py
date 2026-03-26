import os
from tempfile import TemporaryFile

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec
from PIL import Image

from ..config import config
from ..functions.analysis import PlayerStrength


def _load_cjk_font_from_static() -> str | None:
    """优先从 static 目录加载项目自带字体，保证容器与本地渲染一致。"""
    static_candidates = [
        "ShangguMonoSC-Regular.otf",
        "ResourceHanRoundedCN-Bold.ttf",
    ]
    for filename in static_candidates:
        font_path = os.path.join(config.static_resource_path, filename)
        if not os.path.exists(font_path):
            continue
        try:
            fm.fontManager.addfont(font_path)
            return fm.FontProperties(fname=font_path).get_name()
        except Exception:
            continue
    return None


def _find_cjk_font() -> str:
    """按优先级选取可用的 CJK 字体，兼容 Windows 和 Linux 容器环境。"""
    static_font = _load_cjk_font_from_static()
    if static_font:
        return static_font

    exact_candidates = [
        "SimHei",  # Windows
        "Noto Sans CJK SC",  # Debian/Ubuntu fonts-noto-cjk
        "Noto Sans CJK JP",
        "Noto Sans CJK TC",
        "Noto Sans CJK KR",
        "Noto Sans CJK",
        "Noto Serif CJK SC",
        "Noto Serif CJK JP",
        "WenQuanYi Micro Hei",
        "AR PL UMing CN",
        "Noto Sans CJK",
        "Noto Serif CJK",
        "WenQuanYi",
        "Source Han Sans",
        "Source Han Serif",
    ]

    available = sorted({f.name for f in fm.fontManager.ttflist})

    for font in exact_candidates:
        if font in available:
            return font

    return "DejaVu Sans"  # 最终回退（无 CJK 字形，但不会崩溃）


_DEFAULT_FONT = _find_cjk_font()
_FONT_KWARGS = {"fontfamily": _DEFAULT_FONT}
plt.rcParams["font.sans-serif"] = [_DEFAULT_FONT]
plt.rcParams["font.family"] = [_DEFAULT_FONT]
plt.rcParams["axes.unicode_minus"] = False


def draw_player_strength_analysis(data: PlayerStrength) -> Image.Image:
    fig = plt.figure(figsize=(18, 8))
    # 中间的“难度标签统计”最多 3 项数据；若占满整行高度会显得 y 轴被过度拉伸。
    # 这里用 3x3 网格让中间条形图只占中间一格，左右雷达图占满整列高度。
    gs = GridSpec(
        3,
        3,
        width_ratios=[1, 0.6, 1],
        # 顶行给“难度标签统计”用：压缩高度，避免数据少时显得 y 轴过长、留白过多
        height_ratios=[0.38, 1.0, 1.0],
        wspace=0.2,
        hspace=0.0,
    )

    # 子图1：配置标签统计（雷达图）
    ax1 = fig.add_subplot(gs[:, 0], polar=True)
    ax1.set_title("配置标签统计", fontsize=16, fontweight="bold", color="#000000", family=_DEFAULT_FONT, y=1.10)
    categories = list(data.patterns_strengths.keys())
    values = list(data.patterns_strengths.values())
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    values += values[:1]  # 闭合图形
    angles += angles[:1]

    ax1.plot(angles, values, "o-", color="#4ECDC4", linewidth=2, label="强度")
    ax1.fill(angles, values, color="#4ECDC4", alpha=0.25)
    ax1.set_thetagrids(np.degrees(angles[:-1]), categories, fontsize=10, color="#444444", **_FONT_KWARGS)  # type: ignore  # noqa: E501
    ax1.set_ylim(0, max(values) * 1.1 if values else 1)
    ax1.grid(True, linestyle="--", alpha=0.3, color="#CCCCCC")
    ax1.spines["polar"].set_color("#88CCDD")
    ax1.tick_params(axis="y", colors="#88CCDD")

    # 子图2：难度标签统计（水平条形图）
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_title("难度标签统计", fontsize=16, fontweight="bold", color="#000000", family=_DEFAULT_FONT)

    # 按值降序显示：高值在上、低值在下
    difficulty_items = sorted(data.difficulty_strengths.items(), key=lambda kv: kv[1], reverse=False)
    labels = [k for k, _ in difficulty_items]
    values = [v for _, v in difficulty_items]
    n_labels = len(labels)
    y_spacing = 0.55 if n_labels <= 3 else 1.0
    y_pos = np.arange(n_labels) * y_spacing

    bars = ax2.barh(y_pos, values, color="#4ECDC4", alpha=0.8, height=0.32)

    # 设置 y 轴刻度和标签
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(
        labels,
        fontsize=12,
        color="#444444",
        ha="right",
        fontdict={"family": _DEFAULT_FONT},
    )

    # 让第一项（最大值）显示在最上方
    ax2.invert_yaxis()

    if n_labels > 0:
        ax2.set_ylim(y_pos[0] - y_spacing * 0.6, y_pos[-1] + y_spacing * 0.6)

    # 设置 x 轴范围，避免过长
    max_val = (max(values) * 1.1) if values else 1
    ax2.set_xlim(0, max_val)
    ax2.set_xticks(np.arange(0, int(max_val) + 1, 5))  # 每 5 一个刻度（用于网格定位）
    ax2.grid(True, axis="x", linestyle="--", alpha=0.3, color="#CCCCCC")
    # 去除 x 轴刻度线和刻度文本（保留网格线）
    ax2.tick_params(axis="x", which="both", bottom=False, top=False, labelbottom=False)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.spines["left"].set_color("#88CCDD")
    ax2.spines["bottom"].set_color("#88CCDD")

    # 在条形图上标注数值
    for i, bar in enumerate(bars):
        width = bar.get_width()
        ax2.text(
            width + 0.5,
            bar.get_y() + bar.get_height() / 2,
            str(int(width)),
            ha="left",
            va="center",
            fontsize=12,
            color="#000000",
            fontweight="bold",
        )

    # 子图3：评价标签统计（雷达图）
    ax3 = fig.add_subplot(gs[:, 2], polar=True)
    ax3.set_title("评价标签统计", fontsize=16, fontweight="bold", color="#000000", family=_DEFAULT_FONT, y=1.10)
    categories = list(data.song_evaluates.keys())
    values = list(data.song_evaluates.values())
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]

    ax3.plot(angles, values, "o-", color="#4ECDC4", linewidth=2, label="强度")
    ax3.fill(angles, values, color="#4ECDC4", alpha=0.25)
    ax3.set_thetagrids(np.degrees(angles[:-1]), categories, fontsize=10, color="#444444", **_FONT_KWARGS)  # type: ignore # noqa: E501
    ax3.set_ylim(0, max(values) * 1.1 if values else 1)
    ax3.grid(True, linestyle="--", alpha=0.3, color="#CCCCCC")
    ax3.spines["polar"].set_color("#88CCDD")
    ax3.tick_params(axis="y", colors="#88CCDD")

    # plt.tight_layout()

    # 保存为临时PNG
    with TemporaryFile("wb+") as temp_file:
        plt.savefig(temp_file, dpi=150, bbox_inches="tight", transparent=True)
        plt.close()

        temp_file.seek(0)
        plot_img = Image.open(temp_file).convert("RGBA")

        # 添加背景
        bg_path = config.static_resource_path + "/mai/pic/UI_TTR_BG_Base.png"
        if os.path.exists(bg_path):
            bg_img = Image.open(bg_path).convert("RGBA")
            # 缩放背景以适应图片大小
            bg_img = bg_img.resize(plot_img.size)

            # 添加颜色遮罩
            mask = Image.new("RGBA", plot_img.size, (255, 255, 255, 100))
            bg_img = Image.alpha_composite(bg_img, mask)

            # 合并图片
            final_img = Image.alpha_composite(bg_img, plot_img)
        else:
            final_img = plot_img

    return final_img
