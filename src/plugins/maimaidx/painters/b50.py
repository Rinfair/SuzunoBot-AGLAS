from PIL import ImageDraw

from ..score import PlayerMaiB50, PlayerMaiInfo
from ._base import ScoreBaseImage
from ._config import ACCENT_COLOR, PANEL_BG, PANEL_BORDER, SUBTEXT_COLOR, TEXT_COLOR
from .utils import find_all_clear_rank


class DrawBest(ScoreBaseImage):
    def __init__(self) -> None:
        super().__init__()

    def draw(self, player_info: PlayerMaiInfo, best50: PlayerMaiB50):
        self.reset_im()

        all_clear_rank = find_all_clear_rank(best50.standard + best50.dx)
        self.draw_profile(player_info, all_clear_rank)

        self._rounded_rectangle(
            self._dr,
            (430, 218, 970, 286),
            fill=PANEL_BG,
            outline=PANEL_BORDER,
            width=2,
            radius=26,
        )
        self._sy.draw(700, 244, 26, "Best 50", TEXT_COLOR, "mm")

        sd_rating = sum(score.dx_rating for score in best50.standard)
        dx_rating_sum = sum(score.dx_rating for score in best50.dx)
        self._tb.draw(
            700,
            272,
            18,
            f"B35 {round(sd_rating)} + B15 {round(dx_rating_sum)} = {player_info.rating}",
            ACCENT_COLOR,
            "mm",
        )

        self._sy.draw(120, 220, 20, "Standard 35", SUBTEXT_COLOR, "lm")
        self._sy.draw(120, 1068, 20, "Current Version 15", SUBTEXT_COLOR, "lm")

        self.whiledraw(best50.standard)
        self.whiledraw(best50.dx, 1085)
        self.draw_footer()
        return self._im
