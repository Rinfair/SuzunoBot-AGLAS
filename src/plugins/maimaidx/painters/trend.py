import os
from datetime import datetime
from tempfile import TemporaryFile
from typing import List, Literal, Optional, Sequence, Tuple

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from ..config import config
from ..score.providers.lxns import LXNSRatingTrend

_DEFAULT_FONT = "SimHei"
plt.rcParams["font.sans-serif"] = [_DEFAULT_FONT]
plt.rcParams["axes.unicode_minus"] = False


def _format_trend_date_labels(dates: Sequence[str]) -> Tuple[List[str], bool]:
    """将日期字符串格式化为更短的刻度标签（优先 %m-%d）。

    返回 (labels, all_parsed_ok)。
    """

    labels: List[str] = []
    ok = True
    for d in dates:
        try:
            dt = datetime.fromisoformat(d.replace("Z", "+00:00"))
            labels.append(dt.strftime("%m-%d"))
        except ValueError:
            ok = False
            labels.append(d)
    return labels, ok


def _parse_trend_dates(dates: Sequence[str]) -> Tuple[List[datetime], bool]:
    """将日期字符串解析为 datetime 列表，用于真实时间轴。"""

    parsed: List[datetime] = []
    ok = True
    for d in dates:
        try:
            parsed.append(datetime.fromisoformat(d.replace("Z", "+00:00")))
        except ValueError:
            ok = False
            # 占位，最终会 fallback 到 index 模式
            parsed.append(datetime.fromtimestamp(0))
    return parsed, ok


