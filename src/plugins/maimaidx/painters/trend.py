import os
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryFile
from typing import List, Literal, Optional, Sequence, Tuple

import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from ..score.providers.lxns import LXNSRatingTrend
from .render_core import BOT_LABEL, SIYUAN, build_maimai_background, footer_design

_DEFAULT_FONT_PROP = None
for font_path in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc", str(SIYUAN)):
    if not Path(font_path).exists():
        continue
    try:
        fm.fontManager.addfont(str(font_path))
        _DEFAULT_FONT_PROP = fm.FontProperties(fname=str(font_path))
        break
    except Exception:
        _DEFAULT_FONT_PROP = None
_DEFAULT_FONT = _DEFAULT_FONT_PROP.get_name() if _DEFAULT_FONT_PROP else "DejaVu Sans"
plt.rcParams["font.sans-serif"] = [_DEFAULT_FONT]
plt.rcParams["font.family"] = [_DEFAULT_FONT]
plt.rcParams["axes.unicode_minus"] = False


def _format_trend_date_labels(dates: Sequence[str]) -> Tuple[List[str], bool]:
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
    parsed: List[datetime] = []
    ok = True
    for d in dates:
        try:
            parsed.append(datetime.fromisoformat(d.replace("Z", "+00:00")))
        except ValueError:
            ok = False
            parsed.append(datetime.fromtimestamp(0))
    return parsed, ok


def draw_player_rating_trend(
    trends: Sequence[LXNSRatingTrend],
    *,
    title: Optional[str] = None,
    show_standard_dx: bool = True,
    x_axis: Literal["index", "time"] = "time",
) -> Image.Image:
    sorted_trends = sorted(trends, key=lambda t: str(t.get("date", "")))
    dates = [t["date"] for t in sorted_trends]
    totals = [int(t["total"]) for t in sorted_trends]
    standards = [int(t["standard_total"]) for t in sorted_trends]
    dxs = [int(t["dx_total"]) for t in sorted_trends]

    x_values: np.ndarray
    labels, _ = _format_trend_date_labels(dates)
    if x_axis == "time":
        parsed_dates, ok = _parse_trend_dates(dates)
        if ok:
            x_values = np.asarray(mdates.date2num(parsed_dates), dtype=float)
        else:
            x_values = np.arange(len(sorted_trends), dtype=float)
            x_axis = "index"
    else:
        x_values = np.arange(len(sorted_trends), dtype=float)

    fig = plt.figure(figsize=(18, 6), dpi=150)
    ax = fig.add_subplot(111)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.18)

    if title:
        ax.set_title(title, fontsize=18, fontweight="bold", color="#000000", fontproperties=_DEFAULT_FONT_PROP, pad=14)

    c_total = "#5865F2"
    c_std = "#43A047"
    c_dx = "#D6469A"
    y_min = min(totals + (standards + dxs if show_standard_dx else []))
    y_max = max(totals + (standards + dxs if show_standard_dx else []))
    pad = max(10, int((y_max - y_min) * 0.08))
    y_base = y_min - pad
    ax.set_ylim(y_base, y_max + pad)

    ax.fill_between(x_values, totals, y_base, color=c_total, alpha=0.18, linewidth=0)
    ax.plot(x_values, totals, linewidth=2.2, color=c_total, label="总 Rating")
    if show_standard_dx:
        ax.fill_between(x_values, standards, y_base, color=c_std, alpha=0.10, linewidth=0)
        ax.plot(x_values, standards, linewidth=1.6, color=c_std, alpha=0.95, label="旧版本谱面")
        ax.fill_between(x_values, dxs, y_base, color=c_dx, alpha=0.10, linewidth=0)
        ax.plot(x_values, dxs, linewidth=1.6, color=c_dx, alpha=0.95, label="新版本谱面")

    ax.grid(True, linestyle="--", alpha=0.28, color="#D5D7E3")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#C7C8D6")
    ax.spines["bottom"].set_color("#C7C8D6")
    ax.margins(x=0.01)

    if x_axis == "time":
        if len(labels) <= 6:
            ax.set_xticks(x_values)
            ax.set_xticklabels(labels, rotation=35, ha="right")
        else:
            try:
                ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=6, maxticks=10))
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
            except Exception:
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

    ax.tick_params(axis="x", labelsize=11, colors="#49454F")
    ax.tick_params(axis="y", labelsize=11, colors="#49454F")
    legend = ax.legend(loc="upper left", frameon=True)
    if _DEFAULT_FONT_PROP is not None:
        for text in legend.get_texts():
            text.set_fontproperties(_DEFAULT_FONT_PROP)

    with TemporaryFile("wb+") as temp_file:
        plt.savefig(temp_file, dpi=150, transparent=True, bbox_inches=None, pad_inches=0)
        plt.close()

        temp_file.seek(0)
        plot_img = Image.open(temp_file).convert("RGBA")
        bg_img = build_maimai_background(plot_img.width, plot_img.height)
        final_img = Image.alpha_composite(bg_img, plot_img)

    footer_design(final_img, f"Designed by Yuri-YuzuChaN & BlueDeer233. Generated by {BOT_LABEL}", bottom=95, width=min(1000, final_img.width - 80))
    return final_img
