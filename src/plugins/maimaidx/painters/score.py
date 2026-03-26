from __future__ import annotations

from typing import List, Optional

from PIL import Image

from ..functions.recommend_songs import RecommendSong, RecommendSongs
from ..score import PlayerMaiInfo, PlayerMaiScore
from ._base import ScoreBaseImage
from ._config import ACCENT_COLOR, PANEL_BG, PANEL_BORDER, SUBTEXT_COLOR, TEXT_COLOR
from .utils import change_column_width, coloum_width, find_all_clear_rank


class DrawScores(ScoreBaseImage):
    def __init__(self, image: Optional[Image.Image] = None) -> None:
        super().__init__(image)

    def draw_scorelist(
        self, player_info: PlayerMaiInfo, scores: List[PlayerMaiScore], title: str, page: int = 1, page_size: int = 50
    ) -> Image.Image:
        self.reset_im()

        all_clear_rank = find_all_clear_rank(scores)
        self.draw_profile(player_info, all_clear_rank)

        self._rounded_rectangle(
            self._dr,
            (430, 218, 970, 286),
            fill=PANEL_BG,
            outline=PANEL_BORDER,
            width=2,
            radius=26,
        )
        self._sy.draw(700, 242, 26, title, TEXT_COLOR, "mm")

        score_page = scores[(page - 1) * page_size : page * page_size]
        self.whiledraw(score_page, 320)
        self.draw_footer()
        return self._im

    def _draw_rise_card(self, x: int, y: int, data: RecommendSong, min_dx_rating: int) -> None:
        diff_color = self.bg_color[data.level_index]
        self._rounded_rectangle(
            self._dr,
            (x, y, x + 598, y + 124),
            fill=(255, 255, 255, 232),
            outline=diff_color,
            width=3,
            radius=28,
        )

        cover = self._load_cover(data.song_id, (90, 90))
        self._im.alpha_composite(cover, (x + 16, y + 17))
        self._draw_badge(x + 16, y + 98, str(data.song_id), diff_color, width=90)
        self._draw_badge(x + 520, y + 16, data.type.upper(), diff_color, width=58)

        title = data.title
        if coloum_width(title) > 28:
            title = change_column_width(title, 28) + "..."
        self._sy.draw(x + 124, y + 28, 18, title, TEXT_COLOR, "lm")
        self._sy.draw(
            x + 124,
            y + 54,
            14,
            f"Diff {data.difficulty_value:.1f} ({data.difficulty_value_fit:.2f})",
            SUBTEXT_COLOR,
            "lm",
        )

        self._tb.draw(x + 124, y + 86, 20, f"{data.old_achievements:.4f}% -> {data.target_achievements:.4f}%", diff_color, "lm")
        increase_ra = data.target_dx_rating - min_dx_rating
        self._tb.draw(x + 124, y + 108, 15, f"Target Ra {data.target_dx_rating} (+{increase_ra})", ACCENT_COLOR, "lm")

    def draw_rise(self, songs: RecommendSongs, min_dx_rating: int) -> Image.Image:
        self.reset_im()

        self._rounded_rectangle(
            self._dr,
            (66, 32, 642, 104),
            fill=PANEL_BG,
            outline=PANEL_BORDER,
            width=2,
            radius=28,
        )
        self._rounded_rectangle(
            self._dr,
            (758, 32, 1334, 104),
            fill=PANEL_BG,
            outline=PANEL_BORDER,
            width=2,
            radius=28,
        )
        self._sy.draw(354, 68, 28, "Old Version Recommendations", TEXT_COLOR, "mm")
        self._sy.draw(1046, 68, 28, "Current Version Recommendations", TEXT_COLOR, "mm")

        for index, song in enumerate(songs.old_version):
            self._draw_rise_card(46, 136 + index * 142, song, min_dx_rating)
        for index, song in enumerate(songs.new_version):
            self._draw_rise_card(736, 136 + index * 142, song, min_dx_rating)

        self.draw_footer()
        return self._im
