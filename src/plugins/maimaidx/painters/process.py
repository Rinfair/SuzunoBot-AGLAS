from io import BytesIO
from typing import List, Tuple, Union

from PIL import Image, ImageDraw, ImageFont

from ..functions.process import LevelProcessData, PlateProcessData, UnfinishedSong
from ._config import FONT_MAIN

# Mapping for difficulties names
DIFF_NAMES = ["Basic", "Advanced", "Expert", "Master", "Re:Master"]


class ProcessPainter:
    def __init__(self, data: Union[PlateProcessData, LevelProcessData]):
        self.data = data
        self.font_size = 20
        self.font = ImageFont.truetype(str(FONT_MAIN), self.font_size)
        self.padding = 20
        self.line_spacing = 6
        self.bg_color = (255, 255, 255)
        self.text_color = (0, 0, 0)
        self.id_color = (70, 70, 200)  # Blueish for ID

    def draw_plate(self, use_difficult: bool = False) -> BytesIO:
        if not isinstance(self.data, PlateProcessData):
            raise ValueError("Data must be PlateProcessData")

        lines = []
        d = self.data

        # Header
        lines.append((f"{d.ver_name}{d.plan} 剩余进度", True))  # Title

        # Difficult mode (filtering for High Level songs)
        if use_difficult:
            # List only difficult songs
            for item in d.difficult_left:
                line_str = self._format_song(item)
                lines.append((line_str, False))

            lines.append((f"剩余合计 {len(d.difficult_left)} 首", False))

        else:
            # Summary mode or Full List if short
            # Logic: If > 60 total, just show summary counts per difficulty
            if d.total_left > 60:
                # Summary
                lists = [d.basic_left, d.advanced_left, d.expert_left, d.master_left, d.remaster_left]
                for i, l in enumerate(lists):
                    if l:
                        lines.append((f"{DIFF_NAMES[i]} 剩余 {len(l)} 首", False))
                lines.append((f"剩余合计 {d.total_left} 首", False))
            else:
                # Full List by difficulty
                lists = [d.basic_left, d.advanced_left, d.expert_left, d.master_left, d.remaster_left]
                for i, l in enumerate(lists):
                    if not l:
                        continue
                    # Header for diff? No, just list them?
                    # Original code: "DiffName Remaining X" then list?
                    # Original code loops and prints.
                    for item in l:
                        line_str = self._format_song(item)
                        lines.append((line_str, False))
                lines.append((f"剩余合计 {d.total_left} 首", False))

        return self._render(lines)

    def draw_level(self) -> BytesIO:
        if not isinstance(self.data, LevelProcessData):
            raise ValueError("Data must be LevelProcessData")

        lines = []
        d = self.data

        # Header
        lines.append((f"{d.level} {d.plan} 进度", True))

        # Stats
        stats = (
            f"总计: {d.counts['total']}  完成: {d.counts['completed']}  "
            f"剩余: {d.counts['unfinished']}  未玩: {d.counts['not_played']}"
        )
        lines.append((stats, False))
        lines.append(("", False))  # Spacer

        # List Unfinished + Not Played
        # Limit length? Older plugin usually lists them.
        # Check count. If > 50?
        # Sort by ID?
        # d.unfinished is (Song, Score, DiffIdx)
        # d.not_played is (Song, DiffIdx)

        # We want to display them.
        # Just mix them?

        # Let's list unfinished (partial score) first
        if d.unfinished:
            lines.append(("--- 未达标 ---", False))
            for s, sc, idx in d.unfinished:
                if sc is None:
                    continue

                status = f"{sc.achievements:.4f}%"
                if sc.fc:
                    status += f" {sc.fc}"
                if sc.fs:
                    status += f" {sc.fs}"
                line = f"No.{s.id} [{DIFF_NAMES[idx]}] {s.title} {status}"
                lines.append((line, False))

        if d.not_played:
            lines.append(("--- 未游玩 ---", False))
            for s, idx in d.not_played:
                line = f"No.{s.id} [{DIFF_NAMES[idx]}] {s.title}"
                lines.append((line, False))

        if not d.unfinished and not d.not_played:
            lines.append(("恭喜！全部达成！", True))

        return self._render(lines)

    def _format_song(self, item: UnfinishedSong) -> str:
        # Format: No.123 [Master] Title Status
        # Original: No.01 123456 [Master] 13.5 Title Status
        s = item.song
        return f"No.{s.id} [{DIFF_NAMES[item.difficulty]}] {item.level_value} {s.title} {item.status}"

    def _render(self, lines: List[Tuple[str, bool]]) -> BytesIO:
        # Calculate size
        max_width: int = 0
        total_height: int = self.padding * 2

        # Font instances
        font_reg = self.font
        # Make a bold title font?
        font_bold = ImageFont.truetype(str(FONT_MAIN), int(self.font_size * 1.5))

        processed_lines = []

        draw_temp = ImageDraw.Draw(Image.new("RGB", (1, 1)))

        for text, is_title in lines:
            f = font_bold if is_title else font_reg
            bbox = draw_temp.textbbox((0, 0), text, font=f)
            w = int(bbox[2] - bbox[0])
            h = int(bbox[3] - bbox[1])
            # Add some vertical spacing
            h += self.line_spacing
            if is_title:
                h += 10

            max_width = max(max_width, w)
            total_height += h
            processed_lines.append((text, f, h))

        width = int(max_width + self.padding * 2)
        height = int(total_height)

        img = Image.new("RGB", (width, height), self.bg_color)
        draw = ImageDraw.Draw(img)

        y = self.padding
        for text, f, h_inc in processed_lines:
            draw.text((self.padding, y), text, font=f, fill=self.text_color)
            y += h_inc

        bio = BytesIO()
        img.save(bio, format="PNG")
        bio.seek(0)
        return bio