def draw_player_rating_trend(
    trends: Sequence[LXNSRatingTrend],
    *,
    title: Optional[str] = None,
    show_standard_dx: bool = True,
    x_axis: Literal["index", "time"] = "time",
) -> Image.Image:
    """绘制玩家 RatingTrend 折线图。

    :param trends: 趋势数据列表（包含 total/standard/dx/date）
    :param title: 图表标题
    :param show_standard_dx: 是否同时绘制 standard/dx 两条分量线
    """

    # 按 date 排序
    sorted_trends = sorted(trends, key=lambda t: str(t.get("date", "")))
    dates = [t["date"] for t in sorted_trends]
    totals = [int(t["total"]) for t in sorted_trends]
    standards = [int(t["standard_total"]) for t in sorted_trends]
    dxs = [int(t["dx_total"]) for t in sorted_trends]

    # x 轴：
    # - index：每条数据等间隔（适合“数据点很多，只看走势”，不会被日期空档拉开）
    # - time：按真实日期间隔（适合“希望空档可见”，但视觉上会出现间距不均）
    x_values: np.ndarray
    labels, _ = _format_trend_date_labels(dates)
    if x_axis == "time":
        parsed_dates, ok = _parse_trend_dates(dates)
        if ok:
            # mdates.date2num -> ndarray[float]，满足类型检查也可用于 fill_between
            x_values = np.asarray(mdates.date2num(parsed_dates), dtype=float)
        else:
            x_values = np.arange(len(sorted_trends), dtype=float)
            x_axis = "index"
    else:
        x_values = np.arange(len(sorted_trends), dtype=float)

    bg_path = config.static_resource_path + "/mai/pic/UI_TTR_BG_Base.png"
    dpi = 150
    bg_size: tuple[int, int] | None = None
    if os.path.exists(bg_path):
        try:
            with Image.open(bg_path) as _bg_probe:
                bg_size = _bg_probe.size
        except Exception:
            bg_size = None

    # 如果有背景图，则让画布尺寸与背景像素尺寸一致，这样不会拉伸背景。
    if bg_size:
        fig = plt.figure(figsize=(bg_size[0] / dpi, bg_size[1] / dpi), dpi=dpi)
    else:
        fig = plt.figure(figsize=(18, 6), dpi=dpi)
    ax = fig.add_subplot(111)

    # 先给一个基础边距；后面会根据 y 轴数值位数自适应加大 left，避免刻度数字被裁剪。
    fig.subplots_adjust(left=0.06, right=0.98, top=0.92, bottom=0.18)

    if title:
        ax.set_title(title, fontsize=18, fontweight="bold", color="#000000", family=_DEFAULT_FONT, pad=14)

    # 颜色与现有 analysis 保持同一套主色
    c_total = "#4ECDC4"
    c_std = "#5B8FF9"
    c_dx = "#F6BD16"

    # y 轴范围：上下留白，避免贴边
    y_min = min(totals + (standards + dxs if show_standard_dx else []))
    y_max = max(totals + (standards + dxs if show_standard_dx else []))
    pad = max(10, int((y_max - y_min) * 0.08))
    y_base = y_min - pad
    ax.set_ylim(y_base, y_max + pad)

    # 不使用 bbox_inches='tight' 保存时，超出画布的 ticklabel 会被裁剪。
    # 这里根据 y 轴数值位数动态加大 left 边距（常见 5 位数时会被截断最后一位）。
    y_digits = max(len(str(abs(int(y_base)))), len(str(abs(int(y_max + pad)))))
    extra_left = max(0.0, (y_digits - 4) * 0.02)
    fig.subplots_adjust(left=min(0.18, 0.06 + extra_left), right=0.98, top=0.92, bottom=0.18)

    # 带填充的折线图：数据多时不绘制端点（无 marker）
    ax.fill_between(x_values, totals, y_base, color=c_total, alpha=0.18, linewidth=0)
    ax.plot(x_values, totals, linewidth=2.2, color=c_total, label="Rating")
    if show_standard_dx:
        ax.fill_between(x_values, standards, y_base, color=c_std, alpha=0.10, linewidth=0)
        ax.plot(x_values, standards, linewidth=1.6, color=c_std, alpha=0.95, label="旧版本铺面")
        ax.fill_between(x_values, dxs, y_base, color=c_dx, alpha=0.10, linewidth=0)
        ax.plot(x_values, dxs, linewidth=1.6, color=c_dx, alpha=0.95, label="新版本铺面")

    ax.grid(True, linestyle="--", alpha=0.28, color="#CCCCCC")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#88CCDD")
    ax.spines["bottom"].set_color("#88CCDD")

    ax.margins(x=0.01)

    # x 轴标签：点数多时稀疏显示，避免挤在一起
    if x_axis == "time":
        # 真实时间轴：交给 AutoDateLocator 控制刻度密度
        try:
            ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=6, maxticks=10))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        except Exception:
            # fallback：仍然手动稀疏刻度
            if len(labels) > 16:
                step = max(1, len(labels) // 10)
                ax.set_xticks(x_values[::step])
                ax.set_xticklabels(labels[::step], rotation=35, ha="right")
            else:
                ax.set_xticks(x_values)
                ax.set_xticklabels(labels, rotation=35, ha="right")
    else:
        if len(labels) > 16:
            step = max(1, len(labels) // 10)
            ax.set_xticks(x_values[::step])
            ax.set_xticklabels(labels[::step], rotation=35, ha="right")
        else:
            ax.set_xticks(x_values)
            ax.set_xticklabels(labels, rotation=35, ha="right")

    ax.tick_params(axis="x", labelsize=11, colors="#444444")
    ax.tick_params(axis="y", labelsize=11, colors="#444444")

    ax.legend(loc="upper left", frameon=True)

    with TemporaryFile("wb+") as temp_file:
        # 不使用 bbox_inches='tight'，避免输出尺寸被裁剪到不等于背景尺寸
        plt.savefig(temp_file, dpi=dpi, transparent=True, bbox_inches=None, pad_inches=0)
        plt.close()

        temp_file.seek(0)
        plot_img = Image.open(temp_file).convert("RGBA")

        # 添加背景
        if os.path.exists(bg_path):
            bg_img = Image.open(bg_path).convert("RGBA")

            # 若 plot 尺寸与背景不一致，则等比缩放 plot 以适配背景。
            if plot_img.size != bg_img.size:
                bw, bh = bg_img.size
                pw, ph = plot_img.size
                scale = min(bw / pw, bh / ph)
                tw = max(1, int(pw * scale))
                th = max(1, int(ph * scale))
                plot_img = plot_img.resize((tw, th))

                canvas = Image.new("RGBA", bg_img.size, (0, 0, 0, 0))
                canvas.alpha_composite(plot_img, ((bw - tw) // 2, (bh - th) // 2))
                plot_img = canvas

            mask = Image.new("RGBA", bg_img.size, (255, 255, 255, 100))
            bg_img = Image.alpha_composite(bg_img, mask)
            final_img = Image.alpha_composite(bg_img, plot_img)
        else:
            final_img = plot_img

    return final_img
