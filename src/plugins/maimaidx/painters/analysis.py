import os
from tempfile import TemporaryFile

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec
from PIL import Image

from ..functions.analysis import PlayerStrength
from .render_core import BOT_LABEL, SIYUAN, build_maimai_background, footer_design


def _load_cjk_font() -> fm.FontProperties | None:
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        str(SIYUAN),
    ]
    for font_path in candidates:
        if not os.path.exists(font_path):
            continue
        try:
            fm.fontManager.addfont(font_path)
            return fm.FontProperties(fname=font_path)
        except Exception:
            continue
    return None


_DEFAULT_FONT_PROP = _load_cjk_font()
_DEFAULT_FONT = _DEFAULT_FONT_PROP.get_name() if _DEFAULT_FONT_PROP else "DejaVu Sans"
_FONT_KWARGS = {"fontfamily": _DEFAULT_FONT}
plt.rcParams["font.sans-serif"] = [_DEFAULT_FONT]
plt.rcParams["font.family"] = [_DEFAULT_FONT]
plt.rcParams["axes.unicode_minus"] = False


def draw_player_strength_analysis(data: PlayerStrength) -> Image.Image:
    fig = plt.figure(figsize=(18, 8))
    gs = GridSpec(3, 3, width_ratios=[1, 0.6, 1], height_ratios=[0.38, 1.0, 1.0], wspace=0.2, hspace=0.0)

    ax1 = fig.add_subplot(gs[:, 0], polar=True)
    ax1.set_title("配置标签统计", fontsize=16, fontweight="bold", color="#000000", fontproperties=_DEFAULT_FONT_PROP, y=1.10)
    categories = list(data.patterns_strengths.keys())
    values = list(data.patterns_strengths.values())
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]
    ax1.plot(angles, values, "o-", color="#7C81FF", linewidth=2.4, label="强度")
    ax1.fill(angles, values, color="#7C81FF", alpha=0.20)
    ax1.set_thetagrids(np.degrees(angles[:-1]), categories, fontsize=10, color="#49454F", **_FONT_KWARGS)
    ax1.set_ylim(0, max(max(values), 1) * 1.1 if values else 1)
    ax1.grid(True, linestyle="--", alpha=0.28, color="#D5D7E3")
    ax1.spines["polar"].set_color("#C7C8D6")
    ax1.tick_params(axis="y", colors="#7A748F")

    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_title("难度标签统计", fontsize=16, fontweight="bold", color="#000000", fontproperties=_DEFAULT_FONT_PROP)
    difficulty_items = sorted(data.difficulty_strengths.items(), key=lambda kv: kv[1], reverse=False)
    labels = [k for k, _ in difficulty_items]
    bars_value = [v for _, v in difficulty_items]
    y_spacing = 0.55 if len(labels) <= 3 else 1.0
    y_pos = np.arange(len(labels)) * y_spacing
    bars = ax2.barh(y_pos, bars_value, color=["#43A047", "#F5A623", "#EF5350", "#7C5CFF", "#D6469A"][: len(labels)], alpha=0.85, height=0.32)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(labels, fontsize=12, color="#49454F", ha="right", fontdict={"family": _DEFAULT_FONT})
    ax2.invert_yaxis()
    if len(labels) > 0:
        ax2.set_ylim(y_pos[0] - y_spacing * 0.6, y_pos[-1] + y_spacing * 0.6)
    max_val = (max(bars_value) * 1.1) if bars_value else 1
    ax2.set_xlim(0, max_val)
    ax2.set_xticks(np.arange(0, int(max_val) + 1, 5))
    ax2.grid(True, axis="x", linestyle="--", alpha=0.28, color="#D5D7E3")
    ax2.tick_params(axis="x", which="both", bottom=False, top=False, labelbottom=False)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.spines["left"].set_color("#C7C8D6")
    ax2.spines["bottom"].set_color("#C7C8D6")
    for bar in bars:
        width = bar.get_width()
        ax2.text(width + 0.5, bar.get_y() + bar.get_height() / 2, str(int(width)), ha="left", va="center", fontsize=12, color="#1D1B20", fontweight="bold")

    ax3 = fig.add_subplot(gs[:, 2], polar=True)
    ax3.set_title("评价标签统计", fontsize=16, fontweight="bold", color="#000000", fontproperties=_DEFAULT_FONT_PROP, y=1.10)
    categories = list(data.song_evaluates.keys())
    values = list(data.song_evaluates.values())
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]
    ax3.plot(angles, values, "o-", color="#D6469A", linewidth=2.4, label="强度")
    ax3.fill(angles, values, color="#D6469A", alpha=0.18)
    ax3.set_thetagrids(np.degrees(angles[:-1]), categories, fontsize=10, color="#49454F", **_FONT_KWARGS)
    ax3.set_ylim(0, max(max(values), 1) * 1.1 if values else 1)
    ax3.grid(True, linestyle="--", alpha=0.28, color="#D5D7E3")
    ax3.spines["polar"].set_color("#C7C8D6")
    ax3.tick_params(axis="y", colors="#7A748F")

    with TemporaryFile("wb+") as temp_file:
        plt.savefig(temp_file, dpi=150, bbox_inches="tight", transparent=True)
        plt.close()

        temp_file.seek(0)
        plot_img = Image.open(temp_file).convert("RGBA")
        bg_img = build_maimai_background(plot_img.width, plot_img.height)
        final_img = Image.alpha_composite(bg_img, plot_img)

    footer_design(final_img, f"Designed by Yuri-YuzuChaN & BlueDeer233. Generated by {BOT_LABEL}", bottom=95, width=min(1000, final_img.width - 80))
    return final_img
